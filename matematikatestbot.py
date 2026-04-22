import os
import logging
import re
import json
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Muhit o'zgaruvchilari
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Flask va Telegram Application
app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

def load_data():
    global db
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r") as f:
                db = json.load(f)
        except: pass

def save_data():
    try:
        with open("data.json", "w") as f:
            json.dump(db, f)
    except: pass

def main_keyboard(uid):
    btns = [[KeyboardButton("📚 Testlar")], [KeyboardButton("📊 Natijam")], [KeyboardButton("ℹ️ Yordam")]]
    if uid == ADMIN_ID: btns.append([KeyboardButton("⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await update.message.reply_text(f"👋 Salom! Test botiga xush kelibsiz.", reply_markup=main_keyboard(uid))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = context.user_data

    if text == "🔙 Orqaga":
        data.clear()
        return await update.message.reply_text("Menyu", reply_markup=main_keyboard(uid))

    if text == "📚 Testlar":
        btns = [[KeyboardButton("🎓 DTM"), KeyboardButton("📜 MILLIY")], [KeyboardButton("🔙 Orqaga")]]
        return await update.message.reply_text("Kategoriyani tanlang:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if text in ["🎓 DTM", "📜 MILLIY"]:
        cat = "DTM" if "DTM" in text else "MILLIY"
        tests = [t for t, c in db["categories"].items() if c == cat]
        if not tests: return await update.message.reply_text("❌ Testlar yo'q")
        keyboard = [[InlineKeyboardButton(t, callback_data=f"test_{t}")] for t in tests]
        return await update.message.reply_text("Testni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

    if text == "📊 Natijam":
        data["state"] = "check"
        return await update.message.reply_text("Test ID sini kiriting:")

    if data.get("state") == "check":
        tid = text.upper()
        if tid in db["answers"]:
            data.update({"state": "ans", "tid": tid})
            return await update.message.reply_text("Javoblarni yuboring (masalan: abcd...):")
        return await update.message.reply_text("❌ ID topilmadi.")

    if data.get("state") == "ans":
        correct = db["answers"][data["tid"]]
        user_ans = re.sub(r"[^a-e]", "", text.lower())
        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        data.clear()
        return await update.message.reply_text(f"✅ Natija: {score}/{len(correct)}", reply_markup=main_keyboard(uid))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("test_", "")
    if tid in db["pdfs"]:
        await query.message.reply_document(db["pdfs"][tid])

# ================= WEBHOOK (MUHIM QISM) =================
@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    if request.method == "POST":
        # Bot hali ishga tushmagan bo'lsa, uni uyg'otamiz
        if not application.updater:
            await application.initialize()
            await application.start()
        
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "OK", 200

@app.route("/")
def index(): return "Bot is alive!", 200

async def setup_bot():
    load_data()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Webhookni bir marta o'rnatish
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    logging.info(f"Webhook set to: {WEBHOOK_URL}/{TOKEN}")

if __name__ == "__main__":
    # Avval botni sozlaymiz
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    loop.run_until_complete(setup_bot())
    
    # Keyin Flaskni yoqamiz
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
