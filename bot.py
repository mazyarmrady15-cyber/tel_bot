import os
import json
import asyncio
import threading
from pathlib import Path
from http.server import SimpleHTTPRequestHandler, HTTPServer

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.dispatcher.filters import CommandStart
from deep_translator import GoogleTranslator
import speech_recognition as sr
from pydub import AudioSegment


def run_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHTTPRequestHandler)
    server.serve_forever()


threading.Thread(target=run_server, daemon=True).start()

TOKEN = "اینجا توکن رباتت رو بذار"
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

language_options = {
    'فارسی': 'fa',
    'انگلیسی': 'en',
    'فرانسوی': 'fr',
    'آلمانی': 'de',
    'اسپانیایی': 'es',
}


def get_language_keyboard():
    buttons = [
        [KeyboardButton(text=name) for name in list(language_options.keys())[i:i + 2]]
        for i in range(0, len(language_options), 2)
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def change_language():
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="تغییر زبان مقصد", callback_data="change_target")]]
    )


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


@dp.message_handler(CommandStart())
async def start_reply(message: Message):
    user_id = str(message.from_user.id)
    user_langs.pop(user_id, None)
    save_user_langs(user_langs)
    await message.answer(
        "سلام به ربات مترجم خوش آمدید. زبان مقصد را انتخاب کنید:",
        reply_markup=get_language_keyboard()
    )


@dp.message_handler(lambda m: m.text in language_options.keys())
async def handler_language_selection(message: Message):
    user_id = str(message.from_user.id)
    selected_lang = language_options[message.text]
    user_langs[user_id] = selected_lang
    save_user_langs(user_langs)
    await message.answer(
        "متن را وارد کنید:\nبرای تغییر زبان مقصد دکمه زیر را فشار دهید.",
        reply_markup=change_language()
    )


@dp.callback_query_handler(lambda c: c.data == "change_target")
async def change_target(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_langs.pop(user_id, None)
    save_user_langs(user_langs)
    await callback.message.answer("زبان مقصد جدید را انتخاب کنید:", reply_markup=get_language_keyboard())
    await callback.answer()


@dp.message_handler(content_types=["text"])
async def reply_message(message: Message):
    user_id = str(message.from_user.id)
    target_lang = user_langs.get(user_id)

    if not target_lang:
        await message.answer("ابتدا زبان مقصد را انتخاب کنید. دستور /start را بزنید.")
        return

    try:
        tarjome = GoogleTranslator(source="auto", target=target_lang).translate(message.text)
        await message.reply(f"ترجمه:\n{tarjome}")
    except Exception as e:
        await message.reply(f"خطا در ترجمه: {e}")


@dp.message_handler(content_types=["voice"])
async def voice_translator(message: Message):
    user_id = str(message.from_user.id)
    target_lang = user_langs.get(user_id)

    if not target_lang:
        await message.answer("ابتدا با دستور /start زبان مقصد را انتخاب کنید.")
        return

    file_info = await bot.get_file(message.voice.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)

    ogg_path = f"voice_{user_id}.ogg"
    wav_path = f"voice_{user_id}.wav"

    with open(ogg_path, "wb") as f:
        f.write(downloaded_file.read())

    user_voice = AudioSegment.from_ogg(ogg_path)
    user_voice.export(wav_path, format="wav")

r = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        final_voice = r.record(source)
        try:
            Txt = r.recognize_google(final_voice, language="fa-IR")
            tarjome = GoogleTranslator(source="auto", target=target_lang).translate(Txt)
            await message.reply(f"ترجمه:\n{tarjome}", reply_markup=change_language())
        except Exception as e:
            await message.reply(f"خطا در پردازش صدا: {e}")

    os.remove(ogg_path)
    os.remove(wav_path)


if name == "__main__":
    executor.start_polling(dp, skip_updates=True)
