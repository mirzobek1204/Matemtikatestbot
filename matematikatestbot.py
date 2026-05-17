import os
import logging
import re
import json
import asyncio
from threading import Thread
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

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

app = Flask(__name__)

db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json") as f:
            try:
                db = json.load(f)
            except:
                pass

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await update.message.reply_text(
        f"👋 Salom, {name}!\n\n"
        f"📚 Matematika Test Botiga xush kelibsiz!\n"
        f"Quyidagi bo'limlardan birini tanlang:",
        reply_markup=main_keyboard(uid)
    )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    data = context.user_data

    if text == "🔙 Orqaga":
        data.clear()
        return await update.message.reply_text("🏠 Asosiy menyu:", reply_markup=main_keyboard(uid))

    if text == "📚 Testlar":
        btns = [
            [KeyboardButton("🎓 DTM"), KeyboardButton("📜 Matematika Milliy Sertifikati")],
            [KeyboardButton("🔙 Orqaga")]
        ]
        return await update.message.reply_text(
            "📚 Qaysi test turini tanlaysiz?",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True)
        )

    if text == "👤 Profil":
        total_users = len(db["users"])
        return await update.message.reply_text(
            f"👤 Profilingiz\n\n"
            f"🆔 ID: {uid}\n"
            f"👥 Jami foydalanuvchilar: {total_users}",
            reply_markup=main_keyboard(uid)
        )

    if text == "ℹ️ Yordam":
        return await update.message.reply_text(
            "ℹ️ Yordam\n\n"
            "📚 Testlar — DTM yoki Milliy Sertifikat testlarini ishlang\n"
            "📊 Natijam — Test javoblaringizni tekshiring\n\n"
            "📩 Muammo bo'lsa: @admin_username",
            reply_markup=main_keyboard(uid)
        )

    
    if text == "⚙️ Admin Panel" and uid == ADMIN_ID:
        btns = [
            [KeyboardButton("➕ Test qo'shish")],
            [KeyboardButton("📋 Testlar ro'yxati"), KeyboardButton("👥 Foydalanuvchilar")],
            [KeyboardButton("🔙 Orqaga")]
        ]
        return await update.message.reply_text(
            "⚙️ Admin Panel:",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True)
        )

    if text == "👥 Foydalanuvchilar" and uid == ADMIN_ID:
        return await update.message.reply_text(
            f"👥 Jami foydalanuvchilar: {len(db['users'])} ta"
        )

    if text == "📋 Testlar ro'yxati" and uid == ADMIN_ID:
        if not db["categories"]:
            return await update.message.reply_text("❌ Hozircha testlar yo'q")
        lst = "\n".join([f"• {t} ({c})" for t, c in db["categories"].items()])
        return await update.message.reply_text(f"📋 Testlar:\n\n{lst}")

    if text == "➕ Test qo'shish" and uid == ADMIN_ID:
        btns = [
            [KeyboardButton("🎓 DTM"), KeyboardButton("📜 MILLIY")],
            [KeyboardButton("🔙 Orqaga")]
        ]
        data["state"] = "admin_cat"
        return await update.message.reply_text(
            "Kategoriya tanlang:",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True)
        )

    if data.get("state") == "admin_cat" and uid == ADMIN_ID:
        cat_map = {"🎓 DTM": "DTM", "📜 MILLIY": "MILLIY"}
        if text in cat_map:
            data["cat"] = cat_map[text]
            data["state"] = "admin_tid"
            return await update.message.reply_text("📝 Test ID kiriting (masalan: MATH001):")

    if data.get("state") == "admin_tid" and uid == ADMIN_ID:
        data["tid"] = text.upper()
        data["state"] = "admin_ans"
        return await update.message.reply_text("🔑 Javoblarni kiriting (masalan: abcdea):")

    if data.get("state") == "admin_ans" and uid == ADMIN_ID:
        answers = re.sub(r"[^a-e]", "", text.lower())
        data["answers"] = answers
        data["state"] = "pdf"
        return await update.message.reply_text(
            f"✅ Javoblar saqlandi: {answers}\n\n📎 Endi PDF faylni yuboring:"
        )

    
    menus = {"🎓 DTM": "DTM", "📜 Matematika Milliy Sertifikati": "MILLIY"}
    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]
        if not tests:
            return await update.message.reply_text("❌ Bu kategoriyada test yo'q")
        keyboard = [[InlineKeyboardButton(f"📘 {t}", callback_data=f"test_{t}")] for t in tests]
        return await update.message.reply_text(
            "📘 Test tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    
    if text == "📊 Natijam":
        data["state"] = "check"
        return await update.message.reply_text("🔍 Test ID kiriting:")

    if data.get("state") == "check":
        tid = text.upper()
        if tid in db["answers"]:
            data["state"] = "ans"
            data["tid"] = tid
            total = len(db["answers"][tid])
            return await update.message.reply_text(
                f"✅ Test topildi! ({total} ta savol)\n\n"
                f"🧠 Javoblaringizni yuboring (masalan: abcdea):"
            )
        return await update.message.reply_text("❌ Bunday ID topilmadi. Qayta kiriting:")

    if data.get("state") == "ans":
        correct = db["answers"][data["tid"]]
        user_ans = re.sub(r"[^a-e]", "", text.lower())
        score = sum(1 for i in range(min(len(correct), len(user_ans))) if user_ans[i] == correct[i])
        total = len(correct)
        percent = int((score / total) * 100) if total else 0

        if percent >= 90:
            emoji = "🏆"
        elif percent >= 70:
            emoji = "✅"
        elif percent >= 50:
            emoji = "⚠️"
        else:
            emoji = "❌"

        data.clear()
        return await update.message.reply_text(
            f"{emoji} NATIJA\n\n"
            f"✅ To'g'ri: {score}/{total}\n"
            f"❌ Xato: {total - score}/{total}\n"
            f"📈 Foiz: {percent}%\n\n"
            f"{'🎉 Ajoyib natija!' if percent >= 90 else '💪 Davom eting!'}",
            reply_markup=main_keyboard(uid)
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    tid = query.data.replace("test_", "")
    if tid in db["pdfs"]:
        await query.message.reply_document(
            db["pdfs"][tid],
            caption=f"📘 {tid} — Test variantlari"
        )
    else:
        await query.message.reply_text("❌ Bu test uchun fayl topilmadi")

async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if context.user_data.get("state") == "pdf":
        tid = context.user_data["tid"]
        db["answers"][tid] = context.user_data["answers"]
        db["pdfs"][tid] = update.message.document.file_id
        db["categories"][tid] = context.user_data["cat"]
        save_data()
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ Test muvaffaqiyatli qo'shildi!\n\n"
            f"🆔 ID: {tid}\n"
            f"📂 Kategoriya: {db['categories'][tid]}",
            reply_markup=main_keyboard(ADMIN_ID)
        )


loop = asyncio.new_event_loop()

def run_loop():
    asyncio.set_event_loop(loop)
    loop.run_forever()

Thread(target=run_loop, daemon=True).start()


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


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), application.bot)
    asyncio.run_coroutine_threadsafe(
        application.process_update(update), loop
    ).result(timeout=30)
    return "OK", 200

@app.route("/")
def index():
    return "✅ Math Test Bot ishlayapti!", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
