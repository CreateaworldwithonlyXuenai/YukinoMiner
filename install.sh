#!/bin/bash
# YukinoMiner - 环境安装脚本
# 支持: macOS / Linux / Windows(WSL)

set -e

echo "=========================================="
echo "⛏️ YukinoMiner 环境安装"
echo "=========================================="

OS="unknown"
if [[ "$OSTYPE" == "linux-gnu"* ]]; then OS="linux"
elif [[ "$OSTYPE" == "darwin"* ]]; then OS="macos"
fi
echo "📱 系统: $OS"

# Python
if command -v python3 &> /dev/null; then PYTHON="python3"
elif command -v python &> /dev/null; then PYTHON="python"
else echo "❌ 未找到 Python 3.8+"; exit 1; fi
$PYTHON --version
echo "✅ Python OK"

# pip deps
echo ""
echo "📦 安装依赖..."
$PYTHON -m pip install --upgrade pip
$PYTHON -m pip install -r requirements.txt

# ffmpeg
echo ""
echo "🎬 检查 ffmpeg..."
if command -v ffmpeg &> /dev/null && command -v ffprobe &> /dev/null; then
    echo "✅ ffmpeg OK"
    ffmpeg -version | head -1
else
    echo "⚠️ ffmpeg 未安装，尝试自动安装..."
    if [[ "$OS" == "macos" ]]; then
        if command -v brew &> /dev/null; then brew install ffmpeg
        else echo "❌ 请安装 Homebrew 后重试"; exit 1; fi
    elif [[ "$OS" == "linux" ]]; then
        if command -v apt &> /dev/null; then sudo apt update && sudo apt install -y ffmpeg
        elif command -v yum &> /dev/null; then sudo yum install -y ffmpeg
        elif command -v pacman &> /dev/null; then sudo pacman -S ffmpeg
        else echo "❌ 不支持的包管理器"; exit 1; fi
    else
        echo "❌ 请手动安装 ffmpeg: https://ffmpeg.org/download.html"
        exit 1
    fi
fi

# Verify
echo ""
echo "🔍 验证..."
$PYTHON -m demucs --help > /dev/null 2>&1 && echo "✅ demucs OK" || echo "⚠️ demucs 验证失败"
ffmpeg -version > /dev/null 2>&1 && echo "✅ ffmpeg OK" || echo "⚠️ ffmpeg 验证失败"

echo ""
echo "=========================================="
echo "🎉 安装完成!"
echo ""
echo "快速开始:"
echo "  python -m yukinominer extract -v \"S2E08.mkv\" -t timestamps.csv -o ./output"
echo "  python -m yukinominer batch -v ./videos/ -t ./timestamps/ -o ./batch_output"
echo "=========================================="
