import os
import sys
import json
import time
import shutil
import subprocess
import threading
import mimetypes
from urllib.parse import urlparse, parse_qs
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

# Bắt buộc UTF-8 cho console Windows tránh UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Cấu hình máy chủ
HOST = "127.0.0.1"
PORT = 7860
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
DATA_DIR = os.path.join(BASE_DIR, "data")

# Trạng thái tiến trình toàn cục
state = {
    "status": "idle",      # idle, running, completed, error
    "stage": 0,            # 0: None, 1: Frames, 2: COLMAP, 3: Training, 4: Splat
    "stage_text": "Sẵn sàng",
    "progress": 0,         # 0 - 100
    "scene_name": "",
    "logs": [],
    "error_msg": "",
    "final_ply": "",
    "final_splat": ""
}

process_lock = threading.Lock()
current_process = None

def add_log(message):
    timestamp = time.strftime("[%H:%M:%S] ")
    line = timestamp + message
    with process_lock:
        state["logs"].append(line)
        if len(state["logs"]) > 2000:
            state["logs"] = state["logs"][-2000:]
    print(line)

def scan_models():
    """Quét toàn bộ mô hình đã dựng trong thư mục output/"""
    models = []
    if not os.path.exists(OUTPUT_DIR):
        return models

    for item in os.listdir(OUTPUT_DIR):
        item_path = os.path.join(OUTPUT_DIR, item)
        if not os.path.isdir(item_path):
            continue

        pc_dir = os.path.join(item_path, "point_cloud")
        if not os.path.exists(pc_dir):
            continue

        for iter_folder in os.listdir(pc_dir):
            iter_path = os.path.join(pc_dir, iter_folder)
            if not os.path.isdir(iter_path) or not iter_folder.startswith("iteration_"):
                continue

            ply_path = os.path.join(iter_path, "point_cloud.ply")
            splat_path = os.path.join(iter_path, "point_cloud.splat")

            has_ply = os.path.exists(ply_path)
            has_splat = os.path.exists(splat_path)

            if has_ply or has_splat:
                steps = iter_folder.replace("iteration_", "")
                ply_size_mb = round(os.path.getsize(ply_path) / (1024 * 1024), 1) if has_ply else 0
                splat_size_mb = round(os.path.getsize(splat_path) / (1024 * 1024), 1) if has_splat else 0
                
                # Thời gian tạo
                mtime = os.path.getmtime(splat_path if has_splat else ply_path)
                mtime_str = time.strftime("%d/%m/%Y %H:%M", time.localtime(mtime))

                models.append({
                    "scene": item,
                    "iteration": steps,
                    "folder_rel": os.path.relpath(iter_path, BASE_DIR).replace("\\", "/"),
                    "has_ply": has_ply,
                    "ply_size_mb": ply_size_mb,
                    "ply_path": os.path.relpath(ply_path, BASE_DIR).replace("\\", "/") if has_ply else "",
                    "has_splat": has_splat,
                    "splat_size_mb": splat_size_mb,
                    "splat_path": os.path.relpath(splat_path, BASE_DIR).replace("\\", "/") if has_splat else "",
                    "created_at": mtime_str
                })

    # Sắp xếp mới nhất lên đầu
    models.sort(key=lambda x: x["created_at"], reverse=True)
    return models

def scan_videos():
    """Quét các file video trong thư mục gốc"""
    vids = []
    valid_exts = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    for f in os.listdir(BASE_DIR):
        ext = os.path.splitext(f)[1].lower()
        if ext in valid_exts:
            full_p = os.path.join(BASE_DIR, f)
            size_mb = round(os.path.getsize(full_p) / (1024 * 1024), 1)
            vids.append({
                "filename": f,
                "size_mb": size_mb,
                "path": f
            })
    return vids

def run_pipeline_worker(video_file, scene_name, frames, iterations, resolution):
    global current_process
    with process_lock:
        state["status"] = "running"
        state["stage"] = 1
        state["stage_text"] = "Bước 1/4: Đang trích xuất ảnh từ video..."
        state["progress"] = 10
        state["scene_name"] = scene_name
        state["logs"] = []
        state["error_msg"] = ""
        state["final_ply"] = ""
        state["final_splat"] = ""

    add_log(f"🎬 Bắt đầu Pipeline 3DGS cho video: {video_file}")
    add_log(f"⚙️ Cấu hình: Scene={scene_name}, Frames={frames}, Iterations={iterations}, Resolution=1/{resolution}")

    # Chạy script video_to_3dgs.py qua python venv
    py_exec = sys.executable
    script_path = os.path.join(BASE_DIR, "video_to_3dgs.py")
    cmd = [
        py_exec, "-u", script_path,
        "-v", video_file,
        "-s", scene_name,
        "--frames", str(frames),
        "--iterations", str(iterations),
        "-r", str(resolution)
    ]

    # Thiết lập biến môi trường UTF-8 toàn diện cho subprocess
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"

    try:
        # Sử dụng binary mode để hoàn toàn không bị phụ thuộc vào bảng mã charmap của Windows
        current_process = subprocess.Popen(
            cmd,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env
        )

        for raw_line in iter(current_process.stdout.readline, b''):
            clean_line = raw_line.decode('utf-8', errors='replace').strip()
            if not clean_line:
                continue
            add_log(clean_line)

            # Cập nhật stage và progress dựa trên log
            if "BƯỚC 1: TRÍCH XUẤT ẢNH" in clean_line:
                state["stage"] = 1
                state["stage_text"] = "Bước 1/4: Đang trích xuất ảnh sắc nét (Laplacian filter)..."
                state["progress"] = 15
            elif "COLMAP: Trích xuất đặc trưng" in clean_line:
                state["stage"] = 2
                state["stage_text"] = "Bước 2/4: COLMAP đang trích xuất đặc trưng ảnh (SIFT)..."
                state["progress"] = 30
            elif "COLMAP: Khớp đặc trưng" in clean_line:
                state["stage"] = 2
                state["stage_text"] = "Bước 2/4: COLMAP đang ghép cặp camera (Sequential Matching)..."
                state["progress"] = 45
            elif "COLMAP: Tái tạo cấu trúc không gian" in clean_line:
                state["stage"] = 2
                state["stage_text"] = "Bước 2/4: COLMAP đang tái tạo không gian 3D (Mapper)..."
                state["progress"] = 55
            elif "Huấn luyện 3D Gaussian Splatting" in clean_line:
                state["stage"] = 3
                state["stage_text"] = f"Bước 3/4: Đang huấn luyện 3DGS ({iterations} steps trên RTX 4050)..."
                state["progress"] = 70
            elif "Iteration" in clean_line and "/30000" in clean_line:
                state["progress"] = 80
            elif "Iteration" in clean_line and "/7000" in clean_line:
                state["progress"] = 85
            elif "BƯỚC 4: TỰ ĐỘNG NÉN FILE" in clean_line:
                state["stage"] = 4
                state["stage_text"] = "Bước 4/4: Đang nén file .ply sang .splat siêu nhẹ..."
                state["progress"] = 95
            elif "HOÀN TẤT TOÀN BỘ QUY TRÌNH" in clean_line:
                state["progress"] = 100

        current_process.wait()
        ret_code = current_process.returncode

        if ret_code == 0:
            output_dir = os.path.join(OUTPUT_DIR, f"{scene_name}_demo")
            ply_path = os.path.join(output_dir, "point_cloud", f"iteration_{iterations}", "point_cloud.ply")
            splat_path = os.path.join(output_dir, "point_cloud", f"iteration_{iterations}", "point_cloud.splat")

            with process_lock:
                state["status"] = "completed"
                state["stage"] = 4
                state["stage_text"] = "🎉 Hoàn tất dựng mô hình 3D thành công!"
                state["progress"] = 100
                if os.path.exists(ply_path):
                    state["final_ply"] = os.path.relpath(ply_path, BASE_DIR).replace("\\", "/")
                if os.path.exists(splat_path):
                    state["final_splat"] = os.path.relpath(splat_path, BASE_DIR).replace("\\", "/")

            add_log("✅ Pipeline hoàn tất thành công 100%!")
        else:
            with process_lock:
                state["status"] = "error"
                state["stage_text"] = f"❌ Đã xảy ra lỗi (Exit code: {ret_code})"
                state["error_msg"] = f"Tiến trình dừng đột ngột với mã lỗi {ret_code}."
            add_log(f"❌ Tiến trình thất bại với mã lỗi {ret_code}.")

    except Exception as e:
        with process_lock:
            state["status"] = "error"
            state["stage_text"] = f"❌ Ngoại lệ: {str(e)}"
            state["error_msg"] = str(e)
        add_log(f"❌ Ngoại lệ hệ thống: {e}")
    finally:
        current_process = None

HTML_PAGE = """<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Gaussian Splatting Studio</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: #090d16;
            color: #f1f5f9;
        }
        .code-font {
            font-family: 'JetBrains Mono', monospace;
        }
        .glass-card {
            background: rgba(18, 24, 38, 0.7);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .glass-card-hover {
            transition: all 0.25s ease;
        }
        .glass-card-hover:hover {
            border-color: rgba(99, 102, 241, 0.4);
            transform: translateY(-2px);
            box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.15);
        }
        /* Custom scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: rgba(0,0,0,0.2); }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.15); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(99, 102, 241, 0.5); }
    </style>
</head>
<body class="min-h-screen flex flex-col">

    <!-- Top Navigation Bar -->
    <header class="glass-card sticky top-0 z-50 px-6 py-3.5 flex items-center justify-between border-b border-slate-800">
        <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 via-purple-600 to-pink-500 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                <i class="fa-solid fa-cube text-white text-lg"></i>
            </div>
            <div>
                <h1 class="text-lg font-bold bg-gradient-to-r from-white via-slate-100 to-indigo-300 bg-clip-text text-transparent">3DGS Studio</h1>
                <p class="text-xs text-slate-400">Gaussian Splatting Pipeline & Viewer • RTX 4050 6GB</p>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <nav class="flex items-center bg-slate-900/80 p-1 rounded-xl border border-slate-800">
            <button onclick="switchTab('studio')" id="tab-btn-studio" class="tab-btn px-4 py-1.5 rounded-lg text-sm font-medium transition-all text-white bg-indigo-600 shadow-sm flex items-center gap-2">
                <i class="fa-solid fa-wand-magic-sparkles text-xs"></i> Studio 1-Click
            </button>
            <button onclick="switchTab('gallery')" id="tab-btn-gallery" class="tab-btn px-4 py-1.5 rounded-lg text-sm font-medium transition-all text-slate-400 hover:text-white flex items-center gap-2">
                <i class="fa-solid fa-shapes text-xs"></i> Bộ Sưu Tập 3D
            </button>
            <button onclick="switchTab('viewer')" id="tab-btn-viewer" class="tab-btn px-4 py-1.5 rounded-lg text-sm font-medium transition-all text-slate-400 hover:text-white flex items-center gap-2">
                <i class="fa-solid fa-vr-cardboard text-xs"></i> 3D Viewer
            </button>
            <button onclick="switchTab('docs')" id="tab-btn-docs" class="tab-btn px-4 py-1.5 rounded-lg text-sm font-medium transition-all text-slate-400 hover:text-white flex items-center gap-2">
                <i class="fa-solid fa-book-bookmark text-xs"></i> Cẩm Nang
            </button>
        </nav>

        <div class="flex items-center gap-3">
            <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                <span class="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span> RTX 4050 Ready
            </span>
        </div>
    </header>

    <!-- Main Content Area -->
    <main class="flex-1 max-w-7xl w-full mx-auto p-6">

        <!-- TAB 1: STUDIO PIPELINE -->
        <div id="tab-studio" class="tab-content space-y-6">
            <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">

                <!-- Left Column: Settings & Trình thiết lập -->
                <div class="lg:col-span-5 space-y-5">
                    <div class="glass-card rounded-2xl p-6 shadow-xl">
                        <div class="flex items-center justify-between pb-4 border-b border-slate-800 mb-5">
                            <h2 class="text-base font-bold text-white flex items-center gap-2">
                                <i class="fa-solid fa-video text-indigo-400"></i> Video Đầu Vào
                            </h2>
                            <button onclick="refreshVideos()" title="Quét lại file video" class="text-xs text-slate-400 hover:text-indigo-400">
                                <i class="fa-solid fa-rotate-right"></i> Làm mới
                            </button>
                        </div>

                        <!-- Video Selection -->
                        <div class="space-y-4">
                            <div>
                                <label class="block text-xs font-medium text-slate-300 mb-1.5">Chọn file video có sẵn trong thư mục:</label>
                                <select id="video-select" onchange="onVideoSelectChange()" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2.5 text-sm text-white focus:outline-none focus:border-indigo-500">
                                    <option value="">-- Đang quét video... --</option>
                                </select>
                            </div>

                            <div class="relative flex py-1 items-center">
                                <div class="flex-grow border-t border-slate-800"></div>
                                <span class="flex-shrink mx-3 text-xs text-slate-500 uppercase">Hoặc tải lên video mới</span>
                                <div class="flex-grow border-t border-slate-800"></div>
                            </div>

                            <!-- Upload Box -->
                            <div class="border-2 border-dashed border-slate-700 hover:border-indigo-500/50 rounded-xl p-4 text-center cursor-pointer transition-colors bg-slate-900/40 relative">
                                <input type="file" id="video-upload-input" accept="video/mp4,video/quicktime,video/webm" onchange="uploadVideoFile()" class="absolute inset-0 opacity-0 cursor-pointer">
                                <i class="fa-solid fa-cloud-arrow-up text-2xl text-slate-400 mb-1"></i>
                                <p class="text-xs font-medium text-slate-300">Bấm hoặc Kéo thả video (.mp4, .mov, .webm) vào đây</p>
                                <p class="text-[11px] text-slate-500 mt-0.5">Thời lượng lý tưởng: 20s - 45s (quay 360° chậm và đều tay)</p>
                            </div>
                        </div>

                        <!-- Pipeline Parameters -->
                        <div class="pt-5 mt-5 border-t border-slate-800 space-y-4">
                            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Cấu Hình Huấn Luyện (3DGS)</h3>

                            <div>
                                <label class="block text-xs font-medium text-slate-300 mb-1">Tên Mô Hình (Scene Name):</label>
                                <input type="text" id="scene-name-input" placeholder="ví dụ: my_room, plant_flower" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3.5 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
                            </div>

                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <label class="block text-xs font-medium text-slate-300 mb-1">Số frame trích xuất:</label>
                                    <input type="number" id="frames-input" value="110" min="50" max="300" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
                                    <span class="text-[10px] text-slate-500 mt-0.5 block">100 - 130 là tối ưu nhất</span>
                                </div>
                                <div>
                                    <label class="block text-xs font-medium text-slate-300 mb-1">Độ phân giải (-r):</label>
                                    <select id="resolution-select" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500">
                                        <option value="2" selected>Giảm 1/2 (Khuyên dùng 6GB VRAM)</option>
                                        <option value="1">Giữ nguyên 100% (Cần nhiều VRAM)</option>
                                        <option value="4">Giảm 1/4 (Siêu nhẹ & Nhanh)</option>
                                    </select>
                                </div>
                            </div>

                            <div>
                                <label class="block text-xs font-medium text-slate-300 mb-1">Chất Lượng / Số Vòng Lặp:</label>
                                <div class="grid grid-cols-2 gap-2">
                                    <label class="cursor-pointer">
                                        <input type="radio" name="iterations-radio" value="7000" checked class="peer sr-only">
                                        <div class="peer-checked:border-indigo-500 peer-checked:bg-indigo-500/10 peer-checked:text-indigo-300 border border-slate-700 bg-slate-900/60 rounded-xl p-3 text-center transition-all">
                                            <div class="text-sm font-bold">7,000 steps</div>
                                            <div class="text-[11px] text-slate-400 mt-0.5">Nhanh (~5-7 phút)</div>
                                        </div>
                                    </label>
                                    <label class="cursor-pointer">
                                        <input type="radio" name="iterations-radio" value="30000" class="peer sr-only">
                                        <div class="peer-checked:border-purple-500 peer-checked:bg-purple-500/10 peer-checked:text-purple-300 border border-slate-700 bg-slate-900/60 rounded-xl p-3 text-center transition-all">
                                            <div class="text-sm font-bold">30,000 steps</div>
                                            <div class="text-[11px] text-slate-400 mt-0.5">Siêu Nét (~15 phút)</div>
                                        </div>
                                    </label>
                                </div>
                            </div>

                            <div class="flex items-center gap-2 pt-1">
                                <input type="checkbox" id="auto-splat-checkbox" checked class="w-4 h-4 rounded text-indigo-600 bg-slate-900 border-slate-700 focus:ring-0">
                                <label for="auto-splat-checkbox" class="text-xs text-slate-300 cursor-pointer">
                                    Tự động nén sang định dạng siêu nhẹ <span class="font-bold text-indigo-400">.splat</span> sau khi dựng xong
                                </label>
                            </div>
                        </div>

                        <!-- Action Button -->
                        <div class="mt-6 pt-4 border-t border-slate-800">
                            <button id="btn-start-pipeline" onclick="startPipeline()" class="w-full py-3.5 px-4 bg-gradient-to-r from-indigo-600 via-indigo-500 to-purple-600 hover:from-indigo-500 hover:to-purple-500 text-white font-bold rounded-xl shadow-lg shadow-indigo-500/25 flex items-center justify-center gap-2 transition-all transform active:scale-[0.98]">
                                <i class="fa-solid fa-rocket text-base"></i> BẮT ĐẦU DỰNG 3D 1-CLICK
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Right Column: Live Pipeline Monitor & Console Output -->
                <div class="lg:col-span-7 space-y-5">
                    <div class="glass-card rounded-2xl p-6 shadow-xl flex flex-col h-[670px]">
                        <div class="flex items-center justify-between pb-4 border-b border-slate-800">
                            <div class="flex items-center gap-2">
                                <span id="pipeline-status-badge" class="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700">
                                    <i class="fa-solid fa-circle text-[8px] mr-1"></i> Đang chờ lệnh
                                </span>
                                <span id="pipeline-stage-text" class="text-xs text-slate-300 font-medium">Hệ thống sẵn sàng.</span>
                            </div>
                            <div id="progress-percent" class="text-sm font-bold text-indigo-400 code-font">0%</div>
                        </div>

                        <!-- Progress Bar Stages -->
                        <div class="py-4">
                            <div class="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800">
                                <div id="progress-bar-fill" class="bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 h-full w-0 transition-all duration-300 rounded-full"></div>
                            </div>

                            <!-- 4 Visual Stage Steps -->
                            <div class="grid grid-cols-4 gap-2 mt-3 text-center">
                                <div id="step-node-1" class="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                                    <div class="text-[11px] font-semibold text-slate-400">1. Cắt Ảnh</div>
                                    <div class="text-[9px] text-slate-500">Laplacian Filter</div>
                                </div>
                                <div id="step-node-2" class="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                                    <div class="text-[11px] font-semibold text-slate-400">2. COLMAP</div>
                                    <div class="text-[9px] text-slate-500">SIFT & SfM</div>
                                </div>
                                <div id="step-node-3" class="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                                    <div class="text-[11px] font-semibold text-slate-400">3. Train 3DGS</div>
                                    <div class="text-[9px] text-slate-500">Gaussian Splatting</div>
                                </div>
                                <div id="step-node-4" class="p-2 rounded-lg bg-slate-900/60 border border-slate-800">
                                    <div class="text-[11px] font-semibold text-slate-400">4. Nén .splat</div>
                                    <div class="text-[9px] text-slate-500">Tiết kiệm 88%</div>
                                </div>
                            </div>
                        </div>

                        <!-- Console Output Window -->
                        <div class="flex-1 flex flex-col min-h-0 mt-2 bg-slate-950 rounded-xl border border-slate-800 overflow-hidden">
                            <div class="px-3.5 py-2 bg-slate-900/80 border-b border-slate-800 flex items-center justify-between text-xs text-slate-400">
                                <span class="flex items-center gap-1.5"><i class="fa-solid fa-terminal text-[11px] text-indigo-400"></i> Terminal Output</span>
                                <button onclick="clearLogs()" class="hover:text-slate-200 text-[11px]">Xóa log</button>
                            </div>
                            <div id="console-logs" class="flex-1 p-3.5 overflow-y-auto code-font text-xs text-slate-300 space-y-1 select-text">
                                <div class="text-slate-500">// Hệ thống đã khởi tạo. Hãy chọn video và nhấn "Bắt đầu dựng 3D" để chạy quy trình tự động.</div>
                            </div>
                        </div>

                        <!-- Completion Card (Shown when finished) -->
                        <div id="completion-box" class="hidden mt-4 p-4 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-between">
                            <div>
                                <h4 class="text-sm font-bold text-emerald-400 flex items-center gap-2">
                                    <i class="fa-solid fa-circle-check"></i> Đã dựng thành công mô hình 3D!
                                </h4>
                                <p class="text-xs text-slate-300 mt-0.5" id="completion-details"></p>
                            </div>
                            <div class="flex gap-2">
                                <button id="btn-view-result" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg shadow flex items-center gap-1.5">
                                    <i class="fa-solid fa-eye"></i> Xem ngay
                                </button>
                                <button id="btn-open-result-folder" class="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg border border-slate-700 flex items-center gap-1.5">
                                    <i class="fa-solid fa-folder-open"></i> Mở folder
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

            </div>
        </div>

        <!-- TAB 2: MODEL GALLERY -->
        <div id="tab-gallery" class="tab-content hidden space-y-6">
            <div class="flex items-center justify-between">
                <div>
                    <h2 class="text-xl font-bold text-white">Bộ Sưu Tập Mô Hình 3D Đã Dựng</h2>
                    <p class="text-xs text-slate-400 mt-1">Danh sách toàn bộ các cảnh Gaussian Splatting đã huấn luyện trong máy của bạn.</p>
                </div>
                <button onclick="refreshModels()" class="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-xl border border-slate-700 flex items-center gap-2">
                    <i class="fa-solid fa-rotate-right"></i> Làm mới danh sách
                </button>
            </div>

            <!-- Model Grid -->
            <div id="models-grid" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                <div class="text-center py-12 col-span-3 text-slate-500 text-sm">
                    <i class="fa-solid fa-spinner fa-spin text-2xl mb-2 text-indigo-400 block"></i> Đang tải danh sách mô hình...
                </div>
            </div>
        </div>

        <!-- TAB 3: 3D VIEWER -->
        <div id="tab-viewer" class="tab-content hidden space-y-4">
            <div class="glass-card rounded-2xl p-4 flex items-center justify-between">
                <div class="flex items-center gap-3">
                    <span class="text-xs font-bold text-slate-400 uppercase">Mô hình đang xem:</span>
                    <select id="viewer-model-select" onchange="changeViewerModel()" class="bg-slate-900 border border-slate-700 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-indigo-500">
                        <option value="">-- Chọn mô hình để xem --</option>
                    </select>
                </div>
                <div class="flex items-center gap-3 text-xs">
                    <span class="text-slate-400"><i class="fa-solid fa-mouse text-indigo-400 mr-1"></i> Chuột trái: Xoay | Chuột phải: Di chuyển | Cuộn: Thu phóng</span>
                    <a href="https://superspl.at/editor" target="_blank" class="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium flex items-center gap-1.5">
                        <i class="fa-solid fa-arrow-up-right-from-square"></i> Mở Web Editor Đầy Đủ
                    </a>
                </div>
            </div>

            <!-- Viewer Container -->
            <div class="glass-card rounded-2xl overflow-hidden h-[720px] relative border border-slate-800">
                <iframe id="splat-iframe" src="https://superspl.at/editor" class="w-full h-full border-0"></iframe>
                <div id="viewer-overlay-tip" class="absolute bottom-4 left-4 right-4 bg-slate-900/90 backdrop-blur-md border border-slate-700/60 p-3 rounded-xl flex items-center justify-between text-xs text-slate-300">
                    <div class="flex items-center gap-2">
                        <i class="fa-solid fa-circle-info text-indigo-400 text-sm"></i>
                        <span>Để xem mô hình máy bạn: Nhấn nút <b>"Mở thư mục chứa file"</b> bên dưới rồi <b>kéo thả file .splat</b> vào khung trên!</span>
                    </div>
                    <button id="btn-quick-open-folder" class="px-3 py-1 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium">
                        📂 Mở Thư Mục File
                    </button>
                </div>
            </div>
        </div>

        <!-- TAB 4: DOCS & CHEAT SHEET -->
        <div id="tab-docs" class="tab-content hidden space-y-6">
            <div class="glass-card rounded-2xl p-6 shadow-xl space-y-6">
                <div>
                    <h2 class="text-lg font-bold text-white flex items-center gap-2">
                        <i class="fa-solid fa-shield-halved text-indigo-400"></i> Quy Tắc Vàng Tối Ưu Cho Card Đồ Họa RTX 4050 6GB
                    </h2>
                    <p class="text-xs text-slate-400 mt-1">Cách để render cảnh rộng mà không bao giờ bị tràn bộ nhớ VRAM (CUDA Out of Memory).</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                        <div class="text-sm font-bold text-indigo-300 flex items-center gap-2">
                            <i class="fa-solid fa-compress"></i> 1. Cờ Giảm Tỷ Lệ Ảnh (-r 2)
                        </div>
                        <p class="text-xs text-slate-400 leading-relaxed">
                            Mặc định hệ thống tự động thêm cờ <code class="text-indigo-300 bg-slate-950 px-1 py-0.5 rounded">-r 2</code> để nén độ phân giải ảnh xuống 1/2 khi train. Tiết kiệm ~2GB VRAM mà mắt thường khó nhận biết sự khác biệt.
                        </p>
                    </div>

                    <div class="p-4 rounded-xl bg-slate-900/80 border border-slate-800 space-y-2">
                        <div class="text-sm font-bold text-purple-300 flex items-center gap-2">
                            <i class="fa-solid fa-microchip"></i> 2. Nạp Dữ Liệu Lên RAM Máy Tính (--data_device cpu)
                        </div>
                        <p class="text-xs text-slate-400 leading-relaxed">
                            Toàn bộ hàng trăm tấm ảnh sẽ được giữ trên thanh RAM (16GB/32GB) của máy tính thay vì nhét hết vào VRAM 6GB của card màn hình, giảm thêm ~2-3GB VRAM.
                        </p>
                    </div>
                </div>

                <div class="border-t border-slate-800 pt-5 space-y-4">
                    <h3 class="text-sm font-bold text-white flex items-center gap-2">
                        <i class="fa-solid fa-camera text-indigo-400"></i> Bí Quyết Quay Video Để Mô Hình 3D Đẹp Nhất
                    </h3>
                    <ul class="space-y-2.5 text-xs text-slate-300 list-disc list-inside leading-relaxed">
                        <li><b>Tốc độ di chuyển:</b> Đi thật chậm và đều tay. Tránh lia máy hoặc xoay người quá nhanh (sẽ làm nhòe ảnh do motion blur khiến COLMAP không dựng được).</li>
                        <li><b>Độ bao phủ 360 độ:</b> Quay quanh vật thể ở 2–3 độ cao khác nhau (ngang tầm mắt, chếch từ trên xuống 45°, và thấp từ dưới lên).</li>
                        <li><b>Ánh sáng:</b> Đảm bảo đủ sáng, ánh sáng cố định, tránh các bề mặt phản chiếu gương bóng hoặc ánh đèn nhấp nháy.</li>
                        <li><b>Thời lượng lý tưởng:</b> Video khoảng <b>25 - 45 giây</b> ở chất lượng 1080p hoặc 4K là chuẩn nhất.</li>
                    </ul>
                </div>
            </div>
        </div>

    </main>

    <script>
        let currentTab = 'studio';
        let currentSplatPathToView = '';
        let lastLogIndex = 0;

        function switchTab(tabId) {
            currentTab = tabId;
            document.querySelectorAll('.tab-content').forEach(el => el.classList.add('hidden'));
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('bg-indigo-600', 'text-white', 'shadow-sm');
                btn.classList.add('text-slate-400');
            });

            document.getElementById('tab-' + tabId).classList.remove('hidden');
            const activeBtn = document.getElementById('tab-btn-' + tabId);
            activeBtn.classList.remove('text-slate-400');
            activeBtn.classList.add('bg-indigo-600', 'text-white', 'shadow-sm');

            if (tabId === 'gallery') {
                refreshModels();
            }
        }

        // Fetch videos list
        async function refreshVideos() {
            try {
                const res = await fetch('/api/videos');
                const vids = await res.json();
                const select = document.getElementById('video-select');
                select.innerHTML = '';

                if (vids.length === 0) {
                    select.innerHTML = '<option value="">Không tìm thấy file video nào (.mp4, .mov...)</option>';
                    return;
                }

                vids.forEach(v => {
                    const opt = document.createElement('option');
                    opt.value = v.path;
                    opt.textContent = `${v.filename} (${v.size_mb} MB)`;
                    select.appendChild(opt);
                });

                onVideoSelectChange();
            } catch (e) {
                console.error("Lỗi quét video:", e);
            }
        }

        function onVideoSelectChange() {
            const select = document.getElementById('video-select');
            const sceneInput = document.getElementById('scene-name-input');
            if (select.value) {
                const base = select.value.replace(/\\.[^/.]+$/, "");
                sceneInput.value = base;
            }
        }

        // Upload Video
        async function uploadVideoFile() {
            const fileInput = document.getElementById('video-upload-input');
            if (!fileInput.files || fileInput.files.length === 0) return;

            const file = fileInput.files[0];
            const formData = new FormData();
            formData.append('video', file);

            const statusBadge = document.getElementById('pipeline-stage-text');
            statusBadge.textContent = `Đang tải lên: ${file.name}...`;

            try {
                const res = await fetch('/api/upload_video', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (data.success) {
                    await refreshVideos();
                    document.getElementById('video-select').value = data.filename;
                    onVideoSelectChange();
                    statusBadge.textContent = `Đã tải lên xong ${file.name}!`;
                } else {
                    alert('Lỗi tải video: ' + data.error);
                }
            } catch (err) {
                alert('Lỗi upload: ' + err);
            }
        }

        // Start Pipeline
        async function startPipeline() {
            const videoPath = document.getElementById('video-select').value;
            let sceneName = document.getElementById('scene-name-input').value.trim();
            const frames = parseInt(document.getElementById('frames-input').value) || 110;
            const resolution = parseInt(document.getElementById('resolution-select').value) || 2;
            const iterations = parseInt(document.querySelector('input[name="iterations-radio"]:checked').value) || 7000;

            if (!videoPath) {
                alert('Vui lòng chọn hoặc tải lên một file video!');
                return;
            }
            if (!sceneName) {
                sceneName = videoPath.replace(/\\.[^/.]+$/, "");
            }

            const btn = document.getElementById('btn-start-pipeline');
            btn.disabled = true;
            btn.classList.add('opacity-50', 'cursor-not-allowed');

            try {
                const res = await fetch('/api/start', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        video_path: videoPath,
                        scene_name: sceneName,
                        frames: frames,
                        iterations: iterations,
                        resolution: resolution
                    })
                });
                const result = await res.json();
                if (!result.success) {
                    alert('Lỗi khởi động: ' + result.error);
                    btn.disabled = false;
                    btn.classList.remove('opacity-50', 'cursor-not-allowed');
                }
            } catch (err) {
                alert('Lỗi kết nối máy chủ: ' + err);
                btn.disabled = false;
                btn.classList.remove('opacity-50', 'cursor-not-allowed');
            }
        }

        // Poll pipeline status
        async function pollStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                // Update status badge
                const badge = document.getElementById('pipeline-status-badge');
                const stageText = document.getElementById('pipeline-stage-text');
                const progressFill = document.getElementById('progress-bar-fill');
                const progressPercent = document.getElementById('progress-percent');
                const startBtn = document.getElementById('btn-start-pipeline');

                stageText.textContent = data.stage_text;
                progressFill.style.width = data.progress + '%';
                progressPercent.textContent = data.progress + '%';

                // Step highlights
                for (let i = 1; i <= 4; i++) {
                    const stepEl = document.getElementById('step-node-' + i);
                    if (data.stage === i) {
                        stepEl.className = 'p-2 rounded-lg bg-indigo-600/20 border border-indigo-500 shadow-sm';
                    } else if (data.stage > i) {
                        stepEl.className = 'p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/30';
                    } else {
                        stepEl.className = 'p-2 rounded-lg bg-slate-900/60 border border-slate-800';
                    }
                }

                if (data.status === 'running') {
                    badge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20';
                    badge.innerHTML = '<i class="fa-solid fa-spinner fa-spin text-[10px] mr-1"></i> Đang xử lý...';
                    startBtn.disabled = true;
                    startBtn.classList.add('opacity-50', 'cursor-not-allowed');
                    document.getElementById('completion-box').classList.add('hidden');
                } else if (data.status === 'completed') {
                    badge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
                    badge.innerHTML = '<i class="fa-solid fa-check text-[10px] mr-1"></i> Hoàn thành';
                    startBtn.disabled = false;
                    startBtn.classList.remove('opacity-50', 'cursor-not-allowed');

                    const compBox = document.getElementById('completion-box');
                    compBox.classList.remove('hidden');
                    document.getElementById('completion-details').textContent = 
                        `Mô hình ${data.scene_name} (${data.final_splat || data.final_ply})`;

                    document.getElementById('btn-view-result').onclick = () => {
                        viewSplatInViewer(data.final_splat || data.final_ply);
                    };
                    document.getElementById('btn-open-result-folder').onclick = () => {
                        openFolder(data.final_splat || data.final_ply);
                    };
                } else if (data.status === 'error') {
                    badge.className = 'px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20';
                    badge.innerHTML = '<i class="fa-solid fa-triangle-exclamation text-[10px] mr-1"></i> Lỗi';
                    startBtn.disabled = false;
                    startBtn.classList.remove('opacity-50', 'cursor-not-allowed');
                }

                // Append logs
                const consoleLogs = document.getElementById('console-logs');
                if (data.logs.length > lastLogIndex) {
                    for (let i = lastLogIndex; i < data.logs.length; i++) {
                        const div = document.createElement('div');
                        div.textContent = data.logs[i];
                        if (data.logs[i].includes('❌') || data.logs[i].includes('Lỗi')) {
                            div.className = 'text-rose-400 font-medium';
                        } else if (data.logs[i].includes('✅') || data.logs[i].includes('🎉')) {
                            div.className = 'text-emerald-400 font-medium';
                        } else if (data.logs[i].includes('🚀') || data.logs[i].includes('BƯỚC')) {
                            div.className = 'text-indigo-300 font-semibold mt-1';
                        }
                        consoleLogs.appendChild(div);
                    }
                    lastLogIndex = data.logs.length;
                    consoleLogs.scrollTop = consoleLogs.scrollHeight;
                }

            } catch (err) {
                // Server might be temporarily busy
            }
        }

        function clearLogs() {
            document.getElementById('console-logs').innerHTML = '';
            lastLogIndex = 0;
        }

        // Fetch Models Gallery
        async function refreshModels() {
            const grid = document.getElementById('models-grid');
            const viewerSelect = document.getElementById('viewer-model-select');
            grid.innerHTML = '<div class="text-center py-12 col-span-3 text-slate-500 text-sm"><i class="fa-solid fa-spinner fa-spin text-2xl mb-2 text-indigo-400 block"></i> Đang tải...</div>';

            try {
                const res = await fetch('/api/models');
                const models = await res.json();

                grid.innerHTML = '';
                viewerSelect.innerHTML = '<option value="">-- Chọn mô hình để xem --</option>';

                if (models.length === 0) {
                    grid.innerHTML = '<div class="text-center py-12 col-span-3 text-slate-500 text-sm">Chưa có mô hình 3D nào được dựng trong thư mục output/</div>';
                    return;
                }

                models.forEach(m => {
                    // Populate viewer select
                    const opt = document.createElement('option');
                    opt.value = m.splat_path || m.ply_path;
                    opt.textContent = `${m.scene} (${m.iteration} steps)`;
                    viewerSelect.appendChild(opt);

                    // Create Card
                    const card = document.createElement('div');
                    card.className = 'glass-card glass-card-hover rounded-2xl p-5 flex flex-col justify-between shadow-lg relative overflow-hidden';

                    const splatBadge = m.has_splat 
                        ? `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">.splat (${m.splat_size_mb} MB)</span>`
                        : `<span class="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">Chưa nén .splat</span>`;

                    const compressBtn = !m.has_splat && m.has_ply
                        ? `<button onclick="compressToSplat('${m.ply_path}')" class="px-3 py-1.5 bg-purple-600 hover:bg-purple-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5"><i class="fa-solid fa-file-zipper"></i> Nén sang .splat</button>`
                        : '';

                    card.innerHTML = `
                        <div>
                            <div class="flex items-start justify-between">
                                <div>
                                    <h3 class="text-base font-bold text-white">${m.scene}</h3>
                                    <p class="text-xs text-slate-400 mt-0.5">${m.iteration} iterations • ${m.created_at}</p>
                                </div>
                                ${splatBadge}
                            </div>

                            <div class="mt-4 p-3 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1.5 text-xs">
                                <div class="flex justify-between">
                                    <span class="text-slate-400">File gốc (.ply):</span>
                                    <span class="code-font text-slate-200">${m.has_ply ? m.ply_size_mb + ' MB' : 'N/A'}</span>
                                </div>
                                <div class="flex justify-between">
                                    <span class="text-slate-400">File nén (.splat):</span>
                                    <span class="code-font font-bold text-indigo-400">${m.has_splat ? m.splat_size_mb + ' MB' : 'N/A'}</span>
                                </div>
                            </div>
                        </div>

                        <div class="mt-5 pt-4 border-t border-slate-800 flex items-center justify-between gap-2">
                            <button onclick="viewSplatInViewer('${m.splat_path || m.ply_path}')" class="flex-1 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-xl flex items-center justify-center gap-1.5 shadow-sm">
                                <i class="fa-solid fa-eye"></i> Xem 3D
                            </button>
                            ${compressBtn}
                            <button onclick="openFolder('${m.folder_rel}')" title="Mở thư mục trong Explorer" class="p-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-xl border border-slate-700">
                                <i class="fa-solid fa-folder-open"></i>
                            </button>
                        </div>
                    `;

                    grid.appendChild(card);
                });

            } catch (err) {
                grid.innerHTML = `<div class="text-center py-12 col-span-3 text-rose-400 text-sm">Lỗi tải danh sách: ${err}</div>`;
            }
        }

        // View model in 3D viewer tab
        function viewSplatInViewer(filePath) {
            if (!filePath) return;
            currentSplatPathToView = filePath;
            switchTab('viewer');
            document.getElementById('viewer-model-select').value = filePath;
            document.getElementById('btn-quick-open-folder').onclick = () => openFolder(filePath);
        }

        function changeViewerModel() {
            const select = document.getElementById('viewer-model-select');
            if (select.value) {
                viewSplatInViewer(select.value);
            }
        }

        // Open Windows Explorer folder
        async function openFolder(targetPath) {
            try {
                await fetch('/api/open_folder', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path: targetPath })
                });
            } catch (err) {
                alert('Lỗi mở thư mục: ' + err);
            }
        }

        // Compress PLY to SPLAT
        async function compressToSplat(plyPath) {
            if (!confirm(`Bạn có muốn nén file này sang .splat để giảm 88% dung lượng không?\\n${plyPath}`)) return;

            try {
                const res = await fetch('/api/convert_splat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ply_path: plyPath })
                });
                const data = await res.json();
                if (data.success) {
                    alert('Nén thành công! File .splat đã được tạo.');
                    refreshModels();
                } else {
                    alert('Lỗi nén: ' + data.error);
                }
            } catch (err) {
                alert('Lỗi: ' + err);
            }
        }

        // Initialize on page load
        window.onload = () => {
            refreshVideos();
            setInterval(pollStatus, 1000);
        };
    </script>
</body>
</html>
"""

class StudioRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Tắt bớt log HTTP console để tránh tràn màn hình
        pass

    def send_json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        path = url.path

        if path == "/" or path == "/index.html":
            body = HTML_PAGE.encode('utf-8')
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        elif path == "/api/status":
            with process_lock:
                data = dict(state)
            self.send_json_response(data)
            return

        elif path == "/api/videos":
            vids = scan_videos()
            self.send_json_response(vids)
            return

        elif path == "/api/models":
            models = scan_models()
            self.send_json_response(models)
            return

        # Phục vụ file tĩnh kết quả (.splat, .ply)
        elif path.startswith("/output/") or path.startswith("/data/"):
            file_rel = path.lstrip("/")
            file_abs = os.path.abspath(os.path.join(BASE_DIR, file_rel))
            # Bảo mật path traversal
            if os.path.commonpath([BASE_DIR, file_abs]) == BASE_DIR and os.path.isfile(file_abs):
                self.serve_file(file_abs)
                return
            else:
                self.send_error(404, "File not found")
                return

        self.send_error(404, "Not Found")

    def serve_file(self, file_path):
        size = os.path.getsize(file_path)
        mime, _ = mimetypes.guess_type(file_path)
        if not mime:
            mime = "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(size))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with open(file_path, "rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def do_POST(self):
        url = urlparse(self.path)
        path = url.path

        if path == "/api/start":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(raw_body)

            video_path = data.get("video_path")
            scene_name = data.get("scene_name")
            frames = int(data.get("frames", 110))
            iterations = int(data.get("iterations", 7000))
            resolution = int(data.get("resolution", 2))

            if not video_path:
                self.send_json_response({"success": False, "error": "Thiếu video_path"}, 400)
                return

            if state["status"] == "running":
                self.send_json_response({"success": False, "error": "Một tiến trình khác đang chạy!"}, 400)
                return

            # Khởi chạy pipeline trên background thread
            t = threading.Thread(
                target=run_pipeline_worker,
                args=(video_path, scene_name, frames, iterations, resolution),
                daemon=True
            )
            t.start()

            self.send_json_response({"success": True})
            return

        elif path == "/api/open_folder":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(raw_body)

            target = data.get("path", "")
            full_path = os.path.abspath(os.path.join(BASE_DIR, target))

            if os.path.isfile(full_path):
                folder = os.path.dirname(full_path)
            elif os.path.isdir(full_path):
                folder = full_path
            else:
                folder = OUTPUT_DIR

            try:
                subprocess.Popen(["explorer.exe", folder])
                self.send_json_response({"success": True})
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, 500)
            return

        elif path == "/api/convert_splat":
            content_len = int(self.headers.get("Content-Length", 0))
            raw_body = self.rfile.read(content_len).decode("utf-8")
            data = json.loads(raw_body)

            ply_rel = data.get("ply_path", "")
            ply_abs = os.path.abspath(os.path.join(BASE_DIR, ply_rel))

            if not os.path.exists(ply_abs):
                self.send_json_response({"success": False, "error": "File PLY không tồn tại"}, 404)
                return

            py_exec = sys.executable
            splat_script = os.path.join(BASE_DIR, "ply_to_splat.py")
            cmd = [py_exec, splat_script, ply_abs]
            
            try:
                res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True)
                stdout_str = res.stdout.decode('utf-8', errors='replace') if res.stdout else ""
                stderr_str = res.stderr.decode('utf-8', errors='replace') if res.stderr else ""
                if res.returncode == 0:
                    self.send_json_response({"success": True})
                else:
                    self.send_json_response({"success": False, "error": stderr_str or stdout_str}, 500)
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, 500)
            return

        elif path == "/api/upload_video":
            content_type = self.headers.get("Content-Type", "")
            if not "multipart/form-data" in content_type:
                self.send_json_response({"success": False, "error": "Content-Type must be multipart/form-data"}, 400)
                return

            try:
                # Phân tích boundary
                boundary = content_type.split("boundary=")[1].encode()
                content_len = int(self.headers.get("Content-Length", 0))
                body = self.rfile.read(content_len)

                parts = body.split(b"--" + boundary)
                uploaded_filename = None

                for part in parts:
                    if b'filename="' in part:
                        header_part, file_data = part.split(b"\r\n\r\n", 1)
                        # Bỏ \r\n cuối của file_data
                        if file_data.endswith(b"\r\n"):
                            file_data = file_data[:-2]

                        # Trích xuất filename
                        headers_str = header_part.decode('utf-8', errors='ignore')
                        for line in headers_str.split("\r\n"):
                            if "filename=" in line:
                                fname = line.split('filename="')[1].split('"')[0]
                                fname = os.path.basename(fname)
                                uploaded_filename = fname
                                target_save = os.path.join(BASE_DIR, fname)
                                with open(target_save, "wb") as f_out:
                                    f_out.write(file_data)
                                break

                if uploaded_filename:
                    self.send_json_response({"success": True, "filename": uploaded_filename})
                else:
                    self.send_json_response({"success": False, "error": "Không tìm thấy file hợp lệ trong upload"}, 400)
            except Exception as e:
                self.send_json_response({"success": False, "error": str(e)}, 500)
            return

        self.send_error(404, "Not Found")

def start_server():
    server_address = (HOST, PORT)
    try:
        httpd = ThreadingHTTPServer(server_address, StudioRequestHandler)
        print("=" * 60)
        print("🎉 3D GAUSSIAN SPLATTING WEB STUDIO ĐÃ KHỞI CHẠY THÀNH CÔNG!")
        print(f"👉 Mở trình duyệt truy cập: http://localhost:{PORT}")
        print("=" * 60)
        httpd.serve_forever()
    except OSError as e:
        if e.errno == 10048 or "already in use" in str(e).lower():
            alt_port = PORT + 1
            print(f"⚠️ Cổng {PORT} đang bận, chuyển sang cổng {alt_port}...")
            httpd = ThreadingHTTPServer((HOST, alt_port), StudioRequestHandler)
            print(f"👉 Mở trình duyệt truy cập: http://localhost:{alt_port}")
            httpd.serve_forever()
        else:
            raise e

if __name__ == "__main__":
    start_server()
