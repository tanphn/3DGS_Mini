import os
import sys
import argparse
import subprocess
import shutil

# Bắt buộc UTF-8 cho console Windows tránh UnicodeEncodeError (charmap / cp1258)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

from process_video import process_video_to_dataset
from ply_to_splat import convert_ply_to_splat

def run_step(cmd_args, desc, env=None):
    print("\n" + "=" * 60)
    print(f"🚀 {desc}")
    print(f"💻 Lệnh: {' '.join(str(x) for x in cmd_args)}")
    print("=" * 60)
    sys.stdout.flush()

    ret = subprocess.call(cmd_args, env=env)
    if ret != 0:
        print(f"\n❌ Lỗi: {desc} thất bại với mã lỗi {ret}.")
        sys.exit(ret)

def video_to_3dgs_pipeline(video_path, scene_name=None, frames=110, iterations=7000, resolution=2):
    if not os.path.exists(video_path):
        print(f"❌ Lỗi: Không tìm thấy file video: {video_path}")
        return

    if scene_name is None:
        scene_name = os.path.splitext(os.path.basename(video_path))[0]

    base_dir = os.path.dirname(os.path.abspath(__file__))
    scene_dir = os.path.join(base_dir, "data", scene_name)
    output_dir = os.path.join(base_dir, "output", f"{scene_name}_demo")
    colmap_bin = os.path.join(base_dir, "colmap", "bin")
    colmap_plugins = os.path.join(base_dir, "colmap", "plugins")
    colmap_exe = os.path.join(colmap_bin, "colmap.exe")

    if not os.path.exists(colmap_exe):
        print(f"❌ Lỗi: Không tìm thấy COLMAP tại {colmap_exe}")
        return

    # Thiết lập biến môi trường chuẩn cho COLMAP và PyTorch
    env = os.environ.copy()
    env["PATH"] = colmap_bin + os.pathsep + env.get("PATH", "")
    env["QT_PLUGIN_PATH"] = colmap_plugins
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    # Bước 1: Trích xuất ảnh từ video
    print("\n" + "#" * 60)
    print(f"BƯỚC 1: TRÍCH XUẤT ẢNH TỪ VIDEO -> {scene_dir}")
    print("#" * 60)
    process_video_to_dataset(video_path, scene_dir, target_frames=frames)

    # Bước 2: Thiết lập COLMAP
    distorted_dir = os.path.join(scene_dir, "distorted")
    sparse_distorted = os.path.join(distorted_dir, "sparse")
    database_path = os.path.join(distorted_dir, "database.db")
    input_images = os.path.join(scene_dir, "input")
    os.makedirs(sparse_distorted, exist_ok=True)

    # Nếu có database.db cũ bị lỗi trước đó thì xóa đi làm mới
    if os.path.exists(database_path):
        try:
            os.remove(database_path)
        except Exception:
            pass

    # Bước 2.1: Feature Extraction
    run_step(
        [
            colmap_exe, "feature_extractor",
            "--database_path", database_path,
            "--image_path", input_images,
            "--ImageReader.camera_model", "OPENCV",
            "--ImageReader.single_camera", "1"
        ],
        "COLMAP: Trích xuất đặc trưng ảnh (Feature Extraction)",
        env=env
    )

    # Bước 2.2: Sequential Matching (Tối ưu riêng cho video chuỗi)
    run_step(
        [
            colmap_exe, "sequential_matcher",
            "--database_path", database_path,
            "--SequentialMatching.overlap", "15"
        ],
        "COLMAP: Khớp đặc trưng tuần tự video (Sequential Matching)",
        env=env
    )

    # Bước 2.3: Mapper (Dựng không gian 3D & xác định camera poses)
    run_step(
        [
            colmap_exe, "mapper",
            "--database_path", database_path,
            "--image_path", input_images,
            "--output_path", sparse_distorted,
            "--Mapper.ba_global_function_tolerance", "0.000001"
        ],
        "COLMAP: Tái tạo cấu trúc không gian (Mapper & Bundle Adjustment)",
        env=env
    )

    # Bước 2.4: Image Undistorter (Khử méo ảnh sang chuẩn Pinhole)
    sparse_0 = os.path.join(sparse_distorted, "0")
    if not os.path.exists(sparse_0):
        print(f"❌ Lỗi: Mapper không tìm thấy thư mục tái tạo tại {sparse_0}")
        return

    run_step(
        [
            colmap_exe, "image_undistorter",
            "--image_path", input_images,
            "--input_path", sparse_0,
            "--output_path", scene_dir,
            "--output_type", "COLMAP"
        ],
        "COLMAP: Khử méo ảnh (Image Undistortion)",
        env=env
    )

    # Tổ chức lại thư mục sparse chuẩn cho 3DGS
    sparse_final_0 = os.path.join(scene_dir, "sparse", "0")
    os.makedirs(sparse_final_0, exist_ok=True)
    sparse_parent = os.path.join(scene_dir, "sparse")
    for fname in os.listdir(sparse_parent):
        if fname != '0':
            src = os.path.join(sparse_parent, fname)
            dst = os.path.join(sparse_final_0, fname)
            if os.path.isfile(src):
                shutil.move(src, dst)

    # Bước 3: Huấn luyện 3D Gaussian Splatting
    python_exe = sys.executable
    train_script = os.path.join(base_dir, "train.py")
    train_cmd = [
        python_exe, "-u", train_script,
        "-s", scene_dir,
        "-m", output_dir,
        "--iterations", str(iterations),
        "-r", str(resolution),
        "--data_device", "cpu"
    ]
    run_step(train_cmd, f"Huấn luyện 3D Gaussian Splatting ({iterations} steps)", env=env)

    # Bước 4: Tự động nén sang .splat
    final_ply = os.path.join(output_dir, "point_cloud", f"iteration_{iterations}", "point_cloud.ply")
    if os.path.exists(final_ply):
        print("\n" + "#" * 60)
        print("BƯỚC 4: TỰ ĐỘNG NÉN FILE .PLY SANG .SPLAT SIÊU NHẸ")
        print("#" * 60)
        convert_ply_to_splat(final_ply)

    print("\n" + "🎉" * 30)
    print("HOÀN TẤT TOÀN BỘ QUY TRÌNH TỪ VIDEO -> MÔ HÌNH 3D!")
    print(f"👉 File .ply:   {final_ply}")
    final_splat = os.path.splitext(final_ply)[0] + ".splat"
    if os.path.exists(final_splat):
        print(f"👉 File .splat: {final_splat}")
    print("Mở https://superspl.at/editor và kéo file .splat vào để xem ngay!")
    print("🎉" * 30)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Tự động 100% từ Video thành mô hình 3D Gaussian Splatting")
    parser.add_argument("-v", "--video", required=True, help="Đường dẫn đến file video (.mp4)")
    parser.add_argument("-s", "--scene", default=None, help="Tên cảnh (mặc định lấy theo tên video)")
    parser.add_argument("--frames", type=int, default=110, help="Số khung hình trích xuất (mặc định: 110)")
    parser.add_argument("--iterations", type=int, default=7000, help="Số bước train (mặc định: 7000)")
    parser.add_argument("-r", "--resolution", type=int, default=2, help="Tỷ lệ giảm độ phân giải (mặc định: 2)")
    args = parser.parse_args()

    video_to_3dgs_pipeline(args.video, args.scene, args.frames, args.iterations, args.resolution)

