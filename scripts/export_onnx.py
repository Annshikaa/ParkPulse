"""Export YOLOv8n to ONNX FP32.

Usage:
    python scripts/export_onnx.py
Output:
    models/yolov8n_fp32.onnx
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pathlib import Path
import structlog

log = structlog.get_logger(__name__)

OUTPUT = Path("models/yolov8n_fp32.onnx")


def main() -> None:
    from ultralytics import YOLO

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    log.info("loading_model", weights="yolov8n.pt")
    model = YOLO("yolov8n.pt")

    log.info("exporting_onnx", output=str(OUTPUT))
    model.export(format="onnx", imgsz=640, simplify=True, opset=17)

    # ultralytics exports next to the .pt file; move it to models/
    exported = Path("yolov8n.onnx")
    if exported.exists():
        exported.rename(OUTPUT)
        log.info("moved_onnx", path=str(OUTPUT))
    elif OUTPUT.exists():
        log.info("onnx_already_at_target", path=str(OUTPUT))
    else:
        log.error("export_failed", expected=str(OUTPUT))
        sys.exit(1)

    size_mb = OUTPUT.stat().st_size / 1e6
    log.info("export_complete", path=str(OUTPUT), size_mb=round(size_mb, 2))
    print(f"\nFP32 ONNX model saved to {OUTPUT} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
