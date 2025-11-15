# YOLOhbb 标注工具

包含两个脚本：

- `count_yolohbb.py`：统计标签中不同类别的数量，按运行顺序把结果写入 `count-result` 目录，避免覆盖历史结果。
- `compute_diameter.py`：根据输入的像素比例尺（像素对应的真实长度）计算每个标注对象的真实直径，按运行顺序把结果写入 `diameter-result` 目录，且数值在 CSV 中保留两位小数。

输入格式

* 将X-Anylabeling输出的txt标注与对应图片存放在同一个文件夹中作为输入目录即可。建议使用绝对目录。

依赖

- Python 3.7+
- Pillow（用于读取图像尺寸）

安装（Windows cmd）：

```
python -m pip install --user -r requirements.txt
```

主要行为更新

- 默认输出目录已更改：计数脚本默认输出到 `count-result`，直径脚本默认输出到 `diameter-result`。你也可以用 `--out` 指定其他目录。
- 每次运行会为输出文件自动生成按序号编号的文件名，避免后一次运行覆盖前一次结果。如：
  - `count-result/counts_per_image_001.csv` 和 `count-result/counts_total_001.csv`（下一次运行会生成 `_002`）
  - `diameter-result/diameters_001.csv`（数值字段 `diameter_pixels` 和 `real_diameter` 在 CSV 中保留两位小数，如 `12.34`）

使用示例（Windows cmd）

统计标签数量（处理整个标签文件夹，输出到默认 `count-result`）：

```
python "d:\基因组所工作\model-and-script\count_yolohbb.py" "d:\path\to\labels_folder"
```

或指定输出目录：

```
python "d:\基因组所工作\model-and-script\count_yolohbb.py" "d:\path\to\labels_folder" --out "d:\my_results\count-result"
```

计算直径（例如：100 像素 = 10 微米，输出到默认 `diameter-result`）：

```
python "d:\基因组所工作\model-and-script\compute_diameter.py" "d:\path\to\labels_folder" --scale-pixels 100 --scale-real 10 --50um
```

或指定输出目录：

```
python "d:\genome work\model-and-script\compute_diameter.py" "d:\path\to\labels_folder" --scale-pixels 100 --scale-real 10 --50um --out "d:\my_results\diameter-result"
```

标签格式与实现细节（重要说明）

- 支持的行格式：`class x y w h`（或带 angle）与 `class x1 y1 x2 y2 x3 y3 x4 y4`（4 点多边形）。
- 对于 bbox（w,h）格式：
  - 若 w,h ≤ 1 且存在同名图像文件（同目录或父目录，支持 .jpg/.jpeg/.png/.tif/.tiff/.bmp），脚本会用图片尺寸把归一化坐标换算为像素；
  - 若 w 或 h > 1，则认为这些为像素值并直接使用；
  - 若坐标为归一化但未找到图片，脚本会跳过该条并在 stderr 打印警告（因为无法恢复像素）。
- 对于 8 字段（4 个顶点）格式：若顶点坐标是归一化且找到图片，会把点转换为像素后取顶点间最大欧氏距离作为对象的直径估计。

输出编号规则

- 脚本会在目标输出目录中搜索已有的符合前缀的 CSV 文件（例如 `counts_per_image_###.csv` 或 `diameters_###.csv`），解析出最大编号并使用下一个编号作为新运行的索引（格式为三位数，例如 001、002）。
- 对于并发写入场景（多个脚本同时运行）该简单方法可能不是完全原子化；如果你需要并发安全的方案，我可以改用锁文件或包含时间戳的命名策略。

路径与运行建议

- 路径中含空格请使用双引号（"）。建议使用绝对路径以避免当前工作目录带来的歧义。
- 如果需要批量对不同参数（例如不同 scale）分别运行单个标签文件，可在 cmd 中使用 `for` 循环：

```
for %f in (d:\data\labels\*.txt) do python "d:\基因组所工作\model-and-script\compute_diameter.py" "%f" --scale-pixels 100 --scale-real 10 --unit um
```
