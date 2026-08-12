/**
 * 逐字重播的行為驗證：不掉字、不重複、不落後、結束點正確。
 *
 * 這四件事任何一件壞掉都不會在畫面上明顯報錯——掉字只是答案少幾個字，落後只是感覺變慢，
 * 結束點錯了則是存進 sessionStorage 的內容被截斷，要重新整理才看得出來。所以用真實計時器
 * 跑一遍，整支不到三秒。
 *
 *   node scripts/verify_typewriter.mjs
 */

import { createTypewriter } from '../src/composables/useChatLogic.js'

const failures = []
const check = (label, ok, detail = '') => {
    console.log(`  [${ok ? 'OK' : 'FAIL'}] ${label}${detail ? ' -- ' + detail : ''}`)
    if (!ok) failures.push(label)
}

const sink = () => {
    let text = ''
    return { append: (t) => { text += t }, get text() { return text } }
}

const seg = (n, ch) => ch.repeat(n)

async function main() {
    console.log('\n[1] 逐字播完後內容與送進去的完全一致（不掉字、不重複、不亂序）')
    {
        const out = sink()
        const tw = createTypewriter(out.append, { charsPerSecond: 300 })
        const parts = [seg(20, 'a'), seg(359, 'b'), seg(15, 'c'), seg(232, 'd')]
        for (const p of parts) tw.push(p)
        await tw.end()
        check('內容相符', out.text === parts.join(''),
              `${out.text.length} vs ${parts.join('').length} chars`)
    }

    console.log('\n[2] end() 要等佇列播完才 resolve（否則存檔會存到半截）')
    {
        const out = sink()
        const tw = createTypewriter(out.append, { charsPerSecond: 60, maxLagMs: 400 })
        tw.push(seg(400, 'x'))
        const before = out.text.length
        await tw.end()
        check('resolve 前沒有播完', before < 400, `resolve 前 ${before} chars`)
        check('resolve 後全部到齊', out.text.length === 400, `${out.text.length} chars`)
    }

    console.log('\n[3] 落後時會自動加速：一大段的播放時間受 maxLagMs 約束，')
    console.log('    而不是 佇列長度 / 地板速度（400 字 / 60 字每秒 = 6.7 秒）')
    {
        const out = sink()
        const tw = createTypewriter(out.append, { charsPerSecond: 60, maxLagMs: 500 })
        const t0 = Date.now()
        tw.push(seg(400, 'y'))
        await tw.end()
        const took = Date.now() - t0
        check('播放時間接近 maxLagMs 而非 6.7 秒', took < 1500, `${took}ms`)
        check('沒有因為加速而掉字', out.text.length === 400, `${out.text.length} chars`)
    }

    console.log('\n[4] 串流持續進來時不會越積越多（後端約 115 字/秒）')
    {
        const out = sink()
        const tw = createTypewriter(out.append, { charsPerSecond: 60, maxLagMs: 500 })
        let sent = 0
        for (let i = 0; i < 10; i++) {
            tw.push(seg(120, 'z')); sent += 120
            await new Promise(r => setTimeout(r, 100))   // 1200 字 / 1 秒，遠快於地板速度
        }
        const lag = sent - out.text.length
        const t0 = Date.now()
        await tw.end()
        check('串流期間的落後量有界', lag < 700, `落後 ${lag} chars`)
        check('串流結束後很快收尾', Date.now() - t0 < 1500, `${Date.now() - t0}ms`)
        check('總量正確', out.text.length === sent, `${out.text.length} vs ${sent}`)
    }

    console.log('\n[5] flush() 同步倒完剩下的字，之後的 push 直接貼上')
    {
        const out = sink()
        const tw = createTypewriter(out.append, { charsPerSecond: 1 })
        tw.push(seg(300, 'p'))
        tw.flush()
        check('flush 後立刻到齊（同步）', out.text.length === 300, `${out.text.length} chars`)
        tw.push('後續')
        check('flush 後的 push 直接貼上', out.text.endsWith('後續'), out.text.slice(-4))
        await tw.end()
    }

    console.log(`\n${failures.length ? '[FAILED] ' + failures.join('; ') : '[DONE] all checks passed'}`)
    process.exit(failures.length ? 1 : 0)
}

main()
