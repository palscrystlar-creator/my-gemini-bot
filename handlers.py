from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from groq import Groq

router = Router()
ai_client = Groq(api_key="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")

# 1. Tugmalar menyusi
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 IELTS Mock", callback_data="start_mock")],
        [InlineKeyboardButton(text="📖 Ovozli hikoya", callback_data="start_story")],
        [InlineKeyboardButton(text="🧮 Matematika", callback_data="start_math")]
    ])

# 2. /start buyrug'i uchun menyuni chaqirish
@router.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Salom! Quyidagi menyudan kerakli bo'limni tanlang:", reply_markup=get_main_menu())

# 3. Tugmalarga javob beruvchi callback handlerlar
@router.callback_query(F.data == "start_mock")
async def mock_callback(callback: types.CallbackQuery):
    await callback.message.answer("Mock test boshlandi! Savol: Where are you from?")
    await callback.answer()

@router.callback_query(F.data == "start_story")
async def story_callback(callback: types.CallbackQuery):
    await callback.message.answer("Hikoya mavzusini yozing (masalan: /story Mars)")
    await callback.answer()

@router.callback_query(F.data == "start_math")
async def math_callback(callback: types.CallbackQuery):
    await callback.message.answer("Matematik misolni yozing (masalan: 25 * 4):")
    await callback.answer()

# 4. Oddiy matn va matematika uchun handler
@router.message(F.text & ~F.text.startswith("/"))
async def global_handler(message: types.Message):
    # Matematikani aniqlash va yechish
    if any(op in message.text for op in ["+", "-", "*", "/"]):
        comp = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": f"Ushbu misolni yechib ber va tushuntir: {message.text}"}], 
            model="llama-3.3-70b-versatile"
        )
        await message.answer(comp.choices[0].message.content)
    else:
        # Oddiy chat
        comp = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": message.text}], 
            model="llama-3.3-70b-versatile"
        )
        await message.answer(comp.choices[0].message.content)
