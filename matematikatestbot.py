import os
import asyncio
import logging
import json
import re
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, Message

# Logging
logging.basicConfig(level=logging.INFO)

# Tokenni olish
TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", 0))

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Ma'lumotlar bazasi (Sizning data.json)
db = {"answers": {}, "pdfs": {}, "categories": {}, "users": []}

def load_data():
    global db
    if os.path.exists("data.json"):
        with open("data.json", "r") as f:
            try: db = json.load(f)
            except: pass

def save_data():
    with open("data.json", "w") as f:
        json.dump(db, f)

# Klaviaturani yaratish funksiyasi
def main_keyboard(uid):
    kb = [
        [KeyboardButton(text="📚 Testlar")],
        [KeyboardButton(text="📊 Natijam"), KeyboardButton(text="👤 Profil")],
        [KeyboardButton(text="ℹ️ Yordam")]
    ]
    if uid == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- Handlers ---

@dp.message(Command("start"))
async def cmd_start(message: Message):
    uid = message.from_user.id
    if uid not in db["users"]:
        db["users"].append(uid)
        save_data()
    await message.answer("Matematika botiga xush kelibsiz!", reply_markup=main_keyboard(uid))

@dp.message(F.text == "📚 Testlar")
async def show_tests(message: Message):
    kb = [
        [KeyboardButton(text="🎓 DTM"), KeyboardButton(text="📜 Milliy Sertifikat")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    await message.answer("Bo'limni tanlang:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

# Admin Panel (Faqat sizga ko'rinadi)
@dp.message(F.text == "⚙️ Admin Panel", F.from_user.id == ADMIN_ID)
async def admin_panel(message: Message):
    kb = [
        [KeyboardButton(text="➕ Test qo'shish")],
        [KeyboardButton(text="🔙 Orqaga")]
    ]
    await message.answer("Admin rejimidasiz:", reply_markup=ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True))

@dp.message(F.text == "🔙 Orqaga")
async def go_back(message: Message):
    await cmd_start(message)

# Botni ishga tushirish
async def main():
    load_data()
    print("Bot ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
