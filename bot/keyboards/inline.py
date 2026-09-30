"""Inline keyboards for clarifying drink parameters."""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from typing import Optional


def get_volume_clarification_keyboard(drink_name: str, abv: Optional[float] = None) -> InlineKeyboardMarkup:
    """Build keyboard for choosing drink volume."""
    builder = InlineKeyboardBuilder()
    
    # Context-specific quick buttons
    name_lower = drink_name.lower()
    if any(k in name_lower for k in ["пиво", "сидр", "эль", "лагер"]):
        builder.row(
            InlineKeyboardButton(text="🍺 0.33 л", callback_data=f"vol:330:{drink_name}"),
            InlineKeyboardButton(text="🍺 0.45 л (банка)", callback_data=f"vol:450:{drink_name}"),
            InlineKeyboardButton(text="🍺 0.5 л", callback_data=f"vol:500:{drink_name}"),
        )
        builder.row(
            InlineKeyboardButton(text="🍺 1.0 л", callback_data=f"vol:1000:{drink_name}"),
            InlineKeyboardButton(text="🍺 1.5 л", callback_data=f"vol:1500:{drink_name}"),
            InlineKeyboardButton(text="🍺 2.0 л", callback_data=f"vol:2000:{drink_name}"),
        )
    elif any(k in name_lower for k in ["вино", "шампанское", "просекко"]):
        builder.row(
            InlineKeyboardButton(text="🍷 125 мл", callback_data=f"vol:125:{drink_name}"),
            InlineKeyboardButton(text="🍷 150 мл (бокал)", callback_data=f"vol:150:{drink_name}"),
            InlineKeyboardButton(text="🍷 200 мл", callback_data=f"vol:200:{drink_name}"),
        )
        builder.row(
            InlineKeyboardButton(text="🍾 750 мл (бутылка)", callback_data=f"vol:750:{drink_name}"),
            InlineKeyboardButton(text="🍾 1.0 л", callback_data=f"vol:1000:{drink_name}"),
        )
    elif any(k in name_lower for k in ["водка", "коньяк", "виски", "текила", "ром", "джин", "самогон"]):
        builder.row(
            InlineKeyboardButton(text="🥃 40 мл", callback_data=f"vol:40:{drink_name}"),
            InlineKeyboardButton(text="🥃 50 мл (шот)", callback_data=f"vol:50:{drink_name}"),
            InlineKeyboardButton(text="🥃 100 мл", callback_data=f"vol:100:{drink_name}"),
        )
        builder.row(
            InlineKeyboardButton(text="🍾 250 мл (чекушка)", callback_data=f"vol:250:{drink_name}"),
            InlineKeyboardButton(text="🍾 500 мл (бутылка)", callback_data=f"vol:500:{drink_name}"),
            InlineKeyboardButton(text="🍾 700 мл", callback_data=f"vol:700:{drink_name}"),
        )
    else:
        # General options
        builder.row(
            InlineKeyboardButton(text="🥃 50 мл", callback_data=f"vol:50:{drink_name}"),
            InlineKeyboardButton(text="🍷 150 мл", callback_data=f"vol:150:{drink_name}"),
            InlineKeyboardButton(text="🍺 500 мл", callback_data=f"vol:500:{drink_name}"),
        )
        builder.row(
            InlineKeyboardButton(text="🍾 750 мл", callback_data=f"vol:750:{drink_name}"),
            InlineKeyboardButton(text="🍼 1000 мл", callback_data=f"vol:1000:{drink_name}"),
        )

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_clarification")
    )
    return builder.as_markup()


def get_abv_clarification_keyboard(volume_ml: float, drink_name: str) -> InlineKeyboardMarkup:
    """Build keyboard for choosing drink ABV percentage."""
    builder = InlineKeyboardBuilder()

    name_lower = drink_name.lower()
    if any(k in name_lower for k in ["пиво", "сидр", "эль"]):
        builder.row(
            InlineKeyboardButton(text="🍺 4.0%", callback_data=f"abv:4.0:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍺 4.5%", callback_data=f"abv:4.5:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍺 5.0%", callback_data=f"abv:5.0:{volume_ml}:{drink_name}"),
        )
        builder.row(
            InlineKeyboardButton(text="🍺 6.0%", callback_data=f"abv:6.0:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍺 7.5%", callback_data=f"abv:7.5:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍺 8.5% (крепкое)", callback_data=f"abv:8.5:{volume_ml}:{drink_name}"),
        )
    elif any(k in name_lower for k in ["вино", "шампанское"]):
        builder.row(
            InlineKeyboardButton(text="🍷 10.5%", callback_data=f"abv:10.5:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍷 11.5%", callback_data=f"abv:11.5:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍷 12.5%", callback_data=f"abv:12.5:{volume_ml}:{drink_name}"),
        )
        builder.row(
            InlineKeyboardButton(text="🍷 13.5%", callback_data=f"abv:13.5:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍷 14.5%", callback_data=f"abv:14.5:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍷 18.0% (крепленое)", callback_data=f"abv:18.0:{volume_ml}:{drink_name}"),
        )
    else:
        builder.row(
            InlineKeyboardButton(text="🍸 5.0%", callback_data=f"abv:5.0:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🍷 12.0%", callback_data=f"abv:12.0:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🧪 20.0%", callback_data=f"abv:20.0:{volume_ml}:{drink_name}"),
        )
        builder.row(
            InlineKeyboardButton(text="🥃 35.0%", callback_data=f"abv:35.0:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🥃 40.0%", callback_data=f"abv:40.0:{volume_ml}:{drink_name}"),
            InlineKeyboardButton(text="🔥 50.0%", callback_data=f"abv:50.0:{volume_ml}:{drink_name}"),
        )

    builder.row(
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_clarification")
    )
    return builder.as_markup()

