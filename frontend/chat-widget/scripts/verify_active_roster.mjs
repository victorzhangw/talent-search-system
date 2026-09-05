/**
 * 鎖定名單不再依賴分頁清單（修正計畫 Unit 5）。
 *
 * 用法：
 *     cd frontend/chat-widget
 *     node scripts/verify_active_roster.mjs
 *
 * 對照的缺陷：`activeConversationCandidatesObjects` 本來是拿 `candidates` 過濾出來的，
 * 而 `candidates` 是分頁清單（PAGE_LIMIT = 20，`fetchCandidates(false)` 整個取代）。鎖定
 * 的人只要不在當前那一頁，晶片上的「選定 N 位人選」就會少掉他們，送給後端的
 * `candidates_info` 也會一起少掉。
 *
 * 這裡用 Node 直接驅動 composable：Vue 的 ref/computed 在純 Node 環境可以運作，瀏覽器
 * 專屬的 window / sessionStorage / localStorage / fetch 以最小樁替代。不需要瀏覽器，因此
 * 這份驗證可以重複執行。
 *
 * 不涵蓋的部分（需要真實瀏覽器）：畫面上的晶片實際渲染、DevTools 看到的 Network payload。
 */

// --- 瀏覽器環境的最小樁 ---------------------------------------------------
class MemoryStorage {
    constructor() { this.map = new Map() }
    getItem(k) { return this.map.has(k) ? this.map.get(k) : null }
    setItem(k, v) { this.map.set(k, String(v)) }
    removeItem(k) { this.map.delete(k) }
    clear() { this.map.clear() }
}

globalThis.sessionStorage = new MemoryStorage()
globalThis.localStorage = new MemoryStorage()
globalThis.window = {
    TRAITTY_WIDGET_CONFIG: { apiBaseUrl: 'http://localhost:5000/api/v2' },
    location: { href: 'http://localhost:5173/' },
    open: () => {}
}
// 依 URL 回不同的空成功回應，讓流程走完而不打網路。
let byIdsResponse = []
globalThis.fetch = async (url) => ({
    ok: true,
    json: async () => {
        if (String(url).includes('/candidates/by-ids')) {
            return { success: true, data: byIdsResponse, meta: { missing_candidate_ids: [] } }
        }
        if (String(url).includes(`/chat/`)) {
            return { success: true, data: { messages: [], metadata: null } }
        }
        return { success: true, data: { reports: [] } }
    }
})

const { useChatLogic } = await import('../src/composables/useChatLogic.js')

// --- 測試輔助 -------------------------------------------------------------
const failures = []
const check = (label, condition, detail = '') => {
    console.log(`  [${condition ? 'OK' : 'FAIL'}] ${label}${detail !== '' ? ' -- ' + detail : ''}`)
    if (!condition) failures.push(label)
}

const person = (i) => ({
    candidate_id: 600 + i,
    id: 600 + i,
    name: `受測者${i}`,
    latest_assessment: { assessment_id: 700 + i }
})

const PAGE_1 = Array.from({ length: 20 }, (_, i) => person(i))       // 第一頁
const PAGE_2 = Array.from({ length: 4 }, (_, i) => person(20 + i))   // 第二頁
const ALL = [...PAGE_1, ...PAGE_2]
// 鎖定 6 位，其中 4 位在第二頁——正是使用者回報的「6 位剩 2 位」那個形狀。
const LOCKED = [PAGE_1[0], PAGE_1[1], ...PAGE_2]
const LOCKED_IDS = LOCKED.map(c => c.candidate_id)

const fresh = () => {
    sessionStorage.clear()
    localStorage.clear()
    return useChatLogic()
}

/** 模擬 `fetchCandidates(false)`：整個取代成第一頁。 */
const reloadFirstPageOnly = (logic) => { logic.candidates.value = [...PAGE_1] }

// --- 1. 鎖定當下就把人物件記起來 -------------------------------------------
console.log('\n[1] 鎖定 6 位（4 位在第 2 頁），清單重載成第一頁')
{
    const logic = fresh()
    logic.candidates.value = [...ALL]
    logic.selectedCandidateIds.value = [...LOCKED_IDS]
    await logic.lockSelectionAndStart()
    check('鎖定後立刻是 6 位', logic.activeConversationCandidatesObjects.value.length === 6,
          logic.activeConversationCandidatesObjects.value.length)

    reloadFirstPageOnly(logic)
    const objs = logic.activeConversationCandidatesObjects.value
    check('清單只剩第一頁之後仍然是 6 位', objs.length === 6, objs.length)
    check('第 2 頁那 4 位的姓名還在',
          PAGE_2.every(p => objs.some(o => o.name === p.name)),
          objs.map(o => o.name).join('、'))
    check('順序跟著 activeIds',
          objs.map(o => String(o.candidate_id)).join() === LOCKED_IDS.map(String).join(),
          objs.map(o => o.candidate_id).join())
    check('candidates_info 長度 == candidate_ids 長度',
          objs.length === logic.activeConversationCandidateIds.value.length)
}

// --- 2. 重新整理（sessionStorage 還原）------------------------------------
console.log('\n[2] 重新整理：從 sessionStorage 還原')
{
    const seed = fresh()
    seed.candidates.value = [...ALL]
    seed.selectedCandidateIds.value = [...LOCKED_IDS]
    await seed.lockSelectionAndStart()

    // 換一個新實例，清單只載到第一頁——重新整理後的真實狀態。
    const logic = useChatLogic()
    logic.candidates.value = [...PAGE_1]
    logic.restoreSessionState()
    const objs = logic.activeConversationCandidatesObjects.value
    check('還原後仍是 6 位', objs.length === 6, objs.length)
    check('traitty_selected_candidates 這次真的被讀回來了',
          PAGE_2.every(p => objs.some(o => o.name === p.name)),
          objs.map(o => o.name).join('、'))
}

// --- 3. 開新分頁（localStorage 還原）--------------------------------------
console.log('\n[3] 開新分頁：從 localStorage 還原')
{
    const seed = fresh()
    seed.candidates.value = [...ALL]
    seed.selectedCandidateIds.value = [...LOCKED_IDS]
    await seed.lockSelectionAndStart()
    seed.openNewTab()   // 寫入 traitty_new_tab_state 並重置本視窗

    const logic = useChatLogic()
    logic.candidates.value = [...PAGE_1]
    logic.restoreSessionState()
    const objs = logic.activeConversationCandidatesObjects.value
    check('新分頁還原後仍是 6 位', objs.length === 6, objs.length)
    check('state.selectedCandidates 這次真的被讀回來了',
          PAGE_2.every(p => objs.some(o => o.name === p.name)),
          objs.map(o => o.name).join('、'))
}

// --- 4. 移除一位：三者同步 -------------------------------------------------
console.log('\n[4] 移除一位：晶片、candidate_ids、trait_reports 同步減一')
{
    const logic = fresh()
    logic.candidates.value = [...ALL]
    logic.selectedCandidateIds.value = [...LOCKED_IDS]
    await logic.lockSelectionAndStart()
    // 讓被移除的人在報告快取裡確實有一筆，才驗得出有沒有被清掉。
    const victim = PAGE_2[0].candidate_id
    sessionStorage.setItem('traitty_batch_reports', JSON.stringify(
        Object.fromEntries(LOCKED_IDS.map(id => [String(id), { traits: [] }]))))
    reloadFirstPageOnly(logic)

    logic.removeCandidate(victim)
    const objs = logic.activeConversationCandidatesObjects.value
    check('晶片減為 5 位', objs.length === 5, objs.length)
    check('candidate_ids 也是 5', logic.activeConversationCandidateIds.value.length === 5)
    const reports = JSON.parse(sessionStorage.getItem('traitty_batch_reports'))
    check('trait_reports 少掉被移除的那一位', !(String(victim) in reports),
          Object.keys(reports).length)
    const stored = JSON.parse(sessionStorage.getItem('traitty_selected_candidates'))
    check('存回 sessionStorage 的人物件也是 5 位（不受分頁影響）',
          stored.length === 5, stored.length)
}

// --- 4b. 切換歷史對話 -------------------------------------------------------
console.log('\n[4b] 切換歷史對話：以 metadata.candidates 為準還原')
{
    const logic = fresh()
    logic.candidates.value = [...PAGE_1]     // 清單只有第一頁
    // /candidates/by-ids 回的是完整的一批，包含第 2 頁那 4 位。
    byIdsResponse = LOCKED.map(c => ({ ...c }))
    logic.previewSessionData.value = {
        session_id: 'hist-1',
        metadata: { candidates: LOCKED.map(c => ({ candidate_id: c.candidate_id, name: c.name })) }
    }
    logic.previewMessages.value = []
    await logic.switchContextToPreview()
    const objs = logic.activeConversationCandidatesObjects.value
    check('晶片數等於 metadata.candidates 的人數', objs.length === LOCKED.length,
          `${objs.length} vs ${LOCKED.length}`)
    check('不在當前頁的那 4 位也還原了',
          PAGE_2.every(p => objs.some(o => o.name === p.name)),
          objs.map(o => o.name).join('、'))
}

// --- 5. 新增一位 -----------------------------------------------------------
console.log('\n[5] 新增一位')
{
    const logic = fresh()
    logic.candidates.value = [...ALL]
    logic.selectedCandidateIds.value = [...LOCKED_IDS]
    await logic.lockSelectionAndStart()
    reloadFirstPageOnly(logic)
    // 新增的人在第一頁，但已鎖定的 4 位在第二頁——兩者要同時存在。
    await logic.addCandidates([PAGE_1[5].candidate_id])
    const objs = logic.activeConversationCandidatesObjects.value
    check('增為 7 位', objs.length === 7, objs.length)
    check('原本第 2 頁那 4 位沒有被擠掉',
          PAGE_2.every(p => objs.some(o => o.name === p.name)),
          objs.map(o => o.name).join('、'))
}

// --- 6. 回歸：舊行為確實會壞 -----------------------------------------------
console.log('\n[6] 回歸對照：舊的做法（拿分頁清單過濾）在同一情境下會少掉 4 位')
{
    const logic = fresh()
    logic.candidates.value = [...ALL]
    logic.selectedCandidateIds.value = [...LOCKED_IDS]
    await logic.lockSelectionAndStart()
    reloadFirstPageOnly(logic)
    const oldWay = logic.candidates.value.filter(
        c => logic.activeConversationCandidateIds.value.map(String).includes(String(c.candidate_id)))
    check('舊做法只剩 2 位（這就是「6 位剩 2 位」）', oldWay.length === 2, oldWay.length)
    check('新做法是 6 位', logic.activeConversationCandidatesObjects.value.length === 6)
}

console.log(`\n${failures.length === 0 ? '[DONE] all checks passed'
    : '[FAILED] ' + failures.join('; ')}`)
process.exit(failures.length === 0 ? 0 : 1)
