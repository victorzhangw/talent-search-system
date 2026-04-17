/**
 * Widgey Chat 功能開關設定檔
 *
 * 所有功能的預設值都在此定義。
 * 嵌入方可透過 window.TRAITTY_WIDGET_CONFIG.features 進行覆蓋，
 * 覆蓋的值會與預設值合併（淺層 merge），不需要完整重寫整份設定。
 *
 * 範例（嵌入方 HTML）：
 *   window.TRAITTY_WIDGET_CONFIG = {
 *     apiBaseUrl: "https://...",
 *     features: {
 *       quickQuestions: {
 *         enforceSingleCandidateLimit: false,  // 關閉單人限制（所有問題皆可見）
 *       }
 *     }
 *   }
 */

/** 預設功能設定 */
export const defaultFeatures = {
    quickQuestions: {
        /**
         * 整體快速提問功能開關
         * 設為 false 時，整個快速提問側欄／彈出視窗將完全隱藏
         */
        enabled: true,

        /**
         * 是否啟用「候選人數量限制」過濾規則
         *
         * 設為 true：  根據後端模組的 candidate_mode（single_only / multi_only / both），
         *              在候選人數量不符時自動隱藏不適用的提問。
         * 設為 false： 所有問題無論候選人數量皆顯示（停用此功能）
         */
        enforceSingleCandidateLimit: true
    }
}

/**
 * 取得合併後的功能設定
 *
 * 合併優先順序：外部設定 > 預設值
 * 只做一層淺層合併，不做深層遞迴。
 *
 * @returns {typeof defaultFeatures}
 */
export const getFeatures = () => {
    const external = (window.TRAITTY_WIDGET_CONFIG || {}).features || {}
    return {
        quickQuestions: {
            ...defaultFeatures.quickQuestions,
            ...(external.quickQuestions || {})
        }
    }
}
