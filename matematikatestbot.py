import asyncio
import os
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# CONFIG
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
router = Router()

# USER KEYBOARD
main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📘 Matematika DTM")],
        [KeyboardButton(text="📗 Milliy Sertifikat")],
        [KeyboardButton(text="✅ Kalit tekshirish")],
        [KeyboardButton(text="📞 Admin bilan bog'lanish")]
    ],
    resize_keyboard=True
)

# ADMIN KEYBOARD
admin_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="➕ Test qo'shish")],
        [KeyboardButton(text="🔑 Kalit qo'shish")],
        [KeyboardButton(text="📊 Statistika")]
    ],
    resize_keyboard=True
)

# ANSWER CHECK
correct_answers = "abcdabcd"

def check_answers(user_answers):
    correct = 0
    for i in range(len(correct_answers)):
        if i < len(user_answers) and user_answers[i] == correct_answers[i]:
            correct += 1
    return correct

# START
@router.message(F.text == "/start")
async def start_handler(message: Message):
    await message.answer("Xush kelibsiz!", reply_markup=main_menu)

# USER SECTIONS
@router.message(F.text == "📘 Matematika DTM")
async def dtm(message: Message):
    await message.answer("DTM testlari hali yuklanmagan")

@router.message(F.text == "📗 Milliy Sertifikat")
async def cert(message: Message):
    await message.answer("Milliy sertifikat testlari hali yo‘q")

@router.message(F.text == "✅ Kalit tekshirish")
async def check_prompt(message: Message):
    await message.answer("Javoblarni yubor (masalan: abcdabcd)")

@router.message(F.text == "📞 Admin bilan bog'lanish")
async def contact(message: Message):
    await message.answer("Admin: @username")

# ADMIN PANEL
@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Admin panel", reply_markup=admin_menu)
    else:
        await message.answer("Ruxsat yo‘q")

@router.message(F.text == "📊 Statistika")
async def stats(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Statistika: hali yo‘q")

@router.message(F.text == "➕ Test qo'shish")
async def add_test(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Test qo‘shish keyin yoziladi")

@router.message(F.text == "🔑 Kalit qo'shish")
async def add_key(message: Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Kalit qo‘shish keyin yoziladi")

# ANSWER HANDLER (eng oxirida bo‘lishi shart!)
@router.message()
async def handle_answers(message: Message):
    user_ans = message.text.lower()
    result = check_answers(user_ans)
    await message.answer(f"Natija: {result} ta to‘g‘ri")

# RUN
async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
