import os
import asyncio
import uuid
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web, ClientSession
import edge_tts

# ==================== 1. SERVER VA BOT SOZLAMALARI ====================
BOT_TOKEN = "8799568905:AAGY-PYkbve9LkNp2Fy922FAibTopmomu5s"
GROQ_API_KEY = "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"
WEBHOOK_URL = "https://my-gemini-bot-1-14qh.onrender.com"
PORT = int(os.environ.get("PORT", 8080))

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

os.makedirs("static", exist_ok=True)

# ==================== 2. FSM HOLATLARI ====================
class IELTSMockState(StatesGroup):
    part1_q1 = State()
    part1_q2 = State()
    part1_q3 = State()
    part2_cue = State()
    part3_q1 = State()
    part3_q2 = State()
    part3_q3 = State()

class PracticeState(StatesGroup):
    choosing_ai = State()
    choosing_level = State()
    choosing_topic = State()
    speaking = State()

SYSTEM_PROMPT = "Sizning ismingiz 'ShavkatoV AI'. Foydalanuvchi qaysi tilda gapirsa, faqat o'sha tilda qisqa javob bering."
EXAMINER_PROMPT = """
You are a highly experienced and unpredictable IELTS Speaking Examiner. 
Your goal is to conduct a natural, rigorous, and professional interview. 

STRICT RULES TO AVOID REPETITION & ROBOTIC BEHAVIOR:
1. DYNAMIC OPENINGS: Never start two questions with the same phrase. Use variety: 
   - "That's an interesting perspective...", "I see, and what about...", "Fair enough. Let's shift our focus to...", 
   - "Right. How do you feel about...", "I understand. Tell me more concerning...", "That's a valid point. Moving on to..."
2. NO META-LANGUAGE: Never use phrases like "Here is your next question", "Moving to the next part", or "I understand, let's continue". 
   Maintain the flow of a real, natural conversation.
3. ADAPTIVE PROBING: 
   - If the candidate's answer is short, use a follow-up probe: "Why do you think that is?", "Could you provide an example?".
   - If the candidate's answer is detailed, transition with a summary or a comparative question.
4. QUESTION DIVERSITY: Vary your sentence structure:
   - Direct questions: "What do you think about...?"
   - Evaluative questions: "How has this changed in your country recently?"
   - Hypothetical questions: "What would you do if...?"
5. TONE: You are professional, slightly formal, and encouraging but firm. 
"""

# ==================== 3. GROQ VA AUDIO API FUNKSIYALARI ====================

async def groq_chat_completion(messages, model="llama-3.3-70b-versatile"):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model, "messages": messages}
    async with ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload) as resp:
            result = await resp.json()
            return result["choices"][0]["message"]["content"]

async def groq_transcribe_audio(file_path):
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}
    data = web.FormData()
    data.add_field('file', open(file_path, 'rb'), filename=os.path.basename(file_path))
    data.add_field('model', 'whisper-large-v3')
    async with ClientSession() as session:
        async with session.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, data=data) as resp:
            result = await resp.json()
            return result.get("text", "")

async def send_examiner_voice(message: types.Message, text: str, voice="en-US-BrianNeural"):
    reply_voice_path = f"static/examiner_{message.chat.id}_{uuid.uuid4().hex}.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(reply_voice_path)
        await message.answer_voice(types.FSInputFile(reply_voice_path))
    except:
        await message.answer(f"[Voice Error] {text}")
    finally:
        if os.path.exists(reply_voice_path):
            try: os.remove(reply_voice_path)
            except: pass

async def transcribe_voice(message: types.Message) -> str:
    voice_id = message.voice.file_id
    file = await bot.get_file(voice_id)
    local_voice_path = f"static/{voice_id}.ogg"
    await bot.download_file(file.file_path, local_voice_path)
    try:
        return await groq_transcribe_audio(local_voice_path)
    except:
        return ""
    finally:
        if os.path.exists(local_voice_path):
            try: os.remove(local_voice_path)
            except: pass

# ==================== 4. BOT HANDLERLARI ====================

@dp.message(CommandStart())
async def start_command(message: types.Message):
    webapp_url = f"{WEBHOOK_URL}/"
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[[types.KeyboardButton(text="📞 Live AI Call", web_app=types.WebAppInfo(url=webapp_url))]],
        resize_keyboard=True
    )
    welcome_text = (
        f"<b>Assalomu alaykum, {message.from_user.full_name}!</b> 👋\n\n"
        f"🤖 Men <b>ShavkatoV AI</b> — sizning shaxsiy ingliz tili treneringizman.\n\n"
        f"📱 Pastdagi <b>'📞 Live AI Call'</b> tugmasini bosib, veb-sahifa orqali jonli muloqot rejimiga o'tishingiz mumkin.\n\n"
        f"Yoki bot ichidagi imtihonlarni boshlang:\n"
        f"1️⃣ 🏆 /mock_ielts — To'liq IELTS imtihoni (Part 1, 2, 3 va Band Score)\n"
        f"2️⃣ 🗣 /practice — Erkin muloqot"
    )
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="HTML")

@dp.message(Command("stop"))
async def stop_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏁 Amaliyot yoki imtihon to'xtatildi. Oddiy rejimga qaytdingiz.")

# ==================== TARTIBLI IELTS MOCK TEST TIZIMI ====================

@dp.message(Command("mock_ielts"))
async def start_ielts_mock(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🏆 <b>IELTS Speaking Mock Test boshlandi!</b>\nSavollarga faqat <b>OVOZLI XABAR</b> orqali javob bering.\n\n<i>🎬 Part 1 boshlanmoqda...</i>", parse_mode="HTML")
    
    q1 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT}, 
        {"role": "user", "content": "Act as an examiner. Ask a standard IELTS Part 1 introductory question (about home, work, studies, or hometown). Only output the question."}
    ])
    await message.answer(f"🗣 <b>Examiner (Part 1 - Q1):</b>\n{q1}")
    await send_examiner_voice(message, q1)
    await state.update_data(p1_q1=q1, history=[])
    await state.set_state(IELTSMockState.part1_q1)

@dp.message(IELTSMockState.part1_q1, F.voice)
async def p1_q1_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text:
        await message.answer("Ovozingizni yaxshi eshitolmadim, iltimos qaytadan yuboring.")
        return
    data = await state.get_data()
    history = data.get("history", [])
    history.append({"role": "user", "content": f"Examiner: {data.get('p1_q1')} | Candidate: {text}"})
    
    q2 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT}, 
        {"role": "user", "content": f"Based on this conversation history, ask the second logical Part 1 follow-up question: {history}"}
    ])
    await message.answer(f"🗣 <b>Examiner (Part 1 - Q2):</b>\n{q2}")
    await send_examiner_voice(message, q2)
    await state.update_data(p1_q2=q2, history=history)
    await state.set_state(IELTSMockState.part1_q2)

@dp.message(IELTSMockState.part1_q2, F.voice)
async def p1_q2_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text:
        await message.answer("Ovozingizni yaxshi eshitolmadim, iltimos qaytadan yuboring.")
        return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p1_q2')} | Candidate: {text}"})
    
    q3 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT}, 
        {"role": "user", "content": f"Ask the third and final Part 1 question for a new common topic (weather, hobbies, or food) based on history: {history}"}
    ])
    await message.answer(f"🗣 <b>Examiner (Part 1 - Q3):</b>\n{q3}")
    await send_examiner_voice(message, q3)
    await state.update_data(p1_q3=q3, history=history)
    await state.set_state(IELTSMockState.part1_q3)

@dp.message(IELTSMockState.part1_q3, F.voice)
async def p1_q3_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text:
        await message.answer("Ovozingizni yaxshi eshitolmadim, iltimos qaytadan yuboring.")
        return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p1_q3')} | Candidate: {text}"})
    
    await message.answer("➡️ <b>Part 1 tugadi. Part 2 (Cue Card) boshlanmoqda...</b>\nSizga mavzu beriladi, uni o'qib ovozli xabar orqali 1-2 daqiqa gapiring.", parse_mode="HTML")
    cue_card = await groq_chat_completion([
        {"role": "system", "content": "You are an IELTS examiner. Provide a proper, structured IELTS Speaking Part 2 Cue Card block (Topic with 3-4 bullet points to talk about)."}
    ])
    await message.answer(f"📋 <b>PART 2 - CUE CARD:</b>\n\n{cue_card}\n\n<i>🔴 Tayyor bo'lganingizda to'liq ovoz yuboring.</i>", parse_mode="HTML")
    await send_examiner_voice(message, "Now, read the cue card on your screen. You have one to two minutes to talk about this topic.")
    await state.update_data(p2_cue=cue_card, history=history)
    await state.set_state(IELTSMockState.part2_cue)

@dp.message(IELTSMockState.part2_cue, F.voice)
async def p2_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text:
        await message.answer("Ovozingizni yaxshi eshitolmadim, iltimos qaytadan yuboring.")
        return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Cue Card Topic: {data.get('p2_cue')} | Candidate Long Turn Speech: {text}"})
    
    await message.answer("➡️ <b>Part 2 yakunlandi. Part 3 (Discussion) bosqichiga o'tamiz.</b>\nBu qismda savollar chuqurroq va mavzu doirasida bo'ladi.", parse_mode="HTML")
    p3_q1 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT}, 
        {"role": "user", "content": f"Based on the Part 2 Cue Card topic '{data.get('p2_cue')}', ask a deep abstract analytical Part 3 question."}
    ])
    await message.answer(f"🗣 <b>Examiner (Part 3 - Q1):</b>\n{p3_q1}")
    await send_examiner_voice(message, p3_q1)
    await state.update_data(p3_q1=p3_q1, history=history)
    await state.set_state(IELTSMockState.part3_q1)

@dp.message(IELTSMockState.part3_q1, F.voice)
async def p3_q1_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text:
        await message.answer("Ovozingizni yaxshi eshitolmadim, iltimos qaytadan yuboring.")
        return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p3_q1')} | Candidate: {text}"})
    
    p3_q2 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT}, 
        {"role": "user", "content": f"Challenge the candidate's last opinion or ask a follow-up deep Part 3 question based on: {history}"}
    ])
    await message.answer(f"🗣 <b>Examiner (Part 3 - Q2):</b>\n{p3_q2}")
    await send_examiner_voice(message, p3_q2)
    await state.update_data(p3_q2=p3_q2, history=history)
    await state.set_state(IELTSMockState.part3_q2)

@dp.message(IELTSMockState.part3_q2, F.voice)
async def p3_q2_handler(message: types.Message, state: FSMContext):
    text = await transcribe_voice(message)
    if not text:
        await message.answer("Ovozingizni yaxshi eshitolmadim, iltimos qaytadan yuboring.")
        return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p3_q2')} | Candidate: {text}"})
    
    p3_q3 = await groq_chat_completion([
        {"role": "system", "content": EXAMINER_PROMPT}, 
        {"role": "user", "content": f"Ask the final conclusive deep Part 3 question for this interview based on: {history}"}
    ])
    await message.answer(f"🗣 <b>Examiner (Part 3 - Q3):</b>\n{p3_q3}")
    await send_examiner_voice(message, p3_q3)
    await state.update_data(p3_q3=p3_q3, history=history)
    await state.set_state(IELTSMockState.part3_q3)

@dp.message(IELTSMockState.part3_q3, F.voice)
async def p3_q3_handler(message: types.Message, state: FSMContext):
    await message.answer("🏁 <b>Imtihon to'liq yakunlandi! AI hozir sizning butun suhbatingizni tahlil qilib, rasmiy IELTS hisoboti va Band Score tayyorlamoqda. Iltimos kuting...</b>")
    text = await transcribe_voice(message)
    if not text: return
    data = await state.get_data()
    history = data.get("history")
    history.append({"role": "user", "content": f"Examiner: {data.get('p3_q3')} | Candidate: {text}"})
    
    try:
        # CHIROYLI TEXT VA FORMAT SHABLONI
        report_prompt = (
            f"Analyze this full IELTS interview history step by step:\n{history}\n\n"
            f"Generate an official detailed IELTS report in Uzbek. Follow this exact format strictly.\n"
            f"Use bold headers and structure beautifully with clear spacing. You must output the sections separated by '---' divider:\n\n"
            f"🏆 *OFFICIAL IELTS SPEAKING REPORT* 🏆\n"
            f"**Nomzod:** [User Name]\n"
            f"**Umumiy Baholash Balli (Overall Band Score):** [Score e.g. 6.5 / 9.0]\n"
            f"---"
            f"📈 **1. Fluency and Coherence (Ravanlik va Izchillik)**\n"
            f"• **Tahlil:** [Batafsil fikr]\n"
            f"• **Ball:** [Masalan: 6.0]\n"
            f"---"
            f"🔤 **2. Lexical Resource (So'z boyligi)**\n"
            f"• **Tahlil:** [Batafsil fikr]\n"
            f"• **Ball:** [Masalan: 6.5]\n"
            f"---"
            f"⚖️ **3. Grammatical Range and Accuracy (Grammatika)**\n"
            f"• **Tahlil:** [Batafsil fikr]\n"
            f"• **Ball:** [Masalan: 6.0]\n"
            f"---"
            f"🛠️ **4. Yo'l qo'yilgan asosiy xatolar va tuzatishlar (Key Corrections)**\n"
            f"[Bu yerda nomzod aytgan noto'g'ri gaplarni inglizcha yozib, yoniga to'g'risini chiroyli qilib ko'rsating]\n"
            f"---"
            f"💡 **5. Ballni oshirish uchun tavsiyalar (Tips to Improve)**\n"
            f"[Nomzod uchun foydali maslahatlar]"
        )
        report_content = await groq_chat_completion([{"role": "user", "content": report_prompt}])
        sections = report_content.split("---")
        
        await message.answer("📊 <b>SIZNING RASMIY IELTS MOCK TEST HISOBOTINGIZ:</b>")
        for section in sections:
            clean_section = section.strip()
            if clean_section:
                # Textni chiroyli ko'rinishda Telegram'ga chiqarish (Markdown v2 yoki HTML xatolaridan qochish uchun oddiy parse_mode ishlatmadik yoki toza chiqadi)
                await message.answer(clean_section)
                voice_path = f"static/report_{uuid.uuid4().hex}.mp3"
                # Ovozli o'qishda keraksiz belgilarni olib tashlaymiz
                clean_for_voice = clean_section.replace("**", "").replace("*", "").replace("•", "").replace("`", "")
                communicate = edge_tts.Communicate(clean_for_voice, "uz-UZ-MadinaNeural")
                await communicate.save(voice_path)
                await message.answer_voice(types.FSInputFile(voice_path))
                if os.path.exists(voice_path): os.remove(voice_path)
                await asyncio.sleep(1)
    except Exception as e:
        await message.answer(f"Hisobot tayyorlashda xatolik yuz berdi: {str(e)}")
    finally:
        await state.clear()

# ==================== ERKIN PRACTICE REJIMI HANDLERLARI ====================
@dp.message(Command("practice"))
async def start_practice(message: types.Message, state: FSMContext):
    await state.clear()
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👨‍💼 Mr. Brian (British)", callback_data="ai_en-GB-RyanNeural")],
        [types.InlineKeyboardButton(text="👩‍💼 Miss. Emma (American)", callback_data="ai_en-US-EmmaNeural")]
    ])
    await message.answer("🤖 <b>AI Suhbatdoshingizni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_ai)

@dp.callback_query(F.data.startswith("ai_"))
async def ai_selected(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(chosen_ai=callback.data.split("_")[1])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🟢 Beginner", callback_data="lvl_Beginner")],
        [types.InlineKeyboardButton(text="🟡 Intermediate", callback_data="lvl_Intermediate")],
        [types.InlineKeyboardButton(text="🔴 Advanced", callback_data="lvl_Advanced")]
    ])
    await callback.message.edit_text("📊 <b>Darajangizni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_level)

@dp.callback_query(F.data.startswith("lvl_"))
async def level_selected(callback: types.CallbackQuery, state: FSMContext):
    await state.update_data(chosen_level=callback.data.split("_")[1])
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📱 Technology", callback_data="prctopic_Technology")],
        [types.InlineKeyboardButton(text="✈️ Travel", callback_data="prctopic_Travel")]
    ])
    await callback.message.edit_text("📱 <b>Mavzuni tanlang:</b>", reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(PracticeState.choosing_topic)

@dp.callback_query(F.data.startswith("prctopic_"))
async def topic_selected(callback: types.CallbackQuery, state: FSMContext):
    topic = callback.data.split("_")[1]
    data = await state.get_data()
    ai_voice = data.get("chosen_ai")
    level = data.get("chosen_level")
    await callback.message.delete()
    
    await callback.message.answer(f"🚀 <b>Suhbat boshlandi!</b> To'xtatish uchun /stop deb yozing.")
    custom_prompt = f"You are an English partner. Topic: {topic}. Level: {level}. Keep it short (max 2 sentences) and ask a question."
    first_q = await groq_chat_completion([{"role": "system", "content": custom_prompt}, {"role": "user", "content": "Start conversation"}])
    
    await callback.message.answer(f"💬 <b>AI:</b> {first_q}")
    await send_examiner_voice(callback.message, first_q, voice=ai_voice)
    await state.update_data(practice_history=[{"role": "system", "content": custom_prompt}, {"role": "assistant", "content": first_q}], chosen_ai=ai_voice)
    await state.set_state(PracticeState.speaking)

@dp.message(PracticeState.speaking, F.voice)
async def handle_practice_voice(message: types.Message, state: FSMContext):
    user_text = await transcribe_voice(message)
    if not user_text: return
    data = await state.get_data()
    history = data.get("practice_history", [])
    ai_voice = data.get("chosen_ai")
    history.append({"role": "user", "content": user_text})
    
    ai_response = await groq_chat_completion(history)
    await message.answer(f"✍️ <i>You: {user_text}</i>\n\n💬 <b>AI:</b> {ai_response}")
    await send_examiner_voice(message, ai_response, voice=ai_voice)
    history.append({"role": "assistant", "content": ai_response})
    await state.update_data(practice_history=history)

# --- STANDART MATNLI VA OVOZLI CHAT ---
@dp.message(F.text)
async def normal_text(message: types.Message):
    reply = await groq_chat_completion([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": message.text}])
    await message.answer(reply)

@dp.message(F.voice)
async def normal_voice(message: types.Message):
    user_text = await transcribe_voice(message)
    if not user_text: return
    ai_reply = await groq_chat_completion([{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_text}])
    reply_voice_path = f"static/normal_{uuid.uuid4().hex}.mp3"
    communicate = edge_tts.Communicate(ai_reply, "en-US-EmmaNeural")
    await communicate.save(reply_voice_path)
    await message.answer_voice(types.FSInputFile(reply_voice_path), caption=f"✍️ <i>You: {user_text}</i>")
    if os.path.exists(reply_voice_path): os.remove(reply_voice_path)

# ==================== 5. LIVE CALL WEBAPP INTERFEJSI ====================

async def serve_index(request):
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Live AI Call</title>
        <style>
            body { font-family: Arial, sans-serif; background: #0f172a; color: white; text-align: center; padding: 50px 20px; }
            .status { font-size: 24px; color: #38bdf8; margin-bottom: 40px; }
            .btn { width: 150px; height: 150px; border-radius: 50%; border: none; background: #ef4444; color: white; font-size: 18px; cursor: pointer; box-shadow: 0 0 20px rgba(239, 68, 68, 0.5); font-weight: bold; }
            .btn.recording { background: #22c55e; box-shadow: 0 0 20px rgba(34, 197, 94, 0.5); }
            .response-text { margin-top: 30px; font-style: italic; color: #cbd5e1; }
        </style>
    </head>
    <body>
        <div class="status" id="status">📞 Click to Start Live Call</div>
        <button class="btn" id="callBtn">START</button>
        <div class="response-text" id="respText"></div>

        <script>
            let mediaRecorder;
            let audioChunks = [];
            const btn = document.getElementById('callBtn');
            const status = document.getElementById('status');
            const respText = document.getElementById('respText');

            btn.addEventListener('click', async () => {
                if (!mediaRecorder || mediaRecorder.state === 'inactive') {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    audioChunks = [];
                    
                    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
                    mediaRecorder.onstop = async () => {
                        status.innerText = "⌛ AI is thinking...";
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        const formData = new FormData();
                        formData.append('audio', audioBlob);

                        const res = await fetch('/api/voice-call', { method: 'POST', body: formData });
                        const data = await res.json();
                        
                        if (data.status === 'success') {
                            respText.innerText = "🤖 AI: " + data.text;
                            status.innerText = "🔊 Speaking...";
                            const audio = new Audio(data.audio_url);
                            audio.play();
                            audio.onended = () => { status.innerText = "📞 Click to speak again"; btn.innerText = "TALK"; };
                        }
                    };

                    mediaRecorder.start();
                    status.innerText = "🎙️ Listening... Speak now.";
                    btn.innerText = "STOP";
                    btn.classList.add('recording');
                } else {
                    mediaRecorder.stop();
                    btn.innerText = "PROCESSING";
                    btn.classList.remove('recording');
                }
            });
        </script>
    </body>
    </html>
    """
    return web.Response(text=html_content, content_type='text/html')

async def handle_voice_call_api(request):
    try:
        data = await request.post()
        audio_file = data['audio']
        temp_webm = f"static/call_{uuid.uuid4().hex}.webm"
        with open(temp_webm, 'wb') as f:
            f.write(audio_file.file.read())
        
        user_text = await groq_transcribe_audio(temp_webm)
        if os.path.exists(temp_webm): os.remove(temp_webm)
        
        if not user_text:
            return web.json_response({"status": "success", "text": "I didn't hear you.", "audio_url": ""})
            
        ai_response = await groq_chat_completion([
            {"role": "system", "content": "You are having a continuous live phone call. Keep response under 2 short sentences. Ask a natural question back."},
            {"role": "user", "content": user_text}
        ])
        
        res_filename = f"static/res_{uuid.uuid4().hex}.mp3"
        communicate = edge_tts.Communicate(ai_response, "en-US-EmmaNeural")
        await communicate.save(res_filename)
        
        return web.json_response({
            "status": "success",
            "text": ai_response,
            "audio_url": f"{WEBHOOK_URL}/{res_filename}"
        })
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)}, status=500)

# ==================== 6. ENGINE VA WEBHOOK ISHGA TUSHIRISH ====================

async def handle_webhook(request):
    request_data = await request.json()
    update = types.Update(**request_data)
    await dp.feed_update(bot, update)
    return web.Response(text="OK")

async def on_startup(app):
    await bot.set_webhook(f"{WEBHOOK_URL}/webhook")

def main():
    app = web.Application()
    app.router.add_get('/', serve_index)
    app.router.add_post('/api/voice-call', handle_voice_call_api)
    app.router.add_post('/webhook', handle_webhook)
    app.router.add_static('/static/', path='static', name='static')
    app.on_startup.append(on_startup)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
