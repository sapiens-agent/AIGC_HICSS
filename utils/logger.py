import logging
import os
from logging.handlers import TimedRotatingFileHandler
from .setting import settings

# create logs directory (if not exists)
log_dir = "logs"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# log file path (by date)
log_file = os.path.join(log_dir, "app.log")

# create logger
logger = logging.getLogger("my_logger")
logger.setLevel(settings.LOG_LEVEL.upper())  # set log level, optional DEBUG, INFO, WARNING, ERROR, CRITICAL

# **log format**
formatter = logging.Formatter(
    "%(asctime)s - [%(levelname)s] - %(filename)s:%(lineno)d - %(message)s"
)

# **generate log file by date**
file_handler = TimedRotatingFileHandler(
    log_file, when="midnight", interval=1, backupCount=7, encoding="utf-8"
)
file_handler.suffix = "%Y-%m-%d.log"  # set log file suffix format
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)

# **console log**
console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
console_handler.setLevel(logging.INFO)

# **add handlers**
logger.addHandler(file_handler)
logger.addHandler(console_handler)
