import uuid
import random
from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import FSInputFile
import edge_tts
import os
from groq import Groq

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
@router.message(Command("story"))
async def story_handler(message):
    args = message.text.split(maxsplit=1)
    if len(args) > 1:
        await message.answer("⏳ Yozilmoqda...")
        # Hikoya yaratish va ovozli yuborish mantiqi...
