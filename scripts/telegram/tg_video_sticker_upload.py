import os
import sys
import asyncio
import json

# 將 scripts 根目錄加入路徑以便匯入子模組
script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from telethon import TelegramClient, functions, types
from telethon.tl.functions.stickers import CreateStickerSetRequest
from telethon.tl.types import InputStickerSetItem, InputMediaUploadedDocument, DocumentAttributeFilename, DocumentAttributeVideo
from dotenv import load_dotenv
from utils.path_utils import CONFIG_DIR, WORKSPACE_DIR, CONFIG_PATH, ENV_PATH
from utils.config_utils import config
import telegram.tg_compat
from telegram.tg_compat import handle_flood_wait

# 取得 config.json 設定檔
config_data = {}
if os.path.exists(CONFIG_PATH):
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config_data = json.load(f).get('video', {})

# API 密鑰與基本資訊從 config_utils 獲取
API_ID = config.api_id
API_HASH = config.api_hash
PHONE = config.phone

# 貼圖包設定
PACK_TITLE = config_data.get('pack_title') or 'My Video Stickers'
PACK_SHORT_NAME = config_data.get('pack_short_name') or 'my_video_pack'
DEFAULT_EMOJI = config_data.get('default_emoji') or '✨'

# 資料夾路徑
RELATIVE_DIR = config_data.get('sticker_dir') or 'video/output'
if RELATIVE_DIR.startswith('video/'):
    STICKER_DIR = os.path.join(WORKSPACE_DIR, RELATIVE_DIR)
else:
    STICKER_DIR = os.path.join(WORKSPACE_DIR, "video", "output")

@handle_flood_wait(max_wait=300)
async def main():
    if not all([API_ID, API_HASH, PHONE]):
        print(f"錯誤：請在 {ENV_PATH} 中設定 TG_API_ID, TG_API_HASH 和 TG_PHONE")
        return

    # 初始化 Client
    SESSION_PATH = os.path.join(CONFIG_DIR, 'sticker_session')
    client = TelegramClient(SESSION_PATH, int(API_ID), API_HASH)
    
    print("正在連線至 Telegram...")
    await client.start(phone=PHONE)
    
    if not await client.is_user_authorized():
        print("未授權，請依照提示輸入驗證碼。")
        return
        
    print("成功登入 Telegram！")

    # 取得檔案
    if not os.path.exists(STICKER_DIR):
        print(f"錯誤：找不到資料夾 {STICKER_DIR}")
        return

    files = [f for f in os.listdir(STICKER_DIR) if f.lower().endswith('.webm')]
    if not files:
        print(f"資料夾 {STICKER_DIR} 內沒有可上傳的 WebM 檔案。")
        return

    print(f"準備上傳 {len(files)} 個影片貼圖...")

    sticker_items = []
    for filename in files:
        path = os.path.join(STICKER_DIR, filename)
        print(f"正在處理並上傳: {filename}")
        
        uploaded_file = await client.upload_file(path)
        
        media = await client(functions.messages.UploadMediaRequest(
            peer='me',
            media=InputMediaUploadedDocument(
                file=uploaded_file,
                mime_type='video/webm',
                attributes=[
                    DocumentAttributeFilename(filename),
                    DocumentAttributeVideo(duration=3, w=512, h=512, nosound=True)
                ]
            )
        ))
        
        sticker_items.append(InputStickerSetItem(
            document=types.InputDocument(
                id=media.document.id,
                access_hash=media.document.access_hash,
                file_reference=media.document.file_reference
            ),
            emoji=DEFAULT_EMOJI
        ))

    # 建立貼圖包
    try:
        me = await client.get_me()
        print(f"正在為使用者 {me.first_name} 建立影片貼圖包...")
        
        result = await client(CreateStickerSetRequest(
            user_id=me.id,
            title=PACK_TITLE,
            short_name=PACK_SHORT_NAME,
            stickers=sticker_items,
            videos=True
        ))
        
        sticker_set = result.set
        
        print(f"\n✅ 成功建立影片貼圖包！")
        print(f"標題：{sticker_set.title}")
        print(f"總張數：{sticker_set.count} 張") 
        print(f"連結：https://t.me/addstickers/{sticker_set.short_name}")
        
    except Exception as e:
        print(f"\n❌ 建立失敗：{e}")

    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
