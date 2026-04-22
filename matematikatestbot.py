import os
import logging
import re
import json
import asyncio
from flask import Flask, request
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# Logging sozlamalari
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

# Muhit o'zgaruvchilari
TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

# Flask ilovasi (Render uchun)
server = Flask(__name__)

# Bot ilovasi
application = Application.builder().token(TOKEN).build()

db = {
    "answers": {},
    "pdfs": {},
    "categories": {},
    "users": []
}

# ================= DB =================
def load_data():
    global db
    if os.path.exists("data.json"):
        try:
            with open("data.json", "r") as f:
                content = f.read()
                if content:
                    db = json.loads(content)
        except Exception as e:
            logging.error(f"DB yuklashda xato: {e}")

def save_data():
    try:
        with open("data.json", "w") as f:
            json.dump(db, f)
    except Exception as e:
        logging.error(f"DB saqlashda xato: {e}")

# ================= UI =================
def main_keyboard(uid):
    btns = [
        [KeyboardButton("📚 Testlar")],
        [KeyboardButton("📊 Natijam"), KeyboardButton("👤 Profil")],
        [KeyboardButton("ℹ️ Yordam")],
    ]
    if uid == ADMIN_ID:
        btns.append([KeyboardButton("⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name

    if uid not in db.get("users", []):
        if "users" not in db: db["users"] = []
        db["users"].append(uid)
        save_data()

    await update.message.reply_text(
        f"👋 Salom {name}\n\n📚 Test bot ishlayapti.",
        reply_markup=main_keyboard(uid)
    )

# ================= MAIN =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = context.user_data

    if text == "🔙 Orqaga":
        data.clear()
        return await update.message.reply_text("Menyu", reply_markup=main_keyboard(uid))

    if text == "📚 Testlar":
        btns = [
            [KeyboardButton("🎓 DTM"), KeyboardButton("📜 Matematika Milliy Sertifikati")],
            [KeyboardButton("🔙 Orqaga")]
        ]
        return await update.message.reply_text(
            "📚 Testlar bo'limi:",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True)
        )

    menus = {"🎓 DTM": "DTM", "📜 Matematika Milliy Sertifikati": "MILLIY"}

    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db.get("categories", {}).items() if c == cat]

        if not tests:
            return await update.message.reply_text("❌ Hozircha testlar mavjud emas.")

        keyboard = []
        for t in tests:
            keyboard.append([InlineKeyboardButton(f"📝 {t}", callback_data=f"test_{t}")])

        return await update.message.reply_text(
            "📘 Testlardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    if text == "📊 Natijam":
        data["state"] = "check"
        return await update.message.reply_text("Test ID sini yuboring (Masalan: 1234):")

    if data.get("state") == "check":
        tid = text.upper()
        if tid in db.get("answers", {}):
            data["state"] = "ans"
            data["tid"] = tid
            return await update.message.reply_text("Javoblaringizni yuboring (Masalan: abcd...):")
        return await update.message.reply_text("❌ Bunday ID dagi test topilmadi.")

    if data.get("state") == "ans":
        correct = db["answers"][data["tid"]]
        user_ans = re.sub(r"[^a-e]", "", text.lower())

        if not user_ans:
            return await update.message.reply_text("⚠️ Iltimos, faqat a, b, c, d, e harflaridan foydalanib javob yuboring.")

        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        percent = int((score / len(correct)) * 100) if len(correct) > 0 else 0
        
        data.clear()
        return await update.message.reply_text(
            f"📊 NATIJA\n\n✅ To‘g‘ri: {score}\n❌ Xato: {len(correct)-score}\n📈 Foiz: {percent}%",
            reply_markup=main_keyboard(uid)
        )

# ================= CALLBACK =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("test_", "")

    if tid in db.get("pdfs", {}):
        await query.message.reply_text(f"⏳ {tid} - test yuklanmoqda...")
        await query.message.reply_document(db["pdfs"][tid])
    else:
        await query.message.reply_text("❌ PDF fayl topilmadi.")

# ================= WEBHOOK ROUTE =================
@server.route(f"/{TOKEN}", methods=["POST"])
async def webhook(): # async qo'shdik
    if request.method == "POST":
        # Bot hali tayyor bo'lmasa, initialize qilamiz
        if not application.updater:
            await application.initialize()
            await application.start()
            
        update = Update.de_json(request.get_json(force=True), application.bot)
        await application.process_update(update)
        return "OK", 200
    return "Forbidden", 403

# ================= INIT =================
async def setup():
    load_data()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # Webhookni o'rnatish
    await application.bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

if __name__ == "__main__":
    # Setup funksiyasini faqat bazani yuklash va webhook o'rnatish uchun qoldiramiz
    load_data()
    
    # Webhookni botga ulab qo'yamiz (buni async qilish shart emas bu yerda)
    # Lekin eng yaxshisi Flaskni oddiy ishga tushirib, birinchi request kelganda botni yoqish
    
    port = int(os.environ.get("PORT", 8080))
    server.run(host="0.0.0.0", port=port)
