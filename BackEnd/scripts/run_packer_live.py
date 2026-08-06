"""Drive the LOG packer against the real LLM and print what a user would see.

Usage:
    python scripts/run_packer_live.py --module mgmt_pressure
    python scripts/run_packer_live.py --free "他適合帶新人嗎？"
    python scripts/run_packer_live.py --module mgmt_pressure --dry-run
    python scripts/run_packer_live.py --list

This one DOES spend tokens (every other verify_* script uses a scripted model). --dry-run
assembles and prints the payload without calling anything.

The respondent is built from real trait rows so the payload is representative: it takes
one assessment's traits and picks a score inside each chosen band, which is the same shape
the frontend sends.
"""

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from sqlalchemy import text  # noqa: E402


def build_trait_report(project='CIA', limit=None, band='mixed'):
    """{project_name_abbreviation, traits:[{name, score}]} -- frontend payload shape."""
    from api_v2.database.connection import get_db_engine
    with get_db_engine().connect() as c:
        rows = c.execute(text("""
            SELECT d.trait_id, d.name_en, b.band, b.min_score, b.max_score
            FROM trait_definitions d JOIN trait_bands b USING (trait_id)
            WHERE d.trait_id LIKE :p ORDER BY d.trait_id, b.band
        """), {'p': f'{project}\\_%'}).fetchall()

    chosen, traits = {}, []
    for trait_id, name_en, b, lo, hi in rows:
        if trait_id in chosen:
            continue
        want = {'A': 'A', 'C': 'C'}.get(band) or ('A' if len(chosen) % 3 else 'C')
        if b != want:
            continue
        chosen[trait_id] = b
        traits.append({'name': name_en, 'score': (lo + hi) // 2})
        if limit and len(traits) >= limit:
            break
    return {'project_name_abbreviation': project, 'traits': traits}, chosen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--module', help='module_id, e.g. mgmt_pressure')
    ap.add_argument('--free', help='free-form question text')
    ap.add_argument('--project', default='CIA', choices=['CIA', 'ANI', 'SPA', 'CSR'])
    ap.add_argument('--traits', type=int, default=12, help='how many traits to include')
    ap.add_argument('--band', default='mixed', choices=['mixed', 'A', 'C'])
    ap.add_argument('--dry-run', action='store_true', help='assemble only, no API call')
    ap.add_argument('--list', action='store_true', help='list module ids and exit')
    args = ap.parse_args()

    # A bare app context is all RAGService needs (it reads current_app.config). Going
    # through create_app() would import the whole route tree and its dependencies, which
    # this script has no use for.
    from flask import Flask
    from api_v2.config.settings import Config
    app = Flask(__name__)
    app.config.from_object(Config)

    with app.app_context():
        from api_v2.services.module_map import module_map
        from api_v2.services.packed_chat import try_packed_stream
        from api_v2.services.respondent_adapter import from_trait_reports
        from api_v2.services.log_assembler import assemble

        if args.list:
            for module_id, cfg in module_map.modules.items():
                q = module_map.question_for(module_id)
                print(f'  {module_id:<22} idx={q["idx"]:<3} {q["type"]:<13} '
                      f'{q["audience"]:<12} {cfg["display_name"]}')
            return 0

        if not args.module and not args.free:
            print('need --module or --free (or --list)')
            return 1

        report, chosen = build_trait_report(args.project, args.traits, args.band)
        reports = {'LIVE1': report}
        basics = [{'candidate_id': 'LIVE1', 'name': '王智弘'}]
        respondents = from_trait_reports(reports, basics)
        question = module_map.question_for(args.module) if args.module else None

        print('=' * 70)
        print(f'module={args.module or "(free-form)"}  '
              f'question={question["title"] if question else "-"}  '
              f'type={question["type"] if question else "free"}')
        print(f'respondent: {respondents[0].name}, {len(respondents[0].scores)} traits '
              f'({args.project}) bands={sorted(set(respondents[0].scores.values()))}')

        log = assemble(respondents, question,
                       user_query=args.free if question is None else None)
        print(f'LOG: {len(log.to_log_text().splitlines())} lines / '
              f'{len(log.to_log_text())} chars   unit_check={log.audit["unit_check"]}')
        print(f'injected vocabulary: {len(log.injected_names)} names, '
              f'{len(log.injected_labels)} labels')

        if args.dry_run:
            print('\n--- payload head (40 lines) ---')
            for line in log.to_log_text().splitlines()[:40]:
                print('  ', line[:100])
            print('\n--- task instruction head ---')
            for line in log.instruction.splitlines()[:6]:
                print('  ', line[:100])
            print('\n[DRY RUN] nothing was sent.')
            return 0

        from api_v2.services.rag_engine import RAGService
        rag = RAGService()

        packed = try_packed_stream(rag, args.module, args.free or '', 'expert',
                                   reports, basics, 'LIVE')
        if packed is None:
            print('\npacker declined this request; the route would use the legacy path.')
            return 1

        print('\n' + '=' * 70)
        print('使用者實際會看到的內容')
        print('=' * 70)
        t0 = time.perf_counter()
        first_at = None
        n = 0
        for chunk in packed:
            content = chunk.choices[0].delta.content
            n += 1
            if first_at is None:
                first_at = time.perf_counter() - t0
            print(f'--- 段 {n}  (+{time.perf_counter() - t0:.1f}s)')
            print(content.rstrip())
        total = time.perf_counter() - t0

        audit = packed.finish()
        print('\n' + '=' * 70)
        print(f'segments={n}  first={first_at:.1f}s  total={total:.1f}s')
        print(f'status={audit.get("status")}  retry={audit.get("retry_count")}')
        print(f'sections={audit.get("expected_sections_check")}  '
              f'missing={audit.get("missing_sections")}  '
              f'calibration={audit.get("calibration_evidence_check")}')
        if audit.get('leakage_hits'):
            print(f'leakage_hits={audit["leakage_hits"]}')
        for seg in audit.get('segments', []):
            if seg['rewrites'] or seg['hits']:
                print(f'  seg {seg["index"]}: rewrites={seg["rewrites"]} '
                      f'hits={seg["hits"]} final={seg["final_hits"]}')
        for line in audit.get('log', []):
            print(f'  log: {line}')

        # Independent re-scan of everything released, as a belt-and-braces check.
        from api_v2.services.exit_scanner import ExitScanner
        released = ''.join(s for s in [packed._pipeline.result.answer])
        hits = ExitScanner.for_log(log).scan(released)
        print(f'\n[final re-scan] {len(hits)} hit(s) in the released text'
              + (f': {[h.text for h in hits]}' if hits else ' -- clean'))
        return 0


if __name__ == '__main__':
    sys.exit(main())
