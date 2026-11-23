# 🚀 3DGS_Mini: Lightweight 3D Gaussian Splatting Studio & Video-to-3D Pipeline

<p align="center">
  <img src="assets/teaser.png" alt="3DGS Mini Teaser" width="85%" style="border-radius: 12px; box-shadow: 0 8px 30px rgba(0,0,0,0.5);">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge&logo=python" alt="Python 3.10">
  <img src="https://img.shields.io/badge/PyTorch-2.3.0%2Bcu121-ee4c2c?style=for-the-badge&logo=pytorch" alt="PyTorch">
  <img src="https://img.shields.io/badge/GPU-RTX%204050%206GB%20Optimized-76b900?style=for-the-badge&logo=nvidia" alt="RTX 4050">
  <img src="https://img.shields.io/badge/Web%20UI-Built--in-6366f1?style=for-the-badge" alt="Web UI">
  <img src="https://img.shields.io/badge/Export-.SPLAT%20(-88%25)-10b981?style=for-the-badge" alt="SPLAT">
</p>

---

## 🌟 Giới Thiệu (Overview)

**`3DGS_Mini`** là một phiên bản tối ưu hóa toàn diện của **3D Gaussian Splatting**, được đóng gói thành một bộ công cụ **Studio 1-Click** hoàn chỉnh dành cho máy tính cá nhân và card đồ họa phổ thông (đặc biệt tối ưu hóa riêng cho **NVIDIA RTX 4050 6GB Laptop GPU**).

Không cần phải gõ dòng lệnh phức tạp hay lo lắng về lỗi tràn bộ nhớ VRAM (`CUDA Out of Memory`), bạn có thể dễ dàng chuyển đổi bất kỳ đoạn **video quay bằng điện thoại (.mp4)** thành **mô hình 3D tương tác chân thực** chỉ với 1 cú click chuột!

---

## ✨ Tính Năng Nổi Bật (Key Features)

| Tính Năng | Chi Tiết |
| :--- | :--- |
| 🌐 **Modern Web UI Studio** | Giao diện Web trực quan: Kéo thả video, tùy chỉnh cấu hình, theo dõi tiến trình 4 giai đoạn theo thời gian thực và quản lý thư viện mô hình 3D. |
| 🎥 **1-Click Video to 3D** | Pipeline khép kín tự động: Cắt frame thông minh ➔ Lọc mờ (Laplacian blur) ➔ COLMAP SfM ➔ Huấn luyện 3DGS ➔ Tự động nén sang `.splat`. |
| ⚡ **Tối Ưu RTX 4050 6GB** | Cấu hình nạp dữ liệu lên RAM hệ thống (`--data_device cpu`) kết hợp giảm tỉ lệ ảnh thông minh (`-r 2`), đảm bảo không bao giờ bị tràn VRAM. |
| 📦 **Nén Siêu Nhẹ (.splat)** | Tích hợp thuật toán nén giảm tới **88% dung lượng** (từ ~250MB `.ply` xuống còn ~25-30MB `.splat`), mở tức thì trên trình duyệt web. |
| 👁️ **Interactive 3D Viewer** | Nhúng sẵn trình xem 3D WebGL trực tiếp, hỗ trợ xoay 360°, phóng to thu nhỏ và căn chỉnh góc nhìn mượt mà. |
| 🖱️ **File Chạy 1-Click (.bat)** | Kèm sẵn các file batch tự động kích hoạt môi trường và khởi chạy server/pipeline mà không cần gõ lệnh. |

---

## 🛠️ Cấu Trúc Dự Án (Project Structure)

```text
3DGS_Mini/
├── web_ui.py                  # Máy chủ Web Studio & REST API tích hợp 3D Viewer
├── video_to_3dgs.py           # Pipeline tự động 1-Click từ Video sang 3D (.ply & .splat)
├── process_video.py           # Trích xuất khung hình video & lọc mờ Laplacian
├── ply_to_splat.py            # Thuật toán nén .ply sang định dạng web .splat (-88%)
├── chay_web_ui.bat            # 1-Click mở giao diện Web Studio trên trình duyệt
├── chay_room_tour.bat         # 1-Click chạy mẫu demo video phòng
├── HUONG_DAN_SU_DUNG.md       # Cẩm nang hướng dẫn sử dụng chi tiết từ A-Z
├── environment_rtx40.yml      # Cấu hình môi trường Conda tối ưu cho RTX 40-series
├── gaussian_renderer/         # Module render Gaussian tối ưu tương thích đa nền tảng
├── data/                      # Thư mục chứa dữ liệu trích xuất từ video (tự động tạo)
└── output/                    # Thư mục lưu kết quả mô hình 3D (.ply & .splat)
```

---

## 🚀 Hướng Dẫn Sử Dụng Nhanh (Quick Start)

### Cách 1: Sử dụng Giao diện Web UI (Khuyên dùng)

1. Click đúp vào file **`chay_web_ui.bat`** (hoặc chạy lệnh):
   ```powershell
   python web_ui.py
   ```
2. Mở trình duyệt truy cập: **`http://localhost:7860`**
3. Kéo thả file video `.mp4` vào giao diện và nhấn nút **"🚀 BẮT ĐẦU DỰNG 3D 1-CLICK"**!

<p align="center">
  <img src="assets/web_preview.png" alt="3DGS Web UI Preview" width="85%" style="border-radius: 8px;" onerror="this.style.display='none'">
</p>

### Cách 2: Chạy Dòng Lệnh Tự Động (CLI)

```powershell
# Kích hoạt môi trường
.\.venv\Scripts\Activate.ps1

# Chạy tự động từ video bất kỳ:
python video_to_3dgs.py -v "my_video.mp4" -s "my_scene" --frames 110 --iterations 7000 -r 2
```

Sau khi chạy xong, kết quả `.splat` và `.ply` sẽ nằm tại:  
`output/my_scene_demo/point_cloud/iteration_7000/point_cloud.splat`

---

## 📦 Cách Xem Mô Hình 3D Đã Dựng

* **Cách 1 (Trực tiếp):** Xem ngay trên tab **"3D Viewer"** của Web UI.
* **Cách 2 (Online):** Truy cập **[SuperSplat Editor](https://superspl.at/editor)** và kéo thả file `point_cloud.splat` vào để xem mượt mà 60fps trên mọi thiết bị.

---

## 💡 Bí Quyết Quay Video Chuẩn Đẹp Cho 3DGS

1. **Quỹ đạo quay:** Đi chậm vòng quanh vật thể 360° ở 2–3 độ cao khác nhau (ngang tầm mắt, chếch 45° từ trên xuống, thấp từ dưới lên).
2. **Thời lượng:** Khoảng **25 đến 45 giây** ở độ phân giải 1080p hoặc 4K.
3. **Ánh sáng:** Đủ sáng, ánh sáng cố định, tránh rung lắc hoặc lia máy quá nhanh (motion blur).

---

## ⚖️ Giấy Phép & Lời Cảm Ơn (License & Acknowledgments)

Dự án này được kế thừa và phát triển từ công trình nghiên cứu gốc:
* **Inria / GraphDeco:** [3D Gaussian Splatting for Real-Time Radiance Field Rendering](https://repo-sam.inria.fr/fungraph/3d-gaussian-splatting/) (SIGGRAPH 2023).
* **COLMAP:** [Structure-from-Motion and Multi-View Stereo](https://colmap.github.io/).
* **PlayCanvas:** [SuperSplat Web Viewer](https://github.com/playcanvas/supersplat).

Mã nguồn được phân phối cho mục đích học tập, nghiên cứu và ứng dụng cá nhân theo điều khoản của [LICENSE.md](LICENSE.md).

---
<p align="center">
  <b>Developed & Customized by <a href="https://github.com/tanphn">tanphn</a></b>
</p>
