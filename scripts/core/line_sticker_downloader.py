import os
import sys
import re
import json
import asyncio
import aiohttp
from typing import Optional, Dict, Any

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.path_utils import WORKSPACE_DIR
from utils.line_utils import (
    extract_line_info, 
    fetch_line_metadata, 
    parse_line_resource,
    STICKER_STATIC_URL,
    STICKER_ANIMATION_URL,
    STICKER_POPUP_URL,
    EMOJI_STATIC_URL,
    EMOJI_ANIMATION_URL
)

class LineDownloader:
    """
    負責從 LINE 下載資源的類別。
    
    支援貼圖與表情貼 (Emoji)，具備併發控制與自動重試機制。
    """
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.semaphore = asyncio.Semaphore(5)  # 併發限制
        self.product_type = "STICKER"

    async def download_file(self, session: aiohttp.ClientSession, url: str, path: str):
        """下載單一檔案，使用信號量限制併發。"""
        async with self.semaphore:
            return await self._download_file_recursive(session, url, path)

    async def _download_file_recursive(self, session: aiohttp.ClientSession, url: str, path: str, retries: int = 3):
        """遞迴下載邏輯，支援 @2x 回退。"""
        for attempt in range(retries):
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(path, 'wb') as f:
                            f.write(content)
                        return True
                    elif response.status == 404 and "@2x" in url:
                        fallback_url = url.replace("@2x", "")
                        return await self._download_file_recursive(session, fallback_url, path, retries)
                    elif response.status == 404:
                        return False
            except Exception as e:
                if attempt == retries - 1:
                    print(f"[-] 下載失敗 ({url}): {e}")
            
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
        return False

    async def run(self, url_or_id: str):
        """執行完整的下載流程。"""
        product_id, product_type = extract_line_info(url_or_id)
        self.product_type = product_type
        
        if not product_id:
            print("[-] 無效的 LINE 連結或 ID。")
            return
        
        async with aiohttp.ClientSession() as session:
            display_type = "貼圖包" if product_type == "STICKER" else "Emoji"
            print(f"[*] 正在獲取 {display_type} 資訊 (ID: {product_id})...")
            
            meta = await fetch_line_metadata(session, product_id, product_type, self.headers, self.semaphore)
            if not meta:
                return

            title, is_video, items = await parse_line_resource(session, meta, product_type, product_id, self.headers)
            
            print(f"[+] 發現目標: {title}")
            print(f"[+] 資源類型: {'影片/動態' if is_video else '靜態'}")

            # 決定儲存路徑
            workspace_name = "video" if is_video else "static"
            target_dir = os.path.join(self.workspace_path, workspace_name, "input")
            
            if is_video:
                if product_type == "STICKER":
                    url_template = STICKER_POPUP_URL if 'POPUP' in str(meta) else STICKER_ANIMATION_URL
                else:
                    url_template = EMOJI_ANIMATION_URL
            else:
                url_template = EMOJI_STATIC_URL if product_type == "EMOJI" else STICKER_STATIC_URL

            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            print(f"[*] 共有 {len(items)} 個項目，準備下載至 {target_dir}...")

            tasks = []
            for item_id in items:
                file_url = url_template.format(item_id) if product_type == "STICKER" else url_template.format(product_id, item_id)
                file_path = os.path.join(target_dir, f"{item_id}.png")
                tasks.append(self.download_file(session, file_url, file_path))

            results = await asyncio.gather(*tasks)
            success_count = sum(1 for r in results if r)
            
            print(f"\n[√] 完成！成功下載 {success_count}/{len(items)} 個項目。")
            print(f"[!] 檔案位置: {target_dir}")

def main():
    """CLI 工具進入點。"""
    from utils.path_utils import WORKSPACE_DIR
    downloader = LineDownloader(WORKSPACE_DIR)
    
    print("="*30)
    print(" LINE Downloader (Refactored) ")
    print("="*30)
    target = input("請輸入 LINE 網址或 ID: ").strip()
    if target:
        try:
            asyncio.run(downloader.run(target))
        except KeyboardInterrupt:
            print("\n[!] 取消下載。")
    else:
        print("[-] 請輸入有效資訊。")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[-] 執行失敗: {e}")
    finally:
        input("\n請按 Enter 鍵結束...")
