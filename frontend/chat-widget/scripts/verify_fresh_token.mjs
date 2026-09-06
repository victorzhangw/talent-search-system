/**
 * 每一次打後端 API 之前，都先換一張新的 token（0905 文件 E-11）。
 *
 * 用法：
 *     cd frontend/chat-widget
 *     node scripts/verify_fresh_token.mjs
 *
 * 對照的缺陷：`/auth/login` 簽出來的 token 只有 2 分鐘，而這個 composable 以前是登入時
 * 取一次就一路用到底（`userToken.value` 從不更新）。後端因此不敢驗 exp——一驗，使用者
 * 開著頁面兩分鐘後所有請求都會被擋；不驗，任何人偽造一張 `{"email": "別人"}` 都讀得到
 * 別人的資料。要收緊後端，前端得先會換 token。
 *
 * 這裡驗的就是「會不會換」：用 Node 直接驅動 composable，把 fetch 換成會記帳的樁，
 * 每次 `/auth/login` 回一張**不同**的 token，然後檢查每一個帶 Authorization 的請求
 * 是不是緊接在一次 login 之後，而且用的正是那一次拿到的 token。
 *
 * 不涵蓋的部分（需要真實瀏覽器 / 真後端）：token 真的過期時的行為、後端的驗簽。
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
    open: () => { },
    innerWidth: 1280
}

// --- 會記帳的 fetch 樁 -----------------------------------------------------
let calls = []          // { url, method, auth }
let loginCount = 0

const jsonResponse = (payload) => ({
    ok: true,
    status: 200,
    json: async () => payload,
    // /chat/ 走串流；回一個立刻結束的 reader 就夠，這支不驗回覆內容。
    body: { getReader: () => ({ read: async () => ({ done: true, value: undefined }) }) }
})

globalThis.fetch = async (url, options = {}) => {
    const u = String(url)
    const headers = (options && options.headers) || {}
    const auth = headers.Authorization || headers.authorization || null
    calls.push({ url: u, method: (options.method || 'GET').toUpperCase(), auth })

    if (u.includes('/auth/login')) {
        loginCount += 1
        return jsonResponse({
            success: true,
            data: {
                token: `tok-${loginCount}`,
                user: { email: 'tester@example.com', id: 1 },
                upstream: { env: 'default', base_url: 'https://uat.example.test' }
            }
        })
    }
    if (u.includes('/auth/environments')) {
        return jsonResponse({ success: true, data: { enabled: false, environments: [], current: 'default' } })
    }
    if (u.includes('/candidates/by-ids')) {
        return jsonResponse({ success: true, data: [], meta: { missing_candidate_ids: [] } })
    }
    if (u.includes('/candidates/')) {
        return jsonResponse({ success: true, data: [], meta: { page: { total: 0 } } })
    }
    if (u.includes('/reports/batch')) {
        return jsonResponse({ success: true, data: { reports: [] } })
    }
    if (u.includes('/modules/')) {
        return jsonResponse({ success: true, data: { categories: {} } })
    }
    if (u.includes('/init/')) {
        return jsonResponse({ success: true, data: { status: true, quota_summary: { total: 1, used: 0, remaining: 1 } } })
    }
    if (u.includes('/chat/history')) {
        return jsonResponse({ success: true, data: { today: [], has_more: false } })
    }
    return jsonResponse({ success: true, data: { messages: [], metadata: null } })
}

const { useChatLogic } = await import('../src/composables/useChatLogic.js')

// --- 測試輔助 -------------------------------------------------------------
const failures = []
const check = (label, condition, detail = '') => {
    console.log(`  [${condition ? 'OK' : 'FAIL'}] ${label}${detail !== '' ? ' -- ' + detail : ''}`)
    if (!condition) failures.push(label)
}

const isLogin = (c) => c.url.includes('/auth/login')
/** 帶身分的請求：有 Authorization 的那些。login 自己不帶。 */
const authed = () => calls.filter(c => c.auth !== null && c.auth !== undefined)

const fresh = () => {
    sessionStorage.clear()
    localStorage.clear()
    calls = []
    loginCount = 0
    const logic = useChatLogic(() => { })
    // 這支測的是 token，不是登入流程本身：直接給一個 email 讓 currentUserEmail() 有值。
    window.TRAITTY_WIDGET_CONFIG.userEmail = 'tester@example.com'
    return logic
}

// --- 1. 每個帶身分的請求，前面都緊接著一次 login ---------------------------
console.log('\n[1] 登入之後的四個請求（init / candidates / modules / history）')
{
    const logic = fresh()
    await logic.handleLoginSuccess({
        token: 'tok-from-login',
        user: { email: 'tester@example.com' },
        upstream: { env: 'default', base_url: 'https://uat.example.test' }
    })

    const withAuth = authed()
    check('四個請求都送出了', withAuth.length === 4,
        withAuth.map(c => c.url.replace('http://localhost:5000', '')).join(' , '))
    check('沒有任何請求沿用 handleLoginSuccess 拿到的那張 token',
        withAuth.every(c => c.auth !== 'Bearer tok-from-login'),
        withAuth.map(c => c.auth).join(' , '))

    let everyPrecededByLogin = true
    let everyUsesItsOwnToken = true
    for (const c of withAuth) {
        const i = calls.indexOf(c)
        const prev = calls[i - 1]
        if (!prev || !isLogin(prev)) { everyPrecededByLogin = false; continue }
        // 第 n 次 login 回的是 tok-n；前一個呼叫是第幾次 login 由順序決定。
        const nth = calls.slice(0, i).filter(isLogin).length
        if (c.auth !== `Bearer tok-${nth}`) everyUsesItsOwnToken = false
    }
    check('每個請求的前一個呼叫都是 POST /auth/login', everyPrecededByLogin)
    check('每個請求用的是自己那一次 login 換到的 token', everyUsesItsOwnToken,
        withAuth.map(c => c.auth).join(' , '))
    check('token 每次都不同（沒有重複用同一張）',
        new Set(withAuth.map(c => c.auth)).size === withAuth.length)
}

// --- 2. 其餘呼叫點 ---------------------------------------------------------
console.log('\n[2] 其餘呼叫點：歷史、單一對話、評分、載入更多、報告')
{
    const logic = fresh()
    await logic.handleLoginSuccess({ token: 'tok-from-login', user: { email: 'tester@example.com' } })
    const before = calls.length

    await logic.fetchHistory(1, false)
    await logic.loadHistorySession({ session_id: 'S-1', metadata: { candidates: [] } })
    await logic.rateMessage(42, 1)
    // loadMoreCandidates 只有在還有下一頁時才會送出請求，樁回的是空清單，所以這裡
    // 直接把旗標打開——這一節看的是「有沒有先換 token」，不是分頁邏輯。
    logic.hasMoreCandidates.value = true
    await logic.loadMoreCandidates()
    await new Promise(r => setTimeout(r, 0))

    const fresh_calls = calls.slice(before)
    const withAuth = fresh_calls.filter(c => c.auth)
    check('四個呼叫點都送出了請求', withAuth.length === 4,
        withAuth.map(c => c.url.replace('http://localhost:5000', '')).join(' , '))

    let ok = true
    for (const c of withAuth) {
        const i = calls.indexOf(c)
        if (!calls[i - 1] || !isLogin(calls[i - 1])) ok = false
        const nth = calls.slice(0, i).filter(isLogin).length
        if (c.auth !== `Bearer tok-${nth}`) ok = false
    }
    check('每一個都是「先 login 再打」，且用當次的 token', ok,
        withAuth.map(c => c.auth).join(' , '))
}

// --- 3. 鎖定名單 -> 批次報告 -> 提問 ---------------------------------------
console.log('\n[3] 鎖定名單（批次報告）與提問（/chat/）')
{
    const logic = fresh()
    await logic.handleLoginSuccess({ token: 'tok-from-login', user: { email: 'tester@example.com' } })
    logic.candidates.value = [
        { candidate_id: 601, id: 601, name: '受測者一', latest_assessment: { assessment_id: 701 } },
        { candidate_id: 602, id: 602, name: '受測者二', latest_assessment: { assessment_id: 702 } }
    ]
    logic.selectedCandidateIds.value = [601, 602]

    const before = calls.length
    await logic.lockSelectionAndStart()
    const batch = calls.slice(before).filter(c => c.url.includes('/reports/batch'))
    check('批次報告有送出', batch.length >= 1, batch.length)
    if (batch.length) {
        const i = calls.indexOf(batch[0])
        const nth = calls.slice(0, i).filter(isLogin).length
        check('批次報告：先 login 再打，用當次的 token',
            isLogin(calls[i - 1]) && batch[0].auth === `Bearer tok-${nth}`, batch[0].auth)
    }

    const beforeChat = calls.length
    logic.inputQuery.value = '這幾位的溝通風格如何'
    await logic.sendMessage()
    const chat = calls.slice(beforeChat).filter(c => c.url.endsWith('/chat/'))
    check('/chat/ 有送出', chat.length === 1, chat.length)
    if (chat.length) {
        const i = calls.indexOf(chat[0])
        const nth = calls.slice(0, i).filter(isLogin).length
        check('/chat/：先 login 再打，用當次的 token',
            isLogin(calls[i - 1]) && chat[0].auth === `Bearer tok-${nth}`, chat[0].auth)
    }
}

// --- 4. 原始碼裡不能再有沿用舊 token 的寫法 --------------------------------
console.log('\n[4] 原始碼：沒有任何呼叫點還在沿用 userToken.value')
{
    const { readFileSync, readdirSync } = await import('node:fs')
    const { join } = await import('node:path')

    const walk = (dir) => readdirSync(dir, { withFileTypes: true }).flatMap(e =>
        e.isDirectory() ? walk(join(dir, e.name)) : [join(dir, e.name)])

    const offenders = []
    for (const file of walk('src')) {
        if (!/\.(js|vue)$/.test(file)) continue
        const text = readFileSync(file, 'utf-8')
        // login 本身不帶 Authorization；其餘任何「Bearer + 存起來的值」都是舊寫法。
        for (const line of text.split('\n')) {
            if (line.includes('Bearer ${userToken.value}') || line.includes('Bearer ${props.token}')) {
                offenders.push(`${file}: ${line.trim()}`)
            }
        }
    }
    check('沒有 Bearer ${userToken.value} / ${props.token}', offenders.length === 0,
        offenders.join(' | '))
}

console.log(`\n${failures.length === 0 ? '[DONE] all checks passed' : '[FAILED] ' + failures.join('; ')}`)
process.exit(failures.length === 0 ? 0 : 1)
