# Traitty Chat Widget 整合指南

這份文件說明如何將 Traitty 聊天小工具 (Chat Widget) 整合至您的網站。
目前提供兩種整合方式：**標準 HTML 嵌入** 與 **Google Tag Manager (GTM)**。

## 資源位置
- **CSS 樣式表**: `https://devzoneapi3.aurocore.com/loader.css`
- **JS 主程式**: `https://devzoneapi3.aurocore.com/loader.iife.js`

---

## 方式一：標準 HTML 嵌入 (Standard)

將以下程式碼貼入您網站的 `<head>` 或 `<body>` 結束標籤之前。

### 1. 引入必要檔案
```html
<head>
    <!-- 引入 Widget 樣式 -->
    <link rel="stylesheet" href="https://devzoneapi3.aurocore.com/loader.css">
</head>
```

### 2. 設定與掛載
在 `<body>` 中加入掛載點與設定腳本：

```html
<body>
    <!-- 1. 建立掛載點 (建議放在頁面底部) -->
    <div id="app"></div>

    <!-- 2. 設定參數 -->
    <script>
        window.TRAITTY_WIDGET_CONFIG = {
            // 使用者識別 (必要)
            userEmail: "eva@wepredict.io",
            
            // API 後端位址 (必要)
            // 如果您的網站與 API 同網域，可使用 window.location.origin + "/api/v2"
            // 否則請填寫完整絕對路徑，例如 "https://devzoneapi3.aurocore.com/api/v2"
            apiBaseUrl: "https://devzoneapi3.aurocore.com/api/v2",
            
            // 自動啟動 (必要)
            autoInit: true
        };
    </script>

    <!-- 3. 載入 Widget 主程式 -->
    <script src="https://devzoneapi3.aurocore.com/loader.iife.js"></script>
</body>
```

---

## 方式二：Google Tag Manager (GTM)

使用 GTM 的 **「自訂 HTML (Custom HTML)」** 標籤來動態注入 Widget。

### 設定步驟
1.  在 GTM 中新增一個 **Tag (標籤)**。
2.  類型選擇 **Custom HTML (自訂 HTML)**。
3.  將下方程式碼貼入 HTML 欄位。
4.  Trigger (觸發條件) 設定為 **All Pages (網頁瀏覽)** 或您希望出現的特定頁面。

### GTM 代碼內容
```html
<!-- Traitty Widget Injector -->
<script>
(function() {
    // 1. 設定參數
    window.TRAITTY_WIDGET_CONFIG = {
        userEmail: "eva@wepredict.io", // 請改為實際變數，例如 {{User Email}}
        apiBaseUrl: "https://devzoneapi3.aurocore.com/api/v2",
        autoInit: true
    };

    // 2. 動態載入 CSS
    var link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://devzoneapi3.aurocore.com/loader.css';
    document.head.appendChild(link);

    // 3. 建立掛載點 div (如果頁面上還沒有)
    if (!document.getElementById('app')) {
        var appDiv = document.createElement('div');
        appDiv.id = 'app';
        document.body.appendChild(appDiv);
    }

    // 4. 動態載入 JS
    var script = document.createElement('script');
    script.src = 'https://devzoneapi3.aurocore.com/loader.iife.js';
    script.async = true;
    document.body.appendChild(script);
})();
</script>
```

### GTM 變數建議
*   **userEmail**: 建議使用 GTM 的「資料層變數 (Data Layer Variable)」來動態填入登入使用者的 Email。
    ```javascript
    userEmail: {{User Email}} || "guest@example.com",
    ```

---

## 參數說明 (Configuration)

| 參數名稱 | 類型 | 必填 | 說明 |
| :--- | :--- | :--- | :--- |
| `userEmail` | String | 是 | 用於識別當前使用者的 Email，用於關聯評測報告。 |
| `apiBaseUrl` | String | 是 | 後端 API 的基礎路徑 (包含 `/api/v2`)。 |
| `autoInit` | Boolean | 是 | 設為 `true` 以在腳本載入後自動啟動 Widget。 |
