from asgiref.sync import sync_to_async
from loguru import logger
from telebot import types
from telebot import util
from telebot.async_telebot import AsyncTeleBot
from telebot.asyncio_helper import ApiTelegramException
from telebot.asyncio_storage import StateMemoryStorage

from setting.telegrambot import BotSetting
from app import event

StepCache = StateMemoryStorage()


@sync_to_async
def sync_to_async_func():
    pass


class BotRunner(object):
    def __init__(self):
        self.bot = AsyncTeleBot(BotSetting.token, state_storage=StepCache)

    async def run(self):
        logger.info("Bot Start")
        bot = self.bot
        if BotSetting.proxy_address:
            from telebot import asyncio_helper

            asyncio_helper.proxy = BotSetting.proxy_address
            logger.info("Proxy tunnels are being used!")

        @bot.message_handler(commands=['start', 'help'], chat_types=['private'])
        async def handle_start(message):
            await bot.reply_to(
                message,
                "Please send me a keybox.xml, and I will check if it is valid.\n\n"
                "Github: https://github.com/KimmyXYC/KeyboxChecker.git",
                disable_web_page_preview=True
            )

        @bot.message_handler(content_types=['document'], chat_types=['private'])
        async def handle_keybox(message: types.Message):
            if message.document.mime_type != 'application/xml' and message.document.mime_type != 'text/xml':
                await bot.reply_to(message, "File format error")
                return
            if message.document.file_size > 20 * 1024:
                await bot.reply_to(message, "File size is too large")
                return
            await event.keybox_check(bot, message, message.document)

        @bot.message_handler(commands=['check'])
        async def handle_keybox_check(message: types.Message):
            if message.reply_to_message and message.reply_to_message.document:
                document = message.reply_to_message.document
                if document.mime_type != 'application/xml' and document.mime_type != 'text/xml':
                    await bot.reply_to(message, "File format error")
                    return
                if document.file_size > 20 * 1024:
                    await bot.reply_to(message, "File size is too large")
                    return
                await event.keybox_check(bot, message, document)
            else:
                await bot.reply_to(message, "Please reply to a keybox.xml file")

        try:
            await bot.polling(
                non_stop=True, allowed_updates=util.update_types, skip_pending=True
            )
        except ApiTelegramException as e:
            logger.opt(exception=e).exception("ApiTelegramException")
        except Exception as e:
            logger.exception(e)
