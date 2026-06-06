import os
import sys
from PIL import Image, ImageFilter

script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)

from utils.path_utils import WORKSPACE_DIR

def process_stickers_to_512(input_dir, output_dir, target_size=(512, 512)):
    # 建立輸出資料夾
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"已建立資料夾：{output_dir}")

    # 支援的圖片格式
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp', '.bmp')

    # 取得檔案列表
    if not os.path.exists(input_dir):
        print(f"錯誤：找不到輸入資料夾 {input_dir}")
        return

    files = [f for f in os.listdir(input_dir) if f.lower().endswith(valid_extensions)]
    
    if not files:
        print(f"在 {input_dir} 內找不到圖片檔案。")
        return

    print(f"開始整合處理，目標尺寸 {target_size[0]}x{target_size[1]}，共計 {len(files)} 張圖片...")

    for filename in files:
        try:
            input_path = os.path.join(input_dir, filename)
            # 統一輸出為 .png
            name_without_ext = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, f"{name_without_ext}.png")

            with Image.open(input_path) as img:
                # 1. 確保是 RGBA 模式
                img = img.convert("RGBA")
                
                # 2. 計算等比例縮放後的尺寸 (維持長寬比，但不超過 512)
                img_ratio = img.width / img.height
                target_ratio = target_size[0] / target_size[1]

                if img_ratio > target_ratio:
                    new_width = target_size[0]
                    new_height = int(target_size[0] / img_ratio)
                else:
                    new_height = target_size[1]
                    new_width = int(target_size[1] * img_ratio)

                # 3. 執行高品質縮放 (LANCZOS)
                resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
                
                # 4. 建立全透明底板 (512x512)
                canvas = Image.new("RGBA", target_size, (0, 0, 0, 0))
                
                # 5. 將圖片置中貼上
                offset = (
                    (target_size[0] - new_width) // 2,
                    (target_size[1] - new_height) // 2
                )
                canvas.paste(resized_img, offset)
                
                # 6. 應用銳化濾鏡維持邊緣清晰
                final_img = canvas.filter(ImageFilter.SHARPEN)
                
                # 7. 儲存結果
                final_img.save(output_path, "PNG")
                print(f"處理完成: {filename} -> {os.path.basename(output_path)}")
        
        except Exception as e:
            print(f"處理 {filename} 時發生錯誤: {e}")

if __name__ == "__main__":
    try:
        # 使用 path_utils 定義的路徑
        input_folder = os.path.join(WORKSPACE_DIR, "static", "input")
        output_folder = os.path.join(WORKSPACE_DIR, "static", "output")

        process_stickers_to_512(input_folder, output_folder)
        print("\n所有圖片整合處理完畢！")
        print(f"高品質結果儲存在: {output_folder}")
    except Exception as e:
        print(f"\n[-] 執行失敗: {e}")
    finally:
        input("\n請按 Enter 鍵結束...")
