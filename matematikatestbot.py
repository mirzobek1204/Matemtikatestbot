import logging
import os
import re
import json
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
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
            try: 
                db = json.load(f)
            except: 
                pass

def main_keyboard(uid):
    btns = [[KeyboardButton("📘 Matematika DTM")], [KeyboardButton("📗 Matematika Milliy Sertifikat")],
            [KeyboardButton("📊 NATIJA TEKSHIRISH")], [KeyboardButton("👨‍💻 Admin")]]
    if uid == ADMIN_ID:
        btns.append([KeyboardButton("➕ TEST"), KeyboardButton("🔑 KALIT")])
        btns.append([KeyboardButton("📈 STATISTIKA")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    first_name = update.effective_user.first_name
    
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()

    welcome_text = (
        f"👋 **Assalomu alaykum, {first_name}!**\n\n"
        "🤖 **Matematika Test Botiga xush kelibsiz!**\n\n"
        "Ushbu bot orqali siz:\n"
        "🔹 DTM va Milliy sertifikat testlarini yuklab olishingiz;\n"
        "🔹 Test javoblarini yuborib, natijangizni bilishingiz;\n"
        "🔹 Bilimingizni doimiy tekshirib borishingiz mumkin.\n\n"
        "👇 **Boshlash uchun quyidagi menyudan foydalaning:**"
    )

    await update.message.reply_text(
        text=welcome_text,
        reply_markup=main_keyboard(uid),
        parse_mode="Markdown"
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    user_data = context.user_data

    if text == "🔙 Orqaga":
        user_data.clear()
        return await update.message.reply_text("Menyu:", reply_markup=main_keyboard(uid))

    if text == "👨‍💻 Admin":
        keyboard = [[InlineKeyboardButton("📩 Bog'lanish", url="https://t.me/miracle_1204")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        return await update.message.reply_text(
            "👨‍💻 Admin bilan bog'lanish uchun quyidagi tugmani bosing:",
            reply_markup=reply_markup
        )

    menus = {"📘 Matematika DTM": "DTM", "📗 Matematika Milliy Sertifikat": "MILLIY"}
    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]
        if not tests: 
            return await update.message.reply_text("❌ Hozircha testlar mavjud emas keyinroq urinib ko'ring:")
        btns = [[KeyboardButton(t)] for t in tests]
        btns.append([KeyboardButton("🔙 Orqaga")])
        user_data["state"] = "choose"
        return await update.message.reply_text("Tanlang:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if user_data.get("state") == "choose" and text in db["pdfs"]:
        return await update.message.reply_document(db["pdfs"][text])

    if text == "📊 NATIJA TEKSHIRISH":
        user_data["state"] = "check"
        return await update.message.reply_text("Test ID yozing:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Orqaga")]], resize_keyboard=True))

    if user_data.get("state") == "check":
        tid = text.upper()
        if tid in db["answers"]:
            user_data.update({"state": "ans", "tid": tid})
            return await update.message.reply_text("Javoblarni yuboring:")
        return await update.message.reply_text("❌ Bunday ID dagi test topilmadi.")

    if user_data.get("state") == "ans":
        correct = db["answers"][user_data["tid"]]
        user_ans = re.sub(r'[^a-e]', '', text.lower())
        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        user_data.clear()
        return await update.message.reply_text(f"Natija: {score}/{len(correct)}", reply_markup=main_keyboard(uid))

    if uid == ADMIN_ID:
        if text == "➕ TEST":
            user_data["state"] = "cat"
            return await update.message.reply_text("1-DTM, 2-MILLIY")
        
        if text == "📈 STATISTIKA":
            users_count = len(db.get("users", []))
            tests_count = len(db.get("pdfs", {}))
            keys_count = len(db.get("answers", {}))
            stat_msg = (
                "📊 **Bot Statistikasi:**\n\n"
                f"👤 Foydalanuvchilar: {users_count} ta\n"
                f"📂 Jami testlar: {tests_count} ta\n"
                f"🔑 Kalitlar bazasi: {keys_count} ta\n"
            )
            return await update.message.reply_text(stat_msg, parse_mode="Markdown")

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
