/**
 * S3／S4 劇本：用**真實後端與真實 PRD 資料**驅動 widget 的 composable。
 *
 * 用法（後端要先跑起來）：
 *     cd frontend/chat-widget
 *     node scripts/verify_active_roster_live.mjs            # 打 PRD
 *     UAT_ENV=default node scripts/verify_active_roster_live.mjs
 *
 * 和 `verify_active_roster.mjs` 的差別：那一支用假資料驗邏輯，這一支打真的
 * `localhost:5000`，候選人與特質報告都來自 PRD。所以它會抓到「假資料想不到」的東西——
 * 真實的 candidate_id 型別、真實的分頁行為、reports/batch 真的對不對得起來。
 *
 * **不花額度**：只呼叫 /auth/login、/candidates/、/reports/batch，不提問。
 *
 * 涵蓋不到的：畫面上的實際渲染。那需要瀏覽器；本檔驗的是驅動 UI 的資料來源。
 */

const BACKEND = process.env.WIDGET_BACKEND || 'http://localhost:5000'
const ENV = process.env.UAT_ENV || 'prd'
const EMAIL = process.env.UAT_EMAIL || 'a080697@gmail.com'
const PAGE = 20                       // 與 useChatLogic 的 PAGE_LIMIT 一致

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
    TRAITTY_WIDGET_CONFIG: { apiBaseUrl: `${BACKEND}/api/v2`, userEmail: EMAIL },
    location: { href: 'http://localhost:5300/' },
    open: () => {},
}

const realFetch = globalThis.fetch
let token = null
// widget 的每個呼叫都帶 Authorization；這裡補上，其餘原樣轉發給真後端。
globalThis.fetch = (url, opts = {}) => {
    const headers = { ...(opts.headers || {}) }
    if (token && !headers.Authorization) headers.Authorization = `Bearer ${token}`
    return realFetch(url, { ...opts, headers })
}

const { useChatLogic } = await import('../src/composables/useChatLogic.js')

const failures = []
const check = (label, condition, detail = '') => {
    console.log(`  [${condition ? 'OK' : 'FAIL'}] ${label}${detail !== '' ? ' -- ' + detail : ''}`)
    if (!condition) failures.push(label)
}

const login = async () => {
    const res = await realFetch(`${BACKEND}/auth/login`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: EMAIL, env: ENV }),
    })
    const body = await res.json()
    if (!body?.data?.token) throw new Error(`登入失敗：${JSON.stringify(body).slice(0, 200)}`)
    return body.data
}

const fetchPage = async (limit, offset) => {
    const res = await realFetch(`${BACKEND}/api/v2/candidates/?limit=${limit}&offset=${offset}`,
                                { headers: { Authorization: `Bearer ${token}` } })
    const body = await res.json()
    return (body.data || []).map(c => ({ ...c, id: c.candidate_id }))
}

// --------------------------------------------------------------------------
const auth = await login()
token = auth.token
console.log(`環境：${auth.upstream?.env}  上游：${auth.upstream?.base_url}  帳號：${EMAIL}`)

const page1 = await fetchPage(PAGE, 0)
const page2 = await fetchPage(PAGE, PAGE)
const withAssessment = [...page1, ...page2].filter(c => c.latest_assessment?.assessment_id)
if (page2.length < 4 || withAssessment.length < 6) {
    console.log('[SKIP] 這個環境的候選人不足以做跨頁劇本')
    process.exit(0)
}
// 鎖定 6 位：2 位在第一頁、4 位在第二頁——正是「6 位剩 2 位」的形狀。
const fromP1 = page1.filter(c => c.latest_assessment?.assessment_id).slice(0, 2)
const fromP2 = page2.filter(c => c.latest_assessment?.assessment_id).slice(0, 4)
const LOCKED = [...fromP1, ...fromP2]
const LOCKED_IDS = LOCKED.map(c => c.candidate_id)
console.log(`鎖定 6 位（第 1 頁 ${fromP1.length} 位、第 2 頁 ${fromP2.length} 位）：`
            + LOCKED.map(c => `${c.candidate_id} ${c.name}`).join('、') + '\n')

// widget 的每個呼叫都用 userToken.value 組 Authorization，所以這裡一定要設。
// 沒設的話送出去的是 `Bearer null`，而後端會靜默退回一個寫死的 email 並回 HTTP 200＋空資料
// （見 reports.py / candidates.py 的 fallback）——測試會看起來「通過但沒資料」。
const attach = (logic) => { logic.userToken.value = token; return logic }
const fresh = () => { sessionStorage.clear(); localStorage.clear(); return attach(useChatLogic()) }

// --- S3 跨頁鎖定 + 重新整理 ------------------------------------------------
console.log('[S3] 跨頁鎖定，之後清單只載回第一頁')
{
    const logic = fresh()
    logic.candidates.value = [...page1, ...page2]
    logic.selectedCandidateIds.value = [...LOCKED_IDS]
    await logic.lockSelectionAndStart()
    check('鎖定後是 6 位', logic.activeConversationCandidatesObjects.value.length === 6,
          logic.activeConversationCandidatesObjects.value.length)

    const reports = JSON.parse(sessionStorage.getItem('traitty_batch_reports') || '{}')
    check('每一位都抓到真實的特質報告', Object.keys(reports).length === 6,
          `${Object.keys(reports).length} 份：${Object.keys(reports).join(',')}`)
    const traitCounts = Object.entries(reports).map(([k, r]) => `${k}:${(r.traits || []).length}`)
    check('報告內容非空', Object.values(reports).every(r => (r.traits || []).length > 0),
          traitCounts.join(' '))

    logic.candidates.value = [...page1]        // 模擬 fetchCandidates(false)
    const objs = logic.activeConversationCandidatesObjects.value
    check('清單只剩第一頁後仍是 6 位', objs.length === 6, objs.length)
    check('candidates_info 長度 == candidate_ids 長度',
          objs.length === logic.activeConversationCandidateIds.value.length)
    check('第 2 頁那幾位的姓名沒有掉',
          fromP2.every(p => objs.some(o => o.name === p.name)),
          objs.map(o => o.name).join('、'))
}

console.log('\n[S3b] 重新整理後還原')
{
    const seed = fresh()
    seed.candidates.value = [...page1, ...page2]
    seed.selectedCandidateIds.value = [...LOCKED_IDS]
    await seed.lockSelectionAndStart()

    const logic = attach(useChatLogic())        // 新實例＝重新整理
    logic.candidates.value = [...page1]        // 只載回第一頁
    logic.restoreSessionState()
    const objs = logic.activeConversationCandidatesObjects.value
    check('還原後仍是 6 位', objs.length === 6, objs.length)
    check('第 2 頁那幾位也還原了',
          fromP2.every(p => objs.some(o => o.name === p.name)),
          objs.map(o => o.name).join('、'))
}

// --- S4 切換歷史對話 --------------------------------------------------------
console.log('\n[S4] 切換歷史對話（以 metadata.candidates 還原，走真實 /candidates/by-ids）')
{
    const logic = fresh()
    logic.candidates.value = [...page1]         // 清單只有第一頁
    logic.previewSessionData.value = {
        session_id: 'live-history-probe',
        metadata: { candidates: LOCKED.map(c => ({ candidate_id: c.candidate_id, name: c.name })) },
    }
    logic.previewMessages.value = []
    await logic.switchContextToPreview()
    const objs = logic.activeConversationCandidatesObjects.value
    check('晶片數等於 metadata.candidates 的人數', objs.length === LOCKED.length,
          `${objs.length} vs ${LOCKED.length}`)
    check('不在當前頁的那幾位也還原了',
          fromP2.every(p => objs.some(o => String(o.candidate_id) === String(p.candidate_id))),
          objs.map(o => o.candidate_id).join(','))
    const reports = JSON.parse(sessionStorage.getItem('traitty_batch_reports') || '{}')
    check('還原時一併抓回特質報告', Object.keys(reports).length === LOCKED.length,
          Object.keys(reports).length)
}

// --- 回歸對照 --------------------------------------------------------------
console.log('\n[對照] 舊做法（拿分頁清單過濾）在同一批真實資料上會少掉幾位')
{
    const logic = fresh()
    logic.candidates.value = [...page1, ...page2]
    logic.selectedCandidateIds.value = [...LOCKED_IDS]
    await logic.lockSelectionAndStart()
    logic.candidates.value = [...page1]
    const oldWay = logic.candidates.value.filter(
        c => logic.activeConversationCandidateIds.value.map(String).includes(String(c.candidate_id)))
    check(`舊做法只剩 ${oldWay.length} 位`, oldWay.length === fromP1.length, oldWay.length)
    check('新做法是 6 位', logic.activeConversationCandidatesObjects.value.length === 6)
}

console.log(`\n${failures.length === 0 ? '[DONE] all checks passed'
    : '[FAILED] ' + failures.join('; ')}`)
process.exit(failures.length === 0 ? 0 : 1)
