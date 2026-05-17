import os
import logging
import re
import json
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

# Logging sozlamalari
logging.basicConfig(level=logging.INFO)

# Muhit o'zgaruvchilari
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

flask_app = Flask(__name__)
db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

# --- Ma'lumotlar bilan ishlash ---
def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            try:
                db = json.load(f)
            except:
                pass

def save_data():
    with open("data.json", "w") as f:
        json.dump(db, f)

# --- Klaviatura ---
def main_keyboard(uid):
    btns = [
        [KeyboardButton("📚 Testlar")],
        [KeyboardButton("📊 Natijam"), KeyboardButton("👤 Profil")],
        [KeyboardButton("ℹ️ Yordam")]
    ]
    if uid == ADMIN_ID:
        btns.append([KeyboardButton("⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await update.message.reply_text(
        "Assalomu alaykum! Matematika test botiga xush kelibsiz.", 
        reply_markup=main_keyboard(uid)
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = context.user_data

    if text == "🔙 Orqaga":
        data.clear()
        return await update.message.reply_text("🏠 Asosiy menyu", reply_markup=main_keyboard(uid))

    if text == "📚 Testlar":
        btns = [[KeyboardButton("🎓 DTM"), KeyboardButton("📜 Milliy Sertifikat")], [KeyboardButton("🔙 Orqaga")]]
        return await update.message.reply_text("Kategoriyani tanlang:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if text == "👤 Profil":
        return await update.message.reply_text(f"👤 PROFIL\n\nIsm: {update.effective_user.first_name}\nID: {uid}")

    if text == "ℹ️ Yordam":
        return await update.message.reply_text("Testlarni tanlang, PDFni yeching va ID orqali natijani tekshiring.")

    # --- Admin Logic ---
    if text == "⚙️ Admin Panel" and uid == ADMIN_ID:
        btns = [[KeyboardButton("➕ Test qo'shish")], [KeyboardButton("📋 Testlar ro'yxati")], [KeyboardButton("🔙 Orqaga")]]
        return await update.message.reply_text("⚙️ Admin Panel", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if text == "➕ Test qo'shish" and uid == ADMIN_ID:
        data["state"] = "admin_cat"
        btns = [[KeyboardButton("🎓 DTM"), KeyboardButton("📜 MILLIY")]]
        return await update.message.reply_text("Kategoriyani tanlang:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if data.get("state") == "admin_cat":
        data["cat"] = "DTM" if "DTM" in text else "MILLIY"
        data["state"] = "admin_tid"
        return await update.message.reply_text("Test ID yozing (masalan: M1):")

    if data.get("state") == "admin_tid":
        data["tid"] = text.upper()
        data["state"] = "admin_ans"
        return await update.message.reply_text("Javoblarni yuboring (abcde...):")

    if data.get("state") == "admin_ans":
        data["answers"] = re.sub(r"[^a-e]", "", text.lower())
        data["state"] = "pdf"
        return await update.message.reply_text("Endi test PDF faylini yuboring:")

    # --- User Test Logic ---
    if text in ["🎓 DTM", "📜 Milliy Sertifikat"]:
        cat = "DTM" if "DTM" in text else "MILLIY"
        tests = [t for t, c in db["categories"].items() if c == cat]
        if not tests: return await update.message.reply_text("Hozircha testlar yo'q.")
        keyboard = [[InlineKeyboardButton(f"📘 {t}", callback_data=f"test_{t}")] for t in tests]
        return await update.message.reply_text("Testni tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

    if text == "📊 Natijam":
        data["state"] = "check_id"
        return await update.message.reply_text("Tekshirish uchun Test ID'ni kiriting:")

    if data.get("state") == "check_id":
        tid = text.upper()
        if tid in db["answers"]:
            data["state"] = "waiting_ans"; data["check_tid"] = tid
            return await update.message.reply_text(f"Topildi! Javoblarni yuboring:")
        return await update.message.reply_text("Bunday ID yo'q.")

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
        save_data()
        data.clear()
        await update.message.reply_text("✅ Test qo'shildi!", reply_markup=main_keyboard(ADMIN_ID))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("test_", "")
    if tid in db["pdfs"]:
        await query.message.reply_document(db["pdfs"][tid], caption=f"ID: {tid}")

# --- Server qismi ---
ptb_app = Application.builder().token(TOKEN).build()

@flask_app.route("/webhook", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    loop = asyncio.get_event_loop()
    update = Update.de_json(update_data, ptb_app.bot)
    loop.create_task(ptb_app.process_update(update))
    return "OK", 200

@flask_app.route("/")
def index():
    return "✅ Bot ishlamoqda!", 200

async def setup():
    load_data()
    ptb_app.add_handler(CommandHandler("start", start))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    ptb_app.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))
    ptb_app.add_handler(CallbackQueryHandler(button_handler))
    
    await ptb_app.initialize()
    # Webhookni koddagi /webhook manziliga moslab o'rnatish
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(setup())
    
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
