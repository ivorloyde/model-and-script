# YOLOhbb 标注工具

包含两个脚本：

- `count_yolohbb.py`：统计标签中不同类别的数量，输出 `result/counts_per_image.csv` 和 `result/counts_total.csv`。
- `compute_diameter.py`：根据输入的像素比例尺（像素对应的真实长度）计算每个标注对象的真实直径，输出 `result/diameters.csv`。

依赖
- Python 3.7+
- Pillow（用于读取图像尺寸）

安装示例（Windows cmd）：

```
python -m pip install --user Pillow
```

使用示例：

统计标签数量：

```
python count_yolohbb.py path/to/labels_folder --out result
```

计算直径（例如：100 像素 对应 10 微米）：

```
python compute_diameter.py path/to/labels_folder --scale-pixels 100 --scale-real 10 --unit um --out result
```

说明与假设：
- 脚本支持 `class x y w h`、`class x y w h angle` 和 `class x1 y1 x2 y2 x3 y3 x4 y4` 格式的行。
- 如果坐标是归一化（0..1），脚本需要与标签同名的图像文件来恢复像素尺寸（查找同目录或父目录；支持 jpg/png/tif 等）。
- 如果坐标已经是像素值（数值大于 1），脚本将直接使用。

如果你有特殊的 YOLOhbb 格式（例如其它字段顺序），告诉我样例行我可以直接调整解析逻辑。
