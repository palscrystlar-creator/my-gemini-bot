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
    "part1": ["Where are you from?", "What do you like about your city?"],
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
