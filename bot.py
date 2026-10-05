import datetime
import urllib.parse
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

TOKEN = "TU_BOT_TOKEN_AQUI"
# La URL HTTPS donde sirvas tu index.html (ej. Cloudflare Tunnel, ngrok, Vercel o GitHub Pages)
BASE_WEBAPP_URL = "https://tu-dominio-o-ngrok.app"

TICKETS = {
    "transit": {
        "name": "Bus / Metro",
        "icon": "🚌",
        "amount": 2.00,
        "operator": "Azienda Mobilità e Trasporti (AMT)",
        "terminal": "POS Contactless #4092",
    },
    "trenitalia": {
        "name": "Trenitalia Regionale",
        "icon": "🚆",
        "amount": 9.80,
        "operator": "Trenitalia S.p.A. - Biglietto Regionale",
        "terminal": "Smart Gateway Rail #8821",
    },
}

def get_initial_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚌 Bus / Metro (2,00 €)", callback_data="buy_transit"),
            InlineKeyboardButton("🚆 Trenitalia (9,80 €)", callback_data="buy_trenitalia"),
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Inicializar la lista de compras de la sesión
    context.user_data["purchases"] = []
    
    await update.message.reply_text(
        "🎫 **Terminal de Transporte Digital**\n\n"
        "Selecciona un billete para realizar pagos contactless simulados:",
        reply_markup=get_initial_keyboard(),
        parse_mode="Markdown"
    )

async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("💳 Pago contactless autorizado")

    ticket_key = query.data.replace("buy_", "")
    ticket = TICKETS[ticket_key]

    if "purchases" not in context.user_data:
        context.user_data["purchases"] = []

    # Registrar la compra con timestamp y datos para la vista de detalle
    now = datetime.datetime.now()
    tx_item = {
        "id": f"TX-{now.strftime('%H%M%S')}",
        "name": ticket["name"],
        "icon": ticket["icon"],
        "amount": ticket["amount"],
        "operator": ticket["operator"],
        "terminal": ticket["terminal"],
        "timestamp": now.strftime("%H:%M:%S"),
        "mins_ago": 15  # Requisito: simular que ocurrió hace 15 min
    }
    context.user_data["purchases"].append(tx_item)

    # Serializar la última compra para que la WebApp la ingeste a su localStorage
    encoded_item = urllib.parse.quote(str(tx_item).replace("'", '"'))
    webapp_url = f"{BASE_WEBAPP_URL}?new_tx={encoded_item}"

    # Teclado dinámico: permite seguir comprando o ver la app bancaria
    keyboard = [
        [
            InlineKeyboardButton("🚌 Bus / Metro (2,00 €)", callback_data="buy_transit"),
            InlineKeyboardButton("🚆 Trenitalia (9,80 €)", callback_data="buy_trenitalia"),
        ],
        [
            InlineKeyboardButton(f"📱 Ver en mi App ({len(context.user_data['purchases'])} compras)", web_app=WebAppInfo(url=webapp_url))
        ],
        [
            InlineKeyboardButton("🔄 Resetear Demo", callback_data="reset_demo")
        ]
    ]

    total_gastado = sum(p["amount"] for p in context.user_data["purchases"])

    await query.edit_message_text(
        text=(
            f"✅ **¡Pago realizado con éxito!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 **Último artículo:** {ticket['icon']} {ticket['name']} (-{ticket['amount']:.2f} €)\n"
            f"🧾 **Total compras acumuladas:** {len(context.user_data['purchases'])}\n"
            f"💶 **Gasto sesión:** -{total_gastado:.2f} €\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"Puedes comprar otro billete, abrir tu app bancaria para revisar el extracto detallado o resetear la sesión:"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Sistema reseteado")
    context.user_data["purchases"] = []

    # Enviamos una url con reset=true para que la webapp borre su localStorage
    reset_url = f"{BASE_WEBAPP_URL}?reset=true"

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
    app.run_polling()