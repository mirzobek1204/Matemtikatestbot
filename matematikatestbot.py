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
ADMIN_ID = int(os.getenv("ADMIN_ID"))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ===== DATABASE =====
db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

def save_data():
    with open("data.json", "w") as f:
        json.dump(db, f)

def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json") as f:
            db = json.load(f)

# ===== KEYBOARD =====
def keyboard(uid):
    btns = [
        [KeyboardButton("📘 Matematika DTM")],
        [KeyboardButton("📗 Matematika Milliy Sertifikat")],
        [KeyboardButton("📊 NATIJA TEKSHIRISH")],
        [KeyboardButton("👨‍💻 Admin")]
    ]
    if uid == ADMIN_ID:
        btns.append([KeyboardButton("➕ TEST"), KeyboardButton("🔑 KALIT")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# ===== HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await update.message.reply_text("Bot ishlayapti 🚀", reply_markup=keyboard(uid))

async def message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    user_data = context.user_data

    # ADMIN CONTACT
    if text == "👨‍💻 Admin":
        return await update.message.reply_text("@miracle_1204")

    # ===== CATEGORY =====
    menus = {
        "📘 Matematika DTM": "DTM",
        "📗 Matematika Milliy Sertifikat": "MILLIY"
    }

    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]

        if not tests:
            return await update.message.reply_text("❌ Testlar yo‘q")

        buttons = [[KeyboardButton(t)] for t in tests]
        context.user_data["state"] = "choose"

        return await update.message.reply_text(
            "📑 Testni tanlang:",
            reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True)
        )

    # PDF yuborish
    if context.user_data.get("state") == "choose":
        if text in db["pdfs"]:
            path = db["pdfs"][text]
            if os.path.exists(path):
                with open(path, "rb") as f:
                    await update.message.reply_document(f)

    # ===== ADMIN =====
    if uid == ADMIN_ID:

        if text == "➕ TEST":
            user_data["state"] = "cat"
            return await update.message.reply_text("1-DTM\n2-MILLIY")

        if user_data.get("state") == "cat":
            if text == "1":
                user_data["cat"] = "DTM"
            elif text == "2":
                user_data["cat"] = "MILLIY"
            else:
                return
            user_data["state"] = "id"
            return await update.message.reply_text("ID yoz (M-01):")

        if user_data.get("state") == "id":
            user_data["tid"] = text.upper()
            user_data["state"] = "pdf"
            return await update.message.reply_text("PDF yubor")

        if text == "🔑 KALIT":
            user_data["state"] = "key_id"
            return await update.message.reply_text("Test ID")

        if user_data.get("state") == "key_id":
            user_data["kid"] = text.upper()
            user_data["state"] = "key_val"
            return await update.message.reply_text("Kalit yubor")

        if user_data.get("state") == "key_val":
            db["answers"][user_data["kid"]] = re.sub(r'[^a-e]', '', text.lower())
            save_data()
            user_data.clear()
            return await update.message.reply_text("✅ Saqlandi")

    # ===== RESULT =====
    if text == "📊 NATIJA TEKSHIRISH":
        user_data["state"] = "check"
        return await update.message.reply_text("Test ID yoz")

    if user_data.get("state") == "check":
        tid = text.upper()
        if tid not in db["answers"]:
            return await update.message.reply_text("❌ Topilmadi")
        user_data["tid"] = tid
        user_data["state"] = "ans"
        return await update.message.reply_text("Javob yubor")

    if user_data.get("state") == "ans":
        correct = db["answers"][user_data["tid"]]
        user = re.sub(r'[^a-e]', '', text.lower())
        score = sum(1 for i in range(len(correct)) if i < len(user) and user[i] == correct[i])
        user_data.clear()
        return await update.message.reply_text(f"📊 {score}/{len(correct)}")

# ===== PDF =====
async def pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid == ADMIN_ID and context.user_data.get("state") == "pdf":
        tid = context.user_data["tid"]
        cat = context.user_data["cat"]

        file = await context.bot.get_file(update.message.document.file_id)
        path = f"{tid}.pdf"
        await file.download_to_drive(path)

        db["pdfs"][tid] = path
        db["categories"][tid] = cat
        save_data()

        context.user_data.clear()
        await update.message.reply_text("✅ Yuklandi")

# ===== ROUTES =====
@app.route("/")
def home():
    return "LIVE"

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
    return "ok"

# ===== START =====
if __name__ == "__main__":
    load_data()

    asyncio.run(application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}"))

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message))
    application.add_handler(MessageHandler(filters.Document.PDF, pdf))

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
