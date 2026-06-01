import os
import sys
import json
import asyncio
import aiohttp

# 將腳本根目錄加入路徑以便匯入子模組
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.path_utils import WORKSPACE_DIR, CONFIG_PATH, clear_directory
from core.line_sticker_downloader import LineDownloader
from core.sticker_processor import process_stickers_to_512
from core.video_sticker_processor import process_video_stickers

def update_config(is_video, title, pack_id):
    """更新 config.json 中的貼圖包設定"""
    if not os.path.exists(CONFIG_PATH):
        print(f"[-] 錯誤：找不到 config.json ({CONFIG_PATH})")
        return False
    
    with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    key = "video" if is_video else "static"
    short_name = f"xinooo_stickerkit_line{pack_id}"
    
    if key not in config:
        config[key] = {}
        
    config[key]["pack_title"] = title
    config[key]["pack_short_name"] = short_name
    
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=4, ensure_ascii=False)
    
    print(f"[+] Config 已更新: {title} ({short_name})")
    return True

async def run_step(name, cmd, cwd=None):
    """執行子程序並直接在當前終端顯示即時輸出"""
    print(f"\n>>> 正在執行: {name}")
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd
    )
    return_code = await process.wait()
    
    if return_code != 0:
        print(f"\n[-] {name} 執行失敗，離開代碼: {return_code}")
    
    return return_code == 0

async def main_workflow():
    print("="*40)
    print(" LINE to Telegram 一鍵全自動化工作流 ")
    print("="*40)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    url_or_id = input("請輸入 LINE 貼圖連結或 ID: ").strip()
    if not url_or_id:
        return

    downloader = LineDownloader(WORKSPACE_DIR)
    product_id = downloader.extract_product_id(url_or_id)
    
    async with aiohttp.ClientSession() as session:
        print(f"[*] 正在獲取元數據 (ID: {product_id})...")
        meta = await downloader.fetch_meta(session, product_id)
        if not meta:
            print("[-] 無法獲取元數據，流程中止。")
            return

        # 提取資訊
        title = meta.get('title', {}).get('zh-Hant', meta.get('title', {}).get('en', product_id))
        has_animation = meta.get('hasAnimation', False)
        sticker_type = meta.get('stickerResourceType', 'STATIC')
        is_video = has_animation or sticker_type in ['ANIMATION', 'ANIMATION_SOUND', 'POPUP', 'POPUP_SOUND']
        
        print(f"[+] 貼圖名稱: {title}")
        print(f"[+] 類型: {'影片/動態' if is_video else '靜態'}")

        # 1. 清理舊檔案
        try:
            if is_video:
                clear_directory(os.path.join(WORKSPACE_DIR, "video", "input"))
                clear_directory(os.path.join(WORKSPACE_DIR, "video", "output"))
            else:
                clear_directory(os.path.join(WORKSPACE_DIR, "static", "input"))
                clear_directory(os.path.join(WORKSPACE_DIR, "static", "output"))
        except ValueError as e:
            print(f"[-] 清理目錄時出錯: {e}")
            return

        # 2. 執行下載
        await downloader.run(url_or_id)

        # 3. 更新設定
        update_config(is_video, title, product_id)

        # 4. 執行轉檔處理
        print(f"\n[*] 正在開始轉檔處理...")
        try:
            if is_video:
                input_dir = os.path.join(WORKSPACE_DIR, "video", "input")
                output_dir = os.path.join(WORKSPACE_DIR, "video", "output")
                process_video_stickers(input_dir, output_dir)
                upload_script = os.path.join("telegram", "tg_video_sticker_upload.py")
            else:
                input_dir = os.path.join(WORKSPACE_DIR, "static", "input")
                output_dir = os.path.join(WORKSPACE_DIR, "static", "output")
                process_stickers_to_512(input_dir, output_dir)
                upload_script = os.path.join("telegram", "tg_sticker_upload.py")
        except Exception as e:
            print(f"[-] 轉檔處理出錯: {e}")
            return

        # 5. 執行上傳
        print(f"\n[*] 準備上傳至 Telegram...")
        script_path = os.path.join(script_dir, upload_script)
        
        import sys
        success = await run_step("Telegram 上傳", [sys.executable, script_path], cwd=script_dir)
        
        if success:
            print("\n" + "="*40)
            print(" ✨ 恭喜！全自動化流程已完成！")
            print("="*40)
        else:
            print("\n[-] 上傳過程失敗，請檢查上方錯誤訊息。")

if __name__ == "__main__":
    try:
        asyncio.run(main_workflow())
    except KeyboardInterrupt:
        print("\n[!] 使用者已中斷。")
