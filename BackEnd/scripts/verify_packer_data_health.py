"""Answer the client's 0810 log questions against whichever DB the env points at.

Usage:
    # local (reads BackEnd/api_v2/.env)
    python scripts/verify_packer_data_health.py

    # UAT, read-only, credentials from the shell so nothing is committed
    DB_HOST=... DB_PORT=... DB_USER=... DB_PASSWORD=... DB_NAME=... \
        python scripts/verify_packer_data_health.py

The 0810 log the client reviewed was produced on a *different* machine from the one
this repository is developed on: our own BackEnd/api_v2/logs/2026-08-10/prompts.log,
written by the same code on the same day, contains both of the things they say are
missing. So the packer code is not the variable -- the trait data behind it is, and
this script reads the four tables the packer depends on and then assembles a real LOG
so the answer is the payload itself, not a row count.

Read-only: no INSERT/UPDATE/DELETE, safe against UAT or production.

Sections map one-to-one onto the client's questions:

    [1] 可用於／禁止 missing        -> trait_bands.ai_guidance needs do_raw/dont_raw,
                                       which only migrations run after 2026-08-05
                                       (commit c2d3858) write.
    [2] 交互作用 block missing      -> needs trait_interactions rows whose BOTH band
                                       columns compare equal to trait_bands.band, plus
                                       a populated endpoint_blocks.
    [3] CIA_36 / trait coverage     -> whether the spec's 113 traits are all loaded.
    [4] end-to-end assemble         -> the two blocks either appear in the payload or
                                       they do not.
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

# Shell DB_* wins, so the same script can be aimed at UAT without editing .env.
_shell_db = {k: os.environ.get(k) for k in ('DB_HOST', 'DB_PORT', 'DB_USER',
                                            'DB_PASSWORD', 'DB_NAME')}
from dotenv import load_dotenv  # noqa: E402
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')
for _k, _v in _shell_db.items():
    if _v:
        os.environ[_k] = _v

from sqlalchemy import text  # noqa: E402

from api_v2.database.connection import get_db_engine  # noqa: E402

# The spec's own totals, from docs/0730/Traitty_調整_20260728＿final/traits_113_v6_2.json
# and docs/0805 02_08 V6.3 spec_.xlsx. Hard-coded so the check fails when the DB
# shrinks, rather than comparing the DB against itself.
SPEC_TRAITS = {'ANI': 23, 'CIA': 36, 'SPA': 18, 'CSR': 36}
SPEC_BAND_ROWS = 339
SPEC_INTERACTIONS = 2389
SPEC_ENDPOINTS = 74
SPEC_BLOCKS = 3

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()


def table_exists(conn, name):
    return bool(scalar(conn, "SELECT to_regclass(:n) IS NOT NULL", n=f'public.{name}'))


def main():
    engine = get_db_engine()
    url = engine.url
    print(f'DB target: {url.host}:{url.port}/{url.database} as {url.username} (read-only)')

    with engine.connect() as conn:
        # -- [1] 可用於／禁止 ---------------------------------------------------
        print('\n[1] 判讀主體特質的「可用於／禁止」兩行 (客戶問題 1b)')
        # trait_blocks.render_full_block emits these two lines only when
        # ai_guidance->>'do_raw' / 'dont_raw' are non-empty. The pre-2026-08-05
        # importer wrote only the lossy 'do'/'dont' lists, so a DB loaded before
        # commit c2d3858 renders two lines per trait instead of four -- exactly what
        # the client saw -- with no error anywhere.
        total_bands = scalar(conn, 'SELECT count(*) FROM trait_bands')
        with_raw = scalar(conn, """
            SELECT count(*) FROM trait_bands
            WHERE coalesce(ai_guidance->>'do_raw', '') <> ''
              AND coalesce(ai_guidance->>'dont_raw', '') <> ''
        """)
        # `->>` rather than the `?` key-exists operator: the column is `json`, not
        # `jsonb`, and `?` is jsonb-only (psycopg2.errors.UndefinedFunction).
        legacy_only = scalar(conn, """
            SELECT count(*) FROM trait_bands
            WHERE coalesce(ai_guidance->>'do_raw', '') = ''
              AND coalesce(ai_guidance->>'do', '') <> ''
        """)
        print(f'      trait_bands rows: {total_bands} (spec {SPEC_BAND_ROWS})')
        print(f'      with do_raw+dont_raw: {with_raw}   legacy list-only: {legacy_only}')
        check('every band row carries do_raw/dont_raw', with_raw == total_bands,
              f'{total_bands - with_raw} row(s) would render without 可用於／禁止')
        if legacy_only:
            print('      -> this DB was loaded before commit c2d3858 (2026-08-05 17:00). '
                  'Re-run scripts/migrate_traits_from_excel.py with the V6.3 spec.')

        # -- [2] interaction data ----------------------------------------------
        print('\n[2] 交互作用區塊 (客戶問題 1a)')
        for name in ('endpoint_blocks', 'trait_endpoints'):
            if not table_exists(conn, name):
                check(f'{name} exists', False,
                      'missing -> assemble() raises before anything is logged')
                print('      run scripts/migrations/2026-08-05_add_endpoint_tables.sql')
                return 1

        n_blocks = scalar(conn, 'SELECT count(*) FROM endpoint_blocks')
        n_eps = scalar(conn, 'SELECT count(*) FROM trait_endpoints')
        n_int = scalar(conn, 'SELECT count(*) FROM trait_interactions')
        # `_blocks` empty is the one state that silences BOTH question types at once:
        # scoped gets None from resolve_block, and whole-person's fallback block is
        # then dropped by the ordered_blocks() loop that renders it.
        check('endpoint_blocks populated', n_blocks == SPEC_BLOCKS,
              f'{n_blocks} rows (spec {SPEC_BLOCKS}); 0 silences every sub-block')
        check('trait_endpoints populated', n_eps == SPEC_ENDPOINTS,
              f'{n_eps} rows (spec {SPEC_ENDPOINTS}); 0 empties 作答校準與風險提示')
        check('trait_interactions loaded', n_int == SPEC_INTERACTIONS,
              f'{n_int} rows (spec {SPEC_INTERACTIONS})')

        # Band format. interaction_selector normalizes primary_band in SQL but takes
        # trigger_band verbatim, so a suffix on the trigger side alone drops every
        # candidate to zero while the legacy path (which normalizes both) still works.
        bands = [r[0] for r in conn.execute(text(
            'SELECT DISTINCT band FROM trait_bands ORDER BY 1'))]
        pb = [r[0] for r in conn.execute(text(
            'SELECT DISTINCT primary_band FROM trait_interactions ORDER BY 1'))]
        tb = [r[0] for r in conn.execute(text(
            'SELECT DISTINCT trigger_band FROM trait_interactions '
            'WHERE trigger_band IS NOT NULL ORDER BY 1'))]
        print(f'      trait_bands.band          : {bands}')
        print(f'      interactions.primary_band : {pb}')
        print(f'      interactions.trigger_band : {tb}')
        check('trigger_band matches trait_bands.band verbatim',
              set(tb) <= set(bands),
              f'{sorted(set(tb) - set(bands))} never compares equal -> 0 candidates')

        usable = scalar(conn, """
            SELECT count(*) FROM trait_interactions
            WHERE trigger_trait_id IS NOT NULL AND narrative IS NOT NULL
        """)
        check('rows survive the packer\'s own WHERE clause', usable == SPEC_INTERACTIONS,
              f'{usable} of {n_int}')

        # -- [3] trait coverage -------------------------------------------------
        print('\n[3] 特質涵蓋範圍 (客戶問題 3)')
        by_family = dict(conn.execute(text("""
            SELECT split_part(trait_id, '_', 1), count(*)
            FROM trait_definitions GROUP BY 1 ORDER BY 1
        """)).fetchall())
        print(f'      trait_definitions by family: {by_family}')
        check('all four assessments at full spec size', by_family == SPEC_TRAITS,
              f'spec {SPEC_TRAITS}')
        has36 = scalar(conn, "SELECT count(*) FROM trait_definitions "
                             "WHERE trait_id = 'CIA_36'")
        check('CIA_36 情緒易激度 exists (Q5 and Q14 both scope it)', has36 == 1)

        # -- 廠商送的名字要對得上規格正本的名字（修正計畫 Unit 6）------------------
        # 對不上就整個特質被丟掉，而答案照樣寫得完整，讀的人看不出少了東西。
        from api_v2.services.respondent_adapter import spec_name_key, normalize_en_name
        typo = [r[0] for r in conn.execute(text(
            "select trait_id from trait_definitions where name_en ~ '[0-9]$'"))]
        check('沒有任何 name_en 以數字結尾（ANI_02 曾經是 Resilience1，'
              '害每位 ANI 受測者的韌性都被丟掉）', not typo, typo)
        by_key = {}
        for tid, en in conn.execute(text('select trait_id, name_en from trait_definitions')):
            by_key.setdefault((tid.split('_')[0], normalize_en_name(en)), []).append(tid)
        for abbrev, vendor_name, expected in (
                ('ANI', 'Resilience', 'ANI_02'),
                ('CSR', 'Materialism Avoidance', 'CSR_23'),   # 廠商用字與正本不同，走別名
                ('CSR', 'Material Avoidance', 'CSR_23'),      # 正本用字仍要能命中
                # 同一個字串在 CIA 裡是正本用字。別名若不分測驗，CIA_12 會找不到自己。
                ('CIA', 'Materialism Avoidance', 'CIA_12')):
            hit = by_key.get((abbrev, spec_name_key(vendor_name, abbrev)), [])
            check(f'{abbrev} 的 {vendor_name!r} 解析得到 {expected}', hit == [expected], hit)

    # -- [4] end to end ---------------------------------------------------------
    # Row counts can all look plausible and the payload still come out short, so the
    # last word is an assembled LOG. Uses a respondent carrying every CIA trait, which
    # is what the frontend sends; the client's Q5 log only had CIA_01-12 because it
    # was produced by run_packer_live.py, whose --traits default is 12.
    print('\n[4] 實際組裝一份 LOG (客戶問題 1a + 1b + 3 的合併驗收)')
    from flask import Flask
    from api_v2.config.settings import Config
    app = Flask(__name__)
    app.config.from_object(Config)
    with app.app_context():
        from api_v2.services.log_assembler import Respondent, assemble
        from api_v2.services.module_map import module_map

        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT DISTINCT ON (trait_id) trait_id, band FROM trait_bands
                WHERE trait_id LIKE 'CIA\\_%' ORDER BY trait_id, band
            """)).fetchall()
        scores = {t: b for t, b in rows}
        print(f'      respondent: {len(scores)} CIA traits')

        for module_id, label in (('mgmt_pressure', 'Q5 scoped/single'),
                                 ('team_complement', 'Q14 scoped/multi'),
                                 ('team_meeting', 'Q15 whole_person/multi')):
            question = module_map.question_for(module_id)
            n = 2 if question.get('audience') == 'multi_only' else 1
            people = [Respondent(f'測試{i + 1}', f'T{i + 1}', dict(scores)) for i in range(n)]
            log = assemble(people, question)
            body = log.to_log_text()
            per = log.audit['respondents'][0]
            print(f'      {module_id:<16} {label:<24} '
                  f'full={per["full_blocks"]} index={per["index_lines"]} '
                  f'interactions={per["interaction_blocks"]}')
            check(f'{module_id}: 可用於／禁止 present', '可用於：' in body and '禁止：' in body)
            check(f'{module_id}: at least one 交互作用 sub-block',
                  '#### 交互作用' in body, per['interaction_blocks'])
            if question['type'] == 'scoped':
                cia = set((question['scoped_traits'] or {}).get('CIA') or [])
                check(f'{module_id}: every scoped CIA trait became a full block',
                      per['full_blocks'] == len(cia & set(scores)),
                      f'{per["full_blocks"]} of {len(cia)} scoped')

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
