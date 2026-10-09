import datetime
import os
import urllib.parse
import uuid
from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    MenuButtonDefault,
    Update,
    WebAppInfo,
)
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

load_dotenv()

TOKEN = os.getenv("TOKEN")
BASE_WEBAPP_URL = os.getenv("BASE_WEBAPP_URL")

if not TOKEN or not BASE_WEBAPP_URL:
    raise ValueError("Faltan variables en .env (TOKEN o BASE_WEBAPP_URL)")

TICKETS = {
    "transit": {
        "type": "bus",
        "name": "COMPRA PAISES UME AMT AZIENDA MOBILIT...",
        "amount": 2.00,
    },
    "trenitalia": {
        "type": "tren",
        "name": "Trenitalia - pt wl",
        "amount": 3.00,
    },
}

def get_initial_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚌 Bus / Metro (2,00 €)", callback_data="buy_transit"),
            InlineKeyboardButton("🚆 Trenitalia (3,00 €)", callback_data="buy_trenitalia"),
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.set_chat_menu_button(
            chat_id=update.effective_chat.id,
            menu_button=MenuButtonDefault()
        )
    except Exception:
        pass

    context.user_data["session_id"] = str(uuid.uuid4())[:8]
    context.user_data["purchases"] = []
    
    await update.message.reply_text(
        "🎫 **Terminal de Transporte Digital**\n\n"
        "Selecciona un billete para realizar pagos contactless simulados:",
        reply_markup=get_initial_keyboard(),
        parse_mode="Markdown"
    )

async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass

    ticket_key = query.data.replace("buy_", "")
    ticket = TICKETS.get(ticket_key)
    if not ticket:
        return

    if "session_id" not in context.user_data:
        context.user_data["session_id"] = str(uuid.uuid4())[:8]

    if "purchases" not in context.user_data:
        context.user_data["purchases"] = []

    now = datetime.datetime.now()
    fifteen_min_ago = now - datetime.timedelta(minutes=15)
    tx_timestamp = int(fifteen_min_ago.timestamp())

    # Formato ligero tipo:timestamp
    tx_entry = f"{ticket['type']}:{tx_timestamp}"
    context.user_data["purchases"].append(tx_entry)

    session_id = context.user_data["session_id"]
    all_txs_param = ",".join(context.user_data["purchases"])

    webapp_url = (
        f"{BASE_WEBAPP_URL}?session_id={session_id}"
        f"&txs={urllib.parse.quote(all_txs_param)}"
        f"&v={int(now.timestamp())}"
    )

    keyboard = [
        [
            InlineKeyboardButton("🚌 Bus / Metro (2,00 €)", callback_data="buy_transit"),
            InlineKeyboardButton("🚆 Trenitalia (3,00 €)", callback_data="buy_trenitalia"),
        ],
        [
            InlineKeyboardButton(
                f"📱 Ver en mi App ({len(context.user_data['purchases'])} compras)",
                web_app=WebAppInfo(url=webapp_url)
            )
        ],
        [
            InlineKeyboardButton("🔄 Resetear Demo", callback_data="reset_demo")
        ]
    ]

    total_spent = sum(
        TICKETS["transit"]["amount"] if item.startswith("bus") else TICKETS["trenitalia"]["amount"]
        for item in context.user_data["purchases"]
    )

    await query.edit_message_text(
        text=(
            f"✅ **¡Pago realizado con éxito!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 **Artículo:** {ticket['name']} (-{ticket['amount']:.2f} €)\n"
            f"🧾 **Compras en sesión:** {len(context.user_data['purchases'])}\n"
            f"💶 **Total acumulado:** -{total_spent:.2f} €\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"Abre la app bancaria para revisar el extracto o pulsa Resetear:"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    try:
        await query.answer()
    except BadRequest:
        pass

    context.user_data["session_id"] = str(uuid.uuid4())[:8]
    context.user_data["purchases"] = []

    await query.edit_message_text(
        text=(
            "🎫 **Terminal de Transporte Digital**\n\n"
            "La demo se ha reseteado. Selecciona un billete para comenzar de nuevo:"
        ),
        reply_markup=get_initial_keyboard(),
        parse_mode="Markdown"
    )

if __name__ == "__main__":
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_purchase, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(handle_reset, pattern="^reset_demo$"))

    print("Bot corriendo... Abre Telegram y escribe /start")
    app.run_polling(drop_pending_updates=True)