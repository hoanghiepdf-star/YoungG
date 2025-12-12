import requests
import uuid
import statistics
from telegram import (
    Update, InlineQueryResultArticle, InputTextMessageContent
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, filters, InlineQueryHandler
)

from flask import Flask, request
import asyncio

TOKEN = "8501370644:AAGMN6qHoak7VSLrS-sE0wa22LhMmYlhU44"
WEBHOOK_URL = "https://your-railway-app-url.up.railway.app"  # <-- đổi link Railway


# ==========================================================
#                 GET BINANCE P2P PRICE (ĐÃ FIX)
# ==========================================================
def get_p2p_price(trans_amount_vnd: float = 2_000_000, rows: int = 10, tradeType: str = "BUY"):
    url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (compatible; OTCBot/1.0)"
    }

    payload = {
        "asset": "USDT",
        "fiat": "VND",
        "page": 1,
        "rows": rows,
        "tradeType": tradeType,
        "transAmount": str(int(trans_amount_vnd)),
        "proMerchantAds": False,
        "merchantCheck": False
    }

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=6)
        r.raise_for_status()
        data = r.json()

        prices = []
        for item in data.get("data", []):
            try:
                p = float(item["adv"]["price"])
                prices.append(p)
            except:
                pass

        if not prices:
            return None

        return statistics.median(prices)

    except:
        return None


# ==========================
#       /start
# ==========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Xin chào! 👋\n"
        "Dùng /otc để xem giá USDT/VND.\n"
        "Nhập 2000 hoặc /2000 để tính USDT.\n"
        "Trong cuộc trò chuyện: @OTCEasyBot 2000 để tính."
    )


# ==========================
#       /otc
# ==========================
async def otc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    price = get_p2p_price()
    if price is None:
        await update.message.reply_text("⚠️ Không thể lấy giá từ Binance.")
        return

    await update.message.reply_text(f"OTCEasyBot: {price:,.0f} VND/USDT")


# ==========================
#     CALC USDT / VND
# ==========================
async def calc_usdt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if text.lower().startswith("@otceasybot"):
        parts = text.split(" ", 1)
        if len(parts) == 2:
            text = parts[1]
        else:
            return

    text = text.replace("/", "").replace(",", "").strip()

    if not text.isdigit():
        return

    vnd_input = float(text)
    trans_amount = vnd_input * 1000 if vnd_input < 100000 else vnd_input

    price = get_p2p_price(trans_amount)
    if price is None:
        await update.message.reply_text("⚠️ Không thể lấy giá từ Binance.")
        return

    usdt_amount = trans_amount / price

    await update.message.reply_text(
        f"💰 {trans_amount:,.0f} VND ≈ {usdt_amount:.4f} USDT\n"
        f"Tỉ giá P2P chuẩn: {price:,.0f} VND/USDT"
    )


# ==========================
#     INLINE MODE popup
# ==========================
async def inlinequery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip().replace(",", "")
    results = []

    if query.isdigit():
        vnd_input = float(query)
        vnd_amount = vnd_input * 1000 if vnd_input < 100000 else vnd_input

        price = get_p2p_price(vnd_amount)

        if price:
            usdt_amount = vnd_amount / price
            text = (
                f"💰 {vnd_amount:,.0f} VND ≈ {usdt_amount:.4f} USDT\n"
                f"Tỉ giá P2P: {price:,.0f} VND/USDT"
            )
        else:
            text = "⚠️ Không thể lấy giá từ Binance."

        results.append(
            InlineQueryResultArticle(
                id=str(uuid.uuid4()),
                title=f"{vnd_amount:,.0f} VND ≈ {usdt_amount:.4f} USDT" if price else "Không lấy được giá",
                description=f"Tỉ giá: {price:,.0f} VND/USDT" if price else "Lỗi Binance",
                input_message_content=InputTextMessageContent(text)
            )
        )

    await update.inline_query.answer(results, cache_time=0)


# ==========================
#     WEBHOOK MODE
# ==========================

app = Flask(__name__)
bot_app = ApplicationBuilder().token(TOKEN).build()


@app.route("/", methods=["POST"])
def webhook():
    json_data = request.get_json(force=True)
    update = Update.de_json(json_data, bot_app.bot)
    asyncio.run(bot_app.process_update(update))
    return "OK", 200


@app.route("/", methods=["GET"])
def home():
    return "Bot is running!"


def main():
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("otc", otc))

    bot_app.add_handler(MessageHandler(filters.Regex(r'^/?\d+$') & filters.ChatType.PRIVATE, calc_usdt))
    bot_app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.GROUPS, calc_usdt))

    bot_app.add_handler(InlineQueryHandler(inlinequery))

    # Set webhook
    asyncio.run(bot_app.bot.set_webhook(WEBHOOK_URL))

    app.run(host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()

