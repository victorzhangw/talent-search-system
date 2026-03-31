import fs from 'fs';
import path from 'path';
import crypto from 'crypto';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// 1. 設定路徑
const distDir = path.join(__dirname, 'dist');
const releasesDir = path.join(__dirname, 'releases');

// 2. 建立帶有時間戳的子資料夾名稱 (格式: YYYYMMDD_HHMMSS)
const now = new Date();
const timestamp = now.getFullYear().toString() +
  (now.getMonth() + 1).toString().padStart(2, '0').slice(-2) +
  now.getDate().toString().padStart(2, '0').slice(-2) + '_' +
  now.getHours().toString().padStart(2, '0').slice(-2) +
  now.getMinutes().toString().padStart(2, '0').slice(-2) +
  now.getSeconds().toString().padStart(2, '0').slice(-2);

const targetDir = path.join(releasesDir, timestamp);

// 3. 計算特定檔案的 SHA-384 雜湊值
function getSRI(filePath) {
  const content = fs.readFileSync(filePath);
  const hash = crypto.createHash('sha384').update(content).digest('base64');
  return `sha384-${hash}`;
}

async function run() {
  try {
    // 檢查 dist 是否存在
    if (!fs.existsSync(distDir)) {
        console.error('❌ 找不到 dist 目錄，請先執行 npm run build');
        process.exit(1);
    }

    // 確保 releases 目錄存在
    if (!fs.existsSync(releasesDir)) {
        fs.mkdirSync(releasesDir, { recursive: true });
    }
    
    // 建立本次發布的子資料夾
    fs.mkdirSync(targetDir, { recursive: true });

    console.log(`\n🚀 正在建立部署包: ${targetDir}`);

    // 定義要處理的關鍵檔案 (由 vite.config.js 定義的檔名)
    const filesToHash = ['loader.iife.js', 'loader.css'];
    let integrityInfo = `Release Version: ${timestamp}\n`;
    integrityInfo += `Generated At: ${now.toLocaleString('zh-TW', { hour12: false })}\n`;
    integrityInfo += `------------------------------------------\n\n`;

    // 複製 dist 到目標資料夾並計算雜湊
    const items = fs.readdirSync(distDir);
    for (const item of items) {
      const srcPath = path.join(distDir, item);
      const destPath = path.join(targetDir, item);

      // 複製檔案/資料夾
      if (fs.lstatSync(srcPath).isDirectory()) {
         fs.cpSync(srcPath, destPath, { recursive: true });
      } else {
        fs.copyFileSync(srcPath, destPath);
        
        // 如果是指定的檔案，計算 SRI
        if (filesToHash.includes(item)) {
          const sri = getSRI(srcPath);
          integrityInfo += `File: ${item}\nSRI: ${sri}\n\n`;
          console.log(`✅ ${item} -> ${sri}`);
        }
      }
    }

    // 寫入 SRI 資訊到 txt
    fs.writeFileSync(path.join(targetDir, 'integrity_hashes.txt'), integrityInfo);
    console.log(`📝 已產出 integrity_hashes.txt`);
    console.log(`✨ 部署包製作完成！可以直接上傳 ${timestamp} 資料夾至伺服器。\n`);

  } catch (err) {
    console.error('❌ 產出部署包時發生錯誤:', err);
    process.exit(1);
  }
}

run();
