import asyncio
from loguru import logger
from telebot import util
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_storage import StateMemoryStorage
from App import Event


class BotRunner(object):
    def __init__(self, config):
        self.bot = config.bot
        self.proxy = config.proxy
        self.config = config

    def botcreate(self):
        bot = AsyncTeleBot(self.bot.botToken, state_storage=StateMemoryStorage())
        return bot, self.bot

    def run(self):
        logger.success("Bot Start")
        bot, _config = self.botcreate()
        if self.proxy.status:
            from telebot import asyncio_helper
            asyncio_helper.proxy = self.proxy.url
            logger.success("Proxy Set")

        @bot.message_handler(commands=['start'], chat_types=['private'])
        async def handle_start(message):
            await bot.reply_to(message, "Please send me a keybox.xml, and I will check if it is valid.")

        @bot.message_handler(content_types=['document'], chat_types=['private'])
        async def handle_keybox(message):
            if message.document.mime_type != 'application/xml' and message.document.mime_type != 'text/xml':
                await bot.reply_to(message, "File format error")
                return
            if message.document.file_size > 20 * 1024:
                await bot.reply_to(message, "File size is too large")
                return
            await Event.keybox_check(bot, message, message.document)

        @bot.message_handler(commands=['check'])
        async def handle_keybox_check(message):
            if message.reply_to_message and message.reply_to_message.document:
                document = message.reply_to_message.document
                if document.mime_type != 'application/xml' and document.mime_type != 'text/xml':
                    await bot.reply_to(message, "File format error")
                    return
                if document.file_size > 20 * 1024:
                    await bot.reply_to(message, "File size is too large")
                    return
                await Event.keybox_check(bot, message, document)
            else:
                await bot.reply_to(message, "Please reply to a keybox.xml file")

        async def main():
            await asyncio.gather(bot.polling(non_stop=True, allowed_updates=util.update_types))

        asyncio.run(main())
