import uuid
import random
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
import edge_tts
import os
from groq import Groq
from aiogram import types
# Router yaratamiz
router = Router()
ai_client = Groq(api_key="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")

# Savollar bazasi (boshqa o'zgaruvchilar ham shu yerda bo'ladi)
QUESTIONS = {
    "part1": ["random?"],
    "part2": ["Describe a book you enjoyed."],
    "part3": ["Why do people read books?"]
}

# Yordamchi funksiya
async def send_voice_response(message, text, voice="en-US-BrianNeural"):
    path = f"voice_{uuid.uuid4().hex}.mp3"
    await edge_tts.Communicate(text, voice).save(path)
    await message.answer_voice(FSInputFile(path), caption=f"🗣 Examiner: {text}")
    os.remove(path)

# Handlerlar (mock_ielts va story qismlari)
@router.message(Command("fact"))
async def get_random_fact(message: types.Message):
    # AI orqali tasodifiy qiziqarli fakt olish
    prompt = "Menga juda qiziqarli va kam odam biladigan bitta fakt ayt."
    completion = ai_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile"
    )
    fact = completion.choices[0].message.content
    
    await message.answer(f"💡 <b>Qiziqarli fakt:</b>\n\n{fact}", parse_mode="HTML")
    @router.message(F.text)
async def math_solver(message: types.Message):
    # Foydalanuvchi yuborgan matn matematikaga o'xshaydimi?
    text = message.text
    # Oddiy tekshiruv: agar tarkibida sonlar va amallar (+, -, *, /, ^) bo'lsa
    if any(char.isdigit() for char in text) and any(op in text for op in ["+", "-", "*", "/", "^", "="]):
        
        await message.answer("🧮 <b>Hisoblanmoqda...</b>", parse_mode="HTML")
        
        prompt = f"Ushbu matematik misolni yechib ber va qadam-ba-qadam tushuntir: {text}"
        completion = ai_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile"
        )
        solution = completion.choices[0].message.content
        
        await message.answer(f"✅ <b>Yechim:</b>\n\n{solution}", parse_mode="HTML")
    else:
        # Agar matematik misol bo'lmasa, oddiy chat sifatida javob beradi
        # (Buning uchun avvalgi chat logic-ni ham shu yerda saqlab qolishingiz kerak)
        pass
