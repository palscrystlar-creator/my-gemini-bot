from aiogram import Router, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.context import FSMContext
import uuid, os, edge_tts
from groq import Groq

router = Router()
ai_client = Groq(api_key="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")

def get_main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏆 IELTS Mock", callback_data="start_mock")],
        [InlineKeyboardButton(text="📖 Ovozli hikoya", callback_data="start_story")],
        [InlineKeyboardButton(text="🧮 Matematika", callback_data="start_math")]
    ])

@router.message(CommandStart())
async def start_cmd(message: types.Message):
    await message.answer("Salom! Bosh menu:", reply_markup=get_main_menu())

@router.callback_query(F.data == "start_mock")
async def start_mock(callback: types.CallbackQuery):
    await callback.message.answer("Mock test boshlandi! Where are you from?")
    await callback.answer()

@router.message(F.text)
async def global_handler(message: types.Message):
    # Matematika
    if any(op in message.text for op in ["+", "-", "*", "/"]):
        comp = ai_client.chat.completions.create(messages=[{"role": "user", "content": f"Yechimni tushuntir: {message.text}"}], model="llama-3.3-70b-versatile")
        await message.answer(comp.choices[0].message.content)
    # Oddiy Chat
    else:
        comp = ai_client.chat.completions.create(messages=[{"role": "user", "content": message.text}], model="llama-3.3-70b-versatile")
        await message.answer(comp.choices[0].message.content)
