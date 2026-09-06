/**
 * 模板用到的名字，`<script setup>` 有沒有解構、`useChatLogic` 有沒有真的匯出。
 *
 * 用法：
 *     cd frontend/chat-widget
 *     node scripts/verify_template_bindings.mjs
 *
 * 為什麼需要：Vue 的模板對「不存在的變數」是靜默的。`v-if="upstreamEnvEnable"`（少一個 d）
 * 會永遠是 undefined，切換器就永遠不出現——沒有錯誤、沒有警告、build 照樣過，只有在
 * 瀏覽器裡盯著看才發現。同理 `{{ activeConversationCandidatesObjects.length }}` 只要名字
 * 錯一個字，「選定 N 位人選」就會整段消失。
 *
 * 這支**不取代**瀏覽器實測——它驗不到 CSS、版面、confirm 對話框、下拉互動。它驗的是
 * 「線有沒有接上」，而那正是靜默失敗的那一類。
 */

import { readFileSync } from 'node:fs'
import { parse } from 'vue/compiler-sfc'

const failures = []
const check = (label, condition, detail = '') => {
    console.log(`  [${condition ? 'OK' : 'FAIL'}] ${label}${detail !== '' ? ' -- ' + detail : ''}`)
    if (!condition) failures.push(label)
}

const stripComments = (src) =>
    src.replace(/\/\*[\s\S]*?\*\//g, '').replace(/\/\/[^\n]*/g, '')

/** 從一個 `{ a, b: c, // 註解 }` 區塊裡取出名字。`side` 決定別名要取哪一邊。 */
const namesIn = (block, side = 'left') => new Set(
    stripComments(block || '').split(/[,\n]/)
        .map(x => x.trim())
        .map(x => {
            if (!x.includes(':')) return x
            const [l, r] = x.split(':')
            return (side === 'left' ? l : r).trim()
        })
        .filter(x => /^[A-Za-z_$][\w$]*$/.test(x)))

// --- useChatLogic 匯出了什麼 ------------------------------------------------
const logicSource = readFileSync('src/composables/useChatLogic.js', 'utf8')
const returnBlock = logicSource.slice(logicSource.lastIndexOf('\n    return {'))
const exported = namesIn(returnBlock)

// --- 元件的 setup 看得到什麼 ------------------------------------------------
const COMPONENT = 'src/components/ChatContainer.vue'
const { descriptor } = parse(readFileSync(COMPONENT, 'utf8'))
const script = descriptor.scriptSetup?.content || ''
const tpl = descriptor.template?.content || ''

const destructureBlock = script.match(/const\s*\{([\s\S]*?)\}\s*=\s*useChatLogic\(/)?.[1] || ''
// 別名（`lockSelectionAndStart: logicLockSelection`）在模板裡用的是右邊那個名字。
const visible = namesIn(destructureBlock, 'right')
for (const m of script.matchAll(/defineProps\s*\(\s*\{([\s\S]*?)\n\}\s*\)/g)) {
    for (const n of namesIn(m[1])) visible.add(n)
}
for (const m of script.matchAll(/(?:const|let|function)\s+([A-Za-z_$][\w$]*)/g)) {
    visible.add(m[1])
}
for (const m of script.matchAll(/^import\s+(?:\{([^}]*)\}|([A-Za-z_$][\w$]*))/gm)) {
    for (const n of (m[1] || m[2] || '').split(',')) {
        const name = n.trim().split(/\s+as\s+/).pop()
        if (name) visible.add(name)
    }
}

console.log(`useChatLogic 匯出 ${exported.size} 個；${COMPONENT} 的 setup 可見 ${visible.size} 個\n`)

console.log('[1] 解構出來的名字，useChatLogic 都有匯出')
{
    const missing = [...namesIn(destructureBlock, 'left')].filter(n => !exported.has(n))
    check('沒有解構到不存在的東西', missing.length === 0, missing.join(', '))
}

console.log('\n[2] 模板用到的名字，setup 都看得到')
{
    const BUILTIN = new Set([
        'true', 'false', 'null', 'undefined', 'in', 'of', 'typeof', 'new', 'return',
        'window', 'Math', 'JSON', 'String', 'Number', 'Object', 'Array', 'console',
        '$emit', '$event', '$slots', '$attrs', '$refs', '$el',   // Vue 模板內建
    ])
    const exprs = [
        ...[...tpl.matchAll(/\{\{([\s\S]*?)\}\}/g)].map(m => m[1]),
        ...[...tpl.matchAll(/(?:v-if|v-else-if|v-show|v-model|:[\w.-]+|@[\w.-]+)="([^"]*)"/g)]
            .map(m => m[1]),
    ]
    // v-for 引入的區域變數不算外部綁定。
    const locals = new Set()
    for (const m of tpl.matchAll(/v-for="\(?\s*([^)"]*?)\s*\)?\s+(?:in|of)\s/g)) {
        for (const n of m[1].split(',')) locals.add(n.trim())
    }

    const used = new Set()
    for (const raw of exprs) {
        // 字串字面值與物件鍵不是綁定：`:class="{'full-page-mode': isFullPage}"` 裡的
        // `full-page-mode`、`'prd'` 都要先拿掉，否則會被當成找不到的變數。
        const e = raw
            .replace(/'[^']*'/g, "''")
            .replace(/`[^`]*`/g, '``')
            .replace(/"[^"]*"/g, '""')
            .replace(/([A-Za-z_$][\w$-]*)\s*:/g, ' ')
        for (const m of e.matchAll(/(?<![.\w$])(\$?[a-z_][\w$]*)/g)) {
            const n = m[1]
            if (!BUILTIN.has(n) && !locals.has(n)) used.add(n)
        }
    }
    const unknown = [...used].filter(n => !visible.has(n)).sort()
    check(`模板用到的 ${used.size} 個名字都找得到`, unknown.length === 0,
          unknown.length ? `找不到：${unknown.join(', ')}` : '')
}

console.log('\n[3] 這次修改新增的綁定確實接上了')
{
    for (const name of ['upstreamEnvEnabled', 'upstreamEnv', 'upstreamEnvOptions',
                        'upstreamBaseUrl', 'isSwitchingEnv', 'currentUserEmail',
                        'activeConversationCandidatesObjects']) {
        check(`${name}：模板有用、setup 有、composable 有匯出`,
              tpl.includes(name) && visible.has(name) && exported.has(name),
              `模板=${tpl.includes(name)} setup=${visible.has(name)} 匯出=${exported.has(name)}`)
    }
    check('「選定 N 位人選」綁的是修好後的那個來源',
          /選定\s*\{\{\s*activeConversationCandidatesObjects\.length\s*\}\}\s*位人選/.test(tpl))
    check('環境切換器以 upstreamEnvEnabled 控制顯示', /v-if="upstreamEnvEnabled"/.test(tpl))
    check('切到非 default 會先確認',
          /@change="onEnvChange/.test(tpl) && /window\.confirm/.test(script))
}

console.log(`\n${failures.length === 0 ? '[DONE] all checks passed'
    : '[FAILED] ' + failures.join('; ')}`)
process.exit(failures.length === 0 ? 0 : 1)
