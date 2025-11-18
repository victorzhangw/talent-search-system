// 用戶引導系統

class UserGuide {
    constructor() {
        this.steps = [];
        this.currentStep = 0;
        this.isActive = false;
        this.overlay = null;
        this.tooltip = null;
        this.storageKey = 'user_guide_completed';
    }

    // 初始化引導系統
    init() {
        this.createOverlay();
        this.createTooltip();
        this.bindEvents();
    }

    // 創建遮罩層
    createOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.className = 'user-guide-overlay';
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 9998;
            display: none;
        `;
        document.body.appendChild(this.overlay);
    }

    // 創建提示框
    createTooltip() {
        this.tooltip = document.createElement('div');
        this.tooltip.className = 'user-guide-tooltip';
        this.tooltip.style.cssText = `
            position: absolute;
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            z-index: 9999;
            max-width: 320px;
            display: none;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
        `;
        document.body.appendChild(this.tooltip);
    }

    // 綁定事件
    bindEvents() {
        // ESC 鍵關閉引導
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isActive) {
                this.stop();
            }
        });

        // 遮罩點擊關閉
        this.overlay.addEventListener('click', (e) => {
            if (e.target === this.overlay) {
                this.stop();
            }
        });
    }

    // 添加引導步驟
    addStep(options) {
        const step = {
            element: options.element,
            title: options.title,
            content: options.content,
            position: options.position || 'bottom',
            action: options.action || null,
            highlight: options.highlight !== false,
            ...options
        };
        this.steps.push(step);
        return this;
    }

    // 開始引導
    start() {
        if (this.isCompleted()) {
            return;
        }

        this.isActive = true;
        this.currentStep = 0;
        this.showStep(0);
    }

    // 顯示指定步驟
    showStep(index) {
        if (index >= this.steps.length) {
            this.complete();
            return;
        }

        const step = this.steps[index];
        const element = typeof step.element === 'string' 
            ? document.querySelector(step.element) 
            : step.element;

        if (!element) {
            console.warn(`引導步驟 ${index + 1} 的元素未找到:`, step.element);
            this.nextStep();
            return;
        }

        // 顯示遮罩
        this.overlay.style.display = 'block';

        // 高亮元素
        if (step.highlight) {
            this.highlightElement(element);
        }

        // 顯示提示框
        this.showTooltip(element, step);

        // 執行步驟動作
        if (step.action) {
            step.action(element);
        }

        // 滾動到元素
        this.scrollToElement(element);
    }

    // 高亮元素
    highlightElement(element) {
        // 移除之前的高亮
        this.removeHighlight();

        // 創建高亮遮罩
        const rect = element.getBoundingClientRect();
        const highlight = document.createElement('div');
        highlight.className = 'user-guide-highlight';
        highlight.style.cssText = `
            position: fixed;
            top: ${rect.top - 4}px;
            left: ${rect.left - 4}px;
            width: ${rect.width + 8}px;
            height: ${rect.height + 8}px;
            border: 2px solid #007bff;
            border-radius: 4px;
            box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5);
            z-index: 9999;
            pointer-events: none;
        `;
        document.body.appendChild(highlight);
    }

    // 移除高亮
    removeHighlight() {
        const existing = document.querySelector('.user-guide-highlight');
        if (existing) {
            existing.remove();
        }
    }

    // 顯示提示框
    showTooltip(element, step) {
        const rect = element.getBoundingClientRect();
        
        // 設置提示框內容
        this.tooltip.innerHTML = `
            <div class="guide-header">
                <h4 style="margin: 0 0 10px 0; color: #333; font-size: 16px; font-weight: 600;">
                    ${step.title}
                </h4>
            </div>
            <div class="guide-content">
                <p style="margin: 0 0 15px 0; color: #666; font-size: 14px; line-height: 1.5;">
                    ${step.content}
                </p>
            </div>
            <div class="guide-footer" style="display: flex; justify-content: space-between; align-items: center;">
                <span style="color: #999; font-size: 12px;">
                    ${this.currentStep + 1} / ${this.steps.length}
                </span>
                <div class="guide-buttons">
                    ${this.currentStep > 0 ? '<button class="guide-btn guide-prev" style="margin-right: 8px;">上一步</button>' : ''}
                    ${this.currentStep < this.steps.length - 1 ? '<button class="guide-btn guide-next">下一步</button>' : '<button class="guide-btn guide-finish">完成</button>'}
                    <button class="guide-btn guide-skip" style="margin-left: 8px;">跳過</button>
                </div>
            </div>
        `;

        // 設置按鈕樣式
        const buttons = this.tooltip.querySelectorAll('.guide-btn');
        buttons.forEach(btn => {
            btn.style.cssText = `
                padding: 6px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
                color: #333;
                font-size: 12px;
                cursor: pointer;
                transition: all 0.2s;
            `;
            
            if (btn.classList.contains('guide-next') || btn.classList.contains('guide-finish')) {
                btn.style.backgroundColor = '#007bff';
                btn.style.color = 'white';
                btn.style.borderColor = '#007bff';
            }
            
            btn.addEventListener('mouseover', () => {
                btn.style.opacity = '0.8';
            });
            
            btn.addEventListener('mouseout', () => {
                btn.style.opacity = '1';
            });
        });

        // 綁定按鈕事件
        const prevBtn = this.tooltip.querySelector('.guide-prev');
        const nextBtn = this.tooltip.querySelector('.guide-next');
        const finishBtn = this.tooltip.querySelector('.guide-finish');
        const skipBtn = this.tooltip.querySelector('.guide-skip');

        if (prevBtn) {
            prevBtn.addEventListener('click', () => this.prevStep());
        }
        if (nextBtn) {
            nextBtn.addEventListener('click', () => this.nextStep());
        }
        if (finishBtn) {
            finishBtn.addEventListener('click', () => this.complete());
        }
        if (skipBtn) {
            skipBtn.addEventListener('click', () => this.stop());
        }

        // 計算提示框位置
        this.positionTooltip(rect, step.position);
        
        // 顯示提示框
        this.tooltip.style.display = 'block';
    }

    // 定位提示框
    positionTooltip(rect, position) {
        let top, left;
        
        switch (position) {
            case 'top':
                top = rect.top - this.tooltip.offsetHeight - 10;
                left = rect.left + (rect.width - this.tooltip.offsetWidth) / 2;
                break;
            case 'bottom':
                top = rect.bottom + 10;
                left = rect.left + (rect.width - this.tooltip.offsetWidth) / 2;
                break;
            case 'left':
                top = rect.top + (rect.height - this.tooltip.offsetHeight) / 2;
                left = rect.left - this.tooltip.offsetWidth - 10;
                break;
            case 'right':
                top = rect.top + (rect.height - this.tooltip.offsetHeight) / 2;
                left = rect.right + 10;
                break;
            default:
                top = rect.bottom + 10;
                left = rect.left + (rect.width - this.tooltip.offsetWidth) / 2;
        }

        // 確保提示框在視窗內
        const margin = 10;
        const maxLeft = window.innerWidth - this.tooltip.offsetWidth - margin;
        const maxTop = window.innerHeight - this.tooltip.offsetHeight - margin;

        left = Math.max(margin, Math.min(left, maxLeft));
        top = Math.max(margin, Math.min(top, maxTop));

        this.tooltip.style.left = left + 'px';
        this.tooltip.style.top = top + 'px';
    }

    // 滾動到元素
    scrollToElement(element) {
        const rect = element.getBoundingClientRect();
        const isVisible = rect.top >= 0 && rect.bottom <= window.innerHeight;
        
        if (!isVisible) {
            element.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'center' 
            });
        }
    }

    // 下一步
    nextStep() {
        this.currentStep++;
        this.showStep(this.currentStep);
    }

    // 上一步
    prevStep() {
        this.currentStep--;
        this.showStep(this.currentStep);
    }

    // 完成引導
    complete() {
        this.markAsCompleted();
        this.stop();
        this.onComplete();
    }

    // 停止引導
    stop() {
        this.isActive = false;
        this.overlay.style.display = 'none';
        this.tooltip.style.display = 'none';
        this.removeHighlight();
    }

    // 標記為已完成
    markAsCompleted() {
        localStorage.setItem(this.storageKey, 'true');
    }

    // 檢查是否已完成
    isCompleted() {
        return localStorage.getItem(this.storageKey) === 'true';
    }

    // 重置引導狀態
    reset() {
        localStorage.removeItem(this.storageKey);
    }

    // 完成回調
    onComplete() {
        // 可以在這裡添加完成後的邏輯
        console.log('用戶引導完成');
    }
}

// 創建全局引導實例
window.userGuide = new UserGuide();

// 頁面載入後初始化
document.addEventListener('DOMContentLoaded', () => {
    window.userGuide.init();
});

// 通用引導配置
const GuideConfigs = {
    // 儀表板引導
    dashboard: {
        init() {
            const guide = new UserGuide();
            guide.init();
            
            guide.addStep({
                element: '.welcome-banner',
                title: '歡迎使用測驗管理系統',
                content: '這是您的個人儀表板，可以查看重要統計資訊和快速操作。'
            });
            
            guide.addStep({
                element: '.dashboard-card:first-child',
                title: '統計卡片',
                content: '這些卡片顯示您的測驗統計資訊，包括邀請數、完成數等。'
            });
            
            guide.addStep({
                element: '.quick-action-btn:first-child',
                title: '快速操作',
                content: '使用這些按鈕可以快速執行常用操作。'
            });
            
            if (document.querySelector('.chart-container')) {
                guide.addStep({
                    element: '.chart-container',
                    title: '趨勢圖表',
                    content: '這裡顯示您的測驗數據趨勢，幫助您瞭解使用情況。'
                });
            }
            
            return guide;
        }
    },
    
    // 邀請管理引導
    invitations: {
        init() {
            const guide = new UserGuide();
            guide.init();
            
            guide.addStep({
                element: '.btn-primary',
                title: '創建邀請',
                content: '點擊此按鈕開始創建新的測驗邀請。'
            });
            
            guide.addStep({
                element: '.table',
                title: '邀請列表',
                content: '這裡顯示所有的測驗邀請，您可以查看狀態和管理邀請。'
            });
            
            return guide;
        }
    },
    
    // 統計分析引導
    statistics: {
        init() {
            const guide = new UserGuide();
            guide.init();
            
            guide.addStep({
                element: '.filter-form',
                title: '篩選條件',
                content: '使用篩選器來自定義您要查看的統計數據。'
            });
            
            guide.addStep({
                element: '#trendChart',
                title: '趨勢圖',
                content: '這個圖表顯示您的測驗數據隨時間的變化趨勢。'
            });
            
            guide.addStep({
                element: '#statusChart',
                title: '狀態分佈',
                content: '此圖表顯示不同狀態的測驗邀請分佈情況。'
            });
            
            return guide;
        }
    }
};

// 導出配置
window.GuideConfigs = GuideConfigs;