from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config import SUPPORT_URL, CHANNEL_URL, TASKS_URL


COUNTRIES = {
    "MX": ("🇲🇽 México", "MXN", 17.00),
    "EC": ("🇪🇨 Ecuador", "USD", 1.00),
    "CO": ("🇨🇴 Colombia", "COP", 4000.00),
    "PE": ("🇵🇪 Perú", "PEN", 3.70),
    "CL": ("🇨🇱 Chile", "CLP", 930.00),
    "AR": ("🇦🇷 Argentina", "ARS", 900.00),
    "US": ("🇺🇸 Estados Unidos", "USD", 1.00),
}


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Ganar Diamantes", callback_data="earn_diamonds")],
        [
            InlineKeyboardButton("🛍️ Tienda", callback_data="shop"),
            InlineKeyboardButton("💳 Saldo", callback_data="recharge")
        ],
        [
            InlineKeyboardButton("🎟️ Cupón", callback_data="coupon"),
            InlineKeyboardButton("📦 Compras", callback_data="purchases")
        ],
        [InlineKeyboardButton("👤 Mi cuenta", callback_data="profile")],
        [
            InlineKeyboardButton("💬 Soporte", url=SUPPORT_URL),
            InlineKeyboardButton("📢 Canal", url=CHANNEL_URL)
        ],
    ])


def countries_menu():
    rows = []

    for code, data in COUNTRIES.items():
        country_name = data[0]
        rows.append([
            InlineKeyboardButton(country_name, callback_data=f"recharge_country:{code}")
        ])

    rows.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu")])
    return InlineKeyboardMarkup(rows)


def recharge_methods_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🅿️ PayPal", callback_data="recharge_method:paypal")],
        [InlineKeyboardButton("💎 Diamantes", callback_data="recharge_method:diamonds")],
        [InlineKeyboardButton("🏦 Transferencia", callback_data="recharge_method:transfer")],
        [InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu")]
    ])


def recharge_back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Recargar saldo", callback_data="recharge")],
        [InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu")]
    ])


def back_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu")]
    ])


def products_menu(products):
    rows = []

    for product_id, name, price, available in products:
        stock = f"✅ {available} disponibles" if available > 0 else "❌ Agotado"

        rows.append([
            InlineKeyboardButton(
                f"🛒 {name}  •  ${price:.2f}  •  {stock}",
                callback_data=f"buy:{product_id}"
            )
        ])

    rows.append([InlineKeyboardButton("💳 Recargar saldo", callback_data="recharge")])
    rows.append([InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu")])

    return InlineKeyboardMarkup(rows)


def earn_diamonds_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Ganar diamantes", url=TASKS_URL)],
        [InlineKeyboardButton("👥 Invitar amigos", callback_data="profile")],
        [InlineKeyboardButton("🎟️ Canjear código", callback_data="coupon")],
        [InlineKeyboardButton("🏠 Volver al inicio", callback_data="menu")]
    ])