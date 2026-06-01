import struct
import asyncio
import telethon
from telethon.tl.functions.stickers import CreateStickerSetRequest
from telethon.errors import FloodWaitError

# 已知相容的 Telethon 版本範圍
COMPATIBLE_VERSION = "1.24" 

def handle_flood_wait(max_wait=300):
    """
    處理 Telegram FloodWaitError 的裝飾器。
    如果等待時間超過 max_wait (秒)，則拋出錯誤。
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except FloodWaitError as e:
                if e.seconds > max_wait:
                    print(f"[-] FloodWait 時間過長 ({e.seconds}s > {max_wait}s)，放棄重試。")
                    raise e
                print(f"[!] 觸發頻率限制，需等待 {e.seconds} 秒...")
                await asyncio.sleep(e.seconds)
                return await wrapper(*args, **kwargs)
        return wrapper
    return decorator

def apply_video_sticker_patch():
    """
    為 CreateStickerSetRequest 套用 Monkey Patch 以支援影片貼圖 (videos=True)。
    此 Patch 會在 Telethon 庫原生支援前作為臨時解決方案。
    """
    version = telethon.__version__
    print(f"[*] 正在檢查 Telethon 版本: {version}")
    
    # 這裡可以根據版本決定是否需要套用 Patch
    # 如果版本已經很新，可能已經內建
    
    _old_init = CreateStickerSetRequest.__init__

    def _new_init(self, user_id, title, short_name, stickers, masks=None, emojis=None, 
                  text_color=None, thumb=None, software=None, videos=None, animated=None):
        _old_init(self, user_id, title, short_name, stickers, masks=masks, emojis=emojis, 
                  text_color=text_color, thumb=thumb, software=software)
        self.videos = videos
        self.animated = animated

    def _new_bytes(self):
        flags = 0
        if self.masks: flags |= 1
        if self.animated: flags |= 2
        if self.thumb: flags |= 4
        if self.software: flags |= 8
        if self.videos: flags |= 16
        if self.emojis: flags |= 32
        if self.text_color: flags |= 64
        
        return b''.join((
            b'g\xab!\x90',
            struct.pack('<I', flags),
            self.user_id._bytes(),
            self.serialize_bytes(self.title),
            self.serialize_bytes(self.short_name),
            b'' if self.thumb is None or self.thumb is False else (self.thumb._bytes()),
            b'\x15\xc4\xb5\x1c', struct.pack('<i', len(self.stickers)), b''.join(x._bytes() for x in self.stickers),
            b'' if self.software is None or self.software is False else (self.serialize_bytes(self.software)),
        ))

    CreateStickerSetRequest.__init__ = _new_init
    CreateStickerSetRequest._bytes = _new_bytes
    print("[+] CreateStickerSetRequest Monkey Patch 已套用 (支援影片貼圖)")

# 預設套用
apply_video_sticker_patch()
