/**
 * 全域 Loading 遮罩功能
 * 用於顯示處理中狀態，防止用戶重複操作
 */

// 防止重複宣告
if (typeof LoadingOverlay === 'undefined') {
    class LoadingOverlay {
    constructor() {
        this.overlay = null;
        this.isShowing = false;
        this.createOverlay();
    }

    createOverlay() {
        // 創建遮罩元素
        this.overlay = document.createElement('div');
        this.overlay.id = 'loading-overlay';
        this.overlay.innerHTML = `
            <div class="loading-content">
                <div class="loading-spinner"></div>
                <div class="loading-text">處理中...</div>
                <div class="loading-subtitle">請稍候，系統正在處理您的請求</div>
            </div>
        `;
        
        // 添加到 body
        document.body.appendChild(this.overlay);
    }

    show(text = '處理中...', subtitle = '請稍候，系統正在處理您的請求') {
        if (this.isShowing) return;
        
        const textElement = this.overlay.querySelector('.loading-text');
        const subtitleElement = this.overlay.querySelector('.loading-subtitle');
        
        if (textElement) textElement.textContent = text;
        if (subtitleElement) subtitleElement.textContent = subtitle;
        
        this.overlay.style.display = 'flex';
        this.isShowing = true;
        
        // 禁用頁面滾動
        document.body.style.overflow = 'hidden';
    }

    hide() {
        if (!this.isShowing) return;
        
        this.overlay.style.display = 'none';
        this.isShowing = false;
        
        // 恢復頁面滾動
        document.body.style.overflow = '';
    }

    updateText(text, subtitle = null) {
        const textElement = this.overlay.querySelector('.loading-text');
        const subtitleElement = this.overlay.querySelector('.loading-subtitle');
        
        if (textElement) textElement.textContent = text;
        if (subtitle && subtitleElement) subtitleElement.textContent = subtitle;
    }
}

    // 創建全域實例
    window.loadingOverlay = new LoadingOverlay();
}

// 自動綁定表單提交事件
if (typeof window.loadingOverlayInitialized === 'undefined') {
    window.loadingOverlayInitialized = true;
    
    document.addEventListener('DOMContentLoaded', function() {
    // 監聽所有表單提交
    document.addEventListener('submit', function(e) {
        const form = e.target;
        
        // 檢查是否有 data-no-loading 屬性
        if (form.getAttribute('data-no-loading') === 'true') {
            return;
        }
        
        // 顯示 loading
        window.loadingOverlay.show('提交中...', '正在處理您的請求，請稍候');
    });
    
    // 監聽所有帶有 data-loading 屬性的按鈕
    document.querySelectorAll('[data-loading]').forEach(button => {
        button.addEventListener('click', function(e) {
            const loadingText = this.getAttribute('data-loading') || '處理中...';
            const loadingSubtitle = this.getAttribute('data-loading-subtitle') || '請稍候，系統正在處理您的請求';
            
            window.loadingOverlay.show(loadingText, loadingSubtitle);
        });
    });
    
    // 監聽所有 AJAX 請求（如果使用 jQuery）
    if (typeof $ !== 'undefined') {
        $(document).ajaxStart(function() {
            window.loadingOverlay.show('載入中...', '正在與伺服器通訊，請稍候');
        });
        
        $(document).ajaxStop(function() {
            window.loadingOverlay.hide();
        });
    }
});

    // 頁面載入或錯誤時隱藏 loading
    window.addEventListener('load', function() {
        if (window.loadingOverlay) {
            window.loadingOverlay.hide();
        }
    });

    window.addEventListener('error', function() {
        if (window.loadingOverlay) {
            window.loadingOverlay.hide();
        }
    });
}