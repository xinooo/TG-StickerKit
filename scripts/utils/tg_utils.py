import os
import sys
from telethon import functions, types, errors

async def check_sticker_pack_exists(client, short_name):
    """
    檢查 Telegram 貼圖包是否已存在。
    
    Args:
        client: 已連線並授權的 TelegramClient 實例
        short_name: 要檢查的貼圖包 short name
        
    Returns:
        bool: 若已存在則回傳 True，否則回傳 False
    """
    try:
        # 使用 GetStickerSetRequest 查詢貼圖包
        result = await client(functions.messages.GetStickerSetRequest(
            stickerset=types.InputStickerSetShortName(short_name=short_name),
            hash=0
        ))
        
        sticker_set = result.set
        print(f"\n[!] 偵測到重複貼圖包：")
        print(f"    標題：{sticker_set.title}")
        print(f"    Short Name: {sticker_set.short_name}")
        print(f"    貼圖數量：{sticker_set.count} 張")
        print(f"    連結：https://t.me/addstickers/{sticker_set.short_name}")
        
        # 環境感知提示
        is_automated = os.environ.get('SKIP_FINAL_INPUT') == '1'
        if not is_automated:
            print(f"\n[提示] 若欲建立新貼圖包，請修改 config.json 中的 pack_short_name 後重試。")
            
        return True
        
    except errors.StickerSetInvalidError:
        # 貼圖包不存在，這是正常的（預期結果）
        return False
    except Exception as e:
        print(f"[-] 檢查貼圖包重複時發生非預期錯誤: {e}")
        # 發生錯誤時保守起見，回傳 False 讓流程嘗試繼續，或視情況中止
        return False
