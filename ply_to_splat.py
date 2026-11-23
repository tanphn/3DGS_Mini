import sys
import os
import argparse
import shutil
import numpy as np

# Bắt buộc UTF-8 cho console Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from plyfile import PlyData, PlyElement

SH_C0 = 0.28209479177387814

def center_ply_file(input_ply_path):
    try:
        plydata = PlyData.read(input_ply_path)
        v = plydata['vertex']
        data = v.data.copy()
        cx = (data['x'].max() + data['x'].min()) / 2.0
        cy = (data['y'].max() + data['y'].min()) / 2.0
        cz = (data['z'].max() + data['z'].min()) / 2.0
        if abs(cx) > 0.1 or abs(cy) > 0.1 or abs(cz) > 0.1:
            data['x'] -= cx
            data['y'] -= cy
            data['z'] -= cz
            el = PlyElement.describe(data, 'vertex')
            tmp_path = input_ply_path + ".tmp.ply"
            PlyData([el]).write(tmp_path)
            shutil.move(tmp_path, input_ply_path)
            print(f"Auto-centered source PLY: shifted by ({-cx:.2f}, {-cy:.2f}, {-cz:.2f})")
    except Exception as e:
        print(f"Warning: could not center PLY in place: {e}")

def convert_ply_to_splat(input_ply_path, output_splat_path=None, opacity_threshold=0.01, center=True):
    if not os.path.exists(input_ply_path):
        print(f"Error: File not found: {input_ply_path}")
        return False

    if center:
        center_ply_file(input_ply_path)

    if output_splat_path is None:
        base, _ = os.path.splitext(input_ply_path)
        output_splat_path = base + ".splat"

    print(f"Reading PLY: {input_ply_path}...")
    plydata = PlyData.read(input_ply_path)
    vertex = plydata['vertex']

    x = np.asarray(vertex['x'], dtype=np.float32)
    y = np.asarray(vertex['y'], dtype=np.float32)
    z = np.asarray(vertex['z'], dtype=np.float32)
    positions = np.stack([x, y, z], axis=-1)

    scale_0 = np.asarray(vertex['scale_0'], dtype=np.float32)
    scale_1 = np.asarray(vertex['scale_1'], dtype=np.float32)
    scale_2 = np.asarray(vertex['scale_2'], dtype=np.float32)
    scales = np.exp(np.stack([scale_0, scale_1, scale_2], axis=-1))

    f_dc_0 = np.asarray(vertex['f_dc_0'], dtype=np.float32)
    f_dc_1 = np.asarray(vertex['f_dc_1'], dtype=np.float32)
    f_dc_2 = np.asarray(vertex['f_dc_2'], dtype=np.float32)
    rgb = (0.5 + SH_C0 * np.stack([f_dc_0, f_dc_1, f_dc_2], axis=-1)) * 255.0
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)

    raw_opacity = np.asarray(vertex['opacity'], dtype=np.float32)
    opacity = 1.0 / (1.0 + np.exp(-raw_opacity))
    
    # Filter out near-invisible Gaussians if requested
    valid_mask = opacity >= opacity_threshold
    print(f"Filtered {np.sum(~valid_mask)} invisible points (opacity < {opacity_threshold}). Retained {np.sum(valid_mask)} points.")

    positions = positions[valid_mask]
    scales = scales[valid_mask]
    rgb = rgb[valid_mask]
    opacity = opacity[valid_mask]

    # Auto-center to (0, 0, 0) so web viewers frame the object immediately
    if center:
        centroid = (positions.max(axis=0) + positions.min(axis=0)) / 2.0
        positions -= centroid
        print(f"Auto-centered model: shifted by {-centroid}")

    alpha = np.clip(opacity * 255.0, 0, 255).astype(np.uint8)[:, None]
    rgba = np.concatenate([rgb, alpha], axis=-1)

    rot_0 = np.asarray(vertex['rot_0'], dtype=np.float32)[valid_mask]
    rot_1 = np.asarray(vertex['rot_1'], dtype=np.float32)[valid_mask]
    rot_2 = np.asarray(vertex['rot_2'], dtype=np.float32)[valid_mask]
    rot_3 = np.asarray(vertex['rot_3'], dtype=np.float32)[valid_mask]
    rots = np.stack([rot_0, rot_1, rot_2, rot_3], axis=-1)
    norm = np.linalg.norm(rots, axis=-1, keepdims=True)
    norm[norm == 0] = 1.0
    rots = rots / norm
    rots_u8 = np.clip(rots * 128.0 + 128.0, 0, 255).astype(np.uint8)

    # Sort splats by importance (volume / opacity) according to antimatter15 / web standards
    sorted_indices = np.argsort(
        -np.prod(scales, axis=-1) / (opacity + 1e-7)
    )
    positions = positions[sorted_indices]
    scales = scales[sorted_indices]
    rgba = rgba[sorted_indices]
    rots_u8 = rots_u8[sorted_indices]

    num_points = positions.shape[0]
    print(f"Writing {num_points} splats to {output_splat_path}...")

    # .splat buffer layout:
    # float32 x 3 (12 bytes)
    # float32 x 3 (12 bytes)
    # uint8 x 4 (4 bytes - RGBA)
    # uint8 x 4 (4 bytes - Rotations)
    # Total = 32 bytes per splat
    dtype_splat = np.dtype([
        ('position', np.float32, (3,)),
        ('scale', np.float32, (3,)),
        ('color', np.uint8, (4,)),
        ('rotation', np.uint8, (4,))
    ])

    splat_data = np.empty(num_points, dtype=dtype_splat)
    splat_data['position'] = positions
    splat_data['scale'] = scales
    splat_data['color'] = rgba
    splat_data['rotation'] = rots_u8

    with open(output_splat_path, 'wb') as f:
        f.write(splat_data.tobytes())

    orig_size_mb = os.path.getsize(input_ply_path) / (1024 * 1024)
    splat_size_mb = os.path.getsize(output_splat_path) / (1024 * 1024)
    print(f"Done! Compression: {orig_size_mb:.1f} MB -> {splat_size_mb:.1f} MB (Reduced by {(1 - splat_size_mb/orig_size_mb)*100:.1f}%)")
    return True

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Convert 3DGS PLY to lightweight .splat")
    parser.add_argument("input", help="Path to input .ply file")
    parser.add_argument("-o", "--output", default=None, help="Path to output .splat file")
    parser.add_argument("--opacity_thresh", type=float, default=0.01, help="Filter out points with opacity below threshold")
    parser.add_argument("--no_center", action="store_true", help="Do not center coordinates around (0,0,0)")
    args = parser.parse_args()

    convert_ply_to_splat(args.input, args.output, args.opacity_thresh, center=not args.no_center)

