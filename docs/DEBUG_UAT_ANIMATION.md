# UAT 動畫異常排查指南

請在 UAT 環境開啟 Chrome DevTools (F12)，依照以下步驟檢查：

## 1. 確認 DOM 元素是否存在
1. 切換到 **Elements** 分頁。
2. 使用左上角的選取工具 (Ctrl+Shift+C) 點擊 Reasoning Block (腦袋圖示附近)。
3. 在 HTML 結構中展開 `.reasoning-header` > `.title` > `.loading-dots`。
4. **檢查：** 是否有看到 3 個 `<span class="bouncing-dot"></span>` 元素？
   - **如果沒有：** 表示 Vue 元件渲染邏輯有問題，可能是條件判斷錯誤。
   - **如果有：** 繼續下一步。

## 2. 檢查樣式計算 (Computed Styles)
選取其中一個 `.bouncing-dot` 元素：
1. 切換到右側的 **Computed** 分頁。
2. 檢查 `width` 和 `height` 是否為 `5px`。
3. 檢查 `display` 是否為 `inline-block` (如果是 `inline`，寬高會無效)。
4. 檢查 `animation-name` 是否為 `global-loading-dots-bounce`。

## 3. 測試動畫是否導致隱藏
因為動畫包含 `scale(0)` (縮小至 0)，如果動畫卡住或初始狀態錯誤，原點可能會消失。
1. 在右側 **Styles** 分頁，找到 `.bouncing-dot` 的樣式規則。
2. 暫時取消勾選 `animation` 屬性。
3. **檢查：** 原點是否出現了？
   - **如果是：** 表示動畫定義有問題（瀏覽器找不到 keyframes）。
   - **如果否：** 表示原點本身就沒被畫出來（可能是背景色問題、透明度問題或被遮擋）。

## 4. 檢查 Keyframes 是否載入
1. 在 Styles 分頁中，點擊 `animation: global-loading-dots-bounce ...` 旁邊的連結（通常是 `index.css` 或 `style.css`）。
2. 在開啟的 CSS 檔案中搜尋 `@keyframes global-loading-dots-bounce`。
3. **檢查：** 是否找得到這段定義？

## 5. 強制顯示測試 (如果是背景色問題)
在 Elements 面板選取 `.bouncing-dot`，直接在 `element.style` 輸入：
```css
border: 1px solid red;
background-color: red !important;
transform: none !important;
opacity: 1 !important;
```
如果看到紅點，代表元素存在但原本樣式導致看不見。
