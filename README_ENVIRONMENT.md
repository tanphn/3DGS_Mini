# Hướng Dẫn Kỹ Thuật: Cấu Hình Môi Trường & Chạy 3D Gaussian Splatting
> **Dành cho:** AI Agent & Developers tiếp nhận dự án này  
> **Cập nhật lần cuối:** 2026-11-02  
> **Tài liệu phân tích:** `environment.yml` & `environment_rtx40.yml`

---

## 1. Phân Tích Chi Tiết Tệp `environment.yml`

Tệp [`environment.yml`](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/environment.yml) là tệp định nghĩa môi trường Conda gốc do nhóm tác giả Inria công bố (năm 2023):

```yaml
name: gaussian_splatting
channels:
  - pytorch
  - conda-forge
  - defaults
dependencies:
  - cudatoolkit=11.6
  - plyfile
  - python=3.7.13
  - pip=22.3.1
  - pytorch=1.12.1
  - torchaudio=0.12.1
  - torchvision=0.13.1
  - tqdm
  - pip:
    - submodules/diff-gaussian-rasterization  # C++/CUDA Custom Rasterizer
    - submodules/simple-knn                  # C++/CUDA KNN Search
    - submodules/fused-ssim                  # CUDA Fast SSIM Loss
    - opencv-python
    - joblib
```

### Ý nghĩa của từng thành phần:
- **`cudatoolkit=11.6` & `pytorch=1.12.1`**: Phiên bản PyTorch và CUDA Runtime cổ điển.
- **`python=3.7.13`**: Phiên bản Python cũ (đã End-of-Life).
- **Các submodules cục bộ (dòng 16–18)**:
  - `diff-gaussian-rasterization`: Trình render vi phân (rasterizer) viết bằng C++/CUDA - cốt lõi thuật toán 3DGS.
  - `simple-knn`: Thư viện tính K-Nearest Neighbors dựa trên CUDA để khởi tạo kích thước ban đầu cho các Gaussian.
  - `fused-ssim`: Hàm mất mát SSIM được tối ưu trực tiếp bằng CUDA kernel.
  > ⚠️ **LƯU Ý:** 3 thư viện trên **KHÔNG PHẢI** là wheel tải từ PyPI, mà là mã nguồn C++/CUDA cần được biên dịch cục bộ (JIT/setup.py build) tại thời điểm cài đặt.

---

## 2. ⚠️ CẢNH BÁO QUAN TRỌNG: Xung Đột Phần Cứng (Gotchas)

### Thông số máy tính hiện tại:
- **Hệ điều hành:** Windows 11 (64-bit)
- **GPU:** NVIDIA GeForce RTX 4050 Laptop GPU (6GB VRAM)
- **Kiến trúc GPU:** Ada Lovelace (`sm_89` / Compute Capability 8.9)
- **NVIDIA Driver:** 566.26 (Hỗ trợ CUDA 12.7)

### Vấn đề chí mạng với `environment.yml` gốc:
1. **Lỗi kiến trúc GPU (`sm_89`):**  
   `environment.yml` gốc chỉ định **CUDA 11.6** và **PyTorch 1.12.1**. Kiến trúc Ada Lovelace (RTX 40-series) chỉ được hỗ trợ từ **CUDA 11.8 trở lên**. Nếu cố tình cài theo file gốc, khi chạy `train.py` sẽ gặp lỗi runtime không thể khắc phục:
   ```text
   RuntimeError: CUDA error: no kernel image is available for execution on the device
   ```
2. **Python 3.7 không tương thích:**  
   Python 3.7 không hỗ trợ PyTorch hiện đại và không tương thích với nhiều thư viện wheel mới trên Windows.

### 👉 Giải pháp: Sử dụng [`environment_rtx40.yml`](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/environment_rtx40.yml)
File này đã được tối ưu sẵn cho card RTX 4050:
- **Python:** `3.10`
- **PyTorch:** `2.1.2`
- **CUDA:** `11.8` (hoặc `12.1` tương thích hoàn hảo kiến trúc `sm_89`)

---

## 3. Điều Kiện Tiên Quyết Để Cài Đặt Trên Windows

Để cài đặt thành công các submodules CUDA (`diff-gaussian-rasterization`, `simple-knn`), hệ điều hành Windows bắt buộc phải có:

1. **Visual Studio C++ Compiler (`cl.exe`):**
   - Đã cài **Visual Studio 2019/2022** kèm workload *"Desktop development with C++"*.
2. **CUDA Toolkit:**
   - Cài đặt bản **CUDA Toolkit 11.8** (hoặc 12.1) khớp với phiên bản PyTorch.
   - Đảm bảo lệnh `nvcc --version` trong terminal trả về kết quả hợp lệ.
3. **Conda Package Manager:**
   - Đã cài **Miniconda** hoặc **Anaconda**.

---

## 4. Quy Trình Cài Đặt Chuẩn Cho Agent Thực Hiện

Khi máy chủ đã có đủ Visual Studio và CUDA Toolkit, Agent thực hiện theo thứ tự các lệnh sau trong PowerShell/Command Prompt:

```powershell
# Cách 1: Sử dụng môi trường ảo .venv đã tạo sẵn trong repo (Khuyến nghị - Dùng được ngay)
cd c:\Users\ASUS\Documents\code\3dgs_Test\gaussian-splatting
.\.venv\Scripts\Activate.ps1

# Cách 2: Tạo lại môi trường Conda từ đầu (nếu cần)
$env:DISTUTILS_USE_SDK="1"
conda env create --file environment_rtx40.yml
conda activate gaussian_splatting

# Kiểm tra PyTorch nhận diện GPU:
python -c "import torch; print('CUDA available:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0))"
```

---

## 5. Dữ Liệu Sẵn Có & Lệnh Chạy Thử Nghiệm (Demo)

### Vị trí Dataset trong máy:
Đã tải và giải nén sẵn bộ dữ liệu Tanks & Temples:
- **Thư mục dataset:** [`gaussian-splatting/tandt_db/tandt/truck`](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/tandt_db/tandt/truck)
- **Số lượng ảnh:** 251 ảnh (`images/`) kèm camera poses trong (`sparse/0/`).

### Ràng buộc VRAM (6GB):
Card RTX 4050 có **6GB VRAM**. Nếu chạy cấu hình mặc định (30,000 steps, full resolution, GPU cache) sẽ bị tràn VRAM (**CUDA Out Of Memory**).  
👉 **BẮT BUỘC sử dụng các tham số tối ưu sau khi train:**

```powershell
python train.py `
  -s tandt_db/tandt/truck `
  -m output/truck_demo `
  --iterations 7000 `
  -r 2 `
  --data_device cpu
```

#### Ý nghĩa các tham số tối ưu:
| Tham số | Mục đích |
| :--- | :--- |
| `-s tandt_db/tandt/truck` | Đường dẫn đến source data đã có sẵn cấu trúc COLMAP |
| `-m output/truck_demo` | Thư mục lưu checkpoint và file `.ply` đầu ra |
| `--iterations 7000` | Giới hạn 7,000 bước (khoảng 5-10 phút) để kiểm thử nhanh thay vì 30,000 bước |
| `-r 2` | Giảm kích thước ảnh xuống 1/2 để giảm lượng bộ nhớ GPU |
| `--data_device cpu` | Đưa ảnh lên RAM thay vì VRAM của GPU, giúp tiết kiệm ~2-3GB VRAM |

---

## 6. Xem Kết Quả Huấn Luyện (Output)

File kết quả dạng Point Cloud 3D Gaussians sẽ xuất hiện tại:
`output/truck_demo/point_cloud/iteration_7000/point_cloud.ply`

**Cách xem nhanh nhất:**
1. Mở trình duyệt truy cập: [PlayCanvas Supersplat](https://playcanvas.com/supersplat/editor)
2. Kéo thả file `point_cloud.ply` hoặc `point_cloud.splat` vào trình duyệt để xoay/zoom xem thời gian thực.

---

## 7. Nén Mô Hình 3DGS (.ply ➔ .splat)

Để giảm dung lượng file phục vụ hiển thị web mượt mà (giảm ~88% dung lượng):
```powershell
python ply_to_splat.py "path/to/point_cloud.ply"

# Ví dụ nén bản 30,000 steps:
python ply_to_splat.py "output/truck_30k/point_cloud/iteration_30000/point_cloud.ply"
```
Kết quả tạo ra file `.splat` siêu nhẹ (~32MB thay vì ~270MB), mở ngay lập tức trên SuperSplat mà không tốn RAM.

---

## 8. Xử Lý Video Tự Quay Thành Dữ Liệu 3DGS (`process_video.py`)

Để biến 1 file video (ví dụ `my_room.mp4`) thành thư mục dữ liệu chuẩn cho 3DGS:
```powershell
python process_video.py -v "my_room.mp4" --frames 120
```
- Tự động phân tích FPS và cắt đều ~120 ảnh chất lượng cao vào `data/my_room/input/`.
- Tự động đo độ nét (Laplacian blur score) và thu nhỏ kích thước hợp lý (tối đa 1920px) để tăng tốc độ tính toán COLMAP.
- In sẵn toàn bộ lệnh tiếp theo (COLMAP ➔ Train ➔ Nén splat).

---

## 9. Tự Động Hóa 1-Click Từ Video Sang Mô Hình 3D (`video_to_3dgs.py`)

Chỉ cần đúng **1 lệnh duy nhất** để thực hiện trọn vẹn: Cắt video ➔ COLMAP (Feature + Match + Map + Undistort) ➔ Train 3DGS ➔ Nén sang `.splat`:

```powershell
python video_to_3dgs.py -v "my_room.mp4"
```
Kết quả `.ply` và `.splat` sẽ được tự động tạo sẵn trong thư mục `output/my_room_demo/`.



