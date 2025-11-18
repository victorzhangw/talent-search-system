# 測試 API v2.1 智能搜索功能
# 使用 PowerShell 腳本測試

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "測試 API v2.1 智能搜索功能" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# 1. 測試健康檢查
Write-Host "[測試 1] 健康檢查..." -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get
    Write-Host "✓ 狀態: $($health.status)" -ForegroundColor Green
    Write-Host "✓ 數據庫: $($health.database)" -ForegroundColor Green
    Write-Host "✓ 特質數量: $($health.traits_loaded)" -ForegroundColor Green
    Write-Host "✓ LLM 啟用: $($health.llm_enabled)" -ForegroundColor Green
    Write-Host "✓ 版本: $($health.version)" -ForegroundColor Green
    
    if ($health.version -ne "2.1.0") {
        Write-Host "⚠️ 警告: 版本不是 2.1.0，可能使用了舊版本" -ForegroundColor Red
    }
} catch {
    Write-Host "❌ 健康檢查失敗: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. 測試搜索功能
Write-Host "[測試 2] 智能搜索..." -ForegroundColor Yellow

$testQueries = @(
    @{query="find communication skills"; name="英文查詢"},
    @{query="leadership"; name="簡單英文"},
    @{query="analytical thinking"; name="分析思考"}
)

foreach ($test in $testQueries) {
    Write-Host ""
    Write-Host "  查詢: $($test.query) ($($test.name))" -ForegroundColor Cyan
    
    try {
        $body = @{query=$test.query} | ConvertTo-Json
        $result = Invoke-RestMethod -Uri "http://localhost:8000/api/search" `
                                    -Method Post `
                                    -ContentType "application/json" `
                                    -Body $body
        
        Write-Host "  ✓ 找到候選人: $($result.total)" -ForegroundColor Green
        Write-Host "  ✓ 返回候選人: $($result.candidates.Count)" -ForegroundColor Green
        
        if ($result.total -eq $result.candidates.Count) {
            Write-Host "  ✓ 數量一致！" -ForegroundColor Green
        } else {
            Write-Host "  ❌ 數量不一致！Total: $($result.total), Count: $($result.candidates.Count)" -ForegroundColor Red
        }
        
        if ($result.total -lt 27) {
            Write-Host "  ✓ 智能匹配生效（不是返回全部 27 人）" -ForegroundColor Green
        } else {
            Write-Host "  ⚠️ 返回了全部候選人，可能沒有匹配到特質" -ForegroundColor Yellow
        }
        
    } catch {
        Write-Host "  ❌ 搜索失敗: $_" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "測試完成！" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "📝 注意事項:" -ForegroundColor Yellow
Write-Host "  • PowerShell 中文查詢會顯示亂碼，但不影響功能" -ForegroundColor Yellow
Write-Host "  • 請在瀏覽器中測試中文查詢" -ForegroundColor Yellow
Write-Host "  • 訪問: http://localhost:8080/talent-chat-frontend.html" -ForegroundColor Yellow
Write-Host ""
