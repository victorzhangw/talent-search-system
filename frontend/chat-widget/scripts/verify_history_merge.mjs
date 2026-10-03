/**
 * 左側歷史清單的合併規則：重抓第一頁、捲到底接下一頁，都不重複、不遺漏、不亂序。
 *
 *   node scripts/verify_history_merge.mjs
 *
 * 規則本身在 useChatLogic.js（mergeHistoryFirstPage / appendHistoryPage / isHistoryOlder）。
 * 這裡除了逐條情境，還有一個模擬：假伺服器用與後端相同的游標規則分頁，客戶端在翻頁中途
 * 遇到「新開對話」「舊對話被聊到而跳到最上面」，刷新後再捲到底，最後的清單必須與伺服器
 * 的完整排序逐筆相同。這是畫面上最難看出錯的一類：多一筆、少一筆、或同一筆出現兩次。
 */

import { appendHistoryPage, isHistoryOlder, mergeHistoryFirstPage } from '../src/composables/useChatLogic.js'

const failures = []
const check = (label, ok, detail = '') => {
    console.log(`  [${ok ? 'OK' : 'FAIL'}] ${label}${!ok && detail !== '' ? ' -- ' + detail : ''}`)
    if (!ok) failures.push(label)
}

const T0 = Date.parse('2026-10-03T03:00:00+00:00')
const iso = (ms) => new Date(ms).toISOString().replace('Z', '+00:00')
const mk = (id, minutesAgo) => ({ session_id: id, last_active_at: iso(T0 - minutesAgo * 60000) })
const ids = (items) => items.map(s => s.session_id)
const empty = { items: [], cursor: null, hasMore: false }

// ---- 假伺服器：與 /chat/history?v=2 相同的排序與游標語意 ----
class FakeServer {
    constructor(rows) { this.rows = rows.map(r => ({ ...r })) }
    sorted() { return [...this.rows].sort((a, b) => (isHistoryOlder(a, b) ? 1 : -1)) }
    page(cursor, limit = 30) {
        let list = this.sorted()
        if (cursor) list = list.filter(s => isHistoryOlder(s, cursor))
        // 回傳複本，像真的 HTTP 回應一樣。回參照的話，伺服器端 touch() 改時間時客戶端手上的
        // 舊副本也跟著變，模擬就永遠看不到過期資料——2026-10-03 變異測試因此漏過一次。
        const items = list.slice(0, limit).map(s => ({ ...s }))
        const hasMore = list.length > limit
        const last = items[items.length - 1]
        return { items, has_more: hasMore, next_cursor: hasMore ? { ...last } : null }
    }
    touch(id, ms) { this.rows.find(r => r.session_id === id).last_active_at = iso(ms) }
    add(row) { this.rows.push(row) }
}

const loadAll = (server, state) => {
    for (let i = 0; i < 100 && state.hasMore; i++) state = appendHistoryPage(state, server.page(state.cursor))
    return state
}

console.log('\n[1] 排序比較')
check('時間較早者較舊', isHistoryOlder(mk('a', 10), mk('b', 5)))
check('同一時間依 session_id（小的較舊）', isHistoryOlder(mk('a', 5), mk('b', 5)) && !isHistoryOlder(mk('b', 5), mk('a', 5)))

console.log('\n[2] 接下一頁')
{
    const s = appendHistoryPage({ items: [mk('a', 1), mk('b', 2)], cursor: 'x', hasMore: true },
        { items: [mk('b', 2), mk('c', 3)], next_cursor: 'y', has_more: false })
    check('已有的不重複加', JSON.stringify(ids(s.items)) === '["a","b","c"]', ids(s.items))
    check('游標與 hasMore 換成新頁的', s.cursor === 'y' && s.hasMore === false)
}

console.log('\n[3] 重抓第一頁')
{
    const s = mergeHistoryFirstPage(empty, { items: [mk('a', 1)], next_cursor: 'c1', has_more: true })
    check('原本是空的 -> 就是新第一頁', ids(s.items).join() === 'a' && s.cursor === 'c1' && s.hasMore)

    const old = { items: [mk('a', 1), mk('b', 2), mk('c', 3), mk('d', 4)], cursor: 'deep', hasMore: true }
    const s2 = mergeHistoryFirstPage(old, { items: [mk('n', 0), mk('a', 1)], next_cursor: 'c2', has_more: true })
    check('新對話放最上面，往下載過的保留', ids(s2.items).join() === 'n,a,b,c,d', ids(s2.items))
    check('保留時沿用原本較深的游標', s2.cursor === 'deep' && s2.hasMore === true)

    const s3 = mergeHistoryFirstPage(old, { items: [{ ...mk('c', 0) }, mk('a', 1)], next_cursor: 'c3', has_more: true })
    check('被聊到而跳上來的那筆，舊位置的那份被去掉', ids(s3.items).join() === 'c,a,b,d', ids(s3.items))

    const s4 = mergeHistoryFirstPage(old, { items: [mk('a', 1), mk('b', 2)], next_cursor: null, has_more: false })
    check('新第一頁已是最後一頁 -> 不保留舊資料（其餘已掉出天數範圍）',
        ids(s4.items).join() === 'a,b' && s4.hasMore === false && s4.cursor === null, ids(s4.items))

    const s5 = mergeHistoryFirstPage(old, { items: [], next_cursor: null, has_more: false })
    check('新第一頁是空的 -> 清單清空', s5.items.length === 0 && !s5.hasMore)
}

console.log('\n[4] 模擬：翻頁中途有新對話與跳上來的對話，刷新後捲到底')
{
    const rows = Array.from({ length: 100 }, (_, i) => mk(`s${String(i).padStart(3, '0')}`, 60 * (i + 1)))
    rows.push(mk('tieA', 60 * 50), mk('tieB', 60 * 50))          // 同時間，測游標的 session_id 次序
    const server = new FakeServer(rows)

    let state = appendHistoryPage(empty, server.page(null))       // 第 1 頁
    state = appendHistoryPage(state, server.page(state.cursor))   // 第 2 頁
    check('前兩頁共 60 筆', state.items.length === 60, state.items.length)

    server.add(mk('new1', 0))                                     // 開了新對話
    server.touch('s045', T0 + 1000)                               // 第 2 頁的一筆被聊到
    server.touch('s080', T0 + 2000)                               // 還沒載入的一筆被聊到

    state = mergeHistoryFirstPage(state, server.page(null))       // 刷新（送出訊息後、開抽屜時）
    check('刷新後最上面是最新的', ids(state.items).slice(0, 3).join() === 's080,s045,new1',
        ids(state.items).slice(0, 3))
    state = loadAll(server, state)                                // 捲到底

    const want = ids(server.sorted())
    const got = ids(state.items)
    check('與伺服器的完整排序逐筆相同', JSON.stringify(got) === JSON.stringify(want),
        `got ${got.length} want ${want.length}`)
    check('沒有任何一筆重複', new Set(got).size === got.length, got.length - new Set(got).size)
    check('最後 hasMore=false', state.hasMore === false)

    // 刷新發生在「已經全部載完」之後
    server.touch('s099', T0 + 3000)
    state = mergeHistoryFirstPage(state, server.page(null))
    state = loadAll(server, state)
    check('全部載完後再刷新、再捲到底，仍與伺服器相同',
        JSON.stringify(ids(state.items)) === JSON.stringify(ids(server.sorted())))
}

console.log(`\n${failures.length ? '[FAILED] ' + failures.join('; ') : '[DONE] all checks passed'}`)
process.exit(failures.length ? 1 : 0)
