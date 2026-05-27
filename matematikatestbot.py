import os
import logging
import re
import json
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Logging
logging.basicConfig(level=logging.INFO)

# Environment variables
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL") # Masalan: https://botingiz-nomi.onrender.com
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

flask_app = Flask(__name__)
db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

# Ma'lumotlarni yuklash va saqlash (Renderda fayllar vaqtinchalik bo'lishi mumkinligini unutmang)
def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            try: db = json.load(f)
            except: pass

def save_data():
    with open("data.json", "w") as f:
        json.dump(db, f)

def main_keyboard(uid):
    btns = [[KeyboardButton("📚 Testlar")], [KeyboardButton("📊 Natijam"), KeyboardButton("👤 Profil")], [KeyboardButton("ℹ️ Yordam")]]
    if uid == ADMIN_ID: btns.append([KeyboardButton("⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# --- Handlers (Sizning kodingiz bilan bir xil, faqat xatoliklar tuzatildi) ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await update.message.reply_text("Matematika botiga xush kelibsiz!", reply_markup=main_keyboard(uid))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = context.user_data
    
    if text == "🔙 Orqaga":
        data.clear()
        return await update.message.reply_text("🏠 Asosiy menyu", reply_markup=main_keyboard(uid))

    if text == "📚 Testlar":
        btns = [[KeyboardButton("🎓 DTM"), KeyboardButton("📜 Milliy Sertifikat")], [KeyboardButton("🔙 Orqaga")]]
        return await update.message.reply_text("Bo'limni tanlang:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if text == "⚙️ Admin Panel" and uid == ADMIN_ID:
        btns = [[KeyboardButton("➕ Test qo'shish")], [KeyboardButton("📋 Testlar ro'yxati")], [KeyboardButton("🔙 Orqaga")]]
        return await update.message.reply_text("⚙️ Admin", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    # Test qo'shish jarayoni
    if text == "➕ Test qo'shish" and uid == ADMIN_ID:
        data["state"] = "admin_cat"
        return await update.message.reply_text("Kategoriya? (DTM yoki MILLIY)")

    if data.get("state") == "admin_cat":
        data["cat"] = text.upper(); data["state"] = "admin_tid"
        return await update.message.reply_text("Test ID yozing:")

    if data.get("state") == "admin_tid":
        data["tid"] = text.upper(); data["state"] = "admin_ans"
        return await update.message.reply_text("Javoblarni yozing:")

    if data.get("state") == "admin_ans":
        data["answers"] = re.sub(r"[^a-e]", "", text.lower())
        data["state"] = "pdf"
        return await update.message.reply_text("PDF yuboring:")

    if text == "📊 Natijam":
        data["state"] = "check_id"
        return await update.message.reply_text("ID kiriting:")

    if data.get("state") == "check_id":
        tid = text.upper()
        if tid in db["answers"]:
            data["state"] = "waiting_ans"
            data["check_tid"] = tid
            return await update.message.reply_text("Javoblarni yuboring:")
        return await update.message.reply_text("Topilmadi.")

    if data.get("state") == "waiting_ans":
        correct = db["answers"][data["check_tid"]]
        user_ans = re.sub(r"[^a-e]", "", text.lower())
        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        await update.message.reply_text(f"Natija: {score}/{len(correct)}")
        data.clear()

async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    if update.effective_user.id == ADMIN_ID and data.get("state") == "pdf":
        tid = data["tid"]
        db["answers"][tid] = data["answers"]
        db["pdfs"][tid] = update.message.document.file_id
        db["categories"][tid] = data["cat"]
        save_data(); data.clear()
        await update.message.reply_text("✅ Saqlandi!")

# --- Application setup ---
ptb_app = Application.builder().token(TOKEN).build()
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
ptb_app.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))

@flask_app.route("/webhook", methods=["POST"])
async def webhook_route():
    update = Update.de_json(request.get_json(force=True), ptb_app.bot)
    await ptb_app.process_update(update)
    return "OK", 200

@flask_app.route("/")
def home():
    return "Bot is running!", 200

# Render uchun asosiy ishga tushirish qismi
if __name__ == "__main__":
    load_data()
    port = int(os.environ.get("PORT", 10000))
    
    # Webhookni sozlash va Flaskni ishga tushirish
    # Muhim: Webhook ishlashi uchun ptb_app initialize bo'lishi kerak
    # Bu usul Renderning Web Service turiga mos keladi
    ptb_app.run_webhook(
        listen="0.0.0.0",
        port=port,
        url_path="webhook",
        webhook_url=f"{WEBHOOK_URL}/webhook"
    )
