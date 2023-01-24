import os
import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from telebot.types import Message

from vk_book_reader import VkBookReader, Extensions

TOKEN = os.environ.get('TG_BOT_TOKEN')

bot = AsyncTeleBot(TOKEN)

bot.search_book_title = None
bot.search_ext = None


@bot.message_handler(commands=['start'])
async def start(message: Message):
    await bot.send_message(
        message.chat.id, "Hello! To load book use /search <book_name author>. Example: /search war and peace tolstoy"
    )


@bot.message_handler(commands=['search'])
async def search(message: Message):
    extensions_keyboard = types.ReplyKeyboardMarkup(one_time_keyboard=True)
    for extension in Extensions:
        extensions_keyboard.add(
            types.KeyboardButton(extension)
        )
    bot.search_book_title = message.text.replace('/search', '').strip()

    await bot.send_message(message.chat.id, 'Choice book format', reply_markup=extensions_keyboard)


@bot.message_handler(content_types=['text'])
async def show_books(message: Message):
    if bot.search_book_title and message.text in Extensions.values():
        bot.search_ext = message.text

    vk_book_reader = VkBookReader(bot.search_ext)
    books = await vk_book_reader.get_books_by_search(q=bot.search_book_title)

    if books:
        markup = types.InlineKeyboardMarkup()
        for book in books:
            markup.add(types.InlineKeyboardButton(text=book.title, url=book.url))
        await bot.send_message(message.chat.id, '-', reply_markup=markup)
    else:
        await bot.send_message(message.chat.id, 'No books were found')


if __name__ == '__main__':
    asyncio.run(bot.polling())
