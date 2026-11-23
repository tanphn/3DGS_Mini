# 📘 CẨM NANG HƯỚNG DẪN SỬ DỤNG 3D GAUSSIAN SPLATTING TỪ A ĐẾN Z

> **Dành cho:** Người sử dụng trực tiếp dự án trên máy Windows (RTX 4050 6GB)  
> **Cập nhật ngày:** 09/11/2026  
> **Thư mục làm việc chính:** `c:\Users\ASUS\Documents\code\3dgs_Test\gaussian-splatting`

---

## 📑 MỤC LỤC
0. [🌟 GIAO DIỆN WEB UI 1-CLICK (Mới nhất - Khuyên dùng)](#0-giao-diện-web-ui-1-click-mới-nhất---khuyên-dùng)
1. [Khắc phục nhanh: Tại sao "Không plot được" file .splat / .ply?](#1-khắc-phục-nhanh-tại-sao-không-plot-được-file-splat--ply)
2. [Cách xem mô hình 3D (Online & Offline)](#2-cách-xem-mô-hình-3d-online--offline)
3. [Quy trình 1: Tự động 1-Click từ Video sang 3D (.splat & .ply)](#3-quy-trình-1-tự-động-1-click-từ-video-sang-3d)
4. [Kỹ thuật quay video để mô hình 3D đẹp nhất](#4-kỹ-thuật-quay-video-để-mô-hình-3d-đẹp-nhất)
5. [Quy trình 2: Huấn luyện thủ công & Đẩy chất lượng lên 30,000 steps](#5-quy-trình-2-huấn-luyện-thủ-công--đẩy-chất-lượng-lên-30000-steps)
6. [Quy trình 3: Nén mô hình (.ply ➔ .splat) tiết kiệm 88% dung lượng](#6-quy-trình-3-nén-mô-hình-ply--splat)
7. [So sánh: Khi nào dùng .ply và khi nào dùng .splat?](#7-so-sánh-khi-nào-dùng-ply-và-khi-nào-dùng-splat)
8. [Quy tắc vàng chống tràn bộ nhớ GPU (RTX 4050 6GB)](#8-quy-tắc-vàng-chống-tràn-bộ-nhớ-gpu-rtx-4050-6gb)
9. [Bảng tra cứu lệnh nhanh (Cheat Sheet)](#9-bảng-tra-cứu-lệnh-nhanh-cheat-sheet)

---

## 0. 🌟 Giao Diện Web UI 1-Click (Mới Nhất - Khuyên Dùng)

Bạn không cần phải mở Terminal gõ lệnh phức tạp nữa! Hệ thống đã có sẵn **Giao diện Web Studio trực quan**:

### Cách khởi động:
- **Cách 1 (Nhanh nhất):** Click đúp vào file [`chay_web_ui.bat`](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/chay_web_ui.bat) trong thư mục dự án.
- **Cách 2 (Qua dòng lệnh):**
  ```powershell
  cd c:\Users\ASUS\Documents\code\3dgs_Test\gaussian-splatting
  .\.venv\Scripts\Activate.ps1
  python web_ui.py
  ```
- Trình duyệt sẽ tự động mở trang web tại địa chỉ: **[http://localhost:7860](http://localhost:7860)**.

### Các tính năng trên Web UI:
1. 🚀 **Studio 1-Click:** Kéo thả video hoặc chọn video có sẵn, chỉnh số frame, chọn chất lượng (7k / 30k) và bấm **"Bắt đầu dựng 3D"**. Có thanh tiến trình 4 giai đoạn và màn hình terminal theo dõi trực tiếp.
2. 🎨 **Bộ Sưu Tập 3D (Model Gallery):** Xem danh sách toàn bộ các mô hình đã dựng kèm dung lượng `.ply` và `.splat`, nút nén 1-click và nút mở thư mục.
3. 🌐 **3D Viewer:** Tích hợp trình xem 3D trực tiếp, xoay 360 độ và phóng to thu nhỏ.
4. 📘 **Cẩm nang & Quy tắc vàng:** Tra cứu nhanh thông số tối ưu cho RTX 4050.

---

---

## 1. Khắc Phục Nhanh: Tại Sao "Không Plot Được" File .splat / .ply?

### Nguyên nhân:
Nếu bạn click đúp vào file `point_cloud.splat` hoặc `point_cloud.ply` ngay trong giao diện VS Code / Cursor / IDE, trình biên tập sẽ báo lỗi:
> *"The file is not displayed in the text editor because it is either binary or very large."*

**Lý do:** VS Code bản chất là **trình soạn thảo văn bản (Text Editor)**, nó không có sẵn engine đồ họa 3D WebGL/DirectX để render mô hình hàng triệu điểm 3D Gaussian Splatting dạng nhị phân.

👉 **Muốn xem / plot mô hình, bạn chỉ cần làm theo Mục 2 dưới đây (mất chưa đầy 5 giây)!**

---

## 2. Cách Xem Mô Hình 3D (Online & Offline)

### Cách 1: Xem bằng Web Viewer (Khuyên dùng - Nhanh nhất & Đẹp nhất)

1. Mở trình duyệt Web (Chrome, Edge, Firefox, Brave) và truy cập:
   👉 **[https://superspl.at/editor](https://superspl.at/editor)** (hoặc [https://playcanvas.com/supersplat/editor](https://playcanvas.com/supersplat/editor))
2. Mở thư mục chứa file trong máy bằng cách chạy lệnh sau trong PowerShell:
   ```powershell
   explorer.exe "c:\Users\ASUS\Documents\code\3dgs_Test\gaussian-splatting\output\plant_demo\point_cloud\iteration_7000"
   ```
3. **Kéo thả** file `point_cloud.splat` (hoặc `point_cloud.ply`) từ cửa sổ Windows Explorer thả thẳng vào trang web.
4. **Thao tác điều khiển góc nhìn:**
   - **Xoay (Rotate):** Giữ chuột trái và kéo.
   - **Di chuyển (Pan):** Giữ chuột phải (hoặc Shift + chuột trái) và kéo.
   - **Phóng to / Thu nhỏ (Zoom):** Lăn bánh xe chuột.
   - **Căn giữa tâm vật thể:** Nhấn phím `F` trên bàn phím.

### Danh sách các file mô hình đã dựng sẵn trong máy bạn:
| Mô hình | Số bước (Iterations) | File nén Web (.splat) | File gốc (.ply) |
| :--- | :--- | :--- | :--- |
| **Chậu cây (`plant`)** | 7,000 steps | [point_cloud.splat](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/output/plant_demo/point_cloud/iteration_7000/point_cloud.splat) (25 MB) | [point_cloud.ply](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/output/plant_demo/point_cloud/iteration_7000/point_cloud.ply) (196 MB) |
| **Xe tải (`truck`)** | 30,000 steps (Nét nhất) | [point_cloud.splat](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/output/truck_30k/point_cloud/iteration_30000/point_cloud.splat) (32 MB) | [point_cloud.ply](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/output/truck_30k/point_cloud/iteration_30000/point_cloud.ply) (283 MB) |
| **Phòng chơi (`playroom`)** | 7,000 steps | N/A | [point_cloud.ply](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/output/playroom_demo/point_cloud/iteration_7000/point_cloud.ply) (217 MB) |
| **Tượng (`drjohnson`)** | 7,000 steps | N/A | [point_cloud.ply](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/output/drjohnson_demo/point_cloud/iteration_7000/point_cloud.ply) (240 MB) |

---

## 3. Quy Trình 1: Tự Động 1-Click Từ Video Sang 3D

Bạn đã có sẵn công cụ tự động hóa toàn diện tại [`video_to_3dgs.py`](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/video_to_3dgs.py).

### Các bước thực hiện:
1. Copy file video của bạn (định dạng `.mp4`, `.mov`, `.avi`) vào thư mục `gaussian-splatting` (ví dụ `my_room.mp4`).
2. Mở PowerShell và chạy:
   ```powershell
   cd c:\Users\ASUS\Documents\code\3dgs_Test\gaussian-splatting
   .\.venv\Scripts\Activate.ps1

   python video_to_3dgs.py -v "my_room.mp4"
   ```
3. **Chương trình sẽ tự động chạy 100% không cần can thiệp:**
   - 📸 **Bước 1:** Cắt ~100-120 ảnh sắc nét, lọc bỏ các khung hình mờ (Laplacian blur filter).
   - 🔍 **Bước 2 (COLMAP):** Trích xuất đặc trưng SIFT, ghép cặp camera (Sequential Matching) và định vị không gian 3D.
   - 🔄 **Bước 3:** Khử méo hình ảnh (Undistort) sang tiêu chuẩn camera Pinhole.
   - 🧠 **Bước 4 (3DGS):** Huấn luyện mô hình 7,000 steps tối ưu cho RTX 4050.
   - 📦 **Bước 5:** Tự động nén sang định dạng siêu nhẹ `.splat`.
4. File đầu ra sẽ nằm tại: `output/my_room_demo/point_cloud/iteration_7000/point_cloud.splat`.

---

## 4. Kỹ Thuật Quay Video Để Mô Hình 3D Đẹp Nhất

COLMAP và 3D Gaussian Splatting cần nhìn thấy sự giao thoa (overlap) giữa các góc nhìn. Khi quay video:

1. **Tốc độ di chuyển:** Đi thật chậm và đều tay. Tránh lia máy hoặc xoay người quá nhanh (sẽ làm nhòe hình do motion blur).
2. **Quỹ đạo quay:**
   - **Với đồ vật đơn lẻ (chậu cây, bàn ghế, tượng):** Đi vòng tròn quanh vật thể 360 độ ở 2-3 độ cao khác nhau (ngang tầm mắt, chếch từ trên xuống, thấp từ dưới lên).
   - **Với cả căn phòng:** Đứng từ 4 góc phòng quay quét vào giữa, sau đó đi men theo các bức tường quay hướng đối diện.
3. **Ánh sáng:** Đảm bảo đủ sáng, ánh sáng cố định, không bật đèn nhấp nháy hoặc ngược sáng quá gắt.
4. **Thời lượng lý tưởng:** Khoảng **20 đến 45 giây** ở độ phân giải 1080p hoặc 4K (hệ thống sẽ tự động giảm tỷ lệ tối ưu khi trích xuất).

---

## 5. Quy Trình 2: Huấn Luyện Thủ Công & Đẩy Chất Lượng Lên 30,000 Steps

Nếu bạn muốn huấn luyện lại một cảnh bất kỳ với độ chi tiết cao hơn (30,000 steps thay vì 7,000 steps):

### Lệnh huấn luyện chất lượng cao (30,000 steps):
```powershell
cd c:\Users\ASUS\Documents\code\3dgs_Test\gaussian-splatting
.\.venv\Scripts\Activate.ps1

python train.py `
  -s data/plant `
  -m output/plant_30k `
  --iterations 30000 `
  --save_iterations 7000 30000 `
  -r 2 `
  --data_device cpu
```

*(Thời gian chạy: Khoảng 12 - 18 phút trên card RTX 4050).*

Sau khi chạy xong, nén file chất lượng cao đó lại:
```powershell
python ply_to_splat.py output/plant_30k/point_cloud/iteration_30000/point_cloud.ply
```

---

## 6. Quy Trình 3: Nén Mô Hình (.ply ➔ .splat)

Script [`ply_to_splat.py`](file:///c:/Users/ASUS/Documents/code/3dgs_Test/gaussian-splatting/ply_to_splat.py) giúp giảm tới 88% kích thước file:

```powershell
cd c:\Users\ASUS\Documents\code\3dgs_Test\gaussian-splatting
.\.venv\Scripts\Activate.ps1

# Cú pháp: python ply_to_splat.py "đường_dẫn_file.ply"
python ply_to_splat.py "output/plant_demo/point_cloud/iteration_7000/point_cloud.ply"
```
Kết quả: Tạo ra file cùng tên nhưng đuôi `.splat` ngay bên cạnh file `.ply`.

---

## 7. So Sánh: Khi Nào Dùng .ply Và Khi Nào Dùng .splat?

| Tiêu chí | File Gốc `.ply` | File Nén `.splat` |
| :--- | :--- | :--- |
| **Dung lượng** | Rất nặng (~200MB - 500MB) | **Siêu nhẹ (~25MB - 35MB)** *(Giảm ~88%)* |
| **Tốc độ tải web** | Chậm, tốn RAM trình duyệt | **Mở tức thì, cực kỳ mượt** |
| **Độ sắc nét & Bóng bẩy** | **Tối đa 100%** (Lưu giữ đầy đủ Spherical Harmonics bậc 1, 2, 3) | **~90-95%** (Chỉ giữ màu gốc DC, lượng tử hóa góc xoay sang 8-bit) |
| **Mục đích sử dụng** | Lưu trữ dữ liệu gốc, render video nghiên cứu, tiếp tục huấn luyện | **Gửi cho khách hàng, nhúng vào trang web, chia sẻ nhanh** |

---

## 8. Quy Tắc Vàng Chống Tràn Bộ Nhớ GPU (RTX 4050 6GB)

Card RTX 4050 có **6GB VRAM**. Nếu chạy cấu hình mặc định của mã nguồn gốc, máy sẽ bị lỗi **CUDA Out of Memory**.  
👉 **Khi gõ lệnh `train.py`, LUÔN LUÔN kèm theo 2 cờ:**

1. `-r 2`: Giảm kích thước ảnh xuống 1/2 để giảm lượng bộ nhớ GPU (giúp tiết kiệm ~2GB VRAM mà mắt thường khó nhận biết khác biệt).
2. `--data_device cpu`: Nạp ảnh huấn luyện vào thanh RAM máy tính thay vì giữ toàn bộ trên bộ nhớ GPU (tiết kiệm thêm ~2-3GB VRAM).

---

## 9. Bảng Tra Cứu Lệnh Nhanh (Cheat Sheet)

### Kích hoạt môi trường:
```powershell
cd c:\Users\ASUS\Documents\code\3dgs_Test\gaussian-splatting
.\.venv\Scripts\Activate.ps1
```

### Chạy tự động 1-Click video:
```powershell
python video_to_3dgs.py -v "tên_video.mp4"
```

### Nén file .ply bất kỳ sang .splat:
```powershell
python ply_to_splat.py "output/tên_mô_hình/point_cloud/iteration_7000/point_cloud.ply"
```

### Mở thư mục kết quả để kéo thả vào trình duyệt:
```powershell
explorer.exe "output\plant_demo\point_cloud\iteration_7000"
```
*(Trình duyệt xem trực tiếp: **[https://superspl.at/editor](https://superspl.at/editor)**)*
