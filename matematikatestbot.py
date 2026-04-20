import os
import logging
import re
import json

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
        with open("data.json") as f:
            try:
                db = json.load(f)
            except:
                pass


def save_data():
    with open("data.json", "w") as f:
        json.dump(db, f)


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

    if uid not in db["users"]:
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

    # ===== TEST MENU =====
    if text == "📚 Testlar":
        btns = [
            [KeyboardButton("🎓 DTM"), KeyboardButton("📜 Matematika Milliy Sertifikati")],
            [KeyboardButton("🔙 Orqaga")]
        ]
        return await update.message.reply_text(
            "📚 Testlar:",
            reply_markup=ReplyKeyboardMarkup(btns, resize_keyboard=True)
        )

    menus = {
        "🎓 DTM": "DTM",
        "📜 Matematika Milliy Sertifikati": "MILLIY",
    }

    if text in menus:
        cat = menus[text]
        tests = [t for t, c in db["categories"].items() if c == cat]

        if not tests:
            return await update.message.reply_text("❌ Test yo‘q")

        keyboard = [
            [InlineKeyboardButton(t, callback_data=f"test_{t}") for t in tests]
        ]

        return await update.message.reply_text(
            "📘 Test tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ===== RESULT =====
    if text == "📊 Natijam":
        data["state"] = "check"
        return await update.message.reply_text("Test ID kiriting:")

    if data.get("state") == "check":
        tid = text.upper()
        if tid in db["answers"]:
            data["state"] = "ans"
            data["tid"] = tid
            return await update.message.reply_text("🧠 Tekshirilmoqda...")
        return await update.message.reply_text("❌ Topilmadi")

    if data.get("state") == "ans":
        correct = db["answers"][data["tid"]]
        user_ans = re.sub(r"[^a-e]", "", text.lower())

        score = sum(
            1 for i in range(min(len(correct), len(user_ans)))
            if user_ans[i] == correct[i]
        )

        percent = int((score / len(correct)) * 100)

        data.clear()

        return await update.message.reply_text(
            f"📊 NATIJA\n\n"
            f"✅ To‘g‘ri: {score}\n"
            f"❌ Xato: {len(correct)-score}\n"
            f"📈 Foiz: {percent}%",
            reply_markup=main_keyboard(uid)
        )


# ================= CALLBACK =================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    tid = query.data.replace("test_", "")

    await query.message.reply_text("⏳ Yuklanmoqda...")

    if tid in db["pdfs"]:
        await query.message.reply_document(db["pdfs"][tid])


# ================= PDF =================
async def pdf_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        if context.user_data.get("state") == "pdf":
            tid = context.user_data["tid"]

            db["pdfs"][tid] = update.message.document.file_id
            db["categories"][tid] = context.user_data["cat"]

            save_data()
            context.user_data.clear()

            await update.message.reply_text("✅ Saqlandi")


# ================= INIT =================
def main():
    load_data()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    application.add_handler(MessageHandler(filters.Document.PDF, pdf_handler))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
    )


if __name__ == "__main__":
    main()
