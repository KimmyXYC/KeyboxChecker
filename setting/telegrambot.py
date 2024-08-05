# -*- coding: utf-8 -*-
# @Time    : 2023/11/18 上午12:32
# @File    : schema.py
# @Software: PyCharm
from typing import Optional

import requests
from dotenv import load_dotenv
from loguru import logger
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class TelegramBot(BaseSettings):
    """
    代理设置
    """

    token: Optional[str] = Field(None, validation_alias="TELEGRAM_BOT_TOKEN")
    proxy_address: Optional[str] = Field(
        None, validation_alias="TELEGRAM_BOT_PROXY_ADDRESS"
    )  # "all://127.0.0.1:7890"
    bot_link: Optional[str] = Field(None, validation_alias="TELEGRAM_BOT_LINK")
    bot_id: Optional[str] = Field(None, validation_alias="TELEGRAM_BOT_ID")
    bot_username: Optional[str] = Field(None, validation_alias="TELEGRAM_BOT_USERNAME")
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    @model_validator(mode="after")
    def bot_validator(self):
        if self.proxy_address:
            logger.success(f"TelegramBot proxy was set to {self.proxy_address}")
        if self.token is None:
            logger.info("\n🍀Check:Telegrambot token is empty")
        if self.bot_id is None and self.token:
            try:
                from telebot import TeleBot

                # 创建 Bot
                if self.proxy_address is not None:
                    from telebot import apihelper

                    if "socks5://" in self.proxy_address:
                        self.proxy_address = self.proxy_address.replace(
                            "socks5://", "socks5h://"
                        )
                    apihelper.proxy = {"https": self.proxy_address}
                _bot = TeleBot(token=self.token).get_me()
                self.bot_id = str(_bot.id)
                self.bot_username = _bot.username
                self.bot_link = f"https://t.me/{self.bot_username}"
            except requests.exceptions.ConnectTimeout:
                logger.error(
                    "\n🍀TelegramBot Connect Error --error ConnectTimeout, Please Check Your Network To Telegram"
                )
                raise requests.exceptions.ConnectTimeout
            except Exception as e:
                logger.error(f"\n🍀TelegramBot Connect Error --error {e}")
            else:
                logger.success(
                    f"🍀TelegramBot Init Connection Success --bot_name {self.bot_username} --bot_id {self.bot_id}"
                )
        return self

    @property
    def available(self):
        return self.token is not None


load_dotenv()
BotSetting = TelegramBot()
