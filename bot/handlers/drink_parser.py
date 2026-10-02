"""Handler for natural text drink logging, clarification keyboards, and /drink command."""
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from bot.database.db import Database
from bot.config import settings
from bot.services.calculator import calculate_vodka_equivalent, get_default_abv_for_drink
from bot.services.parser import parse_natural_drink_text
from bot.services.phrases import (
    get_random_drink_comment,
    get_random_winner_drink_roast
)
from bot.keyboards.inline import (
    get_volume_clarification_keyboard,
    get_abv_clarification_keyboard
)
from bot.services.classifier import classify_drink, calculate_pure_alcohol_grams

logger = logging.getLogger(__name__)
router = Router(name="drink_parser")


async def record_and_notify_drink(
    message: types.Message,
    db: Database,
    user: types.User,
    drink_name: str,
    volume_ml: float,
    abv: float,
    is_callback: bool = False
):
    """Save drink to database and send confirmation response."""
    vodka_ml = calculate_vodka_equivalent(volume_ml, abv)

    # Save to database
    await db.upsert_user(
        user_id=user.id,
        chat_id=message.chat.id,
        username=user.username,
        full_name=user.full_name
    )

    drink_id = await db.add_drink(
        user_id=user.id,
        chat_id=message.chat.id,
        drink_name=drink_name,
        volume_ml=volume_ml,
        abv=abv,
        vodka_equiv_ml=vodka_ml
    )

    category = classify_drink(drink_name, abv)
    pure_alcohol_g = calculate_pure_alcohol_grams(volume_ml, abv)
    await db.add_drink_detail(
        drink_id=drink_id,
        category=category,
        brand=drink_name,
        pure_alcohol_g=pure_alcohol_g
    )

    # Check if this user is the active monthly champion
    active_winner = await db.get_active_monthly_winner(message.chat.id)
    is_active_winner = bool(active_winner and active_winner.get("user_id") == user.id)

    stats = await db.get_user_stats(user.id, message.chat.id)

    name_mention = f"@{user.username}" if user.username else user.full_name

    text = (
        f"🍻 **Записано для {name_mention}:**\n"
        f"• Напиток: **{drink_name.capitalize()}**\n"
        f"• Объём: **{volume_ml:.0f} мл** (крепость **{abv:.1f}%**)\n"
        f"• Водочный эквивалент: **{vodka_ml} мл водки** (40%)\n\n"
        f"📈 **Сегодня:** {stats['today_vodka']} мл | **За неделю:** {stats['week_vodka']} мл водки\n"
    )

    if is_active_winner:
        roast = get_random_winner_drink_roast()
        text += f"\n💀 **АЛКОБАРОН МЕСЯЦА НА СВЯЗИ:**\n_{roast}_"
    else:
        comment = get_random_drink_comment()
        text += f"\n_{comment}_"

    if is_callback:
        await message.edit_text(text, parse_mode="Markdown")
    else:
        await message.reply(text, parse_mode="Markdown")


@router.message(Command("drink", "выпил"))
async def cmd_drink(message: types.Message, db: Database):
    """Direct manual drink logging via command: /drink <volume_ml> <abv> [name]."""
    if not message.from_user:
        return

    parts = message.text.split(maxsplit=3)[1:]
    if len(parts) < 2:
        await message.reply(
            "ℹ️ **Формат команды:**\n`/drink [объем мл] [градус %] [название]`\n\n"
            "Пример:\n`/drink 500 5 пиво`\n`/drink 100 40 водка`",
            parse_mode="Markdown"
        )
        return

    try:
        volume_ml = float(parts[0].replace(",", "."))
        abv = float(parts[1].replace(",", ".").replace("%", ""))
        drink_name = parts[2] if len(parts) > 2 else "алкоголь"

        await record_and_notify_drink(
            message=message,
            db=db,
            user=message.from_user,
            drink_name=drink_name,
            volume_ml=volume_ml,
            abv=abv
        )
    except ValueError:
        await message.reply("⚠️ Не удалось распознать числа. Пример: `/drink 500 5 пиво`", parse_mode="Markdown")


@router.message(Command("cancel", "отмена"))
async def cmd_cancel(message: types.Message, db: Database):
    """Undo the user's most recent drink log in this chat."""
    if not message.from_user:
        return

    deleted = await db.delete_last_drink(message.from_user.id, message.chat.id)
    if not deleted:
        await message.reply("🤷‍♂️ У вас нет недавних записей для отмены.")
        return

    await message.reply(
        f"🗑 **Отменено:** {deleted['drink_name']} ({deleted['volume_ml']} мл, {deleted['vodka_equiv_ml']} мл водки).\n"
        "Запись удалена из базы данных.",
        parse_mode="Markdown"
    )


@router.callback_query(F.data.startswith("vol:"))
async def callback_volume_selected(callback: types.CallbackQuery, db: Database):
    """Handle volume button click."""
    callback_message = callback.message
    if not isinstance(callback_message, types.Message):
        await callback.answer("Кнопка больше недоступна.")
        return
    if not await db.get_auto_detect_drinks(
        callback_message.chat.id,
        default=settings.auto_detect_drinks
    ):
        await callback.answer("Автораспознавание выключено.")
        return

    parts = callback.data.split(":")
    volume_ml = float(parts[1])
    drink_name = parts[2]

    # Check if ABV is known
    abv = get_default_abv_for_drink(drink_name)
    if abv is not None:
        await record_and_notify_drink(
            message=callback_message,
            db=db,
            user=callback.from_user,
            drink_name=drink_name,
            volume_ml=volume_ml,
            abv=abv,
            is_callback=True
        )
    else:
        # Ask for ABV
        kb = get_abv_clarification_keyboard(volume_ml, drink_name)
        await callback_message.edit_text(
            f"👌 Объём: **{volume_ml:.0f} мл** ({drink_name}).\n"
            f"Теперь выберите крепость напитка (ABV %):",
            reply_markup=kb,
            parse_mode="Markdown"
        )
    await callback.answer()


@router.callback_query(F.data.startswith("abv:"))
async def callback_abv_selected(callback: types.CallbackQuery, db: Database):
    """Handle ABV button click."""
    callback_message = callback.message
    if not isinstance(callback_message, types.Message):
        await callback.answer("Кнопка больше недоступна.")
        return
    if not await db.get_auto_detect_drinks(
        callback_message.chat.id,
        default=settings.auto_detect_drinks
    ):
        await callback.answer("Автораспознавание выключено.")
        return

    parts = callback.data.split(":")
    abv = float(parts[1])
    volume_ml = float(parts[2])
    drink_name = parts[3]

    await record_and_notify_drink(
        message=callback_message,
        db=db,
        user=callback.from_user,
        drink_name=drink_name,
        volume_ml=volume_ml,
        abv=abv,
        is_callback=True
    )
    await callback.answer()


@router.callback_query(F.data == "cancel_clarification")
async def callback_cancel(callback: types.CallbackQuery):
    """Cancel clarification dialog."""
    await callback.message.delete()
    await callback.answer("Отменено")


@router.message(F.text)
async def process_natural_text(message: types.Message, db: Database):
    """Parse incoming text messages for natural drinking reports."""
    if not settings.auto_detect_drinks:
        return

    if not message.text or not message.from_user:
        return
    if not await db.get_auto_detect_drinks(
        message.chat.id,
        default=settings.auto_detect_drinks
    ):
        return

    # Skip commands
    if message.text.startswith("/"):
        return

    parsed = parse_natural_drink_text(message.text)
    if not parsed.is_drinking_intent:
        # Not a drink log -> pass through to roaster or ignore
        return

    # If volume is missing, ask for it
    if parsed.needs_volume_clarification:
        kb = get_volume_clarification_keyboard(parsed.drink_name, parsed.abv)
        await message.reply(
            f"🍻 Вы упомянули **{parsed.drink_name}**, но я не понял точный объём.\n"
            f"Сколько выпили?",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return

    # If volume is known, but ABV is missing and not defaultable
    if parsed.needs_abv_clarification:
        kb = get_abv_clarification_keyboard(parsed.volume_ml, parsed.drink_name)
        await message.reply(
            f"🧪 Объём понятен: **{parsed.volume_ml:.0f} мл** ({parsed.drink_name}).\n"
            f"Какая крепость (градус) у этого напитка?",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        return

    # All data available -> record immediately
    await record_and_notify_drink(
        message=message,
        db=db,
        user=message.from_user,
        drink_name=parsed.drink_name,
        volume_ml=parsed.volume_ml,
        abv=parsed.abv
    )

