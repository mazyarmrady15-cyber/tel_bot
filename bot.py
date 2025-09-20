import os
import json
import asyncio
import speech_recognition as sr
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor
from deep_translator import GoogleTranslator
from pydub import AudioSegment

API_TOKEN = "8270631879:AAEXhJ9G_5PPLUUSiqYBgnRpZZ3RNlAp0kY"

# ساخت ربات
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot, storage=MemoryStorage())

# ذخیره زبان کاربران
USER_LANGS_FILE = "user_langs.json"
LANG_OPTIONS = {
    "🇬🇧 English": "en",
    "🇮🇷 فارسی": "fa",
    "🇹🇷 Türkçe": "tr",
    "🇷🇺 Русский": "ru",
    "🇸🇦 العربية": "ar",
    "🇪🇸 Español": "es",
    "🇫🇷 Français": "fr",
}

# ---------- مدیریت فایل زبان ----------
def load_user_langs():
    if os.path.exists(USER_LANGS_FILE):
        with open(USER_LANGS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_user_langs(data):
    with open(USER_LANGS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_langs = load_user_langs()


# ---------- استارت ----------
@dp.message_handler(commands=["start"])
async def command_start(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for lang in LANG_OPTIONS.keys():
        keyboard.add(lang)
    await message.answer("سلام! 🌍 لطفا زبان مورد نظر خود را انتخاب کنید:", reply_markup=keyboard)


# ---------- انتخاب زبان ----------
@dp.message_handler(lambda msg: msg.text in LANG_OPTIONS.keys())
async def set_language(message: types.Message):
    user_id = str(message.from_user.id)
    user_langs[user_id] = LANG_OPTIONS[message.text]
    save_user_langs(user_langs)
    await message.answer(f"زبان شما تنظیم شد: {message.text}", reply_markup=types.ReplyKeyboardRemove())


# ---------- ترجمه متن ----------
@dp.message_handler(content_types=["text"])
async def translate_text(message: types.Message):
    user_id = str(message.from_user.id)
    target_lang = user_langs.get(user_id, "en")

    try:
        translated = GoogleTranslator(source="auto", target=target_lang).translate(message.text)
        await message.reply(translated)
    except Exception as e:
        await message.reply(f"خطا در ترجمه: {e}")


# ---------- ترجمه ویس ----------
@dp.message_handler(content_types=["voice"])
async def voice_translator(message: types.Message):
    user_id = str(message.from_user.id)
    target_lang = user_langs.get(user_id, "en")

    file = await bot.get_file(message.voice.file_id)
    ogg_path = f"voice_{user_id}.ogg"
    wav_path = f"voice_{user_id}.wav"

    await bot.download_file(file.file_path, destination=ogg_path)

    # تبدیل ogg به wav
    AudioSegment.from_file(ogg_path, format="ogg").export(wav_path, format="wav")

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(wav_path) as src:
            audio = recognizer.record(src)
            text = recognizer.recognize_google(audio, language="auto")

            translated = GoogleTranslator(source="auto", target=target_lang).translate(text)
            await message.reply(translated)

    except Exception as e:
        await message.reply(f"خطا در پردازش ویس: {e}")

    finally:
        if os.path.exists(ogg_path):
            os.remove(ogg_path)
        if os.path.exists(wav_path):
            os.remove(wav_path)


# ---------- ران کردن ربات ----------
if name == "__main__":
    executor.start_polling(dp, skip_updates=True)
