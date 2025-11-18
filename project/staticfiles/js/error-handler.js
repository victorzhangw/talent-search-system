// 錯誤處理系統

class ErrorHandler {
    constructor() {
        this.errors = [];
        this.maxErrors = 100;
        this.notificationContainer = null;
        this.init();
    }

    init() {
        this.createNotificationContainer();
        this.bindGlobalErrorHandlers();
    }

    // 創建通知容器
    createNotificationContainer() {
        this.notificationContainer = document.createElement('div');
        this.notificationContainer.id = 'error-notifications';
        this.notificationContainer.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            pointer-events: none;
        `;
        document.body.appendChild(this.notificationContainer);
    }

    // 綁定全局錯誤處理器
    bindGlobalErrorHandlers() {
        // JavaScript 錯誤
        window.addEventListener('error', (event) => {
            this.handleJavaScriptError(event);
        });

        // Promise 拒絕
        window.addEventListener('unhandledrejection', (event) => {
            this.handlePromiseRejection(event);
        });

        // 資源載入錯誤
        window.addEventListener('error', (event) => {
            if (event.target !== window) {
                this.handleResourceError(event);
            }
        }, true);

        // AJAX 錯誤處理
        this.interceptAjaxErrors();
    }

    // 處理 JavaScript 錯誤
    handleJavaScriptError(event) {
        const error = {
            type: 'javascript',
            message: event.message,
            filename: event.filename,
            lineno: event.lineno,
            colno: event.colno,
            stack: event.error ? event.error.stack : null,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent
        };

        this.logError(error);
        this.showNotification('JavaScript 錯誤', error.message, 'error');
    }

    // 處理 Promise 拒絕
    handlePromiseRejection(event) {
        const error = {
            type: 'promise',
            message: event.reason?.message || '未處理的 Promise 拒絕',
            stack: event.reason?.stack || null,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent
        };

        this.logError(error);
        this.showNotification('Promise 錯誤', error.message, 'error');
    }

    // 處理資源載入錯誤
    handleResourceError(event) {
        const error = {
            type: 'resource',
            message: `資源載入失敗: ${event.target.src || event.target.href}`,
            element: event.target.tagName,
            timestamp: new Date().toISOString(),
            url: window.location.href
        };

        this.logError(error);
        this.showNotification('資源載入錯誤', error.message, 'warning');
    }

    // 攔截 AJAX 錯誤
    interceptAjaxErrors() {
        // 攔截 XMLHttpRequest
        const originalXHR = window.XMLHttpRequest;
        const self = this;

        window.XMLHttpRequest = function() {
            const xhr = new originalXHR();
            const originalOpen = xhr.open;
            const originalSend = xhr.send;

            xhr.open = function(method, url, async, user, password) {
                this._method = method;
                this._url = url;
                return originalOpen.apply(this, arguments);
            };

            xhr.send = function(data) {
                this.addEventListener('error', function() {
                    self.handleAjaxError(this, 'network');
                });

                this.addEventListener('load', function() {
                    if (this.status >= 400) {
                        self.handleAjaxError(this, 'http');
                    }
                });

                return originalSend.apply(this, arguments);
            };

            return xhr;
        };

        // 攔截 fetch
        const originalFetch = window.fetch;
        window.fetch = function(url, options) {
            return originalFetch.apply(this, arguments)
                .then(response => {
                    if (!response.ok) {
                        self.handleFetchError(response, url, options);
                    }
                    return response;
                })
                .catch(error => {
                    self.handleFetchError(error, url, options);
                    throw error;
                });
        };
    }

    // 處理 AJAX 錯誤
    handleAjaxError(xhr, type) {
        const error = {
            type: 'ajax',
            subtype: type,
            method: xhr._method,
            url: xhr._url,
            status: xhr.status,
            statusText: xhr.statusText,
            responseText: xhr.responseText,
            timestamp: new Date().toISOString(),
            pageUrl: window.location.href
        };

        this.logError(error);
        
        const message = this.getAjaxErrorMessage(xhr.status);
        this.showNotification('請求錯誤', message, 'error');
    }

    // 處理 Fetch 錯誤
    handleFetchError(response, url, options) {
        const error = {
            type: 'fetch',
            url: url,
            method: options?.method || 'GET',
            status: response?.status || 0,
            statusText: response?.statusText || 'Network Error',
            timestamp: new Date().toISOString(),
            pageUrl: window.location.href
        };

        this.logError(error);
        
        const message = this.getFetchErrorMessage(response?.status || 0);
        this.showNotification('請求錯誤', message, 'error');
    }

    // 獲取 AJAX 錯誤消息
    getAjaxErrorMessage(status) {
        const messages = {
            400: '請求格式錯誤',
            401: '未授權，請重新登入',
            403: '沒有權限執行此操作',
            404: '請求的資源不存在',
            405: '請求方法不被允許',
            408: '請求超時',
            429: '請求過於頻繁，請稍後再試',
            500: '伺服器內部錯誤',
            502: '網關錯誤',
            503: '服務暫時不可用',
            504: '網關超時',
            0: '網路連線錯誤'
        };

        return messages[status] || `未知錯誤 (${status})`;
    }

    // 獲取 Fetch 錯誤消息
    getFetchErrorMessage(status) {
        return this.getAjaxErrorMessage(status);
    }

    // 記錄錯誤
    logError(error) {
        this.errors.push(error);
        
        // 限制錯誤數量
        if (this.errors.length > this.maxErrors) {
            this.errors.shift();
        }

        // 控制台輸出 (只在開發環境)
        if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
            console.error('Error captured:', error);
        }

        // 發送到伺服器（可選）
        this.sendErrorToServer(error);
    }

    // 發送錯誤到伺服器
    sendErrorToServer(error) {
        // 只在生產環境發送
        if (window.location.hostname === 'localhost') {
            return;
        }

        // 使用 beacon API 或 fetch 發送
        if (navigator.sendBeacon) {
            navigator.sendBeacon('/api/errors/', JSON.stringify(error));
        } else {
            fetch('/api/errors/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(error)
            }).catch(() => {
                // 忽略發送錯誤的錯誤
            });
        }
    }

    // 顯示通知
    showNotification(title, message, type = 'info', duration = 5000) {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.style.cssText = `
            background: ${this.getNotificationColor(type)};
            color: white;
            padding: 15px 20px;
            border-radius: 5px;
            margin-bottom: 10px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.2);
            max-width: 350px;
            pointer-events: auto;
            cursor: pointer;
            transform: translateX(100%);
            transition: transform 0.3s ease;
        `;

        notification.innerHTML = `
            <div style="font-weight: bold; margin-bottom: 5px;">${title}</div>
            <div style="font-size: 14px; opacity: 0.9;">${message}</div>
            <div style="position: absolute; top: 5px; right: 10px; font-size: 18px; cursor: pointer;">&times;</div>
        `;

        // 關閉按鈕
        const closeBtn = notification.querySelector('div:last-child');
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.hideNotification(notification);
        });

        // 點擊展開詳情
        notification.addEventListener('click', () => {
            this.showErrorDetails(message);
        });

        this.notificationContainer.appendChild(notification);

        // 動畫顯示
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);

        // 自動隱藏
        setTimeout(() => {
            this.hideNotification(notification);
        }, duration);
    }

    // 隱藏通知
    hideNotification(notification) {
        notification.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 300);
    }

    // 獲取通知顏色
    getNotificationColor(type) {
        const colors = {
            error: '#dc3545',
            warning: '#ffc107',
            info: '#17a2b8',
            success: '#28a745'
        };
        return colors[type] || colors.info;
    }

    // 顯示錯誤詳情
    showErrorDetails(message) {
        const modal = document.createElement('div');
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 10001;
        `;

        const content = document.createElement('div');
        content.style.cssText = `
            background: white;
            padding: 20px;
            border-radius: 8px;
            max-width: 600px;
            max-height: 80vh;
            overflow-y: auto;
            margin: 20px;
        `;

        content.innerHTML = `
            <h3>錯誤詳情</h3>
            <p>${message}</p>
            <div style="margin-top: 20px; text-align: right;">
                <button onclick="this.closest('.modal').remove()" style="padding: 8px 16px; border: none; background: #007bff; color: white; border-radius: 4px; cursor: pointer;">
                    關閉
                </button>
            </div>
        `;

        modal.className = 'modal';
        modal.appendChild(content);
        document.body.appendChild(modal);

        // 點擊遮罩關閉
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });
    }

    // 手動報告錯誤
    reportError(message, type = 'manual') {
        const error = {
            type: type,
            message: message,
            timestamp: new Date().toISOString(),
            url: window.location.href,
            userAgent: navigator.userAgent
        };

        this.logError(error);
        this.showNotification('錯誤報告', message, 'error');
    }

    // 獲取錯誤統計
    getErrorStats() {
        const stats = {
            total: this.errors.length,
            byType: {},
            recent: this.errors.slice(-10)
        };

        this.errors.forEach(error => {
            stats.byType[error.type] = (stats.byType[error.type] || 0) + 1;
        });

        return stats;
    }

    // 清除錯誤記錄
    clearErrors() {
        this.errors = [];
    }
}

// 創建全局錯誤處理器
window.errorHandler = new ErrorHandler();

// 提供便捷方法
window.reportError = function(message, type = 'manual') {
    window.errorHandler.reportError(message, type);
};

// 表單驗證錯誤處理
function handleFormErrors(form, errors) {
    // 清除之前的錯誤
    form.querySelectorAll('.error-message').forEach(el => el.remove());
    form.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));

    // 顯示新錯誤
    for (const [field, messages] of Object.entries(errors)) {
        const input = form.querySelector(`[name="${field}"]`);
        if (input) {
            input.classList.add('is-invalid');
            
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message text-danger mt-1';
            errorDiv.innerHTML = messages.join('<br>');
            
            input.parentNode.appendChild(errorDiv);
        }
    }
}

// 導出便捷方法
window.handleFormErrors = handleFormErrors;

// 網路狀態監控
function monitorNetworkStatus() {
    function updateNetworkStatus() {
        if (!navigator.onLine) {
            window.errorHandler.showNotification(
                '網路連線中斷',
                '請檢查您的網路連線',
                'warning',
                10000
            );
        }
    }

    window.addEventListener('online', () => {
        window.errorHandler.showNotification(
            '網路已連線',
            '網路連線已恢復',
            'success',
            3000
        );
    });

    window.addEventListener('offline', updateNetworkStatus);
}

// 初始化網路監控
document.addEventListener('DOMContentLoaded', monitorNetworkStatus);

// 提供重試機制
function retryRequest(requestFunc, maxRetries = 3, delay = 1000) {
    return new Promise((resolve, reject) => {
        let retries = 0;
        
        function attempt() {
            requestFunc()
                .then(resolve)
                .catch(error => {
                    retries++;
                    if (retries < maxRetries) {
                        setTimeout(attempt, delay * retries);
                    } else {
                        reject(error);
                    }
                });
        }
        
        attempt();
    });
}

// 導出重試方法
window.retryRequest = retryRequest;