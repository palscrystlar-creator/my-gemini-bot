from aiogram import Router, F, types
from groq import Groq
import random

router = Router()
ai_client = Groq(api_key="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")

# GIFlar ro'yxati (har xil kayfiyat uchun)
GIFS = {
    "happy": ["CgACAgQAAxkBAAIFyG...", "CgACAgQAAxkBAAIFyW..."], # Bu yerga Telegramdan olgan FileIDlaringizni qo'ying
    "think": ["CgACAgQAAxkBAAIFym..."]
}

@router.message(F.voice)
async def handle_voice(message: types.Message):
    await message.answer("🎧 Ovozli xabaringiz qabul qilindi, tahlil qilinmoqda...")
    # Bu yerda Whisper API orqali ovozni matnga o'tkazish logikasi bo'ladi
    # Hozircha AIga "Foydalanuvchi ovozli xabar yubordi" deb xabar beramiz
    await chat_with_ai(message, "Foydalanuvchi ovozli xabar yubordi, unga qisqa va qiziqarli javob ber.")

@router.message(F.text | F.sticker | F.emoji)
async def chat_with_ai(message: types.Message, custom_text=None):
    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")
    
    text = custom_text or message.text or "Foydalanuvchi stiker yoki emoji yubordi."
    
    # AIga emojilarni tushunish va javobga qo'shishni buyuramiz
    system_prompt = "Sen juda aqlli, hazilkash va emojilardan foydalanadigan yordamchisan. Javoblaringga mos emojilar qo'sh."
    
    comp = ai_client.chat.completions.create(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ], 
        model="llama-3.3-70b-versatile"
    )
    
    answer = comp.choices[0].message.content
    await message.answer(answer)
