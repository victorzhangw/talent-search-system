# -*- coding: utf-8 -*-
"""Generate assembled payload logs across all four assessments and both band
extremes, reusing the existing demo machinery. The model is never called.

Ad-hoc driver for the 0915 spec regression review; writes to scripts/coverage_logs/.
"""
import os, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'coverage_logs')

def redirect(path_dir):
    from datetime import datetime
    from api_v2.utils.logger import get_prompt_logger
    lg = get_prompt_logger()
    for h in lg.handlers:
        h.base_dir = path_dir
        h.current_date = None
        if h.file_output:
            h.file_output.close(); h.file_output = None
    p = os.path.join(path_dir, datetime.now().strftime('%Y-%m-%d'), 'prompts.log')
    if os.path.exists(p): os.remove(p)
    return p

def main():
    from flask import Flask
    from api_v2.config.settings import Config
    from run_packer_live import build_trait_report
    from api_v2.services.packed_chat import packed_stream
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from demo_prompt_log import _Rag

    app = Flask(__name__); app.config.from_object(Config)
    with app.app_context():
        path = redirect(OUT)
        for project in ('CIA', 'ANI', 'SPA', 'CSR'):
            for band in ('A', 'C'):
                report, chosen = build_trait_report(project, None, band)
                n = len(report['traits'])
                sid = f'COV-{project}-{band}'
                st = packed_stream(_Rag(), None, f'請完整說明這位受測者。', {'C1': report},
                                   [{'candidate_id': 'C1', 'name': '測試受測者'}], sid)
                if st is None:
                    print(f'  {project}/{band}: packed_stream returned None'); continue
                per = st._pipeline.log.audit['respondents'][0]
                print(f'  {project}/{band}: traits={n} full={per["full_blocks"]} '
                      f'index={per["index_lines"]} interactions={per["interaction_blocks"]} '
                      f'dropped={per.get("traits_dropped", 0)}')
        print(f'\nwritten: {path}')

if __name__ == '__main__':
    main()
