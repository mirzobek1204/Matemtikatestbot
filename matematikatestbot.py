import logging
import os
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

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

app = Flask(__name__)
application = Application.builder().token(TOKEN).build()

db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}


# ================= DB =================
def save_data():
    with open("data.json", "w") as f:
        json.dump(db, f)


def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json") as f:
            try:
                db = json.load(f)
            except:
                pass


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


# ================= UX HELPER =================
async def ux(msg, delay=0.4):
    await asyncio.sleep(delay)
    return msg


# ================= START =================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    name = update.effective_user.first_name

    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()

    await update.message.reply_text("👋 Yuklanmoqda...")
    await asyncio.sleep(0.5)

    await update.message.reply_text(
        f"📚  Assalomu alaykum, {name}!\n\nTest botimizga xush kelibsiz 🚀",
        reply_markup=main_keyboard(uid),
    )


# ================= MAIN HANDLER =================
async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    user_data = context.user_data

    if text == "🔙 Orqaga":
        user_data.clear()
        return await update.message.reply_text("Menyu:", reply_markup=main_keyboard(uid))

    # ===== TEST MENU =====
    if text == "📚 Testlar":
        btns = [
            [KeyboardButton("🎓 DTM"), KeyboardButton("📜 Matematika Milliy Sertifikati")],
            [KeyboardButton("🔙 Orqaga")],
        ]
        return await update.message.reply_text(
            "📚 Test bo‘limi\n\nTanlang:",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True),
        )

    # ===== CATEGORY MAP =====
    menus = {
        "🎓 DTM": "DTM",
        "📜 Matematika Milliy Sertifikati": "MILLIY",
    }

    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]

        if not tests:
            return await update.message.reply_text("❌ Test yo‘q")

        keyboard = []
        row = []
        for i, t in enumerate(tests, 1):
            row.append(InlineKeyboardButton(t, callback_data=f"test_{t}"))
            if i % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)

        return await update.message.reply_text(
            "📘 Test tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    # ===== NATIJA =====
    if text == "📊 Natijam":
        user_data["state"] = "check"
        return await update.message.reply_text("Test ID yuboring:")

    if user_data.get("state") == "check":
        tid = text.upper()
        if tid in db["answers"]:
            user_data["state"] = "ans"
            user_data["tid"] = tid
            return await update.message.reply_text("🧠 Tekshirilmoqda...")
        return await update.message.reply_text("❌ Topilmadi")

    if user_data.get("state") == "ans":
        await update.message.reply_text("🧠 Tekshirilmoqda...")
        await asyncio.sleep(1)

        correct = db["answers"][user_data["tid"]]
        user_ans = re.sub(r"[^a-e]", "", text.lower())

        score = sum(
            1 for i in range(min(len(correct), len(user_ans)))
            if user_ans[i] == correct[i]
        )

        percent = int((score / len(correct)) * 100)

        user_data.clear()

        await asyncio.sleep(0.3)

        return await update.message.reply_text(
            f"📊 NATIJANGIZ\n\n"
            f"✅ To‘g‘ri: {score}\n"
            f"❌ Xato: {len(correct)-score}\n"
            f"📈 Foiz: {percent}%",
            reply_markup=main_keyboard(uid),
        )

    # ===== ADMIN =====
    if uid == ADMIN_ID:
        if text == "⚙️ Admin Panel":
            btns = [
                [KeyboardButton("➕ Test qo‘shish")],
                [KeyboardButton("🔑 Kalit qo‘shish")],
                [KeyboardButton("📊 Statistika")],
                [KeyboardButton("🔙 Orqaga")],
            ]
            return await update.message.reply_text(
                "⚙️ Admin Panel",
                reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True),
            )

        if text == "➕ Test qo‘shish":
            user_data["state"] = "cat"
            return await update.message.reply_text("1-DTM, 2-MILLIY")

        if user_data.get("state") == "cat":
            user_data["cat"] = "DTM" if text == "1" else "MILLIY"
            user_data["state"] = "id"
            return await update.message.reply_text("ID yozing:")

        if user_data.get("state") == "id":
            user_data["tid"] = text.upper()
            user_data["state"] = "pdf"
            return await update.message.reply_text("PDF yuboring:")

        if text == "🔑 Kalit qo‘shish":
            user_data["state"] = "key_id"
            return await update.message.reply_text("Test ID:")

        if user_data.get("state") == "key_id":
            user_data["kid"] = text.upper()
            user_data["state"] = "key_val"
            return await update.message.reply_text("Kalit:")

        if user_data.get("state") == "key_val":
            db["answers"][user_data["kid"]] = re.sub(r"[^a-e]", "", text.lower())
            save_data()
            user_data.clear()
            return await update.message.reply_text("✅ Saqlandi", reply_markup=main_keyboard(uid))


# ================= CALLBACK =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data.startswith("test_"):
        tid = data.replace("test_", "")

        await query.message.reply_text("⏳ Yuklanmoqda...")
        await asyncio.sleep(0.8)

        if tid in db["pdfs"]:
            await query.message.reply_document(db["pdfs"][tid])


# ================= PDF =================
async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        if context.user_data.get("state") == "pdf":
            await update.message.reply_text("📥 Saqlanmoqda...")
            await asyncio.sleep(0.5)

            tid = context.user_data["tid"]

            db["pdfs"][tid] = update.message.document.file_id
            db["categories"][tid] = context.user_data["cat"]

            save_data()
            context.user_data.clear()

            await update.message.reply_text("✅ Saqlandi")


# ================= WEB =================
@app.route("/")
def home():
    return "Bot alive"


@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, application.bot)

    loop = asyncio.get_event_loop()
    loop.create_task(application.process_update(update))

    return "ok"


# ================= INIT =================
async def setup():
    load_data()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))
    application.add_handler(CallbackQueryHandler(button_handler))

    await application.initialize()
    await application.start()
    await application.bot.set_webhook(f"{WEBHOOK_URL}/{TOKEN}")


if __name__ == "__main__":
    asyncio.run(setup())
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
