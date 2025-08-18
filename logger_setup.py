#logger 설정
import os
import sys
import logging
from logging.handlers import TimedRotatingFileHandler
from datetime import datetime

def get_logger(name: str):
    LOG_DIR = "logs"
    os.makedirs(LOG_DIR, exist_ok=True)

    # 오늘 날짜를 파일명에 포함
    today_str = datetime.now().strftime("%Y%m%d")
    log_file = os.path.join(LOG_DIR, f"app_{today_str}.log")

    # 로거 생성
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False  # 중복 방지

    # 콘솔 핸들러
    console_handler = logging.StreamHandler(sys.stdout)

    # 파일 핸들러 (자정마다 새 파일 생성)
    file_handler = TimedRotatingFileHandler(
        filename=log_file,
        when="midnight",
        interval=1,
        backupCount=7,
        encoding="utf-8"
    )
    
   # 로그 포맷
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # 기존 핸들러 제거 후 새로 추가 (중복 방지)
    if logger.hasHandlers():
        logger.handlers.clear()

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)


    return logger
