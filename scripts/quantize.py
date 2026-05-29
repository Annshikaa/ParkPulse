"""INT8 dynamic quantization of the FP32 ONNX model.

Dynamic quantization: weights quantized at export time, activations at runtime.
Chosen over static quantization because it requires no calibration dataset —
good for surveillance feeds that change scene context continuously.

Usage:
    python scripts/quantize.py
Input:
    models/yolov8n_fp32.onnx
Output:
    models/yolov8n_int8.onnx
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import structlog

log = structlog.get_logger(__name__)

INPUT = Path("models/yolov8n_fp32.onnx")
OUTPUT = Path("models/yolov8n_int8.onnx")


def main() -> None:
    if not INPUT.exists():
        log.error("fp32_model_missing", path=str(INPUT))
        print(f"ERROR: {INPUT} not found. Run scripts/export_onnx.py first.")
        sys.exit(1)

    from onnxruntime.quantization import quantize_dynamic, QuantType
    import onnx

    log.info("loading_fp32", path=str(INPUT))
    model = onnx.load(str(INPUT))
    fp32_size = INPUT.stat().st_size / 1e6
    log.info("fp32_loaded", size_mb=round(fp32_size, 2))

    log.info("quantizing_int8")
    quantize_dynamic(
        str(INPUT),
        str(OUTPUT),
        weight_type=QuantType.QUInt8,
    )

    int8_size = OUTPUT.stat().st_size / 1e6
    reduction = (1 - int8_size / fp32_size) * 100
    log.info(
        "quantization_complete",
        output=str(OUTPUT),
        fp32_mb=round(fp32_size, 2),
        int8_mb=round(int8_size, 2),
        reduction_pct=round(reduction, 1),
    )
    print(f"\nINT8 model saved to {OUTPUT}")
    print(f"  FP32: {fp32_size:.1f} MB")
    print(f"  INT8: {int8_size:.1f} MB")
    print(f"  Size reduction: {reduction:.1f}%")


if __name__ == "__main__":
    main()
