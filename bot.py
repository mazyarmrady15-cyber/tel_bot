import os
import json
import tempfile
from pathlib import Path
from fastapi import FastAPI, Request
import asyncio

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

WEBHOOK_PATH = "/webhook"
BASE_URL = os.getenv("BASE_URL")  # آدرس public که Render میده
if not BASE_URL:
    raise RuntimeError("BASE_URL env var is required")

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
    await cq.message.edit_text("زبان مقصد جدید را انتخاب کنید", reply_markup=None)
    await cq.message.answer("زبان مقصد را انتخاب کنید:", reply_markup=get_language_keyboard())
    await cq.answer()


@dp.message(F.text)
async def text_translate(message: Message):
    uid = str(message.from_user.id)
    target = user_langs.get(uid)
    if not target:
        await message.answer("ابتدا زبان مقصد را انتخاب کنید (/start).")
        return
    try:
        translated = GoogleTranslator(source="auto", target=target).translate(message.text)
        await message.reply(f"ترجمه:\n{translated}", reply_markup=change_language_kb())
    except Exception as e:
        await message.reply(f"خطا در ترجمه: {e}")


# ---------------- Voice Handler ----------------
@dp.message(F.voice)
async def handle_voice(message: Message):
    uid = str(message.from_user.id)
    target = user_langs.get(uid)
    if not target:
        await message.answer("ابتدا زبان مقصد را انتخاب کنید (/start).")
        return

    await message.answer("🎙 در حال پردازش ویس...")

with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = Path(tmpdir) / f"voice_{uid}.ogg"
        wav_path = Path(tmpdir) / f"voice_{uid}.wav"

        try:
            file_info = await bot.get_file(message.voice.file_id)
            downloaded = await bot.download_file(file_info.file_path)
            with open(ogg_path, "wb") as f:
                f.write(downloaded.read())
        except Exception as e:
            await message.reply(f"❌ خطا در دانلود ویس: {e}")
            return

        try:
            import subprocess
            subprocess.run(["ffmpeg", "-y", "-i", str(ogg_path), str(wav_path)], check=True)
        except Exception as e:
            await message.reply(f"❌ خطا در تبدیل ویس: {e}")
            return

        r = sr.Recognizer()
        try:
            with sr.AudioFile(str(wav_path)) as source:
                audio_data = r.record(source)
            recognized_text = r.recognize_google(audio_data)
        except sr.UnknownValueError:
            recognized_text = ""
        except Exception as e:
            await message.reply(f"❌ خطا در تشخیص گفتار: {e}")
            return

        if not recognized_text:
            await message.reply("❌ متنی از ویس تشخیص داده نشد.")
            return

        try:
            translated_text = GoogleTranslator(source="auto", target=target).translate(recognized_text)
        except Exception as e:
            await message.reply(f"❌ خطا در ترجمه: {e}")
            return

        try:
            tts = gTTS(text=translated_text, lang=target)
            mp3_path = Path(tmpdir) / f"voice_translated_{uid}.mp3"
            tts.save(str(mp3_path))
        except Exception as e:
            await message.reply(f"❌ خطا در ساخت ویس: {e}")
            return

        try:
            await message.reply_document(InputFile(str(mp3_path)), caption="🎧 ترجمه ویس به صورت صدا")
        except Exception as e:
            await message.reply(f"❌ خطا در ارسال فایل: {e}")


# ---------------- Video Handler ----------------
def _save_bytesio_to_file(bytes_or_buffer, path: str):
    if hasattr(bytes_or_buffer, "read"):
        data = bytes_or_buffer.read()
    else:
        data = bytes_or_buffer
    with open(path, "wb") as f:
        f.write(data)


@dp.message(F.video | F.document)
async def handle_video(message: Message):
    uid = str(message.from_user.id)
    target = user_langs.get(uid)
    if not target:
        await message.answer("ابتدا زبان مقصد را انتخاب کنید (/start).")
        return

    await message.answer("📥 ویدیو دریافت شد، در حال پردازش...")

    file_id = None
    file_name = None
    if message.video:
        file_id = message.video.file_id
        file_name = getattr(message.video, "file_name", f"video_{uid}.mp4")
    elif message.document and message.document.mime_type and message.document.mime_type.startswith("video"):
        file_id = message.document.file_id
        file_name = message.document.file_name or f"video_{uid}.mp4"
    else:
        await message.reply("لطفاً فقط فایل ویدیو ارسال کنید.")
        return

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = Path(tmpdir) / file_name
        try:
            file_info = await bot.get_file(file_id)
            downloaded = await bot.download_file(file_info.file_path)
            _save_bytesio_to_file(downloaded, str(video_path))
        except Exception as e:
            await message.reply(f"❌ خطا در دانلود فایل: {e}")
            return

        wav_path = Path(tmpdir) / f"audio_{uid}.wav"
        try:
            clip = VideoFileClip(str(video_path))
            if clip.audio is None:
                await message.reply("این ویدیو صدا ندارد.")
                return
            clip.audio.write_audiofile(str(wav_path), fps=16000, codec="pcm_s16le", verbose=False, logger=None)
            clip.reader.close()
            clip.audio.reader.close_proc()
        except Exception as e:
            await message.reply(f"❌ خطا در استخراج صدا: {e}")
            return
