from aiogram import Router, F, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from groq import Groq
from aiogram import F
import speech_recognition as sr # Audio uchun
import os
from aiogram.filters import Command
router = Router()
ai_client = Groq(api_key="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")

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📱 Mini Ekranni Ochish", web_app=types.WebAppInfo(url="https://google.com"))], # O'zingizning saytingiz linkini qo'ying
        [InlineKeyboardButton(text="🧮 Matematika", callback_data="start_math")]
@router.callback_query(F.data == "start_webapp")
async def webapp_cb(callback: types.CallbackQuery):
    # Bu yerda o'z sahifangiz manzilini yozasiz (Render yoki GitHub Pages linki)
    web_app_url = "https://sizning-saytingiz-nomi.onrender.com/index.html"
    
    await callback.message.answer(
        "Mini oynani ochish uchun pastdagi tugmani bosing:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📱 Saytni ochish", web_app=types.WebAppInfo(url=web_app_url))]
      ])
@router.message(CommandStart())
async def start_cmd(message: types.Message):
    text = "<b>Assalomu alaykum!Men AI yordamchingizman</b> 👋 Men sizning yordamchingizman. Kerakli bo'limni tanlang:"
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
@router.message(F.voice)
async def handle_voice(message: types.Message):
    # Telegramdan faylni yuklab olish
    file_id = message.voice.file_id
    file = await message.bot.get_file(file_id)
    file_path = file.file_path
    
    # Faylni saqlash va matnga o'girish (Bu qismda sizda audio to audio STT bo'lishi kerak)
    # Hozircha oddiy matnli AI ga o'tkazamiz:
    await message.answer("🎧 Ovozingiz eshitildi, tahlil qilinmoqda...")
    
    # AI orqali javob
    comp = ai_client.chat.completions.create(
        messages=[{"role": "user", "content": "Foydalanuvchi ovozli xabar yubordi (uni matnga o'girganimda shuni bildim)"}], 
        model="llama-3.3-70b-versatile"
    )
    await message.answer(comp.choices[0].message.content)
from aiogram.filters import Command

@router.message(Command("help"))
async def help_cmd(message: types.Message):
    text = (
        "<b>Bot yordami:</b>\n\n"
        "1. 🧮 <b>Matematika:</b> Misolni yozing (masalan, 10*5).\n"
        "2. 💬 <b>Suhbat:</b> Shunchaki xabar yozing, javob beraman.\n"
        "3. 📱 <b>Web App:</b> Tugmalardan foydalaning."
    )
    await message.answer(text, parse_mode="HTML")

@router.message(Command("profile"))
async def profile_cmd(message: types.Message):
    user = message.from_user
    text = (
        "👤 <b>Sizning profilingiz:</b>\n\n"
        f"Ismingiz: {user.first_name}\n"
        f"ID: <code>{user.id}</code>\n"
        "Bot xizmatidan foydalanyapsiz!"
    )
    await message.answer(text, parse_mode="HTML")
