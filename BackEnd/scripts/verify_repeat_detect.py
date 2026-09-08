"""「這一輪有多少是把上一輪重寫一遍」的量測（E-16）。

用法：
    python scripts/verify_repeat_detect.py

這支量測**只寫進稽核記錄**，不參與任何判定、不影響攔截、不觸發補生成。所以這裡釘的是
「它量得對不對」與「它沒有被接進判定」兩件事。

語料基線（0818-0908 全部 61 個追問輪，用同一支函式量出來的）：

    ratio >= 0.40                   4 筆（6.6%）
    ratio >= 0.40 且 longest_run >= 300   2 筆  <- 真正的整段重寫

    0.80 / 2654  e4147c25  換 蔡雨築 是否同樣的結論說明。
    0.72 /  369  c4f3f3b3  還有其他建議嗎
    0.68 /   69  896b2143  再一次排序。
    0.52 /   31  ffe409c4  除了 蔡雨築 之外，其他人呢

不打網路、不需要 DB。
"""

import os
import sys

sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'api_v2', '.env'),
            encoding='utf-8-sig')

from api_v2.services.repeat_detect import (  # noqa: E402
    measure, normalize, previous_answer, MIN_CHARS, MAX_CHARS)

failures = []

# 用「一組互不相同的句子」而不是同一句重複，否則把順序打散之後字串完全一樣，
# [6] 就測不出 longest_run 的鑑別力。每句 22-26 字，總長超過 MIN_CHARS。
SENTS_A = [
    '甲方在溝通上偏向開放直接習慣把話說開不太揣測意圖',
    '乙方在會議中傾向先聽再說需要完整脈絡才願意表態',
    '丙方對規則與公平相當敏感程序不透明時會先退一步',
    '丁方講話節奏明快遇到問題傾向先對話而非冷處理',
    '戊方重視關係和諧表達意見時會顧及對方的立場',
    '己方在高壓下容易沉默需要被明確邀請才會發言',
    '庚方習慣先整理再表達不喜歡在會議中臨場反應',
    '辛方對細節要求高會反覆確認資料的正確與完整',
    '壬方擅長把混亂的資訊整理成可執行的行動清單',
    '癸方在跨部門協作時能扮演橋樑降低溝通的成本',
    '子方面對變動的適應力高不會因議題陌生而退縮',
    '丑方決策果斷但需要提醒他人消化資訊所需時間',
]
PARA_A = '。'.join(SENTS_A) + '。'
PARA_B = '。'.join(s[::-1] for s in SENTS_A) + '。'      # 同樣長度、內容完全不同
NEW = '以下是本輪新增的建議內容與後續觀察訊號請主管依實際情況調整。' * 4


def check(label, condition, detail=''):
    print(f"  [{'OK' if condition else 'FAIL'}] {label}"
          f"{(' -- ' + str(detail)) if detail else ''}")
    if not condition:
        failures.append(label)


def hist(*answers):
    """把幾則回答排成 history，中間夾使用者提問。"""
    out = []
    for a in answers:
        out.append({'role': 'user', 'content': '（提問）'})
        out.append({'role': 'assistant', 'content': a})
    return out


def main():
    print('\n[1] normalize：標點與空白不算內容差異')
    # E-16 那一筆的重寫版把半形逗號換成全形（「整合資源,推動」->「整合資源，推動」），
    # 不收斂的話 72% 的重複會被算成 0%。
    check('全形與半形標點正規化後相同',
          normalize('整合資源,推動跨部門協作。') == normalize('整合資源，推動跨部門協作'),
          normalize('整合資源,推動跨部門協作。'))
    check('換行與空白被去掉', normalize(' 甲\n\n乙 \t丙 ') == '甲乙丙')

    print('\n[2] previous_answer：取最後一則 assistant')
    check('多輪時取最後一則', previous_answer(hist('第一輪', '第二輪')) == '第二輪')
    check('沒有 assistant 就是 None', previous_answer([{'role': 'user', 'content': 'x'}]) is None)
    check('空內容不算', previous_answer(hist('  ')) is None)
    check('history 為 None 不炸', previous_answer(None) is None)

    print('\n[3] 沒有可比的前一輪就不量')
    check('第一輪（無 history）回空', measure(PARA_A, []) == {})
    check('history 只有使用者訊息回空',
          measure(PARA_A, [{'role': 'user', 'content': '提問'}]) == {})
    check('本輪太短不量', measure('短短一句話。', hist(PARA_A)) == {})
    check('前一輪太短不量', measure(PARA_A, hist('短')) == {})
    check('answer 為空不炸', measure('', hist(PARA_A)) == {})

    print('\n[4] ratio：本輪有多少比例是上一輪就給過的')
    same = measure(PARA_A, hist(PARA_A))
    check('一字不改 -> ratio 1.0', same['ratio'] == 1.0, same)
    check('一字不改 -> longest_run 等於全長',
          same['longest_run'] == same['chars'], same)
    diff = measure(PARA_B, hist(PARA_A))
    check('完全不同的內容 -> ratio 偏低', diff['ratio'] < 0.35, diff)

    print('\n[5] E-16 的形狀：前面照抄、後面補一段新的')
    e16 = measure(PARA_A + NEW, hist(PARA_A))
    check('ratio 反映重寫的比重', 0.6 <= e16['ratio'] <= 0.95, e16)
    check('longest_run 抓到被整段搬過來的那一塊',
          e16['longest_run'] >= len(normalize(PARA_A)) * 0.9, e16)
    check('分母是本輪，不是上一輪',
          e16['chars'] == len(normalize(PARA_A + NEW)), e16)
    check('prev_chars 記的是上一輪',
          e16['prev_chars'] == len(normalize(PARA_A)), e16)

    print('\n[6] ratio 與 longest_run 分辨的是兩件不同的事')
    # 大 ratio + 小 longest_run ＝ 同樣的次序、逐句改寫（`896b2143`「再一次排序」是
    # 0.68/69）。同一份特質資料寫出來的句子本來就會像，那一類不見得是缺陷。
    # 這裡在每句中間插一個詞，句子與次序都不動——共同片段因此被切成很多小塊。
    reworded = '。'.join(x[:8] + '在多數情況下' + x[8:] for x in SENTS_A) + '。'
    rw = measure(reworded, hist(PARA_A))
    check('逐句改寫後 ratio 仍高', rw['ratio'] > 0.5, rw)
    check('但 longest_run 明顯小於整段搬運',
          rw['longest_run'] < e16['longest_run'] / 4,
          f"{rw['longest_run']} vs {e16['longest_run']}")
    # 順帶釘住一個容易誤解的性質：共同片段是保序的，所以把段落順序整個對調，ratio 會掉，
    # 不會維持在高點。量到的高 ratio 代表「順著同樣的次序重講一遍」。
    check('共同片段保序：次序整個打散時 ratio 會掉',
          measure('。'.join(reversed(SENTS_A)) + '。', hist(PARA_A))['ratio'] < 0.3)

    print('\n[7] 長度上限：不讓極端長的回答拖住收尾')
    huge = '甲' * (MAX_CHARS + 10)
    sk = measure(huge, hist(huge))
    check('超過上限就跳過，並說明原因', sk.get('skipped') == 'too_long', sk)
    check('跳過時不回 ratio', 'ratio' not in sk, sk)
    check('MIN_CHARS 小於 MAX_CHARS', MIN_CHARS < MAX_CHARS)

    print('\n[8] 只記錄，沒有被接進判定')
    services = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                            'api_v2', 'services')

    def src(name):
        return open(os.path.join(services, name), encoding='utf-8').read()

    check('completeness_check 沒有引用 repeat_detect（判定不受影響）',
          'repeat_detect' not in src('completeness_check.py'))
    check('segment_gate 沒有引用 repeat_detect（不影響攔截與補生成）',
          'repeat_detect' not in src('segment_gate.py'))
    check('log_pipeline 沒有引用 repeat_detect',
          'repeat_detect' not in src('log_pipeline.py'))
    packed = src('packed_chat.py')
    check('packed_chat 只把它寫進稽核的 repeat 欄位',
          "audit['repeat']" in packed and packed.count('measure_repeat(') == 1, packed.count('measure_repeat('))
    check('量測失敗不影響請求（包在 try 裡）',
          'repeat measure failed' in packed)

    print(f"\n{'[DONE] all checks passed' if not failures else '[FAILED] ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
