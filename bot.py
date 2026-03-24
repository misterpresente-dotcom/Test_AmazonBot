import json
import requests
import time
import threading
from bs4 import BeautifulSoup
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler

TOKEN = "8558434791:AAEu6RBa354nNlqbMI1VYWAwNr77VFp2_Fc"
DATA_FILE = "tracked_items.json"

# -------------------------
# UTILITIES
# -------------------------
def load_data():
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

def extract_price(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    page = requests.get(url, headers=headers)
    soup = BeautifulSoup(page.content, "html.parser")
    price_span = soup.select_one("#priceblock_ourprice, #priceblock_dealprice")
    if not price_span:
        return None
    price_text = price_span.text.strip().replace("€", "").replace(",", ".")
    return float(price_text)

# -------------------------
# BOT HANDLERS
# -------------------------
def start(update, context):
    update.message.reply_text("Ciao! Inviami un link Amazon e inizierò a monitorarlo!")

def handle_link(update, context):
    url = update.message.text

    if "amazon" not in url:
        update.message.reply_text("Questo non sembra un link Amazon valido.")
        return

    context.user_data["url"] = url

    keyboard = [
        [InlineKeyboardButton("€10", callback_data="10"),
         InlineKeyboardButton("€20", callback_data="20"),
         InlineKeyboardButton("€50", callback_data="50")],
        [InlineKeyboardButton("Inserirò manualmente", callback_data="manual")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        "Perfetto! Scegli la soglia di prezzo:",
        reply_markup=reply_markup
    )

def button(update, context):
    query = update.callback_query
    query.answer()

    url = context.user_data["url"]
    data = load_data()

    if query.data == "manual":
        query.message.reply_text("Scrivi ora la tua soglia prezzo (es: 35.50)")
        context.user_data["manual"] = True
        return

    threshold = float(query.data)
    data[url] = threshold
    save_data(data)
    query.message.reply_text(f"Monitoraggio attivato! Ti avviso quando scende sotto €{threshold}")

def manual_threshold(update, context):
    if "manual" in context.user_data:
        url = context.user_data["url"]
        threshold = float(update.message.text)
        data = load_data()
        data[url] = threshold
        save_data(data)
        update.message.reply_text(f"Perfetto! Notifica impostata a €{threshold}")
        del context.user_data["manual"]

# -------------------------
# PRICE CHECKER THREAD
# -------------------------
def price_checker(context):
    updater = context
    bot = updater.bot
    chat_id = updater.chat_id
    data = load_data()

    while True:
        data = load_data()
        for url, threshold in data.items():
            price = extract_price(url)
            if price and price <= threshold:
                bot.send_message(
                    chat_id=chat_id,
                    text=f"📉 Prezzo sceso!\n{url}\nPrezzo attuale: €{price}"
                )
                del data[url]
                save_data(data)
        time.sleep(1800)  # Controlla ogni 30 min

# -------------------------
# MAIN
# -------------------------
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.regex("http"), handle_link))
dp.add_handler(CallbackQueryHandler(button))
dp.add_handler(MessageHandler(Filters.text & (~Filters.command), manual_threshold))

price_thread = threading.Thread(target=price_checker, args=(updater,), daemon=True)
price_thread.start()

updater.start_polling()
updater.idle()
``