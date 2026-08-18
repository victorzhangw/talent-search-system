import logging
import os
import re
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

def get_conversation_logger():
    """
    獲取專門紀錄對話歷程的 Logger
    """
    return get_daily_logger("Conversation_Logger", "conversations.log", level=logging.INFO)

def get_prompt_logger():
    """
    獲取紀錄「送出前完整 prompt」的 Logger（prompts.log）

    定義放在這裡而非 rag_engine，是因為舊路徑（模組 prompt）與 LOG 打包器路徑都要寫入
    同一個檔案。get_daily_logger 以 name 快取，兩邊各自定義一次的話，先被呼叫的那份
    formatter 會生效、另一份被靜默忽略——實際格式取決於哪條路徑先跑，無法預期。
    """
    formatter_str = "\n============================================================\nTIME: %(asctime)s\n%(message)s\n============================================================"
    return get_daily_logger("RAG_Prompt_Logger", "prompts.log", level=logging.INFO, formatter_str=formatter_str)


def history_text_block(history) -> str:
    """The history block, verbatim, oldest first.

    Lives here rather than beside either caller because the packer path and the legacy
    module-prompt path both write it, and a reviewer comparing the two records should not
    have to work out whether a formatting difference means a behavioural one.

    Not truncated and not summarised. Truncating would defeat the reason it exists: the
    reviewer is deciding whether a weak follow-up answer came from the data or from what
    the model remembered, and an excerpt cannot settle that. Growth is bounded by
    MAX_HISTORY_TURNS, and was measured against real logs before this landed -- a full
    window costs roughly 40% on top of a record that is already 20-39K characters, because
    the respondent trait blocks dominate it either way.
    """
    if not history:
        return '[CONVERSATION HISTORY]\n(none -- first turn of this session)\n'
    lines = [f'[CONVERSATION HISTORY] oldest first, verbatim, {len(history)} messages']
    for i, message in enumerate(history, 1):
        lines.append(f'--- #{i} {str(message.get("role", "?")).upper()} ---')
        lines.append(str(message.get('content', '')))
    return '\n'.join(lines) + '\n'


# session_id 會直接組進檔案路徑。前端送什麼過來後端並不保證，未經檢核的值可以用 `../`
# 把記錄寫到 logs 目錄之外，所以這裡採白名單而非黑名單。
_SAFE_SESSION_RE = re.compile(r'^[A-Za-z0-9_-]{1,64}$')


def _per_session_dir():
    """<彙總檔所在的日期資料夾>/prompts/。

    base_dir 是跟 handler 問來的，不是自己算的：demo/verify 腳本會把 handler 指向別的目錄，
    免得示範用的記錄混進正式的每日稽核軌跡。自己算就會漏掉那個轉向，兩份記錄落在不同地方。
    """
    handlers = [h for h in get_prompt_logger().handlers if hasattr(h, 'base_dir')]
    base_dir = handlers[0].base_dir if handlers else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
    return os.path.join(base_dir, datetime.now().strftime('%Y-%m-%d'), 'prompts')


def write_prompt_record(session_id, text, per_session=False):
    """寫一筆 prompt 記錄：彙總的 prompts.log，以及（開啟時）該 session 的專屬檔。

    彙總檔一定先寫，per-session 的失敗被單獨吞掉。順序是刻意的：per-session 檔是便利設施，
    彙總檔才是稽核軌跡，不能因為多寫一份而讓原本寫得成的記錄消失。這也是當初否決
    「依內容拆成兩個檔」的理由之一——那個做法有兩個都會遺失記錄的失敗點，這個只有一個。

    兩邊寫的是同一段 `text`，per-session 檔自己補上與彙總檔相同的時間戳封裝（logging 的
    formatter 只作用在 handler 上，這裡沒有經過 handler）。
    """
    get_prompt_logger().info(text)
    if not per_session:
        return
    try:
        safe = session_id if _SAFE_SESSION_RE.match(str(session_id or '')) else 'unknown'
        directory = _per_session_dir()
        os.makedirs(directory, exist_ok=True)
        stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(os.path.join(directory, f'{safe}.log'), 'a', encoding='utf-8') as f:
            f.write(f"\n{'=' * 60}\nTIME: {stamp}\n{text}\n{'=' * 60}\n")
    except Exception as e:
        # 這裡不能用 get_prompt_logger()：那會把警告寫進 prompts.log，混在 prompt 記錄中間。
        get_daily_logger('RAG_Logger', 'rag_service.log', level=logging.DEBUG).warning(
            f"[PromptLog] per-session write failed for session={session_id}: {e}")
