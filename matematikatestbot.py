import logging
import os
import re
import json
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
# Application obyektini yaratish
application = Application.builder().token(TOKEN).build()

db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

def save_data():
    try:
        with open("data.json", "w") as f:
            json.dump(db, f)
    except Exception as e:
        logging.error(f"Save error: {e}")

def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json") as f:
            try: db = json.load(f)
            except: pass

def main_keyboard(uid):
    btns = [[KeyboardButton("📘 Matematika DTM")], [KeyboardButton("📗 Matematika Milliy Sertifikat")],
            [KeyboardButton("📊 NATIJA TEKSHIRISH")], [KeyboardButton("👨‍💻 Admin")]]
    if uid == ADMIN_ID:
        btns.append([KeyboardButton("➕ TEST"), KeyboardButton("🔑 KALIT")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await update.message.reply_text("Xush kelibsiz!", reply_markup=main_keyboard(uid))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    user_data = context.user_data

    if text == "🔙 Orqaga":
        user_data.clear()
        return await update.message.reply_text("Menyu:", reply_markup=main_keyboard(uid))

    if text == "👨‍💻 Admin":
        return await update.message.reply_text("@miracle_1204")

    # TESTLARNI KO'RSATISH
    menus = {"📘 Matematika DTM": "DTM", "📗 Matematika Milliy Sertifikat": "MILLIY"}
    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]
        if not tests: return await update.message.reply_text("❌ Testlar yo‘q")
        btns = [[KeyboardButton(t)] for t in tests]
        btns.append([KeyboardButton("🔙 Orqaga")])
        user_data["state"] = "choose"
        return await update.message.reply_text("Tanlang:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if user_data.get("state") == "choose" and text in db["pdfs"]:
        return await update.message.reply_document(db["pdfs"][text])

    # NATIJA TEKSHIRISH
    if text == "📊 NATIJA TEKSHIRISH":
        user_data["state"] = "check"
        return await update.message.reply_text("Test ID yozing:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Orqaga")]], resize_keyboard=True))

    if user_data.get("state") == "check":
        tid = text.upper()
        if tid in db["answers"]:
            user_data.update({"state": "ans", "tid": tid})
            return await update.message.reply_text("Javoblarni yuboring:")
        return await update.message.reply_text("❌ Topilmadi")

    if user_data.get("state") == "ans":
        correct = db["answers"][user_data["tid"]]
        user_ans = re.sub(r'[^a-e]', '', text.lower())
        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        user_data.clear()
        return await update.message.reply_text(f"Natija: {score}/{len(correct)}", reply_markup=main_keyboard(uid))

    # ADMIN QISMI
    if uid == ADMIN_ID:
        if text == "➕ TEST":
            user_data["state"] = "cat"
            return await update.message.reply_text("1-DTM, 2-MILLIY")
        if user_data.get("state") == "cat":
            user_data.update({"cat": ("DTM" if text=="1" else "MILLIY"), "state": "id"})
            return await update.message.reply_text("ID yozing:")
        if user_data.get("state") == "id":
            user_data.update({"tid": text.upper(), "state": "pdf"})
            return await update.message.reply_text("PDF yuboring:")
        if text == "🔑 KALIT":
            user_data["state"] = "key_id"
            return await update.message.reply_text("Test ID:")
        if user_data.get("state") == "key_id":
            user_data.update({"kid": text.upper(), "state": "key_val"})
            return await update.message.reply_text("Kalitlarni yozing:")
        if user_data.get("state") == "key_val":
            db["answers"][user_data["kid"]] = re.sub(r'[^a-e]', '', text.lower())
            save_data()
            user_data.clear()
            return await update.message.reply_text("✅ Saqlandi", reply_markup=main_keyboard(uid))

async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID and context.user_data.get("state") == "pdf":
        db["pdfs"][context.user_data["tid"]] = update.message.document.file_id
        db["categories"][context.user_data["tid"]] = context.user_data["cat"]
        save_data()
        context.user_data.clear()
        await update.message.reply_text("✅ PDF saqlandi!", reply_markup=main_keyboard(ADMIN_ID))

@app.route("/")
def home(): return "OK"

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    # 'active' o'rniga 'running' tekshiruvi yoki to'g'ridan-to'g'ri initialize
    try:
        if not application.updater:
            await application.initialize()
            await application.start()
        
        data = request.get_json(force=True)
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logging.error(f"Error: {e}")
    return '', 200

async def setup():
    load_data()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))
    await application.initialize()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    await application.start()

if __name__ == "__main__":
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(setup())
    except:
        asyncio.run(setup())
    
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
