"""
Verify the trait-interaction band-matching fix in api_v2/services/context_builder.py.

Connects READ-ONLY to the live UAT DB and exercises the real ContextBuilder /
TraitInteraction / TraitBand / TraitDefinition models -- no writes are made to
trait_definitions / trait_bands / trait_interactions.

Usage:
    DB_HOST=... DB_PORT=... DB_USER=... DB_PASSWORD=... DB_NAME=... \
        python BackEnd/scripts/verify_trait_interactions.py

    Credentials are read from the environment (not hardcoded here) so this
    script can be committed without embedding any DB password. See
    database/connection.py::get_db_url() for the same DB_* variable names
    used by the live app.

Writes a human-readable report to:
    docs/investigations/2026-07-14_interaction_fix_verification.md
"""
import sys
import os
import re
from datetime import datetime

for _required in ('DB_HOST', 'DB_USER', 'DB_PASSWORD', 'DB_NAME'):
    if not os.environ.get(_required):
        print(f"[ERROR] Missing required env var {_required}. See usage in this file's docstring.")
        sys.exit(1)

# Allow importing the api_v2 package (same pattern as migrate_traits_from_excel.py)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import func
from api_v2.database import db_session, TraitBand, TraitInteraction, TraitDefinition
from api_v2.services.context_builder import ContextBuilder

REPO_ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
REPORT_PATH = os.path.join(REPO_ROOT, 'docs', 'investigations', '2026-07-14_interaction_fix_verification.md')

MISSING_CSR_TRAITS = ['CSR_01', 'CSR_12', 'CSR_21', 'CSR_23', 'CSR_31', 'CSR_32']

CANDIDATE_1_LABELS = [
    '主動掌控', '擁抱變化', '韌性充沛', '全心投入', '目標路徑清晰', '把不順視為暫時',
    '正向資源充沛', '對結果負全責', '原則守公平', '適度關懷', '情境自控', '適度同理',
    '原則彈性', '規則導向', '觀察後信', '自信含蓄', '策略拿捏', '彈性因應', '品質平衡',
    '理解後遵從', '情境調節', '任務可靠', '有限容忍', '契合時忠誠', '選擇性主動',
    '重點整理', '情境權衡', '適度溫和', '持續記恨', '持續投入',
]
CANDIDATE_2_LABELS = [
    '原則守公平', '流程有序', '低自我中心', '直率不操弄', '誠正節制', '對結果負全責',
    '規範堅守', '無私付出', '主動掌控', '先思後行', '彈性因應', '適度韌性', '契合時投入',
    '理解後遵從', '觀察後信', '選擇性接受', '任務可靠', '情境調節', '適度同理', '情境自控',
    '視情寬容', '現實中保有期待', '適度溫和', '刺激依賴', '有限容忍', '路徑不足',
    '資源不足', '低度依附', '被動回應', '完成優先',
]


def log(lines, text=''):
    print(text)
    lines.append(text)


def build_trait_id_band_map(labels, project='CSR'):
    """Resolve each semantic_label to its (trait_id, band) via trait_bands."""
    rows = db_session.query(TraitBand).filter(
        TraitBand.trait_project == project,
        TraitBand.semantic_label.in_(labels)
    ).all()
    by_label = {r.semantic_label: (r.trait_id, r.band) for r in rows}
    resolved = []
    unresolved = []
    for label in labels:
        if label in by_label:
            resolved.append((label,) + by_label[label])
        else:
            unresolved.append(label)
    return resolved, unresolved


def synth_trait_result(trait_id, band, report):
    """Build a synthetic-but-realistic raw trait_result dict that will pass
    through ContextBuilder's exact-match pipeline (uses our own name_en +
    an in-range score), reproducing the real matching + band-lookup steps."""
    trait_def = db_session.query(TraitDefinition).filter_by(trait_id=trait_id).first()
    band_row = db_session.query(TraitBand).filter_by(trait_id=trait_id, band=band).first()
    if not trait_def or not band_row:
        report.append(f"  [WARN] could not build synthetic data for {trait_id}/{band}")
        return None
    score = band_row.min_score if band_row.min_score is not None else 0
    if band_row.max_score is not None and score > band_row.max_score:
        score = band_row.max_score
    return {
        'chinese_name': trait_def.name_en,
        'score': score,
    }


def make_candidate(name, trait_id_band_pairs, project='CSR'):
    report = []
    trait_results = {}
    for trait_id, band in trait_id_band_pairs:
        r = synth_trait_result(trait_id, band, report)
        if r:
            trait_results[trait_id] = r
    return {
        'candidate_id': name,
        'name': name,
        'position': 'NA',
        'assessment': {
            'project_name_abbreviation': project,
            'trait_results': trait_results,
        },
    }, report


def main():
    lines = []
    log(lines, f"# Trait-Interaction Fix Verification Report")
    log(lines, f"")
    log(lines, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(lines, f"DB target: {os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']} (read-only)")
    log(lines, f"")

    # --- Step 1: empirical proof of the root cause ---
    log(lines, "## Step 1 -- Band format proof (why interactions were always empty)")
    log(lines, "")
    band_vals = sorted({r[0] for r in db_session.query(TraitBand.band).distinct().all()})
    primary_vals = sorted({r[0] for r in db_session.query(TraitInteraction.primary_band).distinct().all()})
    trigger_vals = sorted({r[0] for r in db_session.query(TraitInteraction.trigger_band).distinct().all()})
    log(lines, f"- `trait_bands.band` distinct values: {band_vals}")
    log(lines, f"- `trait_interactions.primary_band` distinct values: {primary_vals}")
    log(lines, f"- `trait_interactions.trigger_band` distinct values: {trigger_vals}")
    mismatch = not set(primary_vals).issubset(set(band_vals))
    log(lines, f"- primary_band vs trait_bands.band mismatch confirmed: **{mismatch}**")
    log(lines, "")

    total_interactions = db_session.query(TraitInteraction).count()
    log(lines, f"- Total rows in `trait_interactions`: {total_interactions}")
    log(lines, "")

    # --- Step 2: minimal deterministic regression case ---
    log(lines, "## Step 2 -- Minimal deterministic regression case")
    log(lines, "")
    known = db_session.query(TraitInteraction).filter(
        TraitInteraction.primary_trait_id.like('CSR_%')
    ).limit(3).all()

    step2_pass = True
    for k in known:
        primary_band_clean = k.primary_band.split('(')[0].strip()
        trigger_band_clean = (k.trigger_band or '').split('(')[0].strip()
        log(lines, f"### Case: primary={k.primary_trait_id} band={k.primary_band!r} "
                    f"trigger={k.trigger_trait_id} band={k.trigger_band!r}")

        cand, cand_report = make_candidate(
            'TestCandidate',
            [(k.primary_trait_id, primary_band_clean), (k.trigger_trait_id, trigger_band_clean)],
        )
        for r in cand_report:
            log(lines, r)

        builder = ContextBuilder({})
        result = builder.build({'enterprise_name': 'Test'}, [cand], mode='expert')
        found = k.narrative.strip() in result['interactions']
        step2_pass = step2_pass and found
        log(lines, f"- interactions component non-empty: {bool(result['interactions'].strip())}")
        log(lines, f"- expected narrative found verbatim: **{found}**")
        log(lines, "")
        log(lines, "```")
        log(lines, result['interactions'].strip() or '(empty)')
        log(lines, "```")
        log(lines, "")

    log(lines, f"**Step 2 overall: {'PASS' if step2_pass and known else 'FAIL/NO DATA'}**")
    log(lines, "")

    # --- Step 3: realistic replay of the real customer session's 2 candidates ---
    log(lines, "## Step 3 -- Realistic replay: 莊苑伶 / 林慧嵐 (docs/prompts.log session)")
    log(lines, "")
    log(lines, "Reconstructed from the `行為面向 —` semantic labels visible in `docs/prompts.log`, "
                "resolved back to (trait_id, band) via `trait_bands`, then re-run through the fixed "
                "`ContextBuilder.build()`. Uses our own `name_en` (guaranteed match) + an in-range "
                "synthetic score, so this does not depend on recovering the original vendor payload.")
    log(lines, "")

    for cand_name, labels in [('莊苑伶', CANDIDATE_1_LABELS), ('林慧嵐', CANDIDATE_2_LABELS)]:
        resolved, unresolved = build_trait_id_band_map(labels)
        log(lines, f"### {cand_name}")
        log(lines, f"- resolved {len(resolved)}/{len(labels)} labels to (trait_id, band)")
        if unresolved:
            log(lines, f"- unresolved labels: {unresolved}")

        pairs = [(t, b) for _, t, b in resolved]
        cand, cand_report = make_candidate(cand_name, pairs)
        for r in cand_report:
            log(lines, r)

        builder = ContextBuilder({})
        result = builder.build({'enterprise_name': 'Test'}, [cand], mode='expert')
        n_interactions = result['interactions'].count('行為交互作用')
        log(lines, f"- interaction narratives found after fix: **{n_interactions}**")
        log(lines, "")
        if result['interactions'].strip():
            log(lines, "```")
            log(lines, result['interactions'].strip())
            log(lines, "```")
        log(lines, "")

    # --- Step 4: audit summary for the 6 silently-missing CSR traits ---
    log(lines, "## Step 4 -- Audit summary: 6 silently-skipped CSR traits")
    log(lines, "")
    log(lines, "Both candidates in the real session were missing exactly the same 6 of 36 CSR "
                "traits (ruling out per-candidate randomness). Confirmed facts:")
    log(lines, "")
    defs = db_session.query(TraitDefinition).filter(TraitDefinition.trait_id.in_(MISSING_CSR_TRAITS)).all()
    defs_by_id = {d.trait_id: d for d in defs}
    log(lines, "| trait_id | name_zh | name_en |")
    log(lines, "|---|---|---|")
    for tid in MISSING_CSR_TRAITS:
        d = defs_by_id.get(tid)
        if d:
            log(lines, f"| {tid} | {d.name_zh} | {d.name_en} |")
        else:
            log(lines, f"| {tid} | (not found in trait_definitions) | |")
    log(lines, "")
    log(lines, "These `name_en` values were independently confirmed to match "
                "`docs/Traitty_RAG_SpeC_v6.1.xlsx` exactly -- our DB is not the source of the mismatch. "
                "The raw vendor payload (from `https://uat.traitty.com`) that would show the actual "
                "label string sent for these 6 traits is not persisted anywhere in this codebase.")
    log(lines, "")
    log(lines, "**Next step (requires a live trigger, not run by this script):** generate one CSR "
                "candidate report through the app (or replay a chat session for a CSR candidate). "
                "The diagnostic logging added in `context_builder.py` (Part B of this fix) will now "
                "record the exact raw `display_name` and failure reason to "
                "`BackEnd/api_v2/logs/<date>/trait_match_audit.log` for any trait that fails to match, "
                "which will reveal the vendor's actual label string for these 6 traits.")
    log(lines, "")

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines) + '\n')
    print(f"\n[OK] report written to {REPORT_PATH}")


if __name__ == '__main__':
    main()
