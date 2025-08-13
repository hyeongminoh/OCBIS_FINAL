#logger 설정
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler

def get_logger(name: str = __name__,
               log_dir: str = "logs",
               level: int = logging.INFO) -> logging.Logger:
    os.makedirs(log_dir, exist_ok=True)

    #포맷
    fmt = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    #콘솔 핸들러
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)

    #파일 핸들러
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, f"{name}.log"),
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    file_handler.setFormatter(fmt)

    #루트 로거 구성(한번만)
    root = logging.getLogger()
    if not root.handlers:
        root.setLevel(level)
        root.addHandler(console)
        root.addHandler(file_handler)

    #모듈 전용 로거 반환
    logger = logging.getLogger(name)
    logger.setLevel(level)
    return logger
