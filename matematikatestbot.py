import logging
import os
import re
import json
import asyncio
from flask import Flask, request
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

# Loglarni sozlash
logging.basicConfig(level=logging.INFO)

# Muhit o'zgaruvchilari (Render'da kiritilishi shart)
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

# ===== DATABASE (Vaqtinchalik) =====
db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

def save_data():
    try:
        with open("data.json", "w") as f:
            json.dump(db, f)
    except Exception as e:
        logging.error(f"Saqlashda xato: {e}")

def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json") as f:
            try:
                db = json.load(f)
            except:
                pass

# ===== KEYBOARDS =====
def main_keyboard(uid):
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
    await update.message.reply_text(
        f"Assalomu alaykum {update.effective_user.first_name}!\nMatematika test botiga xush kelibsiz 🚀", 
        reply_markup=main_keyboard(uid)
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    user_data = context.user_data

    # 1. ORQAGA QAYTISH
    if text == "🔙 Orqaga":
        user_data.clear()
        return await update.message.reply_text("Bosh menyu:", reply_markup=main_keyboard(uid))

    # 2. ADMIN CONTACT
    if text == "👨‍💻 Admin":
        return await update.message.reply_text("Dasturchi: @miracle_1204")

    # 3. KATEGORIYALAR
    menus = {"📘 Matematika DTM": "DTM", "📗 Matematika Milliy Sertifikat": "MILLIY"}
    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]
        if not tests:
            return await update.message.reply_text("❌ Hozircha testlar yuklanmagan.")
        
        buttons = [[KeyboardButton(t)] for t in tests]
        buttons.append([KeyboardButton("🔙 Orqaga")])
        user_data["state"] = "choose"
        return await update.message.reply_text("📑 Testni tanlang:", reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True))

    # 4. PDF YUBORISH (Test tanlanganda)
    if user_data.get("state") == "choose":
        if text in db["pdfs"]:
            file_id = db["pdfs"][text]
            await update.message.reply_document(file_id, caption=f"📑 Test ID: {text}")
            return
        elif text != "🔙 Orqaga":
             return await update.message.reply_text("Iltimos, ro'yxatdagi testlardan birini tanlang.")

    # 5. ADMIN FUNKSIYALARI
    if uid == ADMIN_ID:
        if text == "➕ TEST":
            user_data["state"] = "cat"
            return await update.message.reply_text("Kategoriyani tanlang:\n1 - DTM\n2 - MILLIY", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Orqaga")]], resize_keyboard=True))
        
        if user_data.get("state") == "cat":
            if text in ["1", "2"]:
                user_data["cat"] = "DTM" if text == "1" else "MILLIY"
                user_data["state"] = "id"
                return await update.message.reply_text("Test uchun ID kiriting (masalan: M-01):")
        
        if user_data.get("state") == "id":
            user_data["tid"] = text.upper()
            user_data["state"] = "pdf"
            return await update.message.reply_text(f"{user_data['tid']} uchun PDF faylni yuboring:")

        if text == "🔑 KALIT":
            user_data["state"] = "key_id"
            return await update.message.reply_text("Qaysi test uchun kalit kiritasiz? ID yozing:")

        if user_data.get("state") == "key_id":
            user_data["kid"] = text.upper()
            user_data["state"] = "key_val"
            return await update.message.reply_text(f"{user_data['kid']} uchun kalitlarni yuboring (masalan: abcde...):")

        if user_data.get("state") == "key_val":
            db["answers"][user_data["kid"]] = re.sub(r'[^a-e]', '', text.lower())
            save_data()
            user_data.clear()
            return await update.message.reply_text("✅ Kalitlar muvaffaqiyatli saqlandi!", reply_markup=main_keyboard(uid))

    # 6. NATIJA TEKSHIRISH
    if text == "📊 NATIJA TEKSHIRISH":
        user_data["state"] = "check"
        return await update.message.reply_text("Test ID sini kiriting:", reply_markup=ReplyKeyboardMarkup([[KeyboardButton("🔙 Orqaga")]], resize_keyboard=True))

    if user_data.get("state") == "check":
        tid = text.upper()
        if tid not in db["answers"]:
            return await update.message.reply_text("❌ Bunday ID dagi test topilmadi. Qaytadan urinib ko'ring:")
        user_data["tid"] = tid
        user_data["state"] = "ans"
        return await update.message.reply_text(f"✅ Test topildi. Endi javoblaringizni yuboring (masalan: abcde...):")

    if user_data.get("state") == "ans":
        correct = db["answers"][user_data["tid"]]
        user_ans = re.sub(r'[^a-e]', '', text.lower())
        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        user_data.clear()
        return await update.message.reply_text(
            f"📊 Natijangiz:\n\nTest ID: {user_data.get('tid')}\nTo'g'ri javoblar: {score}\nUmumiy savollar: {len(correct)}",
            reply_markup=main_keyboard(uid)
        )

# PDF fayllarni qabul qilish (Admin uchun)
async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data = context.user_data
    if uid == ADMIN_ID and user_data.get("state") == "pdf":
        tid = user_data["tid"]
        cat = user_data["cat"]
        db["pdfs"][tid] = update.message.document.file_id
        db["categories"][tid] = cat
        save_data()
        user_data.clear()
        await update.message.reply_text(f"✅ {tid} testi bazaga qo'shildi!", reply_markup=main_keyboard(uid))

# ===== WEBHOOK ROUTES =====
@app.route("/")
def home():
    return "Bot is alive!"

@app.route(f"/{TOKEN}", methods=["POST"])
async def webhook():
    if not application.active:
        await application.initialize()
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)
    await application.process_update(update)
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
    asyncio.get_event_loop().run_until_complete(setup())
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
