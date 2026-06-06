from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq

router = Router()
ai_client = Groq(api_key="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")

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Suhbatlashish", callback_data="start_chat")], # Yangi tugma
        [InlineKeyboardButton(text="📖 Ovozli hikoya", callback_data="start_story")],
        [InlineKeyboardButton(text="🧮 Matematika", callback_data="start_math")]
    ])

@router.message(CommandStart())
async def start_cmd(message: types.Message):
    text = "<b>Assalomu alaykum!</b> 👋 Men sizning yordamchingizman. Kerakli bo'limni tanlang:"
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")

@router.callback_query(F.data == "start_story")
async def story_cb(callback: types.CallbackQuery):
    await callback.message.answer("📖 Hikoya mavzusini yozing (masalan: /story Mars)")
    await callback.answer()

@router.callback_query(F.data == "start_math")
async def math_cb(callback: types.CallbackQuery):
    await callback.message.answer("🧮 Matematik misolni yozing (masalan: 5 + 5)")
    await callback.answer()

@router.message(F.text & ~F.text.startswith("/"))
async def chat_with_ai(message: types.Message):
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    # AI uchun yangi ko'rsatma: "Foydalanuvchi qaysi tilda yozsa, o'sha tilda javob ber"
    system_instruction = "Sen foydalanuvchining tilida javob beradigan yordamchisan. Agar foydalanuvchi o'zbekcha yozsa - o'zbekcha, inglizcha yozsa - inglizcha, ruscha yozsa - ruscha javob ber. Javoblaring qisqa va tushunarli bo'lsin."
    
    comp = ai_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": message.text}
        ], 
        model="llama-3.3-70b-versatile"
    )
    
    await message.answer(comp.choices[0].message.content)
@router.callback_query(F.data == "start_chat")
async def chat_cb(callback: types.CallbackQuery):
    await callback.message.answer("💬 Suhbat rejimi faol! Menga savol bering yoki shunchaki gaplashing.")
    await callback.answer()
