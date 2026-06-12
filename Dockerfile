# ── doc2md: 多格式文档转 Markdown ──────────────────────────────────
# 用法:
#   docker build -t doc2md .
#   docker run --rm -v "$(pwd):/data" doc2md /data/report.xlsx
#   docker run --rm -v "$(pwd):/data" doc2md /data/scan.pdf --engine mineru
# ─────────────────────────────────────────────────────────────────────

FROM python:3.12-slim-bookworm

LABEL org.opencontainers.image.title="doc2md"
LABEL org.opencontainers.image.description="Multi-format document to Markdown converter"
LABEL org.opencontainers.image.source="https://github.com/thor/doc2md"
LABEL org.opencontainers.image.version="0.2.0"

# ── 系统依赖 ────────────────────────────────────────────────────────
# LibreOffice: .doc 转 .docx
# Java JRE: OpenDataLoader PDF 引擎
# libgl1 + libglib: opencv-python-headless 需要
RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-writer \
    default-jre-headless \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# ── Python 依赖 ─────────────────────────────────────────────────────
#   核心依赖
RUN pip install --no-cache-dir \
    mammoth>=1.9.0 \
    pandas>=2.2.0 \
    tabulate>=0.9.0 \
    openpyxl>=3.1.0 \
    pymupdf>=1.24.0 \
    opencv-python-headless>=4.8.0 \
    jieba

#   ODL 引擎（Java 混合引擎，约 50MB）
RUN pip install --no-cache-dir opendataloader-pdf

#   MinerU OCR 引擎（约 5GB）
RUN pip install --no-cache-dir "mineru[all]"

#   MinerU VLM 模型（约 4.5GB，从 modelscope 下载）
RUN mineru-models-download --source modelscope --model_type all
ENV MINERU_MODEL_SOURCE=local

# ── 安装 doc2md ─────────────────────────────────────────────────────
COPY pyproject.toml ./
COPY src/ src/
RUN pip install --no-cache-dir -e .

# ── 入口 ─────────────────────────────────────────────────────────────
WORKDIR /data
ENTRYPOINT ["python", "-m", "doc2md"]
