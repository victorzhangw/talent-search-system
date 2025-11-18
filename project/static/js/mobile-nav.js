// 移動端導航優化

document.addEventListener('DOMContentLoaded', function() {
    // 移動端導航初始化
    initMobileNavigation();
    
    // 響應式處理
    handleResponsiveLayout();
    
    // 觸摸手勢支持
    initTouchGestures();
});

function initMobileNavigation() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    const toggleButton = document.querySelector('.sidebar-toggle');
    
    if (!sidebar || !mainContent || !toggleButton) {
        return;
    }
    
    // 移動端側邊欄控制
    function toggleSidebar() {
        const isOpen = sidebar.classList.contains('show');
        
        if (isOpen) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }
    
    function openSidebar() {
        sidebar.classList.add('show');
        
        // 添加遮罩
        const overlay = document.createElement('div');
        overlay.className = 'sidebar-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.5);
            z-index: 1040;
            display: none;
        `;
        
        // 遮罩點擊關閉
        overlay.addEventListener('click', closeSidebar);
        
        document.body.appendChild(overlay);
        
        // 動畫顯示遮罩
        setTimeout(() => {
            overlay.style.display = 'block';
        }, 10);
        
        // 防止背景滾動
        document.body.style.overflow = 'hidden';
    }
    
    function closeSidebar() {
        sidebar.classList.remove('show');
        
        // 移除遮罩
        const overlay = document.querySelector('.sidebar-overlay');
        if (overlay) {
            overlay.remove();
        }
        
        // 恢復背景滾動
        document.body.style.overflow = '';
    }
    
    // 綁定切換按鈕
    toggleButton.addEventListener('click', toggleSidebar);
    
    // 窗口大小變化時的處理
    window.addEventListener('resize', function() {
        if (window.innerWidth >= 992) {
            closeSidebar();
        }
    });
    
    // 導航項點擊處理
    const navLinks = sidebar.querySelectorAll('.nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            // 在移動端點擊導航項後關閉側邊欄
            if (window.innerWidth < 992) {
                setTimeout(closeSidebar, 100);
            }
        });
    });
}

function handleResponsiveLayout() {
    // 響應式表格處理
    const tables = document.querySelectorAll('.table');
    tables.forEach(table => {
        if (!table.parentElement.classList.contains('table-responsive')) {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        }
    });
    
    // 響應式卡片處理
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        if (window.innerWidth < 768) {
            card.classList.add('mobile-card');
        } else {
            card.classList.remove('mobile-card');
        }
    });
    
    // 響應式按鈕組處理
    const buttonGroups = document.querySelectorAll('.btn-group');
    buttonGroups.forEach(group => {
        if (window.innerWidth < 576) {
            group.classList.add('btn-group-vertical');
            group.classList.remove('btn-group');
        } else {
            group.classList.add('btn-group');
            group.classList.remove('btn-group-vertical');
        }
    });
    
    // 窗口大小變化時重新處理
    window.addEventListener('resize', debounce(function() {
        cards.forEach(card => {
            if (window.innerWidth < 768) {
                card.classList.add('mobile-card');
            } else {
                card.classList.remove('mobile-card');
            }
        });
        
        buttonGroups.forEach(group => {
            if (window.innerWidth < 576) {
                group.classList.add('btn-group-vertical');
                group.classList.remove('btn-group');
            } else {
                group.classList.add('btn-group');
                group.classList.remove('btn-group-vertical');
            }
        });
    }, 250));
}

function initTouchGestures() {
    const sidebar = document.querySelector('.sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (!sidebar || !mainContent) {
        return;
    }
    
    let startX = 0;
    let startY = 0;
    let currentX = 0;
    let currentY = 0;
    let isDragging = false;
    
    // 觸摸開始
    document.addEventListener('touchstart', function(e) {
        startX = e.touches[0].clientX;
        startY = e.touches[0].clientY;
        isDragging = false;
    });
    
    // 觸摸移動
    document.addEventListener('touchmove', function(e) {
        if (!e.touches[0]) return;
        
        currentX = e.touches[0].clientX;
        currentY = e.touches[0].clientY;
        
        const deltaX = currentX - startX;
        const deltaY = currentY - startY;
        
        // 判斷是否為水平滑動
        if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 10) {
            isDragging = true;
        }
    });
    
    // 觸摸結束
    document.addEventListener('touchend', function(e) {
        if (!isDragging) return;
        
        const deltaX = currentX - startX;
        const threshold = 50;
        
        // 從左邊緣向右滑動打開側邊欄
        if (startX < 20 && deltaX > threshold) {
            if (!sidebar.classList.contains('show')) {
                sidebar.classList.add('show');
                document.body.style.overflow = 'hidden';
            }
        }
        
        // 從任何位置向左滑動關閉側邊欄
        if (deltaX < -threshold && sidebar.classList.contains('show')) {
            sidebar.classList.remove('show');
            document.body.style.overflow = '';
            
            const overlay = document.querySelector('.sidebar-overlay');
            if (overlay) {
                overlay.remove();
            }
        }
        
        isDragging = false;
    });
}

// 防抖函數
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// 移動端特定的 CSS 類
function addMobileStyles() {
    const style = document.createElement('style');
    style.textContent = `
        @media (max-width: 767.98px) {
            .mobile-card {
                margin-bottom: 1rem;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            
            .mobile-card .card-body {
                padding: 1rem;
            }
            
            .mobile-card .card-header {
                padding: 0.75rem 1rem;
                font-size: 0.9rem;
            }
            
            .btn-group-vertical .btn {
                margin-bottom: 0.25rem;
            }
            
            .btn-group-vertical .btn:last-child {
                margin-bottom: 0;
            }
            
            .table-responsive {
                border: none;
                font-size: 0.875rem;
            }
            
            .table-responsive .table th,
            .table-responsive .table td {
                padding: 0.5rem;
                white-space: nowrap;
            }
            
            .sidebar.show {
                transform: translateX(0);
                box-shadow: 2px 0 5px rgba(0,0,0,0.1);
            }
            
            .sidebar-overlay {
                animation: fadeIn 0.3s ease;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; }
                to { opacity: 1; }
            }
        }
        
        @media (max-width: 575.98px) {
            .container-fluid {
                padding-left: 10px;
                padding-right: 10px;
            }
            
            .row {
                margin-left: -5px;
                margin-right: -5px;
            }
            
            .row > [class*="col-"] {
                padding-left: 5px;
                padding-right: 5px;
            }
            
            .btn {
                font-size: 0.875rem;
                padding: 0.5rem 0.75rem;
            }
            
            .btn-sm {
                font-size: 0.8rem;
                padding: 0.4rem 0.6rem;
            }
            
            .form-control {
                font-size: 16px; /* 防止 iOS 縮放 */
            }
            
            .modal-dialog {
                margin: 0.5rem;
            }
            
            .modal-header {
                padding: 0.75rem 1rem;
            }
            
            .modal-body {
                padding: 1rem;
            }
            
            .modal-footer {
                padding: 0.75rem 1rem;
            }
        }
    `;
    
    document.head.appendChild(style);
}

// 添加移動端樣式
addMobileStyles();

// 虛擬視窗處理（解決移動端 100vh 問題）
function handleViewportHeight() {
    const vh = window.innerHeight * 0.01;
    document.documentElement.style.setProperty('--vh', `${vh}px`);
}

// 初始化和窗口大小變化時更新
handleViewportHeight();
window.addEventListener('resize', debounce(handleViewportHeight, 250));

// 處理移動端輸入框焦點問題
document.addEventListener('focusin', function(e) {
    if (e.target.matches('input, textarea, select')) {
        // 延遲處理，確保虛擬鍵盤已經彈出
        setTimeout(() => {
            e.target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }, 300);
    }
});

// 移動端下拉選單處理 - 只處理移動端
document.addEventListener('DOMContentLoaded', function() {
    // 只在移動端處理下拉選單
    if (window.innerWidth <= 767) {
        const dropdowns = document.querySelectorAll('.dropdown');
        
        dropdowns.forEach(dropdown => {
            const toggle = dropdown.querySelector('.dropdown-toggle');
            const menu = dropdown.querySelector('.dropdown-menu');
            
            if (toggle && menu) {
                toggle.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // 關閉其他下拉選單
                    dropdowns.forEach(other => {
                        if (other !== dropdown) {
                            other.querySelector('.dropdown-menu')?.classList.remove('show');
                        }
                    });
                    
                    // 切換當前下拉選單
                    menu.classList.toggle('show');
                });
            }
        });
        
        // 點擊外部關閉下拉選單
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.dropdown')) {
                dropdowns.forEach(dropdown => {
                    dropdown.querySelector('.dropdown-menu')?.classList.remove('show');
                });
            }
        });
    }
});

// 移動端優化的載入提示
function showMobileLoader(message = '載入中...') {
    const loader = document.createElement('div');
    loader.className = 'mobile-loader';
    loader.innerHTML = `
        <div class="mobile-loader-content">
            <div class="mobile-loader-spinner"></div>
            <div class="mobile-loader-text">${message}</div>
        </div>
    `;
    
    loader.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(255, 255, 255, 0.9);
        z-index: 10000;
        display: flex;
        justify-content: center;
        align-items: center;
    `;
    
    const content = loader.querySelector('.mobile-loader-content');
    content.style.cssText = `
        text-align: center;
        padding: 20px;
    `;
    
    const spinner = loader.querySelector('.mobile-loader-spinner');
    spinner.style.cssText = `
        width: 40px;
        height: 40px;
        border: 4px solid #f3f3f3;
        border-top: 4px solid #007bff;
        border-radius: 50%;
        animation: spin 1s linear infinite;
        margin: 0 auto 15px;
    `;
    
    const text = loader.querySelector('.mobile-loader-text');
    text.style.cssText = `
        color: #666;
        font-size: 14px;
    `;
    
    document.body.appendChild(loader);
    
    return loader;
}

function hideMobileLoader() {
    const loader = document.querySelector('.mobile-loader');
    if (loader) {
        loader.remove();
    }
}

// 導出便捷方法
window.showMobileLoader = showMobileLoader;
window.hideMobileLoader = hideMobileLoader;