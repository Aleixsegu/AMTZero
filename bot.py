import datetime
import json
import os
import urllib.parse
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.error import BadRequest
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

# Cargar variables de entorno desde el archivo .env
load_dotenv()

TOKEN = os.getenv("TOKEN")
BASE_WEBAPP_URL = os.getenv("BASE_WEBAPP_URL")

if not TOKEN:
    raise ValueError("Error: La variable TOKEN no está definida en el archivo .env")

if not BASE_WEBAPP_URL:
    raise ValueError("Error: La variable BASE_WEBAPP_URL no está definida en el archivo .env")

# Catálogo de billetes de transporte para la demo
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

def get_initial_keyboard() -> InlineKeyboardMarkup:
    """Devuelve la botonera inicial con los billetes de compra."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚌 Bus / Metro (2,00 €)", callback_data="buy_transit"),
            InlineKeyboardButton("🚆 Trenitalia (9,80 €)", callback_data="buy_trenitalia"),
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Comando /start: reinicia la sesión del usuario y muestra los botones de compra."""
    context.user_data["purchases"] = []
    
    await update.message.reply_text(
        "🎫 **Terminal de Transporte Digital**\n\n"
        "Selecciona un billete para realizar pagos contactless simulados:",
        reply_markup=get_initial_keyboard(),
        parse_mode="Markdown"
    )

async def handle_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Procesa la compra del billete, actualiza la sesión y añade el botón de la WebApp."""
    query = update.callback_query

    # Responder al callback de forma segura ante timeouts de Telegram
    try:
        await query.answer("💳 Pago contactless autorizado")
    except BadRequest:
        pass

    ticket_key = query.data.replace("buy_", "")
    ticket = TICKETS.get(ticket_key)
    if not ticket:
        return

    if "purchases" not in context.user_data:
        context.user_data["purchases"] = []

    # Construir el objeto de transacción
    now = datetime.datetime.now()
    tx_item = {
        "id": f"TX-{now.strftime('%H%M%S')}",
        "name": ticket["name"],
        "icon": ticket["icon"],
        "amount": ticket["amount"],
        "operator": ticket["operator"],
        "terminal": ticket["terminal"],
        "timestamp": now.strftime("%H:%M:%S"),
        "mins_ago": 15  # Simulación de cargo hace 15 minutos
    }
    context.user_data["purchases"].append(tx_item)

    # Serializar el ítem en JSON codificado para URL
    encoded_item = urllib.parse.quote(json.dumps(tx_item))
    webapp_url = f"{BASE_WEBAPP_URL}?new_tx={encoded_item}"

    # Teclado dinámico con contador acumulado
    keyboard = [
        [
            InlineKeyboardButton("🚌 Bus / Metro (2,00 €)", callback_data="buy_transit"),
            InlineKeyboardButton("🚆 Trenitalia (9,80 €)", callback_data="buy_trenitalia"),
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

    total_spent = sum(p["amount"] for p in context.user_data["purchases"])

    await query.edit_message_text(
        text=(
            f"✅ **¡Pago realizado con éxito!**\n"
            f"━━━━━━━━━━━━━━━━━━━\n"
            f"🛒 **Último artículo:** {ticket['icon']} {ticket['name']} (-{ticket['amount']:.2f} €)\n"
            f"🧾 **Total compras acumuladas:** {len(context.user_data['purchases'])}\n"
            f"💶 **Gasto de la sesión:** -{total_spent:.2f} €\n"
            f"━━━━━━━━━━━━━━━━━━━\n\n"
            f"Puedes comprar otro billete, abrir tu app bancaria para revisar el extracto detallado o resetear la sesión:"
        ),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Limpia el historial de compras y restaura el mensaje inicial."""
    query = update.callback_query

    # Responder al callback de forma segura ante timeouts
    try:
        await query.answer("Sistema reseteado")
    except BadRequest:
        pass

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
    
    # drop_pending_updates=True descarta clics atrasados mientras el bot estuvo apagado
    app.run_polling(drop_pending_updates=True)