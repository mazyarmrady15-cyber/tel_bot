import os
import json
import tempfile
from pathlib import Path
from fastapi import FastAPI, Request

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, InputFile
)

from deep_translator import GoogleTranslator
from gtts import gTTS
import speech_recognition as sr
from moviepy.editor import VideoFileClip

# ---------------- Config ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env var is required")

BASE_URL = os.getenv("BASE_URL")
if not BASE_URL:
    raise RuntimeError("BASE_URL env var is required")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = BASE_URL + WEBHOOK_PATH
PORT = int(os.getenv("PORT", 10000))

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

USER_LANG_FILE = Path("user_langs.json")

language_options = {
    "فارسی": "fa",
    "انگلیسی": "en",
    "فرانسوی": "fr",
    "آلمانی": "de",
    "اسپانیایی": "es",
}


# ---------------- User Langs Storage ----------------
def load_user_langs():
    if USER_LANG_FILE.exists():
        try:
            return json.loads(USER_LANG_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_user_langs(data):
    USER_LANG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


user_langs = load_user_langs()


# ---------------- Keyboards ----------------
def get_language_keyboard():
    names = list(language_options.keys())
    rows = []
    for i in range(0, len(names), 2):
        rows.append([KeyboardButton(text=names[i])] + ([KeyboardButton(text=names[i+1])] if i+1 < len(names) else []))
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)


def change_language_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="تغییر زبان مقصد", callback_data="change_target")]
    ])


# ---------------- Helpers ----------------
def cleanup_temp_files(*files):
    for f in files:
        try:
            if f and Path(f).exists():
                Path(f).unlink()
        except Exception:
            pass


async def translate_and_speak(text: str, lang: str, uid: str):
    translated = GoogleTranslator(source="auto", target=lang).translate(text)
    tts = gTTS(translated, lang=lang)
    temp_file = Path(tempfile.gettempdir()) / f"voice_{uid}.mp3"
    tts.save(temp_file)
    return translated, temp_file


# ---------------- Handlers ----------------
@dp.message(CommandStart())
async def start_handler(message: Message):
    uid = str(message.from_user.id)
    user_langs.pop(uid, None)
    save_user_langs(user_langs)
    await message.answer("سلام 👋 زبان مقصد را انتخاب کنید:", reply_markup=get_language_keyboard())


@dp.message(F.text.in_(language_options.keys()))
async def select_language(message: Message):
    uid = str(message.from_user.id)
    sel = language_options[message.text]
    user_langs[uid] = sel
    save_user_langs(user_langs)
    await message.answer("✅ زبان انتخاب شد. حالا متن، ویس یا ویدیو بفرست.\nبرای تغییر زبان دکمه زیر:", reply_markup=change_language_kb())


@dp.callback_query(F.data == "change_target")
async def change_target_callback(cq: types.CallbackQuery):
    uid = str(cq.from_user.id)
    user_langs.pop(uid, None)
    save_user_langs(user_langs)
    await cq.message.edit_text("زبان مقصد جدید را انتخاب کنید:", reply_markup=get_language_keyboard())


# ---------------- Text ----------------
@dp.message(F.text)
async def handle_text(message: Message):
    uid = str(message.from_user.id)
    if uid not in user_langs:
        await message.answer("لطفاً اول زبان مقصد را انتخاب کنید:", reply_markup=get_language_keyboard())
        return

    lang = user_langs[uid]
    translated, voice_file = await translate_and_speak(message.text, lang, uid)
    await message.answer(translated, reply_markup=change_language_kb())
    await message.answer_voice(InputFile(voice_file))
    cleanup_temp_files(voice_file)

# ---------------- Voice ----------------
@dp.message(F.voice)
async def handle_voice(message: Message):
    uid = str(message.from_user.id)
    if uid not in user_langs:
        await message.answer("لطفاً اول زبان مقصد را انتخاب کنید:", reply_markup=get_language_keyboard())
        return

    lang = user_langs[uid]
    file = await bot.get_file(message.voice.file_id)
    temp_ogg = Path(tempfile.gettempdir()) / f"{uid}.ogg"
    temp_wav = Path(tempfile.gettempdir()) / f"{uid}.wav"
    await bot.download_file(file.file_path, temp_ogg)

    try:
        os.system(f"ffmpeg -i {temp_ogg} {temp_wav} -y -loglevel quiet")
        recognizer = sr.Recognizer()
        with sr.AudioFile(str(temp_wav)) as src:
            audio_data = recognizer.record(src)
            text = recognizer.recognize_google(audio_data, language="fa-IR")
    except Exception:
        await message.answer("❌ خطا در پردازش ویس")
        cleanup_temp_files(temp_ogg, temp_wav)
        return

    translated, voice_file = await translate_and_speak(text, lang, uid)
    await message.answer(translated, reply_markup=change_language_kb())
    await message.answer_voice(InputFile(voice_file))
    cleanup_temp_files(temp_ogg, temp_wav, voice_file)


# ---------------- Video ----------------
@dp.message(F.video)
async def handle_video(message: Message):
    uid = str(message.from_user.id)
    if uid not in user_langs:
        await message.answer("لطفاً اول زبان مقصد را انتخاب کنید:", reply_markup=get_language_keyboard())
        return

    lang = user_langs[uid]
    file = await bot.get_file(message.video.file_id)
    temp_mp4 = Path(tempfile.gettempdir()) / f"{uid}.mp4"
    temp_wav = Path(tempfile.gettempdir()) / f"{uid}.wav"

    await bot.download_file(file.file_path, temp_mp4)
    await message.answer("📩 ویدیو دریافت شد، در حال پردازش...")

    try:
        clip = VideoFileClip(str(temp_mp4))
        clip.audio.write_audiofile(temp_wav, codec="pcm_s16le", logger=None)
        clip.close()

        recognizer = sr.Recognizer()
        with sr.AudioFile(str(temp_wav)) as src:
            audio_data = recognizer.record(src)
            text = recognizer.recognize_google(audio_data, language="fa-IR")
    except Exception:
        await message.answer("❌ خطا در پردازش ویدیو")
        cleanup_temp_files(temp_mp4, temp_wav)
        return

    translated, voice_file = await translate_and_speak(text, lang, uid)
    await message.answer(translated, reply_markup=change_language_kb())
    await message.answer_voice(InputFile(voice_file))
    cleanup_temp_files(temp_mp4, temp_wav, voice_file)


# ---------------- FastAPI ----------------
app = FastAPI()


@app.on_event("startup")
async def on_startup():
    await bot.set_webhook(WEBHOOK_URL)


@app.on_event("shutdown")
async def on_shutdown():
    await bot.delete_webhook()


@app.post(WEBHOOK_PATH)
async def bot_webhook(request: Request):
    update = types.Update.model_validate(await request.json(), context={"bot": bot})
    await dp.feed_update(bot, update)
    return {"ok": True}
