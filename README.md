<div align="center">

# ⛏️ YukinoMiner

> **从《我的青春恋爱物语果然有问题》中克隆雪之下雪乃的声音。**

一个自动化音频提取流水线，专为角色语音研究、AI声线克隆和台词分析设计。

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![ffmpeg](https://img.shields.io/badge/ffmpeg-4.4%2B-orange)](https://ffmpeg.org)
[![demucs](https://img.shields.io/badge/demucs-4.0%2B-purple)](https://github.com/facebookresearch/demucs)

</div>

---

## ✨ 特性

- 🎬 **音轨提取** — 从 MKV/MP4 无损提取 24bit PCM 音轨
- 🎙️ **AI人声分离** — 基于 Demucs 深度模型，自动剥离 BGM 与音效
- 🔪 **精确切片** — CSV 时间戳驱动，按台词/场景/情绪自动命名
- ✨ **智能增强** — 降噪、高低通滤波、LUFS 响度归一化
- 📦 **批量处理** — 整季视频自动匹配时间戳，一键跑完全流程
- 🏷️ **语义命名** — `角色_季集_场景_情绪_台词.wav`，一目了然

---

## 📦 安装

### 环境要求

| 依赖 | 版本 | 安装方式 |
|------|------|---------|
| Python | 3.8+ | [python.org](https://python.org) |
| ffmpeg | 4.4+ | [ffmpeg.org](https://ffmpeg.org) |
| demucs | 4.0+ | `pip install demucs` |

### 快速安装

**macOS / Linux:**
```bash
git clone https://github.com/YOUR_USERNAME/YukinoMiner.git
cd YukinoMiner
bash install.sh
```

**Windows (PowerShell):**
```powershell
git clone https://github.com/YOUR_USERNAME/YukinoMiner.git
cd YukinoMiner
pip install -r requirements.txt
# 手动安装 ffmpeg: https://ffmpeg.org/download.html
```

---

## 🚀 使用

### 1. 准备时间戳 CSV

复制 `examples/timestamps.example.csv`，填入你的素材时间：

```csv
season,episode,scene,emotion,text,start,end,notes
S2,08,车祸真相,崩溃,我不明白为什么,21:34.500,21:38.200,雪乃被八幡戳穿后的颤抖
S2,13,真物宣言,绝望,只是伪物,18:22.100,18:26.800,存在性危机
S3,12,天桥告白,颤抖,扭曲你人生,22:05.000,22:10.500,情绪爆发
```

| 字段 | 说明 | 示例 |
|------|------|------|
| `season` | 季 | `S2` |
| `episode` | 集 | `08` |
| `scene` | 场景名 | `车祸真相` |
| `emotion` | 情绪标签 | `崩溃` |
| `text` | 台词前几个字 | `我不明白为什么` |
| `start` | 开始时间 | `21:34.500` |
| `end` | 结束时间 | `21:38.200` |

### 2. 单文件提取

```bash
python -m yukinominer extract \
  -v "S2E08.mkv" \
  -t "timestamps_S2E08.csv" \
  -o "./output"
```

### 3. 批量提取（推荐）

```bash
python -m yukinominer batch \
  -v "./videos/" \
  -t "./timestamps/" \
  -o "./batch_output"
```

脚本会自动按文件名匹配视频与 CSV。

### 4. 分步调试

```bash
# 仅提取音轨
python -m yukinominer extract -v "S2E08.mkv" -o ./output --step extract

# 仅分离人声
python -m yukinominer extract -i "audio.wav" -o ./output --step separate

# 仅切片
python -m yukinominer extract -i "vocals.wav" -t timestamps.csv -o ./output --step slice

# 仅增强
python -m yukinominer extract -i "./sliced/" -o ./output --step enhance
```

---

## 📂 输出结构

```
output/
├── 01_extracted/          # 原始音轨
│   └── S2E08_audio.wav
├── 02_separated/          # Demucs 分离后人声
│   └── htdemucs_ft/
│       └── S2E08_audio/
│           └── vocals.wav
├── 03_sliced/             # 按时间戳切片
│   ├── 雪乃_S2E08_车祸真相_崩溃_我不明白.wav
│   ├── 雪乃_S2E08_真物宣言_绝望_只是伪物.wav
│   └── ...
├── 04_enhanced/           # 最终增强版
│   ├── 雪乃_S2E08_车祸真相_崩溃_我不明白.wav
│   └── ...
├── run_config.json        # 运行配置记录
└── report.json            # 处理报告
```

---

## ⚙️ 配置

复制 `examples/config.example.json` 为 `config.json`：

```json
{
  "demucs_model": "htdemucs_ft",
  "sample_rate": 44100,
  "normalize_target": -23.0,
  "highpass": 80,
  "lowpass": 8000,
  "noise_reduction": true,
  "output_naming": {
    "template": "{character}_{season}E{episode:02d}_{scene}_{emotion}_{text}",
    "character": "雪乃",
    "max_text_len": 10
  }
}
```

| 参数 | 说明 | 推荐值 |
|------|------|--------|
| `demucs_model` | 人声分离模型 | `htdemucs_ft` |
| `normalize_target` | 响度归一化目标 (LUFS) | `-23` |
| `highpass` | 高通滤波 (Hz) | `80` |
| `lowpass` | 低通滤波 (Hz) | `8000` |

---

## 🎤 用于 AI 语音克隆

提取后的音频可直接用于训练声线模型：

| 工具 | 用途 | 建议数据量 |
|------|------|-----------|
| [RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) | 实时变声/翻唱 | 10–30 分钟 |
| [SoVITS](https://github.com/svc-develop-team/so-vits-svc) | TTS 文本转语音 | 30 分钟–2 小时 |
| [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | 高质量 TTS | 30 分钟–2 小时 |

**雪乃声线训练要点：**
- 早见沙织声线气声重，需多截**清冷坚定**的台词作锚点
- **颤音**（真物宣言、车祸场景）是标志性特征，建议单独标注
- 避免模型偏向「柔弱」，保持「冰之女王」底色

---

## 📋 高价值场景推荐

| 场景 | 位置 | 情绪 | 重要性 |
|------|------|------|--------|
| 侍奉部初遇 | S1E01 | 毒舌+防御 | 声线基准 |
| 三浦事件 | S1E05 | 愤怒+正义 | 情绪爆发 |
| 夜路逃离 | S2E03 | 孤独+羞耻 | 脆弱暴露 |
| 车祸真相 | S2E08 | 崩溃+否认 | 核心恐惧 |
| 真物宣言 | S2E13 | 绝望+否定 | 存在性危机 |
| 阳乃对峙 | S3E08 | 被戳穿+空洞 | 存在性恐惧 |
| 天桥告白 | S3E12 | 颤抖+接纳 | 最终转变 |

---

## 🤝 贡献

欢迎 Issue 和 PR！

- 发现 Bug？请附上报错信息和复现步骤
- 有新功能想法？先开 Issue 讨论
- 提交代码前请确保通过基础测试

---

## 📜 许可

[MIT License](LICENSE) © 2026 YukinoMiner Contributors

> 本工具仅处理用户已合法拥有的视频文件。请尊重版权，支持正版。

---

<div align="center">

*为雪之下雪乃角色研究而生。*

</div>
