import os
import sys
import argparse
import shutil
import cv2
import numpy as np

# Bắt buộc UTF-8 cho console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def estimate_blur(image_gray):
    """Tính độ sắc nét của ảnh dựa trên biến thiên toán tử Laplacian (càng cao càng nét)."""
    return cv2.Laplacian(image_gray, cv2.CV_64F).var()

def process_video_to_dataset(video_path, output_dir=None, target_frames=120, fps=None, max_res=1920, filter_blur=True):
    if not os.path.exists(video_path):
        print(f"❌ Lỗi: Không tìm thấy file video tại: {video_path}")
        return None

    # Xác định thư mục đích
    if output_dir is None:
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        output_dir = os.path.join("data", video_name)
    
    input_images_dir = os.path.join(output_dir, "input")
    os.makedirs(input_images_dir, exist_ok=True)

    print("=" * 60)
    print(f"🎬 ĐANG XỬ LÝ VIDEO: {video_path}")
    print(f"📂 Thư mục xuất dữ liệu: {output_dir}")
    print("=" * 60)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("❌ Lỗi: Không thể mở video bằng OpenCV.")
        return None

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    orig_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    orig_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration_sec = total_frames / video_fps if video_fps > 0 else 0

    print(f"⏱️ Độ dài video: {duration_sec:.1f} giây ({total_frames} frames, {video_fps:.1f} fps)")
    print(f"📐 Độ phân giải gốc: {orig_w} x {orig_h}")

    # Tính toán bước nhảy lấy frame (stride)
    if fps is not None and fps > 0:
        step = max(1, int(round(video_fps / fps)))
    else:
        # Tự động tính step để ra khoảng target_frames
        target = max(30, min(300, target_frames))
        step = max(1, total_frames // target)

    print(f"🎯 Tần suất lấy mẫu: Cách mỗi {step} frames lấy 1 ảnh (khoảng {video_fps / step:.1f} ảnh/giây)...")

    saved_count = 0
    frame_idx = 0
    blur_scores = []

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % step == 0:
            # Thu nhỏ độ phân giải nếu vượt quá max_res để COLMAP chạy nhanh và mượt
            h, w = frame.shape[:2]
            if max(h, w) > max_res:
                scale = max_res / max(h, w)
                new_w, new_h = int(w * scale), int(h * scale)
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            blur_score = estimate_blur(gray)
            blur_scores.append(blur_score)

            # Đặt tên theo chuẩn định dạng 5 chữ số: 00001.jpg, 00002.jpg...
            saved_count += 1
            filename = f"{saved_count:05d}.jpg"
            save_path = os.path.join(input_images_dir, filename)
            cv2.imwrite(save_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])

        frame_idx += 1

    cap.release()

    avg_blur = np.mean(blur_scores) if blur_scores else 0
    print("-" * 60)
    print(f"✅ ĐÃ TRÍCH XUẤT THÀNH CÔNG: {saved_count} ảnh chất lượng cao vào:")
    print(f"   👉 {os.path.abspath(input_images_dir)}")
    print(f"📊 Độ nét trung bình: {avg_blur:.1f} (Càng cao trên 100 là ảnh càng nét)")
    print("=" * 60)

    # Kiểm tra COLMAP trên máy
    colmap_path = shutil.which("colmap")
    local_colmap = os.path.join(os.getcwd(), "colmap", "colmap.bat")
    has_colmap = colmap_path is not None or os.path.exists(local_colmap)

    print("\n🚀 CÁC BƯỚC TIẾP THEO:")
    if not has_colmap:
        print("⚠️ Máy bạn chưa có COLMAP trong PATH. Để dựng 3D từ ảnh vừa cắt:")
        print("   1. Tải bản COLMAP Windows (hỗ trợ CUDA) tại:")
        print("      https://github.com/colmap/colmap/releases (chọn file COLMAP-x.x-windows-cuda.zip)")
        print("   2. Giải nén vào thư mục `gaussian-splatting/colmap`")
        print(f"   3. Chạy lệnh tính góc camera:")
        print(f"      python convert.py -s \"{output_dir}\" --colmap_executable colmap/colmap.bat")
    else:
        print("1. Chạy tính toán camera (COLMAP):")
        print(f"   python convert.py -s \"{output_dir}\"")

    print("\n2. Chạy huấn luyện mô hình 3DGS:")
    print(f"   python train.py -s \"{output_dir}\" -m \"output/{os.path.basename(output_dir)}\" --iterations 7000 -r 2 --data_device cpu")

    print("\n3. Nén file sau khi train:")
    print(f"   python ply_to_splat.py \"output/{os.path.basename(output_dir)}/point_cloud/iteration_7000/point_cloud.ply\"")
    print("=" * 60)

    return output_dir

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Chuyển video thành tập dữ liệu ảnh chuẩn cho 3D Gaussian Splatting")
    parser.add_argument("-v", "--video", required=True, help="Đường dẫn đến file video (ví dụ: my_room.mp4)")
    parser.add_argument("-o", "--output", default=None, help="Thư mục xuất dữ liệu (mặc định: data/<tên_video>)")
    parser.add_argument("--frames", type=int, default=120, help="Số lượng ảnh mục tiêu muốn cắt (mặc định: 120 ảnh)")
    parser.add_argument("--fps", type=float, default=None, help="Chỉ định số khung hình/giây cần trích xuất (tùy chọn)")
    parser.add_argument("--max_res", type=int, default=1920, help="Độ phân giải cạnh dài tối đa (mặc định: 1920px)")
    
    args = parser.parse_args()
    process_video_to_dataset(args.video, args.output, args.frames, args.fps, args.max_res)

