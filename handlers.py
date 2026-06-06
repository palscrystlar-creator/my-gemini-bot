from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

router = Router()
ai_client = Groq(api_key="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")

# 1. TUGMALARNI SHAKLLANTIRISH
def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 IELTS Mock", callback_data="start_mock")],
        [InlineKeyboardButton(text="📖 Ovozli hikoya", callback_data="start_story")],
        [InlineKeyboardButton(text="🧮 Matematika", callback_data="start_math")]
    ])

# 2. START KOMANDASI (TUGMALAR BILAN)
@router.message(CommandStart())
async def start_cmd(message: types.Message):
    # Bu yerda stikerlar va menyu birlashtirilgan
    text = (
        "<b>Assalomu alaykum, aziz foydalanuvchi!</b> 👋\n\n"
        "Men sizning shaxsiy AI yordamchingizman. 🤖\n"
        "Quyidagi imkoniyatlardan foydalanishingiz mumkin:\n\n"
        "🏆 <b>IELTS Mock</b> - Ovozli imtihon topshiring\n"
        "📖 <b>Hikoyalar</b> - AI yordamida audio-hikoyalar tinglang\n"
        "🧮 <b>Matematika</b> - Misollarni yechish va tushunish\n\n"
        "<i>Quyidagi tugmalardan birini tanlang:</i> 👇"
    )
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")

# 3. TUGMALAR ISHLASHI UCHUN CALLBACKLAR
@router.callback_query(F.data == "start_mock")
async def callback_mock(callback: types.CallbackQuery):
    await callback.message.answer("🏆 IELTS Mock test boshlandi!\nSavol: Where are you from?")
    await callback.answer()

@router.callback_query(F.data == "start_story")
async def callback_story(callback: types.CallbackQuery):
    await callback.message.answer("📖 Hikoya mavzusini yozing. Masalan: /story Mars")
    await callback.answer()

@router.callback_query(F.data == "start_math")
async def callback_math(callback: types.CallbackQuery):
    await callback.message.answer("🧮 Matematik misolni yozing. Masalan: 5 * 5 = ?")
    await callback.answer()
@router.message(F.text & ~F.text.startswith("/"))
async def chat_with_ai(message: types.Message):
    # Foydalanuvchiga "yozmoqda..." belgisini ko'rsatish
    await bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # AI orqali javob olish
    completion = ai_client.chat.completions.create(
        messages=[{"role": "user", "content": message.text}],
        model="llama-3.3-70b-versatile"
    )
    
    answer = completion.choices[0].message.content
    await message.answer(answer)
