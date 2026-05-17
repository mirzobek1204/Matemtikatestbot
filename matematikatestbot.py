import os
import logging
import re
import json
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
import asyncio

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

flask_app = Flask(__name__)
db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json") as f:
            try: db = json.load(f)
            except: pass

def save_data():
    with open("data.json", "w") as f:
        json.dump(db, f)

def main_keyboard(uid):
    btns = [
        [KeyboardButton("📚 Testlar")],
        [KeyboardButton("📊 Natijam"), KeyboardButton("👤 Profil")],
        [KeyboardButton("ℹ️ Yordam")],
    ]
    if uid == ADMIN_ID:
        btns.append([KeyboardButton("⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

WELCOME = """
╔══════════════════════════╗
║   📐 MATEMATIKA TEST BOT  ║
╚══════════════════════════╝

Assalomu alaykum, {name}! 👋

DTM va Milliy Sertifikat testlarini
ishlash uchun maxsus platformadasiz.

━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 Testlar — Variantlarni ishlash
📊 Natijam — Javoblarni tekshirish
👤 Profil  — Shaxsiy ma'lumotlar
ℹ️ Yordam  — Qo'llanma
━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 Muvaffaqiyatli tayyorgarlik!
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await update.message.reply_text(WELCOME.format(name=name), reply_markup=main_keyboard(uid))

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = context.user_data

    if text == "🔙 Orqaga":
        data.clear()
        return await update.message.reply_text("🏠 Asosiy menyu", reply_markup=main_keyboard(uid))

    if text == "📚 Testlar":
        btns = [[KeyboardButton("🎓 DTM"), KeyboardButton("📜 Milliy Sertifikat")],[KeyboardButton("🔙 Orqaga")]]
        return await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n📚 TEST TURLARI\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎓 DTM — Davlat Test Markazi\n📜 Milliy Sertifikat — Matematika\n\nQaysi bo'limdan?",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if text == "👤 Profil":
        return await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n👤 SHAXSIY PROFIL\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 Ism: {update.effective_user.first_name}\n🆔 ID: {uid}\n\n🎯 Muvaffaqiyatli tayyorgarlik!",
            reply_markup=main_keyboard(uid))

    if text == "ℹ️ Yordam":
        return await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\nℹ️ QO'LLANMA\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ Testlar bo'limiga kiring\n2️⃣ DTM yoki Milliy tanlang\n"
            "3️⃣ Variantni tanlang\n4️⃣ PDF yuklab ishlang\n"
            "5️⃣ Natijam orqali tekshiring",
            reply_markup=main_keyboard(uid))

    if text == "⚙️ Admin Panel" and uid == ADMIN_ID:
        btns = [[KeyboardButton("➕ Test qo'shish")],[KeyboardButton("📋 Testlar ro'yxati"), KeyboardButton("👥 Foydalanuvchilar")],[KeyboardButton("🔙 Orqaga")]]
        return await update.message.reply_text("⚙️ ADMIN PANEL", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if text == "👥 Foydalanuvchilar" and uid == ADMIN_ID:
        return await update.message.reply_text(f"👥 Jami: {len(db['users'])} ta foydalanuvchi")

    if text == "📋 Testlar ro'yxati" and uid == ADMIN_ID:
        if not db["categories"]: return await update.message.reply_text("❌ Testlar yo'q")
        lst = "\n".join([f"• {t} ({c})" for t, c in db["categories"].items()])
        return await update.message.reply_text(f"📋 TESTLAR:\n\n{lst}")

    if text == "➕ Test qo'shish" and uid == ADMIN_ID:
        btns = [[KeyboardButton("🎓 DTM"), KeyboardButton("📜 MILLIY")],[KeyboardButton("🔙 Orqaga")]]
        data["state"] = "admin_cat"
        return await update.message.reply_text("📂 Kategoriya:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if data.get("state") == "admin_cat" and uid == ADMIN_ID:
        cat_map = {"🎓 DTM": "DTM", "📜 MILLIY": "MILLIY"}
        if text in cat_map:
            data["cat"] = cat_map[text]; data["state"] = "admin_tid"
            return await update.message.reply_text("📝 Test ID (masalan: MATH001):")

    if data.get("state") == "admin_tid" and uid == ADMIN_ID:
        data["tid"] = text.upper(); data["state"] = "admin_ans"
        return await update.message.reply_text("🔑 Javoblar (masalan: abcdea):")

    if data.get("state") == "admin_ans" and uid == ADMIN_ID:
        answers = re.sub(r"[^a-e]", "", text.lower())
        data["answers"] = answers; data["state"] = "pdf"
        return await update.message.reply_text(f"✅ Javoblar: {answers}\n\n📎 PDF yuboring:")

    menus = {"🎓 DTM": "DTM", "📜 Milliy Sertifikat": "MILLIY"}
    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]
        if not tests: return await update.message.reply_text("⚠️ Hozircha testlar yo'q!")
        keyboard = [[InlineKeyboardButton(f"📘 {t}", callback_data=f"test_{t}")] for t in tests]
        return await update.message.reply_text("📘 Test tanlang:", reply_markup=InlineKeyboardMarkup(keyboard))

    if text == "📊 Natijam":
        data["state"] = "check"
        return await update.message.reply_text("🔍 Test ID kiriting:")

    if data.get("state") == "check":
        tid = text.upper()
        if tid in db["answers"]:
            data["state"] = "ans"; data["tid"] = tid
            return await update.message.reply_text(f"✅ Topildi! ({len(db['answers'][tid])} savol)\n\n🖊 Javoblarni kiriting:")
        return await update.message.reply_text("❌ Topilmadi. Qayta kiriting:")

    if data.get("state") == "ans":
        correct = db["answers"][data["tid"]]
        user_ans = re.sub(r"[^a-e]", "", text.lower())
        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        total = len(correct)
        percent = int((score/total)*100) if total else 0
        if percent >= 90: baho, tavsif = "A'lo ✨", "Mukammal! Siz zo'rsiz!"
        elif percent >= 70: baho, tavsif = "Yaxshi 👍", "Yaxshi natija! Davom eting!"
        elif percent >= 50: baho, tavsif = "Qoniqarli ⚠️", "Ko'proq mashq kerak!"
        else: baho, tavsif = "Qoniqarsiz ❌", "Ko'proq o'qish kerak!"
        data.clear()
        return await update.message.reply_text(
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 NATIJA\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ To'g'ri: {score}/{total}\n❌ Xato: {total-score}/{total}\n"
            f"📈 Foiz: {percent}%\n🏅 Baho: {baho}\n\n💬 {tavsif}\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=main_keyboard(uid))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("test_", "")
    if tid in db["pdfs"]:
        await query.message.reply_document(db["pdfs"][tid], caption=f"📘 {tid}\n\n«📊 Natijam» orqali tekshiring!")
    else:
        await query.message.reply_text("❌ Fayl yuklanmagan.")

async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if context.user_data.get("state") == "pdf":
        tid = context.user_data["tid"]
        db["answers"][tid] = context.user_data["answers"]
        db["pdfs"][tid] = update.message.document.file_id
        db["categories"][tid] = context.user_data["cat"]
        save_data()
        context.user_data.clear()
        await update.message.reply_text(f"✅ Qo'shildi!\n🆔 {tid}\n📂 {db['categories'][tid]}", reply_markup=main_keyboard(ADMIN_ID))

async def setup_webhook(app):
    await app.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

def create_app():
    load_data()
    ptb_app = Application.builder().token(TOKEN).build()
    ptb_app.add_handler(CommandHandler("start", start))
    ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    ptb_app.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))
    ptb_app.add_handler(CallbackQueryHandler(button_handler))

    async def process(update_data):
      # ... (tepadagi kodlar o'zgarishsiz qoladi)

# Application ob'ektini global yaratib olamiz
ptb_app = Application.builder().token(TOKEN).build()

async def init_bot():
    """Botni bir marta initialize qilish"""
    await ptb_app.initialize()
    await ptb_app.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update_data = request.get_json(force=True)
    # Loopni olish va update'ni asinxron ishlatish
    loop = asyncio.get_event_loop()
    update = Update.de_json(update_data, ptb_app.bot)
    loop.create_task(ptb_app.process_update(update))
    return "OK", 200

@flask_app.route("/")
def index():
    return "✅ Matematika Test Bot ishlayapti!", 200

# Handlerlarni qo'shish
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
ptb_app.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))
ptb_app.add_handler(CallbackQueryHandler(button_handler))

if __name__ == "__main__":
    # Botni ishga tushirish (Initialize)
    asyncio.run(init_bot())
    
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
