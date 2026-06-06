# TG-StickerKit - Telegram 貼圖自動化工具組

這套工具旨在幫助你快速、高品質地將普通圖片、影片以及 **LINE 貼圖 & Emoji** 轉換為 Telegram 貼圖，並透過 API 實現自動化批次上傳。

---

## 📂 檔案結構 (模組化整理)

- **`scripts/`**: 存放所有核心 Python 程式碼。
  - `main_workflow.py`: **一鍵全自動化工作流 (推薦使用)**。
  - **`core/`**: 核心處理邏輯
    - `line_sticker_downloader.py`: LINE 貼圖/Emoji 自動下載器 (具備併發控制與網路重試)。
    - `sticker_processor.py`: 靜態圖片處理與縮放。
    - `video_sticker_processor.py`: 影片貼圖處理 (FFmpeg 轉 WebM，最佳化畫質)。
  - **`telegram/`**: Telegram API 互動
    - `tg_sticker_upload.py`: 靜態貼圖上傳 (支援自動處理頻率限制)。
    - `tg_video_sticker_upload.py`: 影片貼圖上傳。
    - `tg_compat.py`: API 相容層與 Monkey Patch 防護。
  - **`utils/`**: 共用工具
    - `config_utils.py`: 環境變數與組態安全驗證。
    - `path_utils.py`: 統一路徑管理與安全目錄清理。
    - `line_utils.py`: LINE API URL 模板、產品 ID 解析與資源解析（支援貼圖 + Emoji）。
- **`workspace/`**: 存放貼圖素材的工作區。
  - `static/`: 靜態貼圖的 `input/` 與 `output/`。
  - `video/`: 影片貼圖的 `input/` 與 `output/`。
- **`config/`**: 存放設定檔與私密憑證。
  - `.env`: API 金鑰與敏感資訊。
  - `config.json`: 貼圖包資訊配置檔 (自動化腳本會自動更新此檔)。
  - `sticker_session.session`: Telegram 登入憑證。

---

## 🛠️ 環境準備

1. **安裝 Python**: 確保電腦已安裝 Python 3.8+。

2. **安裝必要套件**:
   
   ```powershell
   pip install Pillow telethon python-dotenv aiohttp
   ```

3. **安裝 FFmpeg**: 影片貼圖處理需要系統中已安裝 `ffmpeg`。

---

## 🚀 使用步驟

### 【推薦】一鍵全自動化流程 (LINE 貼圖 / Emoji 專用)

這是最簡單的方式，腳本會自動處理下載、分類、轉檔、更新配置與上傳。

1. 執行主工作流腳本：
   
   ```powershell
   python scripts/main_workflow.py
   ```

2. **輸入資訊**: 依提示輸入 LINE 貼圖/Emoji 的 ID 或完整網址。

3. **自動化執行**: 
   
   - 腳本會自動判斷貼圖類型。
   - 自動從 LINE 獲取繁體中文標題作為貼圖包名稱。
   - 自動完成轉檔與上傳。

4. **完成**: 直接獲得 Telegram 貼圖包連結。

---

### 【手動】自訂素材流程

如果你有自己的圖片或影片想做成貼圖：

1. **處理素材**: 將檔案放入 `workspace/` 對應類型的 `input/` 中。
2. **執行轉檔**: 執行 `scripts/sticker_processor.py` (靜態) 或 `scripts/video_sticker_processor.py` (影片)。
3. **設定配置**: 編輯 `config/config.json` 手動設定貼圖包標題。
4. **執行上傳**: 執行 `scripts/tg_sticker_upload.py` (靜態) 或 `scripts/tg_video_sticker_upload.py` (影片)。

---

## ⚠️ 注意事項

- **安全性**: `config/` 資料夾內的檔案包含個人機密資訊，**請勿外流**。
- **驗證碼**: 第一次執行上傳時，請在視窗中輸入 Telegram 發送給你的驗證碼。
- **規範**: 影片貼圖必須符合 3 秒內、無聲且為 WebM 格式，本工具已自動幫你處理。
