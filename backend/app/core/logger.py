"""
日志配置模块，用 loguru 来管理日志。
loguru 比 Python 内置的 logging 好用不少，配置简单，还自带颜色和格式化。
这里配了两个输出：一个打到控制台（开发时看），一个写到文件（线上排查问题用）。
"""
import os
import sys
from loguru import logger

from backend.app.core.config import settings

# loguru 默认会往 stderr 输出，先移除掉，下面自己配
logger.remove()

# 第一个输出：控制台，带颜色高亮，看起来比较直观
logger.add(
    sys.stdout,
    level=settings.app_log_level,
    format=(
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    ),
    colorize=True,
)

# 第二个输出：写到 logs/ 目录下的文件里，文件名带日期
# 每天凌晨 0 点自动切一个新文件，旧的保留 30 天然后压缩成 .gz
log_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "logs")
os.makedirs(log_dir, exist_ok=True)

logger.add(
    os.path.join(log_dir, "app_{time:YYYY-MM-DD}.log"),
    level="DEBUG",              # 文件里记录所有级别的日志，方便事后排查
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
    rotation="00:00",           # 每天午夜轮转一个新文件
    retention="30 days",        # 超过 30 天的老日志自动删掉
    compression="gz",           # 旧日志压缩成 gzip 节省磁盘
    encoding="utf-8",
)
