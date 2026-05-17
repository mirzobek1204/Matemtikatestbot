import os
import logging
import re
import json
from threading import Thread
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters

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
            "🎓 DTM — Davlat Test Markazi\n📜 Milliy Sertifikat — Matematika\n\nQaysi bo'limdan test ishlaysiz?",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if text == "👤 Profil":
        return await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n👤 SHAXSIY PROFIL\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📛 Ism: {update.effective_user.first_name}\n🆔 ID: {uid}\n\n🎯 Muvaffaqiyatli tayyorgarlik!",
            reply_markup=main_keyboard(uid))

    if text == "ℹ️ Yordam":
        return await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\nℹ️ FOYDALANISH QO'LLANMASI\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "1️⃣ «📚 Testlar» bo'limiga kiring\n2️⃣ DTM yoki Milliy Sertifikat tanlang\n"
            "3️⃣ Test variantini tanlang\n4️⃣ PDF ni yuklab oling va ishlang\n"
            "5️⃣ «📊 Natijam» orqali tekshiring\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📩 Muammo bo'lsa admin bilan bog'laning",
            reply_markup=main_keyboard(uid))

    if text == "⚙️ Admin Panel" and uid == ADMIN_ID:
        btns = [[KeyboardButton("➕ Test qo'shish")],[KeyboardButton("📋 Testlar ro'yxati"), KeyboardButton("👥 Foydalanuvchilar")],[KeyboardButton("🔙 Orqaga")]]
        return await update.message.reply_text("━━━━━━━━━━━━━━━━━━━━━━━━━━\n⚙️ ADMIN PANEL\n━━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if text == "👥 Foydalanuvchilar" and uid == ADMIN_ID:
        return await update.message.reply_text(
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n👥 FOYDALANUVCHILAR\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📊 Jami: {len(db['users'])} ta foydalanuvchi")

    if text == "📋 Testlar ro'yxati" and uid == ADMIN_ID:
        if not db["categories"]: return await update.message.reply_text("❌ Hozircha testlar mavjud emas.")
        lst = "\n".join([f"  • {t} ({c})" for t, c in db["categories"].items()])
        return await update.message.reply_text(f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n📋 TESTLAR\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n{lst}")

    if text == "➕ Test qo'shish" and uid == ADMIN_ID:
        btns = [[KeyboardButton("🎓 DTM"), KeyboardButton("📜 MILLIY")],[KeyboardButton("🔙 Orqaga")]]
        data["state"] = "admin_cat"
        return await update.message.reply_text("📂 Kategoriyani tanlang:", reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True))

    if data.get("state") == "admin_cat" and uid == ADMIN_ID:
        cat_map = {"🎓 DTM": "DTM", "📜 MILLIY": "MILLIY"}
        if text in cat_map:
            data["cat"] = cat_map[text]; data["state"] = "admin_tid"
            return await update.message.reply_text("📝 Test ID kiriting (masalan: MATH001):")

    if data.get("state") == "admin_tid" and uid == ADMIN_ID:
        data["tid"] = text.upper(); data["state"] = "admin_ans"
        return await update.message.reply_text("🔑 Javoblar kalitini kiriting (masalan: abcdea):")

    if data.get("state") == "admin_ans" and uid == ADMIN_ID:
        answers = re.sub(r"[^a-e]", "", text.lower())
        data["answers"] = answers; data["state"] = "pdf"
        return await update.message.reply_text(f"✅ Javoblar qabul qilindi: {answers}\n\n📎 PDF faylni yuboring:")

    menus = {"🎓 DTM": "DTM", "📜 Milliy Sertifikat": "MILLIY"}
    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]
        if not tests: return await update.message.reply_text("⚠️ Bu bo'limda hozircha testlar mavjud emas.\nTez orada qo'shiladi!")
        keyboard = [[InlineKeyboardButton(f"📘 {t}", callback_data=f"test_{t}")] for t in tests]
        return await update.message.reply_text(
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n📘 TEST VARIANTLARI\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\nVariantni tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard))

    if text == "📊 Natijam":
        data["state"] = "check"
        return await update.message.reply_text("━━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 NATIJA TEKSHIRISH\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n🔍 Test ID kiriting:")

    if data.get("state") == "check":
        tid = text.upper()
        if tid in db["answers"]:
            data["state"] = "ans"; data["tid"] = tid
            return await update.message.reply_text(f"✅ Test topildi! ({len(db['answers'][tid])} savol)\n\n🖊 Javoblarni kiriting (masalan: abcdea):")
        return await update.message.reply_text("❌ Topilmadi. To'g'ri ID kiriting:")

    if data.get("state") == "ans":
        correct = db["answers"][data["tid"]]
        user_ans = re.sub(r"[^a-e]", "", text.lower())
        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        total = len(correct)
        percent = int((score/total)*100) if total else 0
        if percent >= 90: baho, tavsif = "A'lo ✨", "Mukammal natija! Siz zo'rsiz!"
        elif percent >= 70: baho, tavsif = "Yaxshi 👍", "Yaxshi natija! Davom eting!"
        elif percent >= 50: baho, tavsif = "Qoniqarli ⚠️", "Ko'proq mashq qilish zarur!"
        else: baho, tavsif = "Qoniqarsiz ❌", "Ko'proq o'qish kerak!"
        data.clear()
        return await update.message.reply_text(
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━\n📊 NATIJA\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"✅ To'g'ri: {score}/{total}\n❌ Xato:   {total-score}/{total}\n📈 Foiz:   {percent}%\n🏅 Baho:   {baho}\n\n"
            f"💬 {tavsif}\n━━━━━━━━━━━━━━━━━━━━━━━━━━",
            reply_markup=main_keyboard(uid))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("test_", "")
    if tid in db["pdfs"]:
        await query.message.reply_document(db["pdfs"][tid], caption=f"📘 {tid}\n\nIshlang va «📊 Natijam» orqali tekshiring!")
    else:
        await query.message.reply_text("❌ Fayl hali yuklanmagan.")

async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    if context.user_data.get("state") == "pdf":
        tid = context.user_data["tid"]
        db["answers"][tid] = context.user_data["answers"]
        db["pdfs"][tid] = update.message.document.file_id
        db["categories"][tid] = context.user_data["cat"]
        save_data()
        context.user_data.clear()
        await update.message.reply_text(f"✅ Test qo'shildi!\n\n🆔 ID: {tid}\n📂 Kategoriya: {db['categories'][tid]}", reply_markup=main_keyboard(ADMIN_ID))

loop = asyncio.new_event_loop()
Thread(target=lambda: (asyncio.set_event_loop(loop), loop.run_forever()), daemon=True).start()

load_data()
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
application.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))
application.add_handler(CallbackQueryHandler(button_handler))

async def init_app():
    await application.initialize()
    await application.start()
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

asyncio.run_coroutine_threadsafe(init_app(), loop).result(timeout=30)

@flask_app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run_coroutine_threadsafe(application.process_update(update), loop).result(timeout=30)
    return "OK", 200

@flask_app.route("/")
def index(): return "✅ Matematika Test Bot ishlayapti!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host="0.0.0.0", port=port)
