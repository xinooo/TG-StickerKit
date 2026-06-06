import re
import aiohttp
import asyncio
from typing import Optional, Dict, Any

# --- LINE API URL Templates ---
# Stickers
STICKER_META_URL = "https://stickershop.line-scdn.net/stickershop/v1/product/{}/iphone/productInfo.meta"
STICKER_STATIC_URL = "https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/android/sticker@2x.png"
STICKER_ANIMATION_URL = "https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/iPhone/sticker_animation@2x.png"
STICKER_POPUP_URL = "https://stickershop.line-scdn.net/stickershop/v1/sticker/{}/iPhone/sticker_popup.png"

# Emojis (Sticons)
EMOJI_META_URL = "https://stickershop.line-scdn.net/sticonshop/v1/product/{}/iphone/meta.json"
EMOJI_STATIC_URL = "https://stickershop.line-scdn.net/sticonshop/v1/sticon/{}/iPhone/{}.png"
EMOJI_ANIMATION_URL = "https://stickershop.line-scdn.net/sticonshop/v1/sticon/{}/iPhone/{}_animation.png"

# Store Page
EMOJI_STORE_URL = "https://store.line.me/emojishop/product/{}/zh-Hant"

def get_safe_name(name: str) -> str:
    """過濾非法字元以產生安全檔名。"""
    return re.sub(r'[\\/*?:"<>|]', "", name)

def extract_line_info(url: str) -> tuple[Optional[str], str]:
    """
    從連結或字串中提取 LINE 貼圖或 Emoji 的產品 ID 與類型。
    
    Returns:
        tuple: (產品 ID, 產品類型) - 類型為 "STICKER" 或 "EMOJI"。
    """
    url = url.strip().strip('"').strip("'")
    
    # Emoji 模式：ID 通常為十六進位
    emoji_patterns = [
        (r'emojishop/product/([a-f0-9]+)', "EMOJI"),
        (r'emoji/\?id=([a-f0-9]+)', "EMOJI"),
    ]
    # Sticker 模式
    sticker_patterns = [
        (r'stickershop/product/(\d+)', "STICKER"),
        (r'/S/sticker/(\d+)', "STICKER"),
    ]
    
    for pattern, type_name in emoji_patterns + sticker_patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1), type_name
            
    if re.match(r'^(\d+)$', url):
        return url, "STICKER"
        
    return None, "STICKER"

async def fetch_line_emoji_title(session: aiohttp.ClientSession, product_id: str, headers: dict) -> Optional[str]:
    """從 LINE Store 網頁爬取 Emoji 的標題。"""
    url = EMOJI_STORE_URL.format(product_id)
    print(f"[*] 正在從 LINE Store 檢索 Emoji 名稱...")
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                html = await response.text()
                
                # 優先嘗試從 og:title 獲取 (最穩定)
                og_match = re.search(r'property="og:title"\s+content="([^"–|]+)', html)
                if og_match:
                    return og_match.group(1).strip()
                
                # 次要嘗試：<p class="mdSt08Name">
                match = re.search(r'<p class="mdSt08Name">([^<]+)</p>', html)
                if match:
                    return match.group(1).strip()
    except Exception as e:
        print(f"[*] 警告：無法從網頁獲取標題 ({e})")
    return None

async def fetch_line_metadata(session: aiohttp.ClientSession, product_id: str, product_type: str, headers: dict, semaphore: asyncio.Semaphore, retries: int = 3) -> Optional[Dict[str, Any]]:
    """獲取 LINE 產品的元數據。"""
    url_template = EMOJI_META_URL if product_type == "EMOJI" else STICKER_META_URL
    url = url_template.format(product_id)
    
    for attempt in range(retries):
        try:
            async with semaphore:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 404:
                        print(f"[-] 找不到項目 (404): {url}")
                        return None
        except Exception as e:
            if attempt == retries - 1:
                print(f"[-] 獲取元數據失敗: {e}")
        
        if attempt < retries - 1:
            await asyncio.sleep(2 ** attempt)
    return None

async def parse_line_resource(session: aiohttp.ClientSession, meta: Dict[str, Any], product_type: str, product_id: str, headers: dict) -> tuple[str, bool, list[str]]:
    """
    解析 LINE 資源資訊。
    
    Returns:
        tuple: (safe_title, is_video, items_to_download)
    """
    if product_type == "STICKER":
        title = meta.get('title', {}).get('zh-Hant', meta.get('title', {}).get('en', product_id))
        has_animation = meta.get('hasAnimation', False)
        res_type = meta.get('stickerResourceType', 'STATIC')
        is_video = has_animation or res_type in ['ANIMATION', 'ANIMATION_SOUND', 'POPUP', 'POPUP_SOUND']
        items = [s['id'] for s in meta.get('stickers', [])]
    else:
        # Emoji 模式
        web_title = await fetch_line_emoji_title(session, product_id, headers)
        title = web_title if web_title else product_id
        res_type = meta.get('sticonResourceType', 'STATIC')
        is_video = res_type in ['ANIMATION', 'ANIMATION_SOUND']
        items = meta.get('orders', [])
        
    return get_safe_name(title), is_video, items
