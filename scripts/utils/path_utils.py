import os
import shutil

# --- 路徑設定 ---
# 獲取專案根目錄 (TG-StickerKit 這一層)
# 由於此檔案位於 TG-StickerKit/scripts/utils/path_utils.py
# 往上兩層才是 TG-StickerKit
UTILS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.dirname(UTILS_DIR)
BASE_DIR = os.path.dirname(SCRIPTS_DIR)
CONFIG_DIR = os.path.join(BASE_DIR, "config")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
CONFIG_PATH = os.path.join(CONFIG_DIR, "config.json")
ENV_PATH = os.path.join(CONFIG_DIR, ".env")

def get_absolute_path(*paths):
    """獲取正規化的絕對路徑"""
    return os.path.abspath(os.path.join(BASE_DIR, *paths))

def clear_directory(directory):
    """清理資料夾內的所有檔案，但保留目錄本身。包含安全性邊界檢查。"""
    abs_dir = os.path.abspath(directory)
    abs_workspace = os.path.abspath(WORKSPACE_DIR)

    # 安全性檢查：確保目標目錄在 WORKSPACE_DIR 之內
    if not abs_dir.startswith(abs_workspace):
        raise ValueError(f"安全性錯誤：嘗試清理非工作區目錄 {abs_dir}")

    if os.path.exists(abs_dir):
        print(f"[*] 清理目錄: {abs_dir}")
        for filename in os.listdir(abs_dir):
            file_path = os.path.join(abs_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"[-] 無法刪除 {file_path}: {e}")
    else:
        # 冪等性：如果不存在則建立
        os.makedirs(abs_dir, exist_ok=True)
