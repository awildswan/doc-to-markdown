# doc2md

多格式文档转 Markdown，面向 RAG 语料处理。

## 支持的格式

| 格式 | 引擎 | 说明 |
|------|------|------|
| Excel (.xlsx/.xls) | pandas + tabulate | 多 sheet 支持，自动生成 Markdown 表格 |
| Word (.docx) | mammoth | 保留标题层级、列表、表格 |
| PDF（文本层） | pymupdf | 直接提取文本层，速度快，无需 GPU |
| PDF（扫描件）/ 图片 | MinerU | 版面分析 + OCR + 公式识别 + 表格还原 |

> PDF 会自动检测：有文本层走 pymupdf 直提（<50 字符阈值），扫描件走 MinerU OCR。

## 安装

```bash
cd /opt/doc-to-markdown
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# PDF/图片 OCR 支持（MinerU，含模型 ~2GB + CUDA 依赖 ~3GB）
pip install "mineru[all]"
```

## 使用

```bash
# Excel / Word → Markdown
python -m doc2md report.xlsx          # → report.md
python -m doc2md document.docx        # → document.md

# PDF（自动识别文本层 vs 扫描件）
python -m doc2md scan.pdf             # → scan.md

# 图片 → Markdown
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

## 依赖

```
mammoth     — Word .docx 解析
pandas      — Excel 读取
tabulate    — DataFrame → Markdown 表格
openpyxl    — .xlsx 后端
pymupdf     — PDF 文本层提取
mineru[all] — PDF/图片 OCR + 版面分析（可选，~5GB）
```

## License

MIT
