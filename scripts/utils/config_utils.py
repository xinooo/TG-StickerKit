import os
from dotenv import load_dotenv
from .path_utils import ENV_PATH

class TGConfig:
    def __init__(self):
        load_dotenv(ENV_PATH)
        self.api_id = self._get_int('TG_API_ID')
        self.api_hash = self._get_required('TG_API_HASH')
        self.phone = self._get_required('TG_PHONE')

    def _get_required(self, key):
        value = os.getenv(key)
        if not value:
            raise ValueError(f"環境變數缺失: {key}。請在 {ENV_PATH} 中設定。")
        return value

    def _get_int(self, key):
        value = self._get_required(key)
        try:
            return int(value)
        except ValueError:
            raise ValueError(f"環境變數格式錯誤: {key} 應為整數，收到: '{value}'")

# 單例模式方便全域使用
try:
    config = TGConfig()
except ValueError as e:
    # 這裡我們不直接 sys.exit，讓調用者決定如何處理，但通常會導致啟動失敗
    raise e
