import os
import logging
import asyncio

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from config import BOT_TOKEN, BOT_NAME, BANNER_PATH, ADMIN_IDS
from database import (
    init_db,
    get_or_create_user,
    get_user,
    add_balance,
    get_products,
    buy_product,
    add_coupon,
    redeem_coupon,
    get_purchases,
    stats,
    add_product
)
from keyboards import (
    main_menu,
    back_menu,
    recharge_back_menu,
    products_menu,
    earn_diamonds_menu,
    countries_menu,
    recharge_methods_menu,
    COUNTRIES
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

waiting_coupon = set()
waiting_recharge_amount = {}
recharge_data = {}

print(BANNER_PATH)
print(os.path.exists(BANNER_PATH))

def money(n):
    return f"${float(n):.2f} USD"


def home_text(first_name, telegram_id, balance):
    return (
        "╔════════════════════╗\n"
        f"     💜 <b>{BOT_NAME}</b>\n"
        "╚════════════════════╝\n\n"
        "🧾 <b>Panel de usuario</b>\n\n"
        f"👤 <b>Cliente:</b> {first_name or 'Usuario'}\n"
        f"🆔 <b>ID:</b> <code>{telegram_id}</code>\n"
        f"💰 <b>Saldo:</b> <code>{money(balance)}</code>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💎 <b>Gana, compra y canjea desde aquí.</b>\n"
        "Selecciona una opción:"
    )


async def send_banner_message(update: Update, context: ContextTypes.DEFAULT_TYPE, text, keyboard):
    if os.path.exists(BANNER_PATH):
        with open(BANNER_PATH, "rb") as photo:
            msg = await update.effective_chat.send_photo(
                photo=photo,
                caption=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )

        context.user_data["banner_message_id"] = msg.message_id
    else:
        msg = await update.effective_chat.send_message(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )

        context.user_data["banner_message_id"] = msg.message_id


async def edit_banner(update: Update, context: ContextTypes.DEFAULT_TYPE, text, keyboard=None):
    chat_id = update.effective_chat.id
    message_id = context.user_data.get("banner_message_id")

    if not message_id:
        await send_banner_message(update, context, text, keyboard)
        return

    try:
        await context.bot.edit_message_caption(
            chat_id=chat_id,
            message_id=message_id,
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=keyboard
        )
    except Exception:
        try:
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.HTML,
                reply_markup=keyboard
            )
        except Exception:
            await send_banner_message(update, context, text, keyboard)


async def edit_bot_message(query, text, reply_markup=None):
    if query.message.photo:
        await query.edit_message_caption(
            caption=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )
    else:
        await query.edit_message_text(
            text=text,
            parse_mode=ParseMode.HTML,
            reply_markup=reply_markup
        )


async def send_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    ref_id = None

    if context.args and context.args[0].isdigit():
        ref_id = int(context.args[0])

    data = get_or_create_user(user, ref_id)
    telegram_id, username, first_name, balance, invited_by, created_at = data

    text = home_text(first_name, telegram_id, balance)

    await send_banner_message(update, context, text, main_menu())


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_home(update, context)


async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    u = get_or_create_user(user)

    telegram_id, username, first_name, balance, invited_by, created_at = u
    text = home_text(first_name, telegram_id, balance)

    await edit_banner(update, context, text, main_menu())


async def transition_menu(query, loading_text, final_text, final_keyboard, delay=0.45):
    await edit_bot_message(query, loading_text, None)
    await asyncio.sleep(delay)
    await edit_bot_message(query, final_text, final_keyboard)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = update.effective_user
    user_id = user.id
    data = query.data

    await query.answer()
    get_or_create_user(user)

    context.user_data["banner_message_id"] = query.message.message_id

    if data == "earn_diamonds":
        text = (
            "💎 <b>Ganar Diamantes</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Elige una opción para conseguir recompensas:\n\n"
            "🎮 Completa tareas desde la web\n"
            "👥 Invita amigos\n"
            "🎟️ Canjea códigos promocionales\n"
            "💎 Canjea diamantes"
        )

        await transition_menu(query, "💎 <b>Abriendo sección...</b>", text, earn_diamonds_menu())
        return

    if data == "menu":
        waiting_coupon.discard(user_id)
        waiting_recharge_amount.pop(user_id, None)

        u = get_user(user_id)
        balance = u[3] if u else 0

        text = home_text(user.first_name, user_id, balance)
        await transition_menu(query, "🏠 <b>Volviendo al inicio...</b>", text, main_menu())
        return

    if data == "shop":
        products = get_products()

        text = (
            "🛍️ <b>Tienda</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Selecciona un producto para comprar:"
        )

        await transition_menu(query, "🛍️ <b>Abriendo tienda...</b>", text, products_menu(products))
        return

    if data == "coupon":
        waiting_coupon.add(user_id)
        waiting_recharge_amount.pop(user_id, None)

        text = (
            "🎟️ <b>Canjear cupón</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "Escribe el código del cupón en el chat."
        )

        await transition_menu(query, "🎟️ <b>Preparando cupón...</b>", text, back_menu())
        return

    if data == "profile":
        u = get_user(user_id)

        if not u:
            await edit_bot_message(query, "❌ No se encontró tu cuenta.", back_menu())
            return

        telegram_id, username, first_name, balance, invited_by, created_at = u
        bot_username = context.bot.username

        text = (
            "👤 <b>Mi cuenta</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🆔 <b>ID:</b> <code>{telegram_id}</code>\n"
            f"👤 <b>Nombre:</b> {first_name or 'Usuario'}\n"
            f"💰 <b>Saldo:</b> <code>{money(balance)}</code>\n\n"
            "👥 <b>Link de invitación:</b>\n"
            f"<code>https://t.me/{bot_username}?start={telegram_id}</code>"
        )

        await transition_menu(query, "👤 <b>Cargando cuenta...</b>", text, back_menu())
        return

    if data == "recharge":
        waiting_coupon.discard(user_id)
        waiting_recharge_amount.pop(user_id, None)

        text = (
            "💳 <b>Recargar saldo</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "🌎 Primero selecciona tu país:"
        )

        await transition_menu(query, "💳 <b>Abriendo recarga...</b>", text, countries_menu())
        return

    if data.startswith("recharge_country:"):
        country_code = data.split(":", 1)[1]

        if country_code not in COUNTRIES:
            await edit_bot_message(query, "⚠️ País inválido. Selecciona uno de la lista.", countries_menu())
            return

        recharge_data[user_id] = {"country": country_code}
        waiting_recharge_amount[user_id] = True

        country_name, currency, rate = COUNTRIES[country_code]

        text = (
            f"🌎 <b>País seleccionado:</b> {country_name}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"💰 Escribe cuánto quieres recargar en <b>{currency}</b>.\n\n"
            "Ejemplo:\n"
            "<code>100</code>"
        )

        await edit_bot_message(query, text, back_menu())
        return

    if data.startswith("recharge_method:"):
        method = data.split(":", 1)[1]
        info = recharge_data.get(user_id)

        if not info or "amount_usd" not in info or "amount_local" not in info or "country" not in info:
            await edit_bot_message(query, "⚠️ Primero debes seleccionar país y escribir el monto.", countries_menu())
            return

        amount_usd = float(info["amount_usd"])
        amount_local = float(info["amount_local"])
        country_code = info["country"]

        country_name, currency, rate = COUNTRIES[country_code]
        mxn_amount = amount_usd * COUNTRIES["MX"][2]

        if method == "transfer":
            text = (
                "🏦 <b>Pago por transferencia</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"🌎 País: {country_name}\n"
                f"💰 Monto a depositar: <b>{amount_local:.2f} {currency}</b>\n\n"
                "🏧 Cuenta:\n"
                "<code>1271 8000 1905 3207 26</code>\n\n"
                "👤 Nombre:\n"
                "<b>Rafael Alejandro Leonce Suarez</b>\n\n"
                "📩 Luego de hacer la transferencia, envía el comprobante por este chat.\n"
                "Un admin lo revisará y te cargará el saldo."
            )

        elif method == "paypal":
            text = (
                "🅿️ <b>Pago por PayPal</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"💰 Depositar: <b>{amount_usd:.2f} USD</b>\n\n"
                "📧 Usuario PayPal:\n"
                "<code>leoncerafis@gmail.com</code>\n\n"
                "📩 Luego de pagar, envía el comprobante por este chat.\n"
                "Un admin lo revisará y te cargará el saldo."
            )

        elif method == "diamonds":
            diamond_packages = [
                (19, 100),
                (59, 310),
                (99, 520),
                (199, 1060),
                (279, 2180),
                (949, 5600),
            ]

            diamonds = None
            for price_mxn, package_diamonds in diamond_packages:
                if mxn_amount <= price_mxn:
                    diamonds = package_diamonds
                    break

            if diamonds is None:
                packs_needed = int((mxn_amount + 948) // 949)
                diamonds = packs_needed * 5600

            text = (
                "💎 <b>Pago con diamantes</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"💎 Debes recargar: <b>{diamonds} diamantes</b>\n\n"
                "🎮 Recargarle a este ID:\n"
                "<code>ID: 1662214638</code>\n"
                "<code>NOMBRE: RafisAle2410</code>\n\n"
                "📩 Luego de hacer la recarga, envía comprobante por este chat.\n"
                "Un admin lo revisará y te cargará saldo."
            )

        else:
            text = "⚠️ Método inválido."

        await edit_bot_message(query, text, back_menu())
        return

    if data == "purchases":
        rows = get_purchases(user_id)

        if not rows:
            text = (
                "📦 <b>Mis compras</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "No tienes compras todavía."
            )
        else:
            text = "📦 <b>Mis compras</b>\n━━━━━━━━━━━━━━━━━━\n\n"

            for name, price, item, created_at in rows:
                text += (
                    f"• <b>{name}</b> | {money(price)}\n"
                    f"<code>{item}</code>\n\n"
                )

        await transition_menu(query, "📦 <b>Buscando compras...</b>", text, back_menu())
        return

    if data.startswith("buy:"):
        product_id = data.split(":", 1)[1]
        ok, result = buy_product(user_id, product_id)

        if ok:
            text = (
                "✅ <b>Compra completada</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "Tu producto:\n"
                f"<code>{result}</code>\n\n"
                "Guárdalo en un lugar seguro."
            )
            keyboard = back_menu()
        else:
            text = (
                "❌ <b>No se pudo comprar</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"{result}"
            )

            if "Saldo insuficiente" in str(result):
                keyboard = recharge_back_menu()
            else:
                keyboard = back_menu()

        await transition_menu(query, "🛒 <b>Procesando compra...</b>", text, keyboard)
        return


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id

    get_or_create_user(user)

    if user_id in waiting_recharge_amount:
        raw_amount = update.message.text.strip().replace(",", ".")

        try:
            amount_local = float(raw_amount)
        except ValueError:
            text = (
                "⚠️ <b>Monto inválido</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "Escribe un monto válido.\n\n"
                "Ejemplo:\n"
                "<code>100</code>"
            )
            await edit_banner(update, context, text, back_menu())
            return

        if amount_local <= 0:
            text = (
                "⚠️ <b>Monto inválido</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "El monto debe ser mayor a 0."
            )
            await edit_banner(update, context, text, back_menu())
            return

        if user_id not in recharge_data or "country" not in recharge_data[user_id]:
            waiting_recharge_amount.pop(user_id, None)

            text = (
                "⚠️ <b>Falta seleccionar país</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "Primero selecciona tu país."
            )
            await edit_banner(update, context, text, countries_menu())
            return

        waiting_recharge_amount.pop(user_id, None)

        country_code = recharge_data[user_id]["country"]
        country_name, currency, rate = COUNTRIES[country_code]

        amount_usd = amount_local / rate

        recharge_data[user_id]["amount_local"] = amount_local
        recharge_data[user_id]["amount_usd"] = amount_usd

        text = (
            "✅ <b>Monto recibido</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🌎 País: {country_name}\n"
            f"💰 Monto: <b>{amount_local:.2f} {currency}</b>\n\n"
            "Ahora selecciona el método de pago:"
        )

        await edit_banner(update, context, text, recharge_methods_menu())
        return

    if user_id in waiting_coupon:
        waiting_coupon.remove(user_id)

        code = update.message.text.strip()
        ok, msg = redeem_coupon(user_id, code)

        text = (
            ("✅ <b>Cupón canjeado</b>\n" if ok else "❌ <b>Cupón inválido</b>\n") +
            "━━━━━━━━━━━━━━━━━━\n\n" +
            msg
        )

        await edit_banner(update, context, text, back_menu())
        return

    text = (
        "🏠 <b>Menú principal</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "Usa los botones del menú para navegar."
    )

    await edit_banner(update, context, text, main_menu())


async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return await update.message.reply_text("No tienes permisos.")

    total_users, total_balance, total_purchases = stats()

    await update.message.reply_text(
        f"🛠️ Admin\n\n"
        f"Usuarios: {total_users}\n"
        f"Saldo total: ${total_balance:.2f}\n"
        f"Compras: {total_purchases}\n\n"
        "Comandos:\n"
        "/addbalance <id> <monto>\n"
        "/addcoupon <codigo> <monto> <usos>\n"
        "/addproduct <nombre> | <precio> | <stock separado por coma>"
    )


async def cmd_addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    try:
        telegram_id = int(context.args[0])
        amount = float(context.args[1])
    except Exception:
        return await update.message.reply_text("Uso: /addbalance <telegram_id> <monto>")

    ok = add_balance(telegram_id, amount)
    await update.message.reply_text("Saldo agregado." if ok else "Usuario no encontrado.")


async def cmd_addcoupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    try:
        code = context.args[0]
        amount = float(context.args[1])
        uses = int(context.args[2])
    except Exception:
        return await update.message.reply_text("Uso: /addcoupon <codigo> <monto> <usos>")

    add_coupon(code, amount, uses)
    await update.message.reply_text("Cupón creado.")


async def cmd_addproduct(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return

    raw = update.message.text.replace("/addproduct", "", 1).strip()

    try:
        name, price, stock_raw = [x.strip() for x in raw.split("|", 2)]
        items = [x.strip() for x in stock_raw.split(",") if x.strip()]
        product_id = add_product(name, float(price), items)
    except Exception:
        return await update.message.reply_text(
            "Uso: /addproduct Nombre | precio | KEY1,KEY2,KEY3"
        )

    await update.message.reply_text(f"Producto creado con ID {product_id}.")


def main():
    if not BOT_TOKEN:
        raise RuntimeError("Falta BOT_TOKEN en .env")

    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_cmd))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CommandHandler("addbalance", cmd_addbalance))
    app.add_handler(CommandHandler("addcoupon", cmd_addcoupon))
    app.add_handler(CommandHandler("addproduct", cmd_addproduct))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("Bot ejecutándose...")
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    main()