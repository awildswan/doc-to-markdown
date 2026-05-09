# doc2md

多格式文档转 Markdown，面向 RAG 语料处理。

## 支持的格式

| 格式 | 引擎 | 说明 |
|------|------|------|
| Excel (.xlsx/.xls) | pandas + tabulate | 多 sheet，自动生成表格 |
| Word (.docx) | mammoth | 保留标题层级、列表、表格 |
| PDF（文本层） | pymupdf | 直接提取文本，无需 GPU |
| PDF（扫描件）/ 图片 | MinerU pipeline | 版面分析 + OCR + 表格还原 |

> PDF 自动检测文本层（阈值 50 字符）：文本型走 pymupdf 直提，扫描件走 MinerU。
> 扫描件预处理：像素阈值过滤（≤50 保留为文字）+ 连通域去噪斑 + 图片合并回 PDF 再送 MinerU。
> 后处理：jieba 分词过滤低质量乱码行。

## 安装

```bash
cd /opt/doc-to-markdown
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 扫描件 OCR 支持（含 PyTorch + CUDA 依赖，约 5GB）
pip install "mineru[all]"
```

## 使用

```bash
# Excel / Word → Markdown
python -m doc2md report.xlsx          # → report.md
python -m doc2md document.docx        # → document.md

# PDF（自动识别文本层 vs 扫描件）
python -m doc2md scan.pdf             # → scan.md

# 图片 → Markdown（OCR）
python -m doc2md photo.png            # → photo.md

# 指定输出路径
python -m doc2md input.xlsx output/sheet.md
```

## Python API

```python
from doc2md import convert

result = convert("report.xlsx")
print(result.content)        # Markdown 文本
print(result.source_format)  # "xlsx"
print(result.metadata)       # {"sheets": ["Sheet1", "Sheet2"]}

result.save("output.md")     # 写入文件
```

## 已知限制

- **扫描件 OCR 质量**：中文扫描件（尤其目录/多栏/底纹/水印密集的政府文件）MinerU OCR 会产生乱码后缀。预处理（像素过滤）和后处理（jieba 分词清洗）可缓解但未根治。高分辨率原文件效果更好。
- **扫描件速度**：首次运行需下载模型（~2GB），后续 GPU（A5000 24GB）8 页约 50 秒。
- **Docker 模式**：GPU Docker 构建暂不稳定（网络原因），当前使用本地 pip 安装的 MinerU。

## 依赖

```
mammoth                   — Word .docx 解析
pandas + tabulate         — Excel 读取和表格生成
openpyxl                  — .xlsx 后端
pymupdf                   — PDF 文本层提取 + 图片渲染
opencv-python-headless    — 扫描件预处理（阈值过滤/去噪）
jieba                     — OCR 后处理分词清洗
mineru[all]               — PDF/图片 OCR + 版面分析（可选，约 5GB）
```

## License

MIT
