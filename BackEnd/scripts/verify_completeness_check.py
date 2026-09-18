"""Acceptance for the b §8 completeness checks.

Usage:
    python scripts/verify_completeness_check.py

The heading cases come from the acceptance table in `_ LOG 實作補充說明 for victor.txt`;
the rest cover the empty-sections logging rule, the multi-person name rule, free-form
length, calibration evidence, and the incremental (segment-by-segment) path.
"""

import os
import sys

# Windows consoles default to cp950 here, which cannot encode the Chinese in the section
# names this script prints -- without this the whole report comes out mojibake.
sys.stdout.reconfigure(encoding='utf-8')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'api_v2', '.env'), encoding='utf-8-sig')

from api_v2.services.question_table import table  # noqa: E402
from api_v2.services.log_assembler import Respondent  # noqa: E402
from api_v2.services.completeness_check import (  # noqa: E402
    CompletenessChecker, check_answer, heading_candidates, normalize_heading,
    expected_sections_for, SKIP_LOG, UNSPLIT_LOG, EVIDENCE_TERMS, FREE_FORM_MAX_CHARS, owns_section)

CALIB = table.calibration_traits
failures = []


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def sections_answer(q, headings, extra_body=''):
    return '\n\n'.join(headings) + ('\n\n' + extra_body if extra_body else '')


def main():
    q5 = table.get('如何面對困難、壓力、挑戰')          # per_person_sections=False
    qpp = table.get('領導風格與潛能分析')                # per_person_sections=True
    q13 = table.get('有效的溝通方法／模式')              # per_person_sections=False（req ecae89f3）
    r1 = [Respondent('王智弘', 'R1', {'CIA_05': 'B'})]

    print('\n[1] Heading matching -- the spec acceptance table')
    cases = [
        ('4. 主管使用提醒', '主管使用提醒', True),
        ('四、主管使用提醒：', '主管使用提醒', True),
        ('以下提供主管使用提醒', '主管使用提醒', False),
        ('主管注意事項', '主管使用提醒', False),
        ('## 主管使用提醒', '主管使用提醒', True),
        ('**主管使用提醒**', '主管使用提醒', True),
        ('第四部分，主管使用提醒', '主管使用提醒', True),
    ]
    for line, expected, should_match in cases:
        got = normalize_heading(line) == normalize_heading(expected)
        check(f'{line!r} vs {expected!r} -> {"match" if should_match else "no match"}',
              got == should_match, f'normalized to {normalize_heading(line)!r}')

    print('\n[1b] 標題與內文同一行（2026-08-25 req f1d36fbb 的六段全滅）')
    # 指令教的就是這個寫法，所以這不是模型不聽話，是比對方式對不上格式。
    inline = [
        ('- **主要領導風格**：推進驅動型', '主要領導風格', True),
        ('2. 主要風險：列出 3 項，每項都要包含', '主要風險', True),
        ('第三部分，需要避免的溝通方式：列出2項', '需要避免的溝通方式', True),
        ('## 溝通風格摘要', '溝通風格摘要', True),
        # 沒有標記的散文不提供標題，即使裡面有冒號
        ('他在壓力下的反應是：話會變少', '他在壓力下的反應是', False),
        # 標籤對不上就是對不上，切分不會放寬這件事
        ('- **主要領導風格**：推進驅動型', '次要領導風格', False),
    ]
    for line, expected, should_match in inline:
        got = normalize_heading(expected) in heading_candidates(line)
        check(f'{line[:26]!r} -> {expected!r} {"命中" if should_match else "不該命中"}',
              got == should_match, heading_candidates(line))

    print('\n[1c] 斜線的空白與全形半形不算差異')
    slash = [
        ('## 四、同組織／專案角色分配建議', '同組織 / 專案角色分配建議', True),
        ('## 四、同組織 / 專案角色分配建議', '同組織／專案角色分配建議', True),
        ('## 同組織/專案角色分配建議', '同組織 / 專案角色分配建議', True),
        ("## 管理 Do / Don't", "管理 Do/Don't", True),
        ("## 管理 Do/Don't", "管理 Do / Don't", True),
        # Do 與 Don't 之間的空白可以收，中英之間的不能——收掉就變成另一個詞了
        ("## 管理Do / Don't", "管理 Do / Don't", False),
        # 收斂不等於放寬：不同的段落名還是不同
        ('## 同組織／團隊角色分配建議', '同組織 / 專案角色分配建議', False),
    ]
    for line, expected, should_match in slash:
        got = normalize_heading(line) == normalize_heading(expected)
        check(f'{line[:24]!r} vs {expected[:20]!r} -> {"命中" if should_match else "不該命中"}',
              got == should_match,
              f'{normalize_heading(line)!r} vs {normalize_heading(expected)!r}')

    print('\n[1d] 全形／半形標點不算差異')
    width = [
        # 指令寫半形，模型在中文句子裡幾乎都輸出全形
        ('## 2. 需要結構或空間？', '需要結構或空間?', True),
        ('## 2. 共同或個別？', '共同或個別?', True),
        ('## 錄用後行動與發展建議（僅供參考）', '錄用後行動與發展建議(僅供參考)', True),
        # 沒有 ASCII 等價物的中文標點維持原樣，不可被當成相同
        ('## 互補、重疊與高風險組合', '互補,重疊與高風險組合', False),
        ('## 需要結構或時間？', '需要結構或空間?', False),
    ]
    for line, expected, should_match in width:
        got = normalize_heading(line) == normalize_heading(expected)
        check(f'{line[:22]!r} vs {expected[:18]!r} -> {"命中" if should_match else "不該命中"}',
              got == should_match,
              f'{normalize_heading(line)!r} vs {normalize_heading(expected)!r}')

    print('\n[2] Subset test on a real question')
    full = sections_answer(q5, q5['expected_sections'])
    res = check_answer(full, r1, q5, CALIB)
    check('all expected headings present -> passed', res.status == 'passed', res.missing_sections)
    res = check_answer(full + '\n\n額外補充\n\n內容', r1, q5, CALIB)
    check('extra headings are allowed', res.status == 'passed', res.missing_sections)
    res = check_answer(sections_answer(q5, q5['expected_sections'][:-1]), r1, q5, CALIB)
    check('a missing heading -> failed', res.status == 'failed'
          and res.missing_sections == [q5['expected_sections'][-1]], res.missing_sections)
    check('reason() names what is missing', '缺少段落' in res.reason(), res.reason())
    res = check_answer('本文提到 ' + ' 和 '.join(q5['expected_sections']), r1, q5, CALIB)
    check('expected text in running prose does NOT count', res.status == 'failed',
          res.missing_sections)

    print('\n[3] Empty expected_sections must be logged, never silently passed')
    for idx in (14, 15, 22):
        q = table.get(idx)
        n = 2 if q['audience'] == 'multi_only' else 1
        rs = [Respondent(f'受測者{i}', f'R{i}', {'CIA_05': 'B'}) for i in range(1, n + 1)]
        res = check_answer('任意回答', rs, q, CALIB)
        check(f'idx {idx}: skipped and logged', res.status in ('skipped', 'failed')
              and SKIP_LOG in res.log_lines, res.log_lines)
    check('the log line is the spec wording verbatim',
          SKIP_LOG == '本題未做段落齊全檢查（原因：指令未定義固定段落標題）')

    print('\n[4] 事項 13: single/multi split with a reported fallback')
    single, note = expected_sections_for(q5, 1)
    multi, note_m = expected_sections_for(q5, 2)
    # expected_sections_multi 已補齊，所以多人不再退回單人清單——這正是 req f1d36fbb
    # 六段全滅的根因。單人版尚未拆分（expected_sections_single 仍是 None），還是走退路，
    # 而那條退路必須繼續被記錄下來。
    check('多人已拆分 -> 用多人清單、不記退回', note_m is None and multi == q5['expected_sections_multi'],
          f'{note_m!r} {multi}')
    check('多人清單確實與單人不同', multi != single, f'{multi} vs {single}')
    check('單人尚未拆分 -> 仍走退路並記錄', note == UNSPLIT_LOG and single == q5['expected_sections'])
    check('the fallback is recorded in the result log',
          UNSPLIT_LOG in check_answer(full, r1, q5, CALIB).log_lines)
    split_q = dict(q5, expected_sections_single=['甲'], expected_sections_multi=['乙', '丙'])
    check('split fields are preferred when present',
          expected_sections_for(split_q, 1)[0] == ['甲']
          and expected_sections_for(split_q, 2)[0] == ['乙', '丙'])
    check('no fallback note once the data is split', expected_sections_for(split_q, 1)[1] is None)

    print('\n[5] Multi-person: each respondent needs their own heading')
    two = [Respondent('王智弘', 'R1', {'CIA_05': 'B'}),
           Respondent('林孟德', 'R2', {'CIA_05': 'B'})]
    # 這一區驗的是「人名有沒有自己的標題」，所以段落本身必須先是齊的——兩人回答要用
    # 多人清單的段落名，拿單人清單來組會先卡在段落齊全檢查，測不到人名這件事。
    body = sections_answer(q5, expected_sections_for(q5, 2)[0])
    # 逐人分段的檢查只在 per_person_sections=True 的題目上跑，所以這一區用 Q21。
    body_pp = sections_answer(qpp, expected_sections_for(qpp, 2)[0])
    res = check_answer('## 王智弘\n\n' + body_pp + '\n\n## 林孟德\n\n' + body_pp,
                       two, qpp, CALIB)
    check('both names present as headings -> passed', res.status == 'passed',
          res.missing_respondents)
    res = check_answer('## 王智弘\n\n' + body_pp, two, qpp, CALIB)
    check('a missing respondent -> failed', res.status == 'failed'
          and res.missing_respondents == ['林孟德'], res.missing_respondents)
    # 「內文提到不算有自己的段落」只在回答**確實照人分段**時成立：這裡王智弘有自己的
    # 標題，所以格式是照人分段的，林孟德只出現在內文就是真的漏了。
    # （原本這條的 fixture 兩個人都沒有標題，那種形狀現在走 by_mention——見 [5c]。）
    res = check_answer('## 王智弘\n\n' + body_pp + '\n\n關於林孟德的部分寫在內文',
                       two, qpp, CALIB)
    check('a name only in running prose does not count',
          res.missing_respondents == ['林孟德'] and res.respondents_check == 'by_section',
          f'{res.missing_respondents} / {res.respondents_check}')
    check('single-person answers are not name-checked',
          not check_answer(body_pp, r1, qpp, CALIB).missing_respondents)

    print('\n[5b] 自由提問也做受測者覆蓋率檢查（修正計畫 Unit 2）')
    res = check_answer('## 王智弘\n\n內容。', two, None, CALIB)
    check('多人自由提問漏掉一位 -> failed 並指出是誰',
          res.status == 'failed' and res.missing_respondents == ['林孟德'],
          res.missing_respondents)
    # E-12：自由提問的漏人只記錄、不補。補生成在自由提問的觸發紀錄是 0 次正確、
    # 3 次誤判（2026-09-07 S8），而誤判的代價是使用者拿到一大段沒問的內容。
    check('自由提問：漏人不交給補生成（appendable_reason 為空）',
          res.appendable_reason() == '', res.appendable_reason())
    check('自由提問：但 reason() 仍然說得出漏了誰',
          '缺少獨立段落的受測者' in res.reason() and '林孟德' in res.reason(), res.reason())
    check('自由提問：status 仍是 failed（會落在 manual_review）',
          res.status == 'failed', res.status)
    check('自由提問：稽核仍記得到 missing_respondents',
          res.as_audit()['missing_respondents'] == ['林孟德'],
          res.as_audit()['missing_respondents'])
    res = check_answer('## 王智弘\n\n內容。\n\n## 林孟德\n\n內容。', two, None, CALIB)
    check('每個人都有標題 -> 不再判缺人', res.missing_respondents == [],
          res.missing_respondents)
    check('單人自由提問仍不做姓名檢查',
          not check_answer('內容。', r1, None, CALIB).missing_respondents)
    # 自由提問沒有指定輸出結構，一份不用標題的排序清單、一張表格都是好答案。全語料 29 筆
    # 多人回覆裡有 9 筆是這種形狀，拿標題當判準會全部判成缺人。
    check('自由提問：寫在內文也算寫到（不要求標題）',
          not check_answer('排序為王智弘、林孟德。', two, None, CALIB).missing_respondents)
    check('題庫題維持嚴格：照人分段時，內文提到不算有自己的段落',
          '林孟德' in check_answer('## 王智弘\n\n' + body_pp
                                 + '\n\n關於林孟德的部分寫在內文',
                                 two, qpp, CALIB).missing_respondents)

    q5_res = check_answer('## 王智弘\n\n' + body_pp
                          + '\n\n關於林孟德的部分寫在內文', two, qpp, CALIB)
    check('題庫題不受影響：漏人仍然交給補生成',
          '缺少獨立段落的受測者' in q5_res.appendable_reason(), q5_res.appendable_reason())

    print('\n[5e] 覆蓋率怎麼判：由回答自己的格式決定（req e332a385 / 5017a070）')
    # 2026-09-08 req e332a385：名單 11 位，逐人分析只寫 7 位，覆蓋率檢查卻判 []。
    # 根因是拿「整行」去比對，而 `- ` 開頭的內文 bullet 也算 marked heading——第 1 節
    # 一條列了 8 個名字的 bullet，一行就讓 8 個人通過。
    eight = [Respondent(n, f'R{i}', {'CIA_05': 'B'})
             for i, n in enumerate(['甲一', '乙二', '丙三', '丁四'])]
    trap = ('- **偏收斂、重結構**：成員可分為「推進組」（甲一、乙二）與'
            '「支援組」（丙三、丁四），兩組節奏不同。\n\n'
            '- **（甲一）**：內容。\n\n- **（乙二）**：內容。')
    res = check_answer(trap, eight, qpp, CALIB)
    check('列了一串名字的內文 bullet 不算那些人的段落',
          res.missing_respondents == ['丙三', '丁四'], res.missing_respondents)
    check('照人分段的回答走 by_section', res.respondents_check == 'by_section',
          res.respondents_check)
    combo = ('- **（甲一）**：內容。\n\n- **（乙二）**：內容。\n\n'
             '- **丙三 vs. 丁四**：這組搭配需要主持保護。')
    check('「A vs. B」的組合標題不算 A 或 B 的段落',
          check_answer(combo, eight, qpp, CALIB).missing_respondents == ['丙三', '丁四'],
          check_answer(combo, eight, qpp, CALIB).missing_respondents)

    # 2026-08-18 req 5017a070：兩人的合作題，回答照主題分段，兩人都寫在內文段落裡。
    # 這種形狀不能用「有沒有自己的標題」去判，否則補生成會在完整的回答後面硬接兩段（E-12）。
    by_theme = ('### 團隊合作價值\n\n王智弘帶來的是推進與品質把關。\n\n'
                '林孟德帶來的是穩定執行與程序把關。\n\n### 可能摩擦\n\n兩人節奏不同。')
    res = check_answer(by_theme, two, qpp, CALIB)
    check('照主題分段、人人都寫到 -> 不判缺人',
          res.missing_respondents == [] and res.respondents_check == 'by_mention',
          f'{res.missing_respondents} / {res.respondents_check}')
    res = check_answer('### 團隊合作價值\n\n王智弘帶來的是推進與品質把關。', two, qpp, CALIB)
    check('照主題分段但真的少一個人 -> 仍判得出來',
          res.missing_respondents == ['林孟德'], res.missing_respondents)
    # by_mention 一律整篇比對。原本題庫題那一半走「一行點到 2 位以內」的比法，理由是
    # e332a385 那條列 8 人的 bullet 不該放行；Unit D 之後 e332a385（Q15）走 by_section，
    # 那條防線在它該防的地方用不到了，留著只在組合題上誤傷——2026-09-09 req 57b052ba
    # （Q13、11 位）把成員歸成「四種典型樣態」，11 個名字全寫到了卻判出 9 位缺席。
    grouped = '### 觀察\n\n成員可分為甲一、乙二、丙三、丁四四組節奏。'
    res = check_answer(grouped, eight, qpp, CALIB)
    check('by_mention：歸類式的敘述也算寫到了',
          res.missing_respondents == [] and res.respondents_check == 'by_mention',
          f'{res.missing_respondents} / {res.respondents_check}')
    check('題庫題與自由提問的 by_mention 判法一致',
          check_answer(grouped, eight, None, CALIB).missing_respondents
          == res.missing_respondents)
    check('真的整篇沒提到的人仍然抓得出來',
          check_answer('### 觀察\n\n只談甲一與乙二。', eight, qpp, CALIB)
          .missing_respondents == ['丙三', '丁四'])

    print('\n[5f] 模型自報人數（只記錄，不影響判定）')
    res = check_answer('以下根據您提供的八位成員特質資料。\n\n'
                       '- **（甲一）**：內容。\n\n- **（乙二）**：內容。'
                       '\n\n- **（丙三）**：內容。\n\n- **（丁四）**：內容。',
                       eight, qpp, CALIB)
    check('開場自報 8 位、名單 4 位 -> 記進稽核', res.stated_count == 8, res.stated_count)
    # status 是 failed，但那是因為這個 fixture 沒有寫 q5 的段落名；重點是自報人數
    # 沒有讓任何一個人被判成缺席。
    check('自報人數不改判定：漏人與否只看段落，這裡人人都有',
          res.missing_respondents == [], res.missing_respondents)
    check('落差寫進 log_lines',
          any('模型自報 8 位' in l for l in res.log_lines), res.log_lines)
    ok = check_answer('以下根據您提供的四位成員特質資料。\n\n'
                      '- **（甲一）**：內容。\n\n- **（乙二）**：內容。'
                      '\n\n- **（丙三）**：內容。\n\n- **（丁四）**：內容。',
                      eight, qpp, CALIB)
    check('數對了就不記', ok.stated_count is None
          and not any('模型自報' in l for l in ok.log_lines), ok.stated_count)
    # req fb7eacbd：提問是「謝淑玲，簡玥瀅 適合的崗位是什麼？」，名單 10 位，模型正確地
    # 寫「兩位」——那不是落差，是使用者只問了兩位。自由提問的名單常常不是回答的範圍。
    check('自由提問不記自報人數',
          check_answer('以下針對兩位說明。甲一…乙二…丙三…丁四…',
                       eight, None, CALIB).stated_count is None)
    check('單人不做這個檢查',
          check_answer('以下針對這兩位。' + body_pp, r1, qpp, CALIB).stated_count is None)
    check('稽核欄位帶得出 stated_count 與 respondents_check',
          res.as_audit()['stated_count'] == 8
          and res.as_audit()['respondents_check'] == 'by_section', res.as_audit())

    print('\n[5g] per_person_sections 閘門（req ecae89f3）')
    # Q13 通篇寫「對象組合」，一句要求逐人的話都沒有；但 2026-09-08 req ecae89f3 的第 4 節
    # 寫成 `- **與洪 玉芳溝通時：** …`，三個這種標籤讓判定以為「這篇是照人分段的」，
    # 於是把寫在內文裡的其餘 8 位全判成漏人，補生成硬接了 1202 字重複的人名清單。
    check('Q15 / Q21 / Q22 是 per_person_sections=True，其餘為 False',
          [q['idx'] for q in table.all() if q.get('per_person_sections')] == [15, 21, 22],
          [q['idx'] for q in table.all() if q.get('per_person_sections')])
    # 段落要寫齊，否則 appendable_reason() 會混進「缺少段落」，測不到受測者那一半。
    prefixed = (sections_answer(q13, expected_sections_for(q13, 2)[0])
                + '\n\n- **與王智弘溝通時：** 說明背景與理由，避免只給結論。')
    res = check_answer(prefixed, two, q13, CALIB)
    check('per_person=False 的題目永遠不走 by_section',
          res.respondents_check == 'by_mention', res.respondents_check)
    check('per_person=False 的漏人只記錄、不交給補生成',
          res.appendable_reason() == '' and res.missing_sections == [],
          res.appendable_reason())
    check('但 reason() 仍說得出漏了誰（落在 manual_review）',
          '林孟德' in res.reason() and res.status == 'failed', res.reason())
    # 「與王智弘溝通時」是建議事項，主詞是讀者不是王智弘——不是他的段落。
    check('owns_section：名字要在標籤開頭，「與X溝通時」不算',
          not owns_section('與王智弘溝通時', '王智弘')
          and owns_section('（王智弘）', '王智弘')
          and owns_section('王智弘——制度推行與關係整合型角色', '王智弘'))
    pp = check_answer(prefixed, two, qpp, CALIB)
    check('同一篇放在 per_person=True 的題目下，仍不把「與X溝通時」當成 X 的段落',
          pp.respondents_check == 'by_mention', pp.respondents_check)

    print('\n[5d] 廠商姓名格式：payload 帶空白與單位，模型寫乾淨的名字')
    vendor = [Respondent('柳 宇賸-人資發展課', 'R1', {'CIA_05': 'B'}),
              Respondent('呂 佳珍教育訓練課', 'R2', {'CIA_05': 'B'}),
              Respondent('Howard Hsu', 'R3', {'CIA_05': 'B'})]
    res = check_answer('*   **柳宇賸**：內容。\n*   **呂佳珍**：內容。\n*   **Howard**：內容。',
                       vendor, None, CALIB)
    check('c5e0ef45 的形狀不再被誤判成漏人', res.missing_respondents == [],
          res.missing_respondents)
    res = check_answer('*   **柳宇賸**：內容。\n*   **Howard Hsu**：內容。',
                       vendor, None, CALIB)
    check('真的沒寫到的那位仍然抓得出來', res.missing_respondents == ['呂 佳珍教育訓練課'],
          res.missing_respondents)

    print('\n[5c] 提問者本人不需要自己的段落')
    vic = [Respondent('Victoria', 'R1', {'CIA_05': 'B'}),
           Respondent('梁婉婷', 'R2', {'CIA_05': 'B'})]
    res = check_answer('## 梁婉婷\n\n內容。', vic, None, CALIB,
                       user_query='我是 Victoria，帶領一個 8 人的電話客服團隊。')
    check('「我是 Victoria」-> Victoria 不列入缺人', res.missing_respondents == [],
          res.missing_respondents)
    # 6920b8fb 的真實提問：自稱與姓名之間隔著一段頭銜，姓名在 payload 裡還帶空白。
    zheng = [Respondent('鄭 皓仁', 'R1', {'CIA_05': 'B'}),
             Respondent('游 雅鳳-FDA', 'R2', {'CIA_05': 'B'})]
    res = check_answer('## 游 雅鳳-FDA\n\n內容。', zheng, None, CALIB,
                       user_query='我是連鎖餐飲門市的責任主管 鄭皓仁，目前同時帶三位新人。')
    check('自稱與姓名間隔著頭銜、姓名帶空白，仍能豁免',
          res.missing_respondents == [], res.missing_respondents)
    res = check_answer('## 游 雅鳳-FDA\n\n內容。', zheng, None, CALIB,
                       user_query='再一次排序')
    check('沒有自稱就照常判缺人', res.missing_respondents == ['鄭皓仁'],
          res.missing_respondents)
    res = check_answer('## 游 雅鳳-FDA\n\n內容。', zheng, None, CALIB,
                       user_query='我是主管。請分析鄭皓仁。')
    check('自稱跨句不算（逗號句號後的姓名不豁免）',
          res.missing_respondents == ['鄭皓仁'], res.missing_respondents)
    # 使用者只在第一輪自我介紹，之後直接問「我照前面的建議…」。只看本輪的話，
    # a6718cb3 與 6920b8fb 的後續輪次會把提問者本人判成漏掉的分析對象。
    res = check_answer('## 游 雅鳳-FDA\n\n內容。', zheng, None, CALIB,
                       user_query='我照前面的建議調整了做法，接下來該怎麼做？',
                       history=[{'role': 'user',
                                 'content': '我是連鎖餐飲門市的責任主管 鄭皓仁。'},
                                {'role': 'assistant', 'content': '好的。'}])
    check('自稱在前幾輪說過，後續輪次仍然豁免', res.missing_respondents == [],
          res.missing_respondents)

    print('\n[6] Free-form: 字數只記錄，不判失敗（U10）')
    # 超字曾經把 status 打成 failed。它從來沒有可行動的意義——補生成修不了（append 只會
    # 更長），所以唯一的效果是讓 manual_review 對自由提問永遠亮著，把真正需要人看的
    # 缺段與佐證問題淹掉。規格值保留，改記在 free_form_length_check。
    res = check_answer('短短的回答。', r1, None, CALIB)
    check('短回答 passed', res.status == 'passed', res.char_count)
    check('短回答 free_form_length_check=passed',
          res.free_form_length_check == 'passed', res.free_form_length_check)
    res = check_answer('字' * (FREE_FORM_MAX_CHARS + 1), r1, None, CALIB)
    check(f'超過 {FREE_FORM_MAX_CHARS} 字仍然 passed（不再判失敗）',
          res.status == 'passed', res.status)
    check('但 free_form_length_check=over_limit',
          res.free_form_length_check == 'over_limit', res.free_form_length_check)
    check('char_count 記下實際字數', res.char_count == FREE_FORM_MAX_CHARS + 1,
          res.char_count)
    check('reason() 不再把超字列為失敗原因', '字' not in res.reason(), res.reason())
    check('稽核紀錄帶得出這兩個欄位',
          res.as_audit()['free_form_length_check'] == 'over_limit'
          and res.as_audit()['char_count'] == FREE_FORM_MAX_CHARS + 1,
          {k: res.as_audit()[k] for k in ('free_form_length_check', 'char_count')})
    res = check_answer('字' * 500 + ' \n' * 800, r1, None, CALIB)
    check('whitespace is not counted', res.char_count == 500, res.char_count)
    check('題庫題不套字數檢查（n/a）',
          check_answer('x' * 2000, r1, q5, CALIB).free_form_length_check == 'n/a')
    check('free-form is not section-checked', not check_answer('x', r1, None, CALIB).missing_sections)

    print('\n[7] Calibration evidence (社會期望反應 A 段)')
    calib_r = [Respondent('王智弘', 'R1', {'CIA_05': 'B', 'CIA_33': 'A'})]
    res = check_answer(body, calib_r, q5, CALIB)
    check('A-band calibration without evidence wording -> failed',
          res.calibration_evidence == 'failed' and res.status == 'failed')
    check('reason() asks for the evidence wording', '佐證' in res.reason(), res.reason())
    for term in EVIDENCE_TERMS:
        res = check_answer(body + f'\n\n建議以{term}進一步確認。', calib_r, q5, CALIB)
        check(f'evidence term 「{term}」 satisfies the check',
              res.calibration_evidence == 'passed')
    res = check_answer(body, [Respondent('王智弘', 'R1', {'CIA_05': 'B', 'CIA_33': 'B'})],
                       q5, CALIB)
    check('B-band calibration does not require evidence', res.calibration_evidence == 'n/a')

    print('\n[8] Incremental accumulation (客戶裁定丙-1)')
    checker = CompletenessChecker(r1, q5, CALIB)
    for i, sec in enumerate(q5['expected_sections']):
        checker.observe(f'{i + 1}. {sec}\n內容內容。\n')
        if i < len(q5['expected_sections']) - 1:
            check(f'no verdict is possible mid-answer (after section {i + 1})',
                  checker.finalize().status == 'failed')
    check('passes once every segment has arrived', checker.finalize().status == 'passed',
          checker.finalize().missing_sections)
    one_shot = check_answer(''.join(f'{i + 1}. {s}\n內容內容。\n'
                                    for i, s in enumerate(q5['expected_sections'])), r1, q5, CALIB)
    check('segment-by-segment and one-shot agree',
          one_shot.status == checker.finalize().status)

    print('\n[8b] segment 邊界不是行邊界（E-15 / req 399ad86d）')
    # 串流的切點是閘門決定的，跟 Markdown 的行毫無關係。399ad86d 的改寫器吃掉了段尾空行
    # （E-14），下一段的 `- **陳 曉玲**：…` 因此黏在前一句後面；讀者看到的是行中的 `- `，
    # Markdown 不算新項目，但當時的 observe() 因為它是新 segment 的第一行而當成標題。
    glued = ('- **甲一**：內容內容，這一行沒有以換行收尾。'
             '- **乙二**：被黏在同一行裡。')
    whole = check_answer(glued, eight, qpp, CALIB)
    split_at = glued.index('- **乙二**')
    c = CompletenessChecker(eight, qpp, CALIB)
    c.observe(glued[:split_at])
    c.observe(glued[split_at:])
    streamed = c.finalize()
    check('分段餵與一次餵，判定必須一致',
          streamed.missing_respondents == whole.missing_respondents,
          f'{streamed.missing_respondents} vs {whole.missing_respondents}')
    # 甲一那一段是真的以 `- **甲一**：` 起行，算她的；乙二黏在同一行的中間，不算。
    check('黏在行中的 `- ` 不算新的段落標題（乙二判缺、甲一不判）',
          whole.missing_respondents == ['乙二', '丙三', '丁四'],
          whole.missing_respondents)
    # 真的有換行時，兩段都要算數——修法不能把正常的情況一起擋掉。
    proper = '- **甲一**：內容。\n\n- **乙二**：內容。'
    c2 = CompletenessChecker(eight, qpp, CALIB)
    cut = proper.index('- **乙二**')
    c2.observe(proper[:cut])
    c2.observe(proper[cut:])
    check('正常換行的兩段仍各自算數',
          c2.finalize().missing_respondents == ['丙三', '丁四'],
          c2.finalize().missing_respondents)
    # 最後一行沒有換行收尾時，finalize() 要把它收進來。
    c3 = CompletenessChecker(eight, qpp, CALIB)
    c3.observe('- **甲一**：內容。\n- **乙二**：最後一行沒有換行')
    check('finalize() 會收掉沒有換行收尾的最後一行',
          c3.finalize().missing_respondents == ['丙三', '丁四'],
          c3.finalize().missing_respondents)

    print('\n[9] 段落名必須逐字出現在自己的指令裡，否則永遠不可能命中')
    # 從 informational 升級為會紅的檢查。這正是「（2項）」那一類缺陷的形狀：段落名帶了
    # 設定檔作者寫的註記，模型再聽話也寫不出來，於是每一次請求都判缺少、觸發一次補生成、
    # 補完仍然不命中，最後標 manual_review。2026-08-25 question 13 的兩次請求就是這樣。
    # 多人清單一併掃，避免補 expected_sections_multi 時重蹈覆轍。
    stale = []
    for q in table.all():
        single_key = 'instruction_multi' if q['audience'] == 'multi_only' else 'instruction_single'
        for field, key in (('expected_sections', single_key),
                           ('expected_sections_multi', 'instruction_multi')):
            for sec in q.get(field) or []:
                if sec not in (q.get(key) or ''):
                    stale.append((q['idx'], field, sec))
    for idx, field, sec in stale:
        print(f'    idx {idx} {field}: {sec!r}')
    check('沒有任何段落名在指令中找不到', not stale, f'{len(stale)} 條')

    print('\n[10] 多人版清單的涵蓋率')
    # None 代表「尚未拆分」，會退回單人清單比對——多人回答因此可能被判成每一段都缺少。
    # [] 是明確宣告「多人版指令沒有固定標題」，檢查會跳過，這是不同的意思。
    unsplit = [q['idx'] for q in table.all()
               if (q.get('expected_sections') or []) and (q.get('instruction_multi') or '').strip()
               and q.get('expected_sections_multi') is None]
    check('有多人版指令且有段落清單的題目都已拆分', not unsplit, f'尚未拆分: {unsplit}')
    for q in table.all():
        for sec in q.get('expected_sections_multi') or []:
            check(f"idx {q['idx']} 的多人段落名可被正規化命中：{sec[:16]}",
                  normalize_heading('## ' + sec) == normalize_heading(sec))

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
