"""把 scripts/verify_*.py 全部跑過一輪，彙總成一個結束碼。

用法：
    python scripts/verify_all.py                    # 全部跑
    python scripts/verify_all.py --list             # 只列出會跑哪些
    python scripts/verify_all.py --only narrative_cleaner exit_scanner
    python scripts/verify_all.py --skip request_identity
    python scripts/verify_all.py --timeout 300

為什麼要有這支
--------------
`scripts/` 底下有三十幾支 `verify_*.py`，而專案唯一的 CI（`.github/workflows/keep-alive.yml`）
只是每十分鐘 ping 一次 Render，沒有任何自動化把關。實作文件 §1.2 訂的「前一單元 Check
未綠，不得開始下一單元」因此完全靠人記得逐支手動跑——紀律沒有東西在守。

這支把那份清單變成一行指令：任何一支非 0 結束，整體就非 0。

刻意不收進來的
--------------
會花錢或需要外部環境的不在自動清單裡，要跑就自己跑：

    scripts/redteam_packer.py      真實模型，DoD 紅隊關卡
    scripts/run_packer_live.py     真實模型，單次人工觀察
    scripts/uat_scenarios.py       打真實 HTTP，會扣受測帳號額度
    scripts/uat_db_check.py        需要 UAT 網段

輸出
----
每支的 stdout/stderr 原樣存到 `scripts/verify_all_logs/verify_all_<時戳>/<名稱>.log`，
彙總表同時印在畫面上並存成同一個目錄下的 `_summary.txt`。失敗的那幾支，摘要會把
輸出的最後幾行一起印出來，省得再去翻檔案。

不用 emoji：本專案的 Windows 主控台常常不是 UTF-8，emoji 會讓 print 直接丟
UnicodeEncodeError（見 CLAUDE.md）。狀態一律用 [OK] / [FAIL] / [TIMEOUT]。
"""

import argparse
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPTS_DIR)
# 專案的虛擬環境。用系統 Python 跑會有四支腳本掛在 `ModuleNotFoundError: flask_limiter`
# ——那不是缺陷，是直譯器挑錯了（`flask-limiter==4.1.1` 只裝在這個 venv 裡）。
VENV_PYTHON = os.path.join(BACKEND_DIR, 'api_v2', '.venv', 'Scripts', 'python.exe')
VENV_PYTHON_POSIX = os.path.join(BACKEND_DIR, 'api_v2', '.venv', 'bin', 'python')
# 刻意不用 scripts/verify_logs/：verify_prompt_log_history.py 會對那個目錄做
# shutil.rmtree()（它要驗的就是 logger 自己建目錄的行為），本 runner 的輸出放進去會
# 在跑到那一支時連同整個目錄被刪掉。
LOG_ROOT = os.path.join(SCRIPTS_DIR, 'verify_all_logs')

# 花錢或需要外部環境的，不進自動清單。名稱是去掉 verify_ 前綴與 .py 後綴的部分。
EXCLUDED = {
    'uat_scenarios',        # 由 scripts/uat_scenarios.py 打真實 HTTP 後才有 log 可讀
}

DEFAULT_TIMEOUT = 600
TAIL_LINES = 12


def discover():
    """scripts/verify_*.py，依檔名排序；verify_all 自己不算。"""
    out = []
    for name in sorted(os.listdir(SCRIPTS_DIR)):
        if not (name.startswith('verify_') and name.endswith('.py')):
            continue
        stem = name[len('verify_'):-len('.py')]
        if name == 'verify_all.py' or stem in EXCLUDED:
            continue
        out.append((stem, os.path.join(SCRIPTS_DIR, name)))
    return out


def resolve_python(explicit=None):
    """要用哪一個直譯器跑這些腳本。

    預設挑專案 venv，不是 `sys.executable`——後者是「誰啟動了這支 runner」，而用系統
    Python 啟動時 `verify_request_identity`／`verify_session_title`／`verify_settlement_env`／
    `verify_typewriter_meta` 會一起掛在 flask_limiter 匯入失敗上，看起來像四個缺陷。
    """
    if explicit:
        return explicit
    for candidate in (VENV_PYTHON, VENV_PYTHON_POSIX):
        if os.path.exists(candidate):
            return candidate
    return sys.executable


def run_one(stem, path, out_dir, timeout, python_exe):
    """跑一支，回傳 (狀態, 秒數, 輸出)。狀態是 OK / FAIL / TIMEOUT。"""
    env = dict(os.environ)
    # 子行程的中文輸出不要在 cp950 主控台炸掉，也讓落地的 log 一律是 UTF-8。
    env['PYTHONIOENCODING'] = 'utf-8'
    started = time.time()
    try:
        proc = subprocess.run(
            [python_exe, path],
            cwd=BACKEND_DIR,          # 這些腳本都假設 cwd 是 BackEnd
            env=env,
            capture_output=True,
            timeout=timeout,
        )
        elapsed = time.time() - started
        text = (proc.stdout + proc.stderr).decode('utf-8', errors='replace')
        status = 'OK' if proc.returncode == 0 else 'FAIL'
        text += f'\n\n[verify_all] returncode={proc.returncode}\n'
    except subprocess.TimeoutExpired as e:
        elapsed = time.time() - started
        captured = (e.stdout or b'') + (e.stderr or b'')
        text = captured.decode('utf-8', errors='replace')
        text += f'\n\n[verify_all] TIMEOUT after {timeout}s\n'
        status = 'TIMEOUT'

    # 有的腳本會清掉共用的輸出目錄，落地前重建一次比較安全。
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, stem + '.log'), 'w', encoding='utf-8') as f:
        f.write(text)
    return status, elapsed, text


def tail(text, n=TAIL_LINES):
    lines = [l for l in text.splitlines() if l.strip()]
    return lines[-n:] if len(lines) > n else lines


def main():
    ap = argparse.ArgumentParser(description='Run every scripts/verify_*.py and aggregate.')
    ap.add_argument('--list', action='store_true', help='只列出會跑哪些，不執行')
    ap.add_argument('--only', nargs='+', metavar='NAME', help='只跑這幾支（去掉 verify_ 前綴）')
    ap.add_argument('--skip', nargs='+', metavar='NAME', default=[], help='跳過這幾支')
    ap.add_argument('--timeout', type=int, default=DEFAULT_TIMEOUT, help='每支的秒數上限')
    ap.add_argument('--python', metavar='EXE', help='指定直譯器，預設用專案 venv')
    args = ap.parse_args()
    python_exe = resolve_python(args.python)

    scripts = discover()
    if args.only:
        wanted = set(args.only)
        scripts = [s for s in scripts if s[0] in wanted]
        missing = wanted - {s[0] for s in scripts}
        if missing:
            print(f'ERROR: 找不到這幾支：{sorted(missing)}')
            return 2
    if args.skip:
        skip = set(args.skip)
        scripts = [s for s in scripts if s[0] not in skip]

    if not scripts:
        print('ERROR: 沒有可執行的腳本')
        return 2

    if args.list:
        print(f'將執行 {len(scripts)} 支：')
        for stem, _ in scripts:
            print(f'  verify_{stem}.py')
        if EXCLUDED:
            print(f'\n刻意排除（會花錢或需外部環境）：{sorted(EXCLUDED)}')
        return 0

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_dir = os.path.join(LOG_ROOT, f'verify_all_{ts}')
    os.makedirs(out_dir, exist_ok=True)

    print(f'[verify_all] {len(scripts)} 支，輸出到 {out_dir}')
    print(f'[verify_all] 直譯器 {python_exe}')
    print('-' * 72)

    results = []
    for i, (stem, path) in enumerate(scripts, 1):
        print(f'[{i:2d}/{len(scripts)}] verify_{stem} ... ', end='', flush=True)
        status, elapsed, text = run_one(stem, path, out_dir, args.timeout, python_exe)
        print(f'[{status}] {elapsed:.1f}s')
        results.append((stem, status, elapsed, text))

    failed = [r for r in results if r[1] != 'OK']
    lines = []
    lines.append('-' * 72)
    lines.append(f'[verify_all] 通過 {len(results) - len(failed)} / {len(results)}')
    if failed:
        lines.append('')
        lines.append('未通過：')
        for stem, status, elapsed, text in failed:
            lines.append(f'  [{status}] verify_{stem}  ({elapsed:.1f}s)')
            for l in tail(text):
                lines.append(f'        {l}')
            lines.append(f'        -> {os.path.join(out_dir, stem + ".log")}')
    summary = '\n'.join(lines)
    print(summary)
    with open(os.path.join(out_dir, '_summary.txt'), 'w', encoding='utf-8') as f:
        f.write(summary + '\n')

    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
