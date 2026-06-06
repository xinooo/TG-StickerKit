import os
import sys
import json
import asyncio
import aiohttp

# 將腳本根目錄加入路徑以便匯入子模組
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.path_utils import WORKSPACE_DIR, CONFIG_PATH, CONFIG_DIR, clear_directory
from utils.line_utils import extract_line_info, fetch_line_metadata, parse_line_resource
from utils.config_utils import config
from utils.tg_utils import check_sticker_pack_exists
from telethon import TelegramClient
from core.line_sticker_downloader import LineDownloader
from core.sticker_processor import process_stickers_to_512
from core.video_sticker_processor import process_video_stickers

def update_config(is_video, title, pack_id):
    """更新 config.json 中的貼圖包設定。"""
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
    """執行子程序並注入環境變數以控制輸出。"""
    print(f"\n>>> 正在執行: {name}")
    
    env = os.environ.copy()
    env['SKIP_FINAL_INPUT'] = '1'
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        env=env
    )
    return_code = await process.wait()
    
    if return_code != 0:
        print(f"\n[-] {name} 執行失敗，離開代碼: {return_code}")
    
    return return_code == 0

async def main_workflow():
    """LINE 貼圖/Emoji 一鍵全自動化轉檔與上傳工作流。"""
    print("="*40)
    print(" LINE to Telegram 一鍵全自動化工作流 ")
    print("="*40)
    
    user_input = input("請輸入 LINE 貼圖連結或 ID: ").strip()
    if not user_input:
        return

    downloader = LineDownloader(WORKSPACE_DIR)
    product_id, product_type = extract_line_info(user_input)
    
    async with aiohttp.ClientSession() as session:
        print(f"[*] 正在獲取元數據 (ID: {product_id})...")
        meta = await fetch_line_metadata(session, product_id, product_type, downloader.headers, downloader.semaphore)
        if not meta:
            print("[-] 無法解析項目，流程中止。")
            return

        # 使用統一的工具解析資源資訊
        title, is_video, _ = await parse_line_resource(session, meta, product_type, product_id, downloader.headers)
        
        print(f"[+] 目錄標題: {title}")
        print(f"[+] 資源類型: {'影片/動態' if is_video else '靜態'}")

        # 1. 準備工作區
        workspace_type = "video" if is_video else "static"
        input_dir = os.path.join(WORKSPACE_DIR, workspace_type, "input")
        output_dir = os.path.join(WORKSPACE_DIR, workspace_type, "output")
        
        try:
            clear_directory(input_dir)
            clear_directory(output_dir)
        except Exception as e:
            print(f"[-] 清理工作區失敗: {e}")
            return

        # 1.5 檢查 Telegram 是否已有相同貼圖包
        print(f"[*] 正在檢查 Telegram 是否已有相同貼圖包...")
        short_name = f"xinooo_stickerkit_line{product_id}"
        
        # 設置環境變數以標示為自動化流程（影響提示訊息）
        os.environ['SKIP_FINAL_INPUT'] = '1'
        
        SESSION_PATH = os.path.join(CONFIG_DIR, 'sticker_session')
        client = TelegramClient(SESSION_PATH, int(config.api_id), config.api_hash)
        try:
            await client.start(phone=config.phone)
            if await check_sticker_pack_exists(client, short_name):
                print("[-] 貼圖包已存在於 Telegram，中止自動化流程以節省資源。")
                return
        except Exception as e:
            print(f"[-] Telegram 預檢連線失敗 (可能未登入): {e}")
            print("[*] 將繼續執行流程，由後續上傳腳本處理連線與檢查。")
        finally:
            await client.disconnect()

        # 2. 執行下載
        await downloader.run(user_input)

        # 3. 更新配置
        if not update_config(is_video, title, product_id):
            return

        # 4. 轉檔處理
        print(f"\n[*] 啟動轉檔引擎...")
        try:
            if is_video:
                process_video_stickers(input_dir, output_dir)
                upload_script = "tg_video_sticker_upload.py"
            else:
                process_stickers_to_512(input_dir, output_dir)
                upload_script = "tg_sticker_upload.py"
        except Exception as e:
            print(f"[-] 轉檔失敗: {e}")
            return

        # 5. 上傳至 Telegram
        print(f"\n[*] 準備上傳至 Telegram...")
        upload_path = os.path.join(script_dir, "telegram", upload_script)
        
        success = await run_step("Telegram 上傳", [sys.executable, upload_path], cwd=script_dir)
        
        if success:
            print("\n" + "="*40)
            print(" ✨ 恭喜！全自動化流程已順利完成！")
            print("="*40)
        else:
            print("\n[-] 流程在最後一步中斷。")

if __name__ == "__main__":
    try:
        asyncio.run(main_workflow())
    except KeyboardInterrupt:
        print("\n[!] 使用者已中斷。")
    finally:
        input("\n請按 Enter 鍵結束...")
