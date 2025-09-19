from aiogram import Bot,Dispatcher,types,F
from aiogram.types import Message,ReplyKeyboardMarkup,KeyboardButton,InlineKeyboardButton,InlineKeyboardMarkup
from aiogram.filters import CommandStart
import asyncio
from deep_translator import GoogleTranslator
import json
from pathlib import Path
import speech_recognition as sr
from pydub import AudioSegment



TOKEN = '8270631879:AAEXhJ9G_5PPLUUSiqYBgnRpZZ3RNlAp0kY'


bot = Bot(token=TOKEN)
dp = Dispatcher()

language_options={
    'فارسی':'fa',
    'انگلیسی':'en',
    'فرانسوی':'fr',
    'آلمانی':'de',
    'اسپانیایی':'es',
}

def get_language_keyboard():
    buttuns = [[KeyboardButton(text=name) for name in list(language_options.keys())[i:i+2]]
    for i in range(0, len(language_options),2)]
    return ReplyKeyboardMarkup(keyboard=buttuns,resize_keyboard=True)

def change_language():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="تغییر زبان مقصد", callback_data="change_target")]])


USER_LANG = Path("user_langs.json")
#temp_user_lang={}

def load_user_langs():
    if USER_LANG.exists():
        with USER_LANG.open("r" ,encoding="utf-8") as f:
            return json.load(f)
    return {}
user_langs = load_user_langs()

def save_user_langs(data):
    with USER_LANG.open("w", encoding="utf-8") as f:
        json.dump(data,f,ensure_ascii=False,indent=2)


@dp.message(CommandStart())
async def start_reply(message:Message):
    user_id = str(message.from_user.id)
    user_langs.pop(user_id,None)
    save_user_langs(user_langs)
    await message.answer( "سلام به ربات مترجم خوش آمدید زبان مقصد را انتخاب کنید " , reply_markup=get_language_keyboard())

@dp.message(F.text.in_(language_options.keys()))
async def handler_language_selection(message:Message):
    user_id = str(message.from_user.id)
    selected_lang = language_options[message.text]
    user_langs[user_id] = selected_lang
    save_user_langs(user_langs)
    await message.answer("متن را وارد کنید: \n  برای تغییر زبان مقصد دکمه زیر را فشار دهید." , reply_markup=change_language())
    reply_markup = types.ReplyKeyboardRemove()

@dp.callback_query(F.data=="change_target")
async def change_target(callback:types.CallbackQuery):
    user_id = str(callback.from_user.id)
    user_langs.pop(user_id,None)
    save_user_langs(user_langs)
    await callback.message.edit_text("زبان مقصد جدید را انتخاب کنید", reply_markup=None)
    await callback.message.answer("زبان مقصد را انتخاب کنید", reply_message=get_language_keyboard())
    await callback.answer()

@dp.message()
async def reply_message(message:Message):
    user_id = str(message.from_user.id)
    lang_data = user_langs.get(user_id)

    if not lang_data:
        await message.answer("ابتدا زبان مقصد را وارد کنید,برای انتخاب دستور /start را وارد کنید.")
        return
    try:
        tarjome = GoogleTranslator(source=lang_data['auto'],target=lang_data).translate(message.text)
        await message.reply(f"ترجمه: \n{tarjome}")
    except Exception as e:
        return f"اوه خطا زد از اول شروع کن /start"

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

