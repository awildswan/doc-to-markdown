# doc2md — 多格式文档转 Markdown（RAG 语料处理）

## 支持的格式

| 格式 | 引擎 | 说明 |
|------|------|------|
| Excel (.xlsx/.xls) | pandas + tabulate | 多 sheet，自动生成表格，单元格换行转 `<br>` |
| Word (.docx/.doc) | mammoth + LibreOffice | 保留标题层级、列表、表格。.doc 自动转 .docx 后处理 |
| PDF（文本层） | pymupdf | 结构化提取：字号推断标题层级、坐标对齐检测表格 |
| PDF（扫描件）/图片 | MinerU + GPU | VLM 版面分析 + OCR + 表格还原，GPU 加速 |

## 环境配置

### Docker（一键）

镜像已打包所有依赖（Python 3.12 + doc2md + MinerU + LibreOffice + Java），无需手动配环境：

```bash
# 构建
docker build -t doc2md .

# Excel / Word / PDF
docker run --rm -v "$(pwd):/data" doc2md /data/report.xlsx
docker run --rm -v "$(pwd):/data" doc2md /data/document.docx
docker run --rm -v "$(pwd):/data" doc2md /data/scan.pdf --engine mineru

# GPU 加速（需 nvidia-docker）
docker run --gpus all --rm -v "$(pwd):/data" doc2md /data/scan.pdf --engine mineru
```

### 手动安装（Windows + GPU）

前提

- Python 3.12（3.14 不支持 MinerU）
- 显卡 + CUDA 驱动（本机 RTX 3050 4GB + CUDA 12.9）

### 1. 创建虚拟环境

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -e .
```

### 2. 安装 MinerU

```bash
pip install "mineru[all]"
```

> 如果 PyPI 连接不稳（hash 校验失败），用 Python 清代理后安装：
> ```bash
> python -c "import os,subprocess,sys;env=os.environ.copy();[env.pop(k,None)for k in('HTTP_PROXY','HTTPS_PROXY','http_proxy','https_proxy','ALL_PROXY','all_proxy')];subprocess.run([sys.executable,'-m','pip','install','mineru[all]'],env=env,check=True)"
> ```

### 3. 下载模型（建议放 D 盘）

```bash
mineru-models-download --source modelscope --model_type all
```

> 模型约 4.5GB，自动写入 `C:\Users\<用户>\mineru.json` 配置文件。

### 4. 安装 CUDA 版 PyTorch

mineru 可能装了 CPU 版 torch，必须换掉：

```bash
pip uninstall torch torchvision -y
# 从 https://pytorch.org 下载 CUDA 12.4 版 whl（约 2.5GB）
# pip install torch-2.6.0+cu124-cp312-cp312-win_amd64.whl
```

验证：
```bash
python -c "import torch; print(torch.cuda.is_available())"  # True
python -c "import torch; print(torch.cuda.get_device_name(0))"  # RTX 3050
```

### 5. 每轮使用前设置环境变量

```bash
export MINERU_MODEL_SOURCE=local
export CUDA_PATH="D:/path/to/.venv/Lib/site-packages/torch/lib"
export HTTP_PROXY= HTTPS_PROXY= http_proxy= https_proxy= ALL_PROXY= all_proxy=
```

## 使用

### 命令行（GPU 模式，推荐）

```bash
mineru -p 文件.pdf -o 输出目录 -b hybrid-auto-engine -l ch
```

输出示例：
```
output/nbd-1/hybrid_auto/
├── nbd-1.md          # Markdown 正文
├── nbd-1_model.json  # 模型元数据
├── nbd-1_middle.json # 中间结果
├── nbd-1_layout.pdf  # 带版面标注的 PDF
├── nbd-1_origin.pdf  # 预处理后原文件
└── images/           # 提取的印章/签名/图片
```

### 通过 doc2md CLI

```bash
python -m doc2md report.xlsx               # Excel
python -m doc2md document.docx             # Word
python -m doc2md scan.pdf --engine mineru  # PDF 
```

### Python API

```python
from doc2md import convert, convert_batch

result = convert("report.xlsx")
print(result.content)
result.save("output.md")
```



## 性能

| 文件 | 页数 | 耗时 |
|------|------|------|
| nbd-1.pdf | 18 | ~4 分钟 |
| nbd-2.pdf | 26 | ~6 分钟 |
| nbd-3.pdf | 1 | ~30 秒 |

> RTX 3050 4GB 显存可跑但处临界状态，多次连续转换可能因显存碎片导致失败。

## 常见问题

| 问题 | 原因 | 解决 |
|------|------|------|
| `CUDA is not available` | PyTorch 是 CPU 版 | 换 CUDA 版 |
| `Can not find $env:CUDA_PATH` | 缺少环境变量 | `export CUDA_PATH=...` |
| `offload_folder` 错误 | 4GB 显存放不下完整模型 | 重启或换 `pipeline` 后端 |
| 下载 hash 不匹配 | 代理/网络干扰 | 清代理 + 设 `--no-cache-dir` |
| turbomind 编译 过长 | `MINERU_FORCE_VLM_OCR_ENABLE=0` 触发重新编译 | 保持 `=0`，等待完成 |

## 依赖

```
mammoth                   — Word .docx 解析
pandas + openpyxl         — Excel 读取
pymupdf                   — PDF 文本提取 + 图片渲染
opencv-python-headless    — 扫描件预处理（Otsu + 去噪）
jieba                     — OCR 后处理乱码清洗
torch (CUDA)              — GPU 计算
mineru[all]               — 版面分析 + OCR + VLM（约 5GB）
```

## License

MIT
