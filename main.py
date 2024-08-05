import asyncio
import sys

from dotenv import load_dotenv
from loguru import logger

from app.controller import BotRunner
from app_conf import settings

load_dotenv()
# 移除默认的日志处理器
logger.remove()
# 添加标准输出
print("从配置文件中读取到的DEBUG为", settings.app.debug)
handler_id = logger.add(sys.stderr, level="INFO" if not settings.app.debug else "DEBUG")
# 添加文件写出
logger.add(
    sink="run.log",
    format="{time} - {level} - {message}",
    level="INFO",
    rotation="100 MB",
    enqueue=True,
)

logger.info("Log Is Secret, Please Don't Share It To Others")


async def main():
    await asyncio.gather(BotRunner().run())


loop = asyncio.get_event_loop()
loop.run_until_complete(main())
