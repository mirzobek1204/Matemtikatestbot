import logging
import os
import re
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters

# ===== LOGGING =====
logging.basicConfig(level=logging.INFO)

# ===== CONFIG =====
ADMIN_ID = 6257157305
TOKEN = os.getenv("BOT_TOKEN")

# ===== DATABASE (simple json) =====
db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

def save_data():
    with open("data.json", "w") as f:
        json.dump(db, f, indent=4)

def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            db = json.load(f)

# ===== KEYBOARDS =====
def main_keyboard(uid):
    btns = [
        [KeyboardButton("📊 NATIJA TEKSHIRISH")],
        [KeyboardButton("👨‍💻 Adminga bog'lanish")]
    ]
    if uid == ADMIN_ID:
        btns.append([KeyboardButton("➕ TEST QO'SHISH"), KeyboardButton("🔑 KALIT QO'SHISH")])
    return ReplyKeyboardMarkup(btns, resize_keyboard=True)

def back_keyboard():
    return ReplyKeyboardMarkup([[KeyboardButton("🔙 MENU")]], resize_keyboard=True)

# ===== START =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await update.message.reply_text("👋 Xush kelibsiz!", reply_markup=main_keyboard(uid))

# ===== MAIN HANDLER =====
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    uid = update.effective_user.id
    user_data = context.user_data

    if text == "🔙 MENU":
        user_data.clear()
        return await update.message.reply_text("🏠 Menu", reply_markup=main_keyboard(uid))

    if text == "👨‍💻 Adminga bog'lanish":
        return await update.message.reply_text("Admin: @miracle_1204")

    # ===== ADMIN =====
    if uid == ADMIN_ID:

        if text == "➕ TEST QO'SHISH":
            user_data['state'] = "test_id"
            return await update.message.reply_text("Test ID yozing (M-01):")

        if user_data.get('state') == "test_id":
            user_data['test_id'] = text.upper()
            user_data['state'] = "pdf"
            return await update.message.reply_text("PDF yuboring:")

        if text == "🔑 KALIT QO'SHISH":
            user_data['state'] = "key_id"
            return await update.message.reply_text("Test ID yozing:")

        if user_data.get('state') == "key_id":
            user_data['key_id'] = text.upper()
            user_data['state'] = "key_value"
            return await update.message.reply_text("Kalitlarni yuboring (abcd...):")

        if user_data.get('state') == "key_value":
            db["answers"][user_data["key_id"]] = re.sub(r'[^a-e]', '', text.lower())
            save_data()
            user_data.clear()
            return await update.message.reply_text("✅ Kalit saqlandi", reply_markup=main_keyboard(uid))

    # ===== RESULT CHECK =====
    if text == "📊 NATIJA TEKSHIRISH":
        user_data['state'] = "check_id"
        return await update.message.reply_text("Test ID yozing:", reply_markup=back_keyboard())

    if user_data.get('state') == "check_id":
        tid = text.upper()
        if tid not in db["answers"]:
            return await update.message.reply_text("❌ Topilmadi")
        user_data['check_id'] = tid
        user_data['state'] = "check_ans"
        return await update.message.reply_text("Javoblarni yuboring:")

    if user_data.get('state') == "check_ans":
        correct = db["answers"][user_data["check_id"]]
        user_ans = re.sub(r'[^a-e]', '', text.lower())

        score = sum(1 for i in range(len(correct)) if i < len(user_ans) and user_ans[i] == correct[i])

        user_data.clear()
        return await update.message.reply_text(f"📊 Natija: {score}/{len(correct)}", reply_markup=main_keyboard(uid))

# ===== PDF HANDLE =====
async def handle_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    user_data = context.user_data

    if uid == ADMIN_ID and user_data.get('state') == "pdf":
        tid = user_data['test_id']
        file = await context.bot.get_file(update.message.document.file_id)

        path = f"{tid}.pdf"
        await file.download_to_drive(path)

        db["pdfs"][tid] = path
        save_data()

        user_data.clear()
        await update.message.reply_text("✅ Test yuklandi", reply_markup=main_keyboard(uid))

# ===== RUN =====
if __name__ == "__main__":
    load_data()

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.Document.PDF, handle_pdf))

    app.run_polling(drop_pending_updates=True)
