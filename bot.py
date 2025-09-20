import os
import json
import threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
import speech_recognition as sr
from pydub import AudioSegment

def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

TOKEN = "YOUR_TOKEN_HERE"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

language_options = {
    "فارسی": "fa",
    "انگلیسی": "en",
    "فرانسوی": "fr",
    "آلمانی": "de",
    "اسپانیایی": "es",
}

def get_language_keyboard():
    buttons = [
        [KeyboardButton(text=name) for name in list(language_options.keys())[i:i+2]]
        for i in range(0, len(language_options), 2)
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def change_language():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تغییر زبان مقصد", callback_data="change_target")]])

USER_LANG = Path("user_langs.json")

def load_user_langs():
    if USER_LANG.exists():
        with USER_LANG.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {}

user_langs = load_user_langs()

def save_user_langs(data):
    with USER_LANG.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

@dp.message_handler(commands=["start"])
async def start_reply(message: Message):
    user_id = str(message.from_user.id)
    user_langs.pop(user_id, None)
    save_user_langs(user_langs)
    await message.reply("سلام! زبان مقصد را انتخاب کنید:", reply_markup=get_language_keyboard())

@dp.message_handler(lambda m: m.text in language_options.keys())
async def handler_language_selection(message: Message):
    user_id = str(message.from_user.id)
    selected_lang = language_options[message.text]
    user_langs[user_id] = selected_lang
    save_user_langs(user_langs)
    await message.reply("متن را وارد کنید.\nبرای تغییر زبان مقصد دکمه زیر را فشار دهید.", reply_markup=change_language())

@dp.callback_query_handler(lambda c: c.data == "change_target")
async def change_target(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_langs.pop(user_id, None)
    save_user_langs(user_langs)
    await callback.message.answer("زبان مقصد جدید را انتخاب کنید:", reply_markup=get_language_keyboard())
    await callback.answer()

@dp.message_handler(lambda m: m.text and m.text not in language_options)
async def reply_message(message: Message):
    user_id = str(message.from_user.id)
    target_lang = user_langs.get(user_id)
    if not target_lang:
        await message.reply("ابتدا زبان مقصد را انتخاب کنید. دستور /start را بزنید.")
        return
    try:
        from deep_translator import GoogleTranslator
        tarjome = GoogleTranslator(source="auto", target=target_lang).translate(message.text)
        await message.reply(f"ترجمه:\n{tarjome}")
    except Exception as e:
        await message.reply(f"خطا در ترجمه: {e}")

@dp.message_handler(content_types=[types.ContentType.VOICE])
async def voice_translator(message: Message):
    user_id = str(message.from_user.id)
    target_lang = user_langs.get(user_id)
    if not target_lang:
        await message.reply("ابتدا زبان مقصد را انتخاب کنید (/start).")
        return
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    ogg_path = f"voice_{user_id}.ogg"
    wav_path = f"voice_{user_id}.wav"
    await file.download(ogg_path)
    user_voice = AudioSegment.from_file(ogg_path, format="ogg")
    user_voice.export(wav_path, format="wav")
    r = sr.Recognizer()
    with sr.AudioFile(wav_path) as src:
        audio_data = r.record(src)
    try:
        Txt = r.recognize_google(audio_data)
        from deep_translator import GoogleTranslator
        tarjome = GoogleTranslator(source="auto", target=target_lang).translate(Txt)
        await message.reply(f"ترجمه:\n{tarjome}", reply_markup=change_language())
    except Exception as e:
        await message.reply(f"خطا در پردازش صدا: {e}")
    try:
        os.remove(ogg_path)
    except:
        pass
    try:
        os.remove(wav_path)
    except:
        pass

if name == "__main__":
    executor.start_polling(dp, skip_updates=True)
