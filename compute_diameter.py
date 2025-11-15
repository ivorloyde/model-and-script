#!/usr/bin/env python3
"""
通过比例尺（像素对应真实长度）计算 YOLO 标注对象的真实直径。

用法示例：
 python compute_diameter.py labels_folder --scale-pixels 100 --scale-real 10 --unit um

支持行格式：
 - class x y w h
 - class x y w h angle
 - class x1 y1 x2 y2 x3 y3 x4 y4

脚本行为要点：
 - 若标注为归一化坐标（0..1），脚本会在同名图片存在时读取图片尺寸转换为像素；否则若坐标已经是像素值则直接使用。
 - 多边形（4点）时，使用顶点之间的最大欧氏距离作为像素直径估计（对旋转目标更稳健）。
 - 输出 CSV: `result/diameters.csv`，包含 image, label_file, class_id, diameter_pixels, real_diameter, unit。
"""
from __future__ import annotations

import argparse
import csv
import math
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from PIL import Image


IMAGE_EXTS = [".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"]


def find_label_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for p in path.rglob("*.txt"):
        yield p


def find_image_for_label(label_path: Path) -> Optional[Path]:
    base = label_path.with_suffix("")
    parent = label_path.parent
    for ext in IMAGE_EXTS:
        cand = parent / (base.name + ext)
        if cand.exists():
            return cand
    # try same stem in parent (in case label is in labels/ and images in images/)
    for ext in IMAGE_EXTS:
        cand = parent.parent / (base.name + ext)
        if cand.exists():
            return cand
    return None


def parse_line_fields(fields: List[float]) -> Tuple[str, List[float]]:
    # Not used heavily here; caller will manage
    return ("", fields)


def max_point_distance(pts: List[Tuple[float, float]]) -> float:
    maxd = 0.0
    n = len(pts)
    for i in range(n):
        x1, y1 = pts[i]
        for j in range(i + 1, n):
            x2, y2 = pts[j]
            d = math.hypot(x2 - x1, y2 - y1)
            if d > maxd:
                maxd = d
    return maxd


def process_label_file(label_path: Path, scale_pixels: float, scale_real: float, unit: str) -> List[dict]:
    out = []
    img_path = find_image_for_label(label_path)
    if img_path:
        with Image.open(img_path) as im:
            img_w, img_h = im.size
    else:
        img_w = img_h = None

    try:
        text = label_path.read_text(encoding="utf-8")
    except Exception:
        text = label_path.read_text(encoding="latin-1")

    for i, line in enumerate(text.splitlines()):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        try:
            cls = int(float(parts[0]))
            nums = [float(x) for x in parts[1:]]
        except Exception as e:
            print(f"warning: parse error {label_path}:{i+1}: {e}", file=sys.stderr)
            continue

        diameter_px = None

        if len(nums) in (4, 5):
            # w,h at positions 2,3 (0-based after class: x,y,w,h)
            w = nums[2]
            h = nums[3]
            # if normalized and image size known
            if (w <= 1.0 and h <= 1.0) and (img_w and img_h):
                w_px = w * img_w
                h_px = h * img_h
                diameter_px = max(w_px, h_px)
            elif w > 1.0 or h > 1.0:
                # assume already pixels
                diameter_px = max(w, h)
            else:
                print(f"warning: normalized bbox but image not found for {label_path}, line {i+1}; skipping", file=sys.stderr)
                continue

        elif len(nums) == 8:
            # polygon points normalized or absolute
            pts = [(nums[j], nums[j + 1]) for j in range(0, 8, 2)]
            # if normalized and have image dims, convert
            if all(0.0 <= x <= 1.0 and 0.0 <= y <= 1.0 for x, y in pts) and (img_w and img_h):
                pts_px = [(x * img_w, y * img_h) for x, y in pts]
            else:
                pts_px = pts
            diameter_px = max_point_distance(pts_px)

        else:
            print(f"warning: unsupported number of fields ({len(nums)}) in {label_path}:{i+1}; skipping", file=sys.stderr)
            continue

        real_diameter = diameter_px * (scale_real / scale_pixels)
        out.append({
            "image": img_path.name if img_path else "",
            "label_file": label_path.name,
            "class_id": cls,
            "diameter_pixels": float(diameter_px),
            "real_diameter": float(real_diameter),
            "unit": unit,
        })

    return out


def save_csv(rows: List[dict], out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "diameters.csv"
    with out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["image", "label_file", "class_id", "diameter_pixels", "real_diameter", "unit"])
        for r in rows:
            writer.writerow([r["image"], r["label_file"], r["class_id"], r["diameter_pixels"], r["real_diameter"], r["unit"]])
    print(f"wrote: {out}")


def main():
    p = argparse.ArgumentParser(description="根据像素->真实长度比例计算标注对象的真实直径")
    p.add_argument("input", type=Path, help="标签文件或包含标签文件的文件夹")
    p.add_argument("--scale-pixels", type=float, required=True, help="比例尺：代表的像素长度（例如显微镜标尺对应的像素数）")
    p.add_argument("--scale-real", type=float, required=True, help="比例尺对应的真实长度（单位在 --unit 中指定）")
    p.add_argument("--unit", type=str, default="um", help="真实长度单位，默认 'um'（微米）")
    p.add_argument("--out", type=Path, default=Path("result"), help="输出目录, 默认 result")
    args = p.parse_args()

    files = list(find_label_files(args.input))
    if not files:
        print("没有找到任何 .txt 标签文件", file=sys.stderr)
        raise SystemExit(2)

    all_rows = []
    for f in files:
        try:
            rows = process_label_file(f, args.scale_pixels, args.scale_real, args.unit)
            all_rows.extend(rows)
        except Exception as e:
            print(f"error processing {f}: {e}", file=sys.stderr)

    save_csv(all_rows, args.out)


if __name__ == "__main__":
    main()
