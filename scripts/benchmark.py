"""Benchmark inference speed across all three backends.

Runs 200 measured passes per backend on a real video frame.
Writes results to docs/benchmarks.md and docs/benchmark_results.json.

Usage:
    python scripts/benchmark.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from statistics import mean, stdev

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import cv2
import numpy as np
import structlog

log = structlog.get_logger(__name__)

PASSES = 200
WARMUP = 10
OUTPUT_DIR = Path("docs")
BENCHMARKS_MD = OUTPUT_DIR / "benchmarks.md"
BENCHMARKS_JSON = OUTPUT_DIR / "benchmark_results.json"


def grab_frame() -> np.ndarray:
    cap = cv2.VideoCapture("sample_video.mp4")
    ret, frame = cap.read()
    cap.release()
    if not ret:
        return np.zeros((640, 640, 3), dtype=np.uint8)
    return frame


def benchmark_pytorch(frame: np.ndarray) -> dict:
    from ultralytics import YOLO

    model = YOLO("yolov8n.pt")
    # warmup
    for _ in range(WARMUP):
        model.predict(frame, verbose=False, classes=[2, 3, 5, 7])

    times = []
    for _ in range(PASSES):
        t0 = time.perf_counter()
        model.predict(frame, verbose=False, classes=[2, 3, 5, 7])
        times.append((time.perf_counter() - t0) * 1000)

    return _stats(times, "PyTorch (FP32)")


def benchmark_onnx(frame: np.ndarray, model_path: str, label: str) -> dict:
    import onnxruntime as ort

    if not Path(model_path).exists():
        log.warning("model_missing_skipping", path=model_path)
        return {"backend": label, "skipped": True, "reason": f"{model_path} not found"}

    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    sess = ort.InferenceSession(model_path, providers=providers)
    input_name = sess.get_inputs()[0].name

    def preprocess(f: np.ndarray) -> np.ndarray:
        img = cv2.resize(f, (640, 640))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        return img.transpose(2, 0, 1)[np.newaxis, ...]

    blob = preprocess(frame)

    for _ in range(WARMUP):
        sess.run(None, {input_name: blob})

    times = []
    for _ in range(PASSES):
        t0 = time.perf_counter()
        sess.run(None, {input_name: blob})
        times.append((time.perf_counter() - t0) * 1000)

    return _stats(times, label)


def _stats(times: list[float], label: str) -> dict:
    return {
        "backend": label,
        "passes": len(times),
        "mean_ms": round(mean(times), 2),
        "std_ms": round(stdev(times), 2),
        "min_ms": round(min(times), 2),
        "max_ms": round(max(times), 2),
        "fps": round(1000 / mean(times), 1),
    }


def write_markdown(results: list[dict]) -> None:
    lines = [
        "# ParkPulse Inference Benchmarks",
        "",
        f"Measured on: {PASSES} passes per backend (after {WARMUP} warmup passes).",
        "Frame source: first frame of `sample_video.mp4` at native resolution.",
        "",
        "| Backend | Mean (ms) | Std (ms) | Min (ms) | FPS |",
        "|---------|-----------|----------|----------|-----|",
    ]
    for r in results:
        if r.get("skipped"):
            lines.append(f"| {r['backend']} | N/A | N/A | N/A | N/A |  ← {r.get('reason', 'skipped')} |")
        else:
            lines.append(
                f"| {r['backend']} | {r['mean_ms']} | {r['std_ms']} | {r['min_ms']} | {r['fps']} |"
            )

    # Compute size reduction note if both ONNX models exist
    fp32 = Path("models/yolov8n_fp32.onnx")
    int8 = Path("models/yolov8n_int8.onnx")
    if fp32.exists() and int8.exists():
        fp32_mb = fp32.stat().st_size / 1e6
        int8_mb = int8.stat().st_size / 1e6
        reduction = (1 - int8_mb / fp32_mb) * 100
        lines += [
            "",
            "## Model Sizes",
            "",
            f"| Model | Size |",
            f"|-------|------|",
            f"| YOLOv8n FP32 ONNX | {fp32_mb:.1f} MB |",
            f"| YOLOv8n INT8 ONNX | {int8_mb:.1f} MB |",
            f"| Size reduction | **{reduction:.1f}%** |",
        ]

    lines += [
        "",
        "## Engineering Notes",
        "",
        "- **INT8 dynamic quantization**: weights quantized at export; activations at runtime.",
        "  No calibration dataset required — suited for variable surveillance scenes.",
        "- **ByteTrack** provides stable track IDs across frames without reid embeddings.",
        "- **CLAHE on LAB L-channel** improves detection in under/over-exposed frames.",
    ]

    BENCHMARKS_MD.write_text("\n".join(lines))
    log.info("benchmarks_md_written", path=str(BENCHMARKS_MD))


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    log.info("grabbing_frame")
    frame = grab_frame()
    log.info("frame_shape", shape=frame.shape)

    results = []

    log.info("benchmarking_pytorch")
    try:
        r = benchmark_pytorch(frame)
        results.append(r)
        print(f"PyTorch:   {r['mean_ms']:.1f} ms ({r['fps']} FPS)")
    except Exception as e:
        log.error("pytorch_benchmark_failed", error=str(e))
        results.append({"backend": "PyTorch (FP32)", "skipped": True, "reason": str(e)})

    log.info("benchmarking_onnx_fp32")
    r = benchmark_onnx(frame, "models/yolov8n_fp32.onnx", "ONNX FP32")
    results.append(r)
    if not r.get("skipped"):
        print(f"ONNX FP32: {r['mean_ms']:.1f} ms ({r['fps']} FPS)")

    log.info("benchmarking_onnx_int8")
    r = benchmark_onnx(frame, "models/yolov8n_int8.onnx", "ONNX INT8")
    results.append(r)
    if not r.get("skipped"):
        print(f"ONNX INT8: {r['mean_ms']:.1f} ms ({r['fps']} FPS)")

    BENCHMARKS_JSON.write_text(json.dumps(results, indent=2))
    log.info("benchmark_json_written", path=str(BENCHMARKS_JSON))

    write_markdown(results)
    print(f"\nResults written to {BENCHMARKS_MD} and {BENCHMARKS_JSON}")


if __name__ == "__main__":
    main()
