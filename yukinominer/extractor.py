#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YukinoMiner - 核心提取引擎
"""

import os
import sys
import json
import csv
import subprocess
import argparse
import logging
from pathlib import Path
from datetime import datetime

DEFAULT_CONFIG = {
    "ffmpeg_path": "ffmpeg",
    "ffprobe_path": "ffprobe",
    "demucs_model": "htdemucs_ft",
    "output_format": "wav",
    "sample_rate": 44100,
    "normalize_target": -23.0,
    "highpass": 80,
    "lowpass": 8000,
    "noise_reduction": True,
    "output_naming": {
        "template": "{character}_{season}E{episode:02d}_{scene}_{emotion}_{text}",
        "character": "雪乃",
        "max_text_len": 10
    }
}

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("YukinoMiner")

def run_cmd(cmd, check=True):
    result = subprocess.run(cmd, capture_output=True, text=True, check=check)
    if result.returncode != 0 and check:
        raise RuntimeError(f"Command failed: {result.stderr}")
    return result.stdout.strip()

def check_deps(config):
    try:
        run_cmd([config["ffmpeg_path"], "-version"], check=False)
        logger.info("✅ ffmpeg OK")
    except FileNotFoundError:
        logger.error("❌ ffmpeg not found. Install: https://ffmpeg.org/download.html")
        return False
    try:
        run_cmd(["python", "-m", "demucs", "--help"], check=False)
        logger.info("✅ demucs OK")
    except:
        logger.warning("⚠️ demucs not found. Install: pip install demucs")
    return True

def time_to_seconds(ts):
    ts = str(ts).strip()
    parts = ts.split(":")
    if len(parts) == 3:
        return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
    elif len(parts) == 2:
        return int(parts[0])*60 + float(parts[1])
    return float(parts[0])

def sanitize(text, max_len=20):
    for ch in '\\/:*?"<>|':
        text = text.replace(ch, "_")
    return text.replace(" ", "_")[:max_len]

def extract_audio(video, out_dir, config):
    out = Path(out_dir) / "01_extracted"
    out.mkdir(parents=True, exist_ok=True)
    dst = out / f"{Path(video).stem}_audio.wav"
    cmd = [config["ffmpeg_path"], "-y", "-i", str(video), "-vn", "-acodec", "pcm_s24le",
           "-ar", str(config["sample_rate"]), "-ac", "2", str(dst)]
    logger.info(f"🎬 Extract: {Path(video).name}")
    run_cmd(cmd)
    return dst

def separate_vocals(audio, out_dir, config):
    out = Path(out_dir) / "02_separated"
    out.mkdir(parents=True, exist_ok=True)
    logger.info(f"🎙️ Separate vocals (model: {config['demucs_model']})")
    cmd = ["python", "-m", "demucs", "--model", config["demucs_model"],
           "--two-stems", "vocals", "-o", str(out), str(audio)]
    run_cmd(cmd)
    model = config["demucs_model"]
    stem = Path(audio).stem
    vocal_file = out / model / stem / "vocals.wav"
    if not vocal_file.exists():
        candidates = list(out.rglob("vocals.wav"))
        if candidates:
            vocal_file = candidates[0]
        else:
            raise FileNotFoundError("vocals.wav not found after separation")
    return vocal_file

def slice_audio(vocal_path, csv_path, out_dir, config):
    out = Path(out_dir) / "03_sliced"
    out.mkdir(parents=True, exist_ok=True)
    slices = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    logger.info(f"📋 {len(rows)} slices to process")
    for idx, row in enumerate(rows, 1):
        season = row.get("season", "S").strip()
        ep = int(row.get("episode", 0))
        scene = sanitize(row.get("scene", "unknown"))
        emotion = sanitize(row.get("emotion", "normal"))
        text = sanitize(row.get("text", ""), config["output_naming"]["max_text_len"])
        start = time_to_seconds(row["start"])
        end = time_to_seconds(row["end"])
        duration = end - start
        if duration <= 0:
            logger.warning(f"Skip invalid timestamp row {idx}")
            continue
        char = config["output_naming"]["character"]
        tpl = config["output_naming"]["template"]
        fname = tpl.format(character=char, season=season, episode=ep, scene=scene, emotion=emotion, text=text) + ".wav"
        dst = out / fname
        cmd = [config["ffmpeg_path"], "-y", "-i", str(vocal_path), "-ss", str(start), "-t", str(duration), "-c", "copy", str(dst)]
        logger.info(f"🔪 [{idx}/{len(rows)}] {start:.1f}s~{end:.1f}s | {emotion}")
        run_cmd(cmd)
        slices.append(dst)
    return slices

def enhance(input_path, out_dir, config):
    out = Path(out_dir) / "04_enhanced"
    out.mkdir(parents=True, exist_ok=True)
    dst = out / Path(input_path).name
    filters = []
    if config.get("highpass"):
        filters.append(f"highpass=f={config['highpass']}")
    if config.get("lowpass"):
        filters.append(f"lowpass=f={config['lowpass']}")
    filters.append(f"loudnorm=I={config['normalize_target']}:TP=-1.5:LRA=11")
    if config.get("noise_reduction"):
        filters.append("afftdn=nf=-25")
    af = ",".join(filters)
    cmd = [config["ffmpeg_path"], "-y", "-i", str(input_path), "-af", af,
           "-ar", str(config["sample_rate"]), "-acodec", "pcm_s24le", str(dst)]
    logger.info(f"✨ Enhance: {Path(input_path).name}")
    run_cmd(cmd)
    return dst

def full_pipeline(video, csv, out, cfg_path=None):
    config = DEFAULT_CONFIG.copy()
    if cfg_path and Path(cfg_path).exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "run_config.json", "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    logger.info("="*50)
    logger.info("🚀 YukinoMiner Pipeline Start")
    logger.info("="*50)
    audio = extract_audio(video, out, config)
    vocals = separate_vocals(audio, out, config)
    slices = slice_audio(vocals, csv, out, config)
    enhanced = []
    for s in slices:
        try:
            enhanced.append(enhance(s, out, config))
        except Exception as e:
            logger.error(f"Enhance failed: {s.name} | {e}")
    report = {"timestamp": datetime.now().isoformat(), "source": str(video),
              "total": len(slices), "enhanced": len(enhanced),
              "files": [str(Path(f).name) for f in enhanced]}
    with open(out / "report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    logger.info("="*50)
    logger.info(f"🎉 Done! Total: {len(slices)} | Enhanced: {len(enhanced)}")
    logger.info("="*50)
    return enhanced

def batch(video_dir, ts_dir, out, cfg_path=None):
    config = DEFAULT_CONFIG.copy()
    if cfg_path and Path(cfg_path).exists():
        with open(cfg_path, "r", encoding="utf-8") as f:
            config.update(json.load(f))
    vdir = Path(video_dir)
    tdir = Path(ts_dir)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    exts = {".mkv", ".mp4", ".avi", ".mov", ".wmv", ".ts"}
    videos = sorted([f for f in vdir.iterdir() if f.suffix.lower() in exts])
    logger.info(f"📁 Found {len(videos)} videos")
    results = []
    for idx, v in enumerate(videos, 1):
        stem = v.stem.lower()
        ts = None
        for c in [v.with_suffix(".csv").name, f"{stem}.csv", stem.replace(" ", "_") + ".csv"]:
            p = tdir / c
            if p.exists():
                ts = p
                break
        if not ts:
            for f in tdir.glob("*.csv"):
                if stem[:5] in f.stem.lower() or f.stem.lower() in stem:
                    ts = f
                    break
        if not ts:
            logger.warning(f"Skip {v.name}: no timestamp CSV")
            results.append({"video": str(v), "status": "skipped", "reason": "no_timestamp"})
            continue
        logger.info(f"\n🎬 [{idx}/{len(videos)}] {v.name} ← {ts.name}")
        sub = out / v.stem
        try:
            audio = extract_audio(v, sub, config)
            vocals = separate_vocals(audio, sub, config)
            slices = slice_audio(vocals, ts, sub, config)
            enhanced = []
            for s in slices:
                try:
                    enhanced.append(str(enhance(s, sub, config)))
                except Exception as e:
                    logger.error(f"Enhance failed: {s.name} | {e}")
            results.append({"video": str(v), "status": "success", "timestamp": str(ts),
                            "slices": len(slices), "enhanced": len(enhanced)})
        except Exception as e:
            logger.error(f"Failed: {v.name} | {e}")
            results.append({"video": str(v), "status": "failed", "reason": str(e)})
    report = {"timestamp": datetime.now().isoformat(), "total": len(videos), "results": results}
    with open(out / "batch_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    success = sum(1 for r in results if r["status"] == "success")
    logger.info(f"\n🎉 Batch done! Success: {success}/{len(videos)}")
    return results

def main():
    parser = argparse.ArgumentParser(description="YukinoMiner - 雪之下雪乃音频提取工具")
    sub = parser.add_subparsers(dest="command", required=True)

    ext = sub.add_parser("extract", help="单文件提取")
    ext.add_argument("-v", "--video", help="视频路径")
    ext.add_argument("-i", "--input-audio", help="音频路径（跳过分離）")
    ext.add_argument("-t", "--timestamps", help="时间戳CSV")
    ext.add_argument("-o", "--output", default="./yukino_output")
    ext.add_argument("-c", "--config", help="配置文件")
    ext.add_argument("--step", choices=["extract", "separate", "slice", "enhance", "all"], default="all")
    ext.add_argument("--check", action="store_true", help="检查环境")

    bat = sub.add_parser("batch", help="批量提取")
    bat.add_argument("-v", "--video-dir", required=True)
    bat.add_argument("-t", "--timestamp-dir", required=True)
    bat.add_argument("-o", "--output", default="./yukino_batch_output")
    bat.add_argument("-c", "--config")

    args = parser.parse_args()
    config = DEFAULT_CONFIG.copy()
    if args.config and Path(args.config).exists():
        with open(args.config, "r", encoding="utf-8") as f:
            config.update(json.load(f))

    if args.command == "extract":
        if args.check:
            check_deps(config)
            return
        if args.step == "all":
            if not args.video or not args.timestamps:
                parser.error("Full pipeline requires --video and --timestamps")
            full_pipeline(args.video, args.timestamps, args.output, args.config)
        elif args.step == "extract":
            extract_audio(args.video, args.output, config)
        elif args.step == "separate":
            separate_vocals(args.input_audio, args.output, config)
        elif args.step == "slice":
            slice_audio(args.input_audio, args.timestamps, args.output, config)
        elif args.step == "enhance":
            p = Path(args.input_audio)
            if p.is_dir():
                for f in p.glob("*.wav"):
                    enhance(f, args.output, config)
            else:
                enhance(p, args.output, config)

    elif args.command == "batch":
        if not check_deps(config):
            sys.exit(1)
        batch(args.video_dir, args.timestamp_dir, args.output, args.config)

if __name__ == "__main__":
    main()
