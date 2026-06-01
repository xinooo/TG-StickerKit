import os
import sys
import subprocess

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.path_utils import WORKSPACE_DIR

def process_video_stickers(input_dir, output_dir):
    # 建立輸出資料夾
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已建立輸出資料夾：{output_dir}")

    # 檢查輸入資料夾
    if not os.path.exists(input_dir):
        print(f"錯誤：找不到輸入資料夾 {input_dir}")
        return

    # 支援的格式
    valid_extensions = ('.mp4', '.mov', '.webm', '.gif', '.png', '.jpg', '.jpeg')

    files = [f for f in os.listdir(input_dir) if f.lower().endswith(valid_extensions)]
    
    if not files:
        print(f"在 {input_dir} 內找不到支援的檔案。")
        return

    print(f"開始批量轉換，共計 {len(files)} 個檔案...")

    for filename in files:
        input_path = os.path.join(input_dir, filename)
        name_without_ext = os.path.splitext(filename)[0]
        output_path = os.path.join(output_dir, f"{name_without_ext}.webm")

        print(f"正在轉換: {filename} -> {name_without_ext}.webm")

        cmd = [
            'ffmpeg', '-y', '-i', input_path,
            '-c:v', 'libvpx-vp9',
            '-b:v', '200k',
            '-r', '30',
            '-an',
            '-auto-alt-ref', '0',
            r'-vf', r'format=rgba,pad=max(iw\,ih):max(iw\,ih):(ow-iw)/2:(oh-ih)/2:color=0x00000000,scale=512:512',
            '-pix_fmt', 'yuva420p',
            '-t', '3',
            output_path
        ]

        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
            print(f"✅ 完成: {name_without_ext}.webm")
        except subprocess.CalledProcessError as e:
            print(f"❌ 轉換 {filename} 失敗: {e.stderr.decode('utf-8', errors='ignore')}")

if __name__ == "__main__":
    # 使用 path_utils 定義的路徑
    input_folder = os.path.join(WORKSPACE_DIR, "video", "input")
    output_folder = os.path.join(WORKSPACE_DIR, "video", "output")

    process_video_stickers(input_folder, output_folder)
    print("\n所有影片貼圖轉換完畢！")
    print(f"結果儲存在: {output_folder}")
