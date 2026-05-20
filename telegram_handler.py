import logging

from telegram import Message, Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

import conversation
import db
from agents.negotiator import continue_negotiation, write_opening_message
from agents.pricer import estimate_price
from config import settings
from conversation import Turn, state

logger = logging.getLogger(__name__)


async def _run_pricer(message: Message) -> None:
    car_request_id = db.save_car_request(
        telegram_message_id=message.message_id,
        chat_id=message.chat_id,
        user_id=message.from_user.id,
        description=message.text,
    )

    estimate = estimate_price(state.description)

    estimate_id = db.save_estimate(
        car_request_id=car_request_id,
        status=estimate.status,
        low_price=estimate.low_price,
        high_price=estimate.high_price,
        currency=estimate.currency,
        reasoning=estimate.reasoning,
        raw_response=estimate.raw_response,
    )

    if estimate.status == "insufficient_info":
        state.phase = "awaiting_info"
        await message.reply_text(estimate.clarifying_question)
        logger.info("Posted clarifying question; phase=awaiting_info")
        return

    state.estimate = estimate
    state.estimate_id = estimate_id
    state.phase = "negotiating"

    opening = write_opening_message(state.description, estimate)
    db.save_negotiation(estimate_id=estimate_id, opening_message=opening)
    state.history.append(Turn(speaker="buyer", text=opening))

    await message.reply_text(opening)
    logger.info("Posted opening message; phase=negotiating")


async def _run_negotiation_turn(message: Message) -> None:
    seller_text = message.text
    state.history.append(Turn(speaker="seller", text=seller_text))

    turn = continue_negotiation(state, seller_text)
    state.history.append(Turn(speaker="buyer", text=turn.message))

    await message.reply_text(turn.message)
    logger.info("Posted negotiation turn; status=%s", turn.status)

    if turn.status in ("deal_agreed", "walk_away"):
        logger.info("Negotiation ended with status=%s; resetting state", turn.status)
        conversation.reset()


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None or message.text is None:
        return

    if message.chat_id != settings.TELEGRAM_CHAT_ID:
        return

    logger.info(
        "Received message in phase=%s from user %s: %s",
        state.phase,
        message.from_user.id,
        message.text[:80],
    )

    try:
        if state.phase == "idle":
            state.description = message.text
            await _run_pricer(message)

        elif state.phase == "awaiting_info":
            state.description = f"{state.description}\n{message.text}"
            await _run_pricer(message)

        elif state.phase == "negotiating":
            await _run_negotiation_turn(message)

    except Exception:
        logger.exception("Error processing message in phase=%s", state.phase)


def build_application() -> Application:
    app = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )
    return app
