import logging
import os
from datetime import datetime

class DateFolderFileHandler(logging.Handler):
    """
    動態根據目前日期建立資料夾，並將 Log 寫入對應日期的資料夾中
    例如: logs/2026-03-06/rag_service.log
    """
    def __init__(self, base_dir, filename, encoding='utf-8'):
        super().__init__()
        self.base_dir = base_dir
        self.filename = filename
        self.encoding = encoding
        self.current_date = None
        self.file_output = None
        
    def _get_file(self):
        today = datetime.now().strftime('%Y-%m-%d')
        # 如果日期換了，或者檔案還沒打開，就關閉舊的並開新的
        if self.current_date != today or self.file_output is None:
            if self.file_output:
                self.file_output.close()
            self.current_date = today
            date_dir = os.path.join(self.base_dir, today)
            os.makedirs(date_dir, exist_ok=True)
            log_path = os.path.join(date_dir, self.filename)
            self.file_output = open(log_path, 'a', encoding=self.encoding)
        return self.file_output

    def emit(self, record):
        try:
            msg = self.format(record)
            f = self._get_file()
            f.write(msg + '\n')
            f.flush() # 確保即時寫入硬碟
        except Exception:
            self.handleError(record)
            
    def close(self):
        if self.file_output:
            self.file_output.close()
            self.file_output = None
        super().close()

def get_daily_logger(name: str, filename: str, level=logging.INFO, formatter_str=None):
    """
    獲取支援每日資料夾的 Logger
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        # 定位至 api_v2 專案根目錄下的 logs
        # __file__ 預期在 api_v2/utils/logger.py
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_base_dir = os.path.join(project_root, 'logs')
        
        handler = DateFolderFileHandler(log_base_dir, filename)
        
        if not formatter_str:
            formatter_str = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            
        formatter = logging.Formatter(fmt=formatter_str, datefmt="%Y-%m-%d %H:%M:%S")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
        
    return logger
