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

# --- Configuration ---
# LINE API URLs
META_URL = "https://stickershop.line-scdn.net/stickershop/v1/product/{}/iphone/productInfo.meta"
# Static sticker URL (High resolution)
STATIC_URL = "https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/android/sticker@2x.png"
# Animated sticker URL (APNG, High resolution)
ANIMATION_URL = "https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/iPhone/sticker_animation@2x.png"
# Popup sticker URL
POPUP_URL = "https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/iPhone/sticker_popup.png"

class LineDownloader:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.semaphore = asyncio.Semaphore(5)  # 限制併發數為 5

    def extract_product_id(self, url: str) -> Optional[str]:
        """從連結或字串中提取 LINE 貼圖產品 ID"""
        # 預處理：移除引號與前後空白
        url = url.strip().strip('"').strip("'")
        
        # 定義多種可能的 URL 模式
        patterns = [
            r'product/(\d+)',        # 網頁版: store.line.me/stickershop/product/123/
            r'/S/sticker/(\d+)',     # 行動版: line.me/S/sticker/123/
            r'^(\d+)$'               # 純數字 ID
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
                
        return None

    async def fetch_meta(self, session: aiohttp.ClientSession, product_id: str, retries: int = 3) -> Optional[Dict[str, Any]]:
        url = META_URL.format(product_id)
        for attempt in range(retries):
            try:
                async with self.semaphore:  # 套用信號量
                    async with session.get(url, headers=self.headers) as response:
                        if response.status == 200:
                            return await response.json()
                        elif response.status == 404:
                            print(f"[-] 無法獲取元數據: 找不到該貼圖包 (HTTP 404)")
                            return None
                        else:
                            print(f"[-] 獲取元數據失敗 (HTTP {response.status})，準備重試...")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"[-] 獲取元數據發生網路錯誤 ({e})，準備重試...")
            except Exception as e:
                print(f"[-] 獲取元數據發生未知錯誤: {e}")
                return None
            
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                print(f"[*] 等待 {wait_time} 秒後進行第 {attempt + 2} 次重試...")
                await asyncio.sleep(wait_time)
        
        print("[-] 獲取元數據重試次數已達上限，放棄下載。")
        return None

    async def download_file(self, session: aiohttp.ClientSession, url: str, path: str):
        async with self.semaphore:  # 只在此處獲取一次信號量
            return await self._download_file_recursive(session, url, path)

    async def _download_file_recursive(self, session: aiohttp.ClientSession, url: str, path: str, retries: int = 3):
        for attempt in range(retries):
            try:
                async with session.get(url, headers=self.headers) as response:
                    if response.status == 200:
                        content = await response.read()
                        with open(path, 'wb') as f:
                            f.write(content)
                        return True
                    elif response.status == 404 and "@2x" in url:
                        # 如果 @2x 不存在，嘗試下載普通版本
                        fallback_url = url.replace("@2x", "")
                        # 遞迴呼叫內部方法，不再重新獲取信號量
                        return await self._download_file_recursive(session, fallback_url, path, retries)
                    elif response.status == 404:
                        print(f"[-] 找不到檔案 {url}")
                        return False
                    else:
                        print(f"[-] 下載失敗 {url}: HTTP {response.status}，準備重試...")
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"[-] 下載過程發生網路錯誤 {url}: {e}，準備重試...")
            except Exception as e:
                print(f"[-] 下載過程發生未知錯誤 {url}: {e}")
                return False
            
            if attempt < retries - 1:
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
                
        print(f"[-] 下載 {url} 重試次數已達上限，放棄下載。")
        return False


    async def run(self, url_or_id: str):
        product_id = self.extract_product_id(url_or_id)
        if not product_id:
            print("[-] 無效的 LINE 貼圖連結或 ID。")
            return
        
        async with aiohttp.ClientSession() as session:
            print(f"[*] 正在獲取貼圖包資訊 (ID: {product_id})...")
            meta = await self.fetch_meta(session, product_id)
            if not meta:
                print("[-] 無法獲取貼圖包資訊。")
                return

            title = meta.get('title', {}).get('zh-Hant', meta.get('title', {}).get('en', product_id))
            # 過濾非法字元
            safe_title = re.sub(r'[\\/*?:"<>|]', "", title)
            
            has_animation = meta.get('hasAnimation', False)
            sticker_type = meta.get('stickerResourceType', 'STATIC')
            
            print(f"[+] 發現貼圖包: {title}")
            print(f"[+] 資源類型: {sticker_type}")

            # 判斷是靜態還是動態/彈出
            is_video = has_animation or sticker_type in ['ANIMATION', 'ANIMATION_SOUND', 'POPUP', 'POPUP_SOUND']
            
            if is_video:
                target_dir = os.path.join(self.workspace_path, "video", "input")
                # 彈出貼圖使用不同的 URL 模板
                url_template = POPUP_URL if 'POPUP' in sticker_type else ANIMATION_URL
                type_name = "動態/彈出"
            else:
                target_dir = os.path.join(self.workspace_path, "static", "input")
                url_template = STATIC_URL
                type_name = "靜態"

            # 確保輸入資料夾存在 (清空舊的或分開存放？這裡我們直接放入 input)
            # 考慮到後續處理腳本是讀取整個資料夾，建議下載前先提醒或清空，
            # 但為了安全，我們直接建立並下載。
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)

            stickers = meta.get('stickers', [])
            print(f"[*] 共有 {len(stickers)} 張貼圖，準備下載至 {target_dir} ({type_name})...")

            tasks = []
            for sticker in stickers:
                s_id = sticker['id']
                file_url = url_template.format(s_id)
                file_path = os.path.join(target_dir, f"{s_id}.png")
                tasks.append(self.download_file(session, file_url, file_path))

            results = await asyncio.gather(*tasks)
            success_count = sum(1 for r in results if r)
            
            print(f"\n[√] 完成！成功下載 {success_count}/{len(stickers)} 張貼圖。")
            print(f"[!] 檔案位置: {target_dir}")
            print(f"[!] 接下來你可以執行對應的處理腳本 (sticker_processor.py 或 video_sticker_processor.py)。")

def main():
    downloader = LineDownloader(WORKSPACE_DIR)
    
    print("="*30)
    print(" LINE Sticker Downloader ")
    print("="*30)
    target = input("請輸入 LINE 貼圖網址或 ID: ").strip()
    if target:
        try:
            asyncio.run(downloader.run(target))
        except KeyboardInterrupt:
            print("\n[!] 使用者取消下載。")
    else:
        print("[-] 請輸入有效的資訊。")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n[-] 執行失敗: {e}")
    finally:
        input("\n請按 Enter 鍵結束...")
