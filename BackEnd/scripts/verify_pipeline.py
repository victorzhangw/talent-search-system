"""End-to-end pipeline and module mapping, driven by a scripted model.

Usage:
    python scripts/verify_pipeline.py

Covers 事項 04 (module_id -> question) and the assemble -> stream -> gate -> audit path.
No API calls: the "model" is a list of canned replies, so the assertions are about what
the pipeline does with them, not about model quality.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.module_map import module_map, ModuleMap  # noqa: E402
from api_v2.services.log_assembler import Respondent, AudienceMismatch  # noqa: E402
from api_v2.services.log_pipeline import (LogPipeline, REWRITE_INSTRUCTION,  # noqa: E402
                                          COMPLETION_INSTRUCTION)
from api_v2.services.segment_gate import STATUS_OK, STATUS_BLOCKED  # noqa: E402

failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def tokens(text, size=7):
    return [text[i:i + size] for i in range(0, len(text), size)]


def main():
    print('\n[1] 事項 04: module_id <-> question')
    check('all 22 modules map', len(module_map) == 22, len(module_map))
    check('recruit_interview -> idx 1', module_map.idx_for('recruit_interview') == 1)
    check('team_meeting -> idx 15', module_map.idx_for('team_meeting') == 15)
    check('reverse lookup works', module_map.module_for(15) == 'team_meeting')
    check('unknown module returns None', module_map.idx_for('nope') is None)
    check('question_for returns the row',
          module_map.question_for('recruit_interview')['title'] == '快速面試提問指南')
    check('mapping is by title, not position',
          all(module_map.question_for(m)['title'] == cfg['display_name']
              for m, cfg in module_map.modules.items()))
    check('an inconsistent mapping raises instead of degrading',
          _rejects_bad_mapping())

    q5 = table.get('如何面對困難、壓力、挑戰')
    r1 = [Respondent('王智弘', 'R1', {'CIA_01': 'A', 'CIA_05': 'B', 'CIA_33': 'A'})]
    sections = q5['expected_sections']
    good = ''.join(f'{i + 1}. {s}\n以行為事例佐證其表現。\n\n' for i, s in enumerate(sections))

    print('\n[2] Happy path')
    seen_messages = []

    def stream_ok(messages):
        seen_messages.append(messages)
        return tokens(good)

    pipe = LogPipeline(r1, q5)
    out = list(pipe.stream(stream_ok))
    check('segments were released', out and ''.join(out) == good, len(out))
    check('status ok', pipe.result.status == STATUS_OK, pipe.result.gate.result.as_audit())
    check('model got system + user, in that order',
          [m['role'] for m in seen_messages[0]] == ['system', 'user'])
    check('the payload carries the trait blocks',
          '[特質 | CIA_05_B' in seen_messages[0][0]['content'])
    check('answer is what was released', pipe.result.answer == ''.join(out))

    print('\n[3] Audit merges packer and guard records')
    audit = pipe.result.audit
    for key in ('question_id', 'audience', 'unit_check', 'status', 'retry_count',
                'expected_sections_check', 'calibration_evidence_check', 'segments'):
        check(f'audit carries {key}', key in audit, audit.get(key))
    check('question_id is the idx', audit['question_id'] == q5['idx'])

    print('\n[4] Leak -> rewrite follow-up')
    leaky = ('1. 壓力情境下的典型反應模式\n他的 CIA_05 表現尚可。\n\n'
             + ''.join(f'{i + 2}. {s}\n以行為事例佐證。\n\n'
                       for i, s in enumerate(sections[1:])))
    prompts = []

    def followup(messages, instruction):
        prompts.append((messages, instruction))
        if instruction.startswith('上一段輸出'):
            return '1. 壓力情境下的典型反應模式\n他在壓力下的自我控制表現尚可。\n\n'
        return '4. 恢復與調適建議\n安排交付後緩衝期。\n\n'

    pipe = LogPipeline(r1, q5, followup_fn=followup)
    out = ''.join(pipe.stream(lambda m: tokens(leaky)))
    check('nothing released contains the marker', 'CIA_05' not in out)
    check('status ok after rewrite', pipe.result.status == STATUS_OK)
    check('one leakage retry', pipe.result.audit['retry_count']['leakage'] == 1,
          pipe.result.audit['retry_count'])

    msgs, instruction = prompts[0]
    check('rewrite prompt names the banned term', 'CIA_05' in instruction)
    check('rewrite prompt asks for a restatement, not a deletion',
          '不是刪除這些字詞' in instruction)
    check('rewrite turn carries the draft as an assistant message',
          msgs[-1]['role'] == 'assistant' and 'CIA_05' in msgs[-1]['content'])
    check('rewrite turn still carries the payload', msgs[0]['role'] == 'system')

    print('\n[5] Missing section -> completion follow-up')
    partial = ''.join(f'{i + 1}. {s}\n以行為事例佐證。\n\n'
                      for i, s in enumerate(sections[:-1]))
    prompts.clear()
    pipe = LogPipeline(r1, q5, followup_fn=followup)
    out = ''.join(pipe.stream(lambda m: tokens(partial)))
    check('the missing section was appended', sections[-1] in out)
    check('status ok', pipe.result.status == STATUS_OK)
    check('counted as a completeness retry, not a leakage one',
          pipe.result.audit['retry_count'] == {'leakage': 0, 'completeness': 1},
          pipe.result.audit['retry_count'])
    check('completion prompt says what is missing',
          prompts and sections[-1] in prompts[0][1], prompts[0][1] if prompts else None)
    check('completion prompt forbids repeating earlier sections',
          '不要重寫或重複已經輸出過的段落' in prompts[0][1])

    print('\n[6] Unfixable leak blocks the rest')
    pipe = LogPipeline(r1, q5, followup_fn=lambda m, i: '他的 CIA_05 還是在。\n\n')
    out = ''.join(pipe.stream(lambda m: tokens(leaky)))
    check('nothing leaked to the caller', 'CIA_05' not in out)
    check('later clean sections were withheld', sections[-1] not in out)
    check('status blocked', pipe.result.status == STATUS_BLOCKED)
    check('the surviving term is in the audit',
          'CIA_05' in pipe.result.audit['leakage_hits'], pipe.result.audit['leakage_hits'])

    print('\n[7] audience is enforced before the model is called')
    called = []
    single_only = table.get('快速面試提問指南')
    two = r1 + [Respondent('林孟德', 'R2', {'CIA_01': 'A'})]
    try:
        LogPipeline(two, single_only)
        raised = False
    except AudienceMismatch:
        raised = True
    check('single_only + 2 respondents raises at construction', raised)
    check('the model was never called', not called)

    print('\n[8] Free-form')
    pipe = LogPipeline(r1, None, user_query='他適合帶新人嗎？')
    out = ''.join(pipe.stream(lambda m: tokens('他在指導他人時通常有耐心。\n\n')))
    check('free-form runs and releases', out.strip().startswith('他在指導'))
    check('the user question is the task instruction',
          pipe.log.instruction.endswith('他適合帶新人嗎？'))
    check('no section check on free-form',
          pipe.result.audit['expected_sections_check'] != 'failed'
          and not pipe.result.audit['missing_sections'])
    # b §8「共同」: this respondent scores A on 社會期望反應, so evidence wording is required
    # even in free-form. Without it the answer is incomplete, not clean-and-done.
    check('missing evidence wording -> manual_review, not ok',
          pipe.result.status == 'manual_review'
          and pipe.result.audit['calibration_evidence_check'] == 'failed',
          pipe.result.status)
    pipe = LogPipeline(r1, None, user_query='他適合帶新人嗎？')
    out = ''.join(pipe.stream(lambda m: tokens('他在指導他人時通常有耐心，建議以行為事例佐證。\n\n')))
    check('with evidence wording -> ok', pipe.result.status == STATUS_OK,
          pipe.result.audit['calibration_evidence_check'])
    r_nocalib = [Respondent('林孟德', 'R9', {'CIA_01': 'A'})]
    pipe = LogPipeline(r_nocalib, None, user_query='他適合帶新人嗎？')
    ''.join(pipe.stream(lambda m: tokens('他做事有一致的自我要求。\n\n')))
    check('no calibration trait -> evidence not required', pipe.result.status == STATUS_OK,
          pipe.result.audit['calibration_evidence_check'])

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


def _rejects_bad_mapping():
    import json
    import tempfile
    data = json.load(open(os.path.join(os.path.dirname(__file__), '..', 'api_v2', 'config',
                                       'quick_modules.json'), encoding='utf-8'))
    first = next(iter(data))
    data[first]['display_name'] = '不存在的題目'
    with tempfile.NamedTemporaryFile('w', suffix='.json', delete=False, encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
        path = f.name
    try:
        ModuleMap(path)
        return False
    except ValueError:
        return True
    finally:
        os.unlink(path)


if __name__ == '__main__':
    sys.exit(main())
