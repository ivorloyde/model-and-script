#!/usr/bin/env python3
"""
统计 YOLOhbb 标注中不同类别的数量。

支持输入单个标签文件或包含标签文件的文件夹（递归）。
支持常见 YOLO / YOLOhbb 行格式：
 - class x y w h
 - class x y w h angle
 - class x1 y1 x2 y2 x3 y3 x4 y4

输出：将结果保存到 `result/counts.csv`，包含每张图的各类计数以及总计。
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable, Tuple


def find_label_files(path: Path) -> Iterable[Path]:
    if path.is_file():
        yield path
        return
    for p in path.rglob("*.txt"):
        yield p


def parse_label_line(line: str) -> Tuple[int, list]:
    parts = line.strip().split()
    if not parts:
        raise ValueError("empty line")
    cls = int(float(parts[0]))
    coords = [float(x) for x in parts[1:]]
    return cls, coords


def process_files(files: Iterable[Path]) -> Tuple[dict, dict]:
    # per-file counts and total counts
    per_file = {}
    total = defaultdict(int)
    for f in files:
        counts = defaultdict(int)
        try:
            text = f.read_text(encoding="utf-8")
        except Exception:
            text = f.read_text(encoding="latin-1")
        for i, line in enumerate(text.splitlines()):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            try:
                cls, _ = parse_label_line(s)
            except Exception as e:
                print(f"warning: failed to parse {f}:{i+1}: {e}", file=sys.stderr)
                continue
            counts[cls] += 1
            total[cls] += 1
        per_file[f.name] = dict(counts)
    return per_file, dict(total)


def _next_index_for_prefix(out_dir: Path, prefix: str) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    max_idx = 0
    pattern = re.compile(rf"^{re.escape(prefix)}_(\d+)\.csv$")
    for p in out_dir.iterdir():
        if not p.is_file():
            continue
        m = pattern.match(p.name)
        if m:
            try:
                idx = int(m.group(1))
                if idx > max_idx:
                    max_idx = idx
            except Exception:
                continue
    return max_idx + 1


def save_results(per_file: dict, total: dict, out_dir: Path):
    # out_dir is the base directory for count results
    out_dir = out_dir or Path("count-result")
    out_dir.mkdir(parents=True, exist_ok=True)
    idx = _next_index_for_prefix(out_dir, "counts_per_image")
    per_file_csv = out_dir / f"counts_per_image_{idx:03d}.csv"
    with per_file_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["image", "class_id", "count"])
        for image, counts in sorted(per_file.items()):
            for cls, c in sorted(counts.items()):
                writer.writerow([image, cls, c])

    total_csv = out_dir / f"counts_total_{idx:03d}.csv"
    with total_csv.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["class_id", "total_count"])
        for cls, c in sorted(total.items()):
            writer.writerow([cls, c])

    print(f"wrote: {per_file_csv}\nwrote: {total_csv}")


def main():
    p = argparse.ArgumentParser(description="统计 YOLOhbb 标注类别数量")
    p.add_argument("input", type=Path, help="标签文件或包含标签文件的文件夹")
    p.add_argument("--out", type=Path, default=Path("count-result"), help="输出目录, 默认 count-result")
    args = p.parse_args()

    files = list(find_label_files(args.input))
    if not files:
        print("没有找到任何 .txt 标签文件", file=sys.stderr)
        raise SystemExit(2)
    per_file, total = process_files(files)
    save_results(per_file, total, args.out)


if __name__ == "__main__":
    main()
