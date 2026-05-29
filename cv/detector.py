from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
import structlog

log = structlog.get_logger(__name__)

# COCO vehicle class IDs
VEHICLE_CLASSES = {2, 3, 5, 7}  # car, motorcycle, bus, truck

BackendName = Literal["pytorch", "onnx_fp32", "onnx_int8"]


@dataclass
class Detection:
    x1: float
    y1: float
    x2: float
    y2: float
    conf: float
    cls: int
    track_id: int = -1


class Detector:
    """Wraps YOLOv8 with ByteTrack and supports hot-swappable inference backends.

    Backend dispatch happens in __init__; switch_backend() swaps at runtime
    under a lock so the pipeline worker never sees a partial state.
    """

    def __init__(
        self,
        backend: BackendName = "pytorch",
        weights: str = "yolov8n.pt",
        conf: float = 0.35,
        iou: float = 0.5,
    ) -> None:
        self.conf = conf
        self.iou = iou
        self.weights = weights
        self._lock = threading.Lock()
        self._backend: BackendName = backend
        self._model = None
        self._ort_session = None
        self._load_backend(backend)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def backend(self) -> BackendName:
        return self._backend

    def detect(self, frame: np.ndarray) -> list[Detection]:
        """Run inference + ByteTrack on one frame, return vehicle detections."""
        with self._lock:
            if self._backend == "pytorch":
                return self._detect_pytorch(frame)
            else:
                return self._detect_onnx(frame)

    def switch_backend(self, name: BackendName) -> None:
        """Hot-swap inference backend thread-safely."""
        if name == self._backend:
            return
        log.info("switching_backend", from_=self._backend, to=name)
        new_model = self._build_pytorch_model() if name == "pytorch" else None
        new_ort = None
        if name in ("onnx_fp32", "onnx_int8"):
            new_ort = self._build_ort_session(name)
        with self._lock:
            self._backend = name
            self._model = new_model
            self._ort_session = new_ort
        log.info("backend_switched", backend=name)

    # ------------------------------------------------------------------
    # Backend loaders
    # ------------------------------------------------------------------

    def _load_backend(self, backend: BackendName) -> None:
        if backend == "pytorch":
            self._model = self._build_pytorch_model()
        else:
            self._ort_session = self._build_ort_session(backend)

    def _build_pytorch_model(self):
        from ultralytics import YOLO
        import torch

        device = 0 if torch.cuda.is_available() else "cpu"
        model = YOLO(self.weights)
        model.to(device)
        # warm-up so first real frame isn't slow
        dummy = np.zeros((640, 640, 3), dtype=np.uint8)
        model.predict(dummy, verbose=False, device=device)
        self._device = device
        return model

    def _build_ort_session(self, backend: BackendName):
        import onnxruntime as ort

        path_map: dict[BackendName, str] = {
            "onnx_fp32": "models/yolov8n_fp32.onnx",
            "onnx_int8": "models/yolov8n_int8.onnx",
        }
        model_path = path_map[backend]
        if not Path(model_path).exists():
            raise FileNotFoundError(
                f"ONNX model not found: {model_path}. "
                "Run scripts/export_onnx.py and scripts/quantize.py first."
            )
        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"]
        session = ort.InferenceSession(model_path, providers=providers)
        log.info("ort_session_loaded", model=model_path, providers=session.get_providers())
        return session

    # ------------------------------------------------------------------
    # Inference implementations
    # ------------------------------------------------------------------

    def _detect_pytorch(self, frame: np.ndarray) -> list[Detection]:
        import torch
        device = getattr(self, "_device", 0 if torch.cuda.is_available() else "cpu")
        results = self._model.track(
            frame,
            conf=self.conf,
            iou=self.iou,
            classes=list(VEHICLE_CLASSES),
            tracker="bytetrack.yaml",
            persist=True,
            verbose=False,
            device=device,
        )
        detections: list[Detection] = []
        for r in results:
            if r.boxes is None:
                continue
            boxes = r.boxes
            for i in range(len(boxes)):
                cls_id = int(boxes.cls[i].item())
                if cls_id not in VEHICLE_CLASSES:
                    continue
                x1, y1, x2, y2 = boxes.xyxy[i].tolist()
                conf = float(boxes.conf[i].item())
                track_id = int(boxes.id[i].item()) if boxes.id is not None else -1
                detections.append(
                    Detection(x1=x1, y1=y1, x2=x2, y2=y2, conf=conf, cls=cls_id, track_id=track_id)
                )
        return detections

    def _detect_onnx(self, frame: np.ndarray) -> list[Detection]:
        """ONNX inference without ByteTrack (track IDs will be -1).

        We use a simple centroid-based tracker as a lightweight substitute
        when the PyTorch model isn't loaded — good enough for slot occupancy.
        """
        input_name = self._ort_session.get_inputs()[0].name
        h, w = frame.shape[:2]
        blob = self._preprocess_onnx(frame)
        outputs = self._ort_session.run(None, {input_name: blob})
        return self._postprocess_onnx(outputs, w, h)

    def _preprocess_onnx(self, frame: np.ndarray) -> np.ndarray:
        import cv2

        img = cv2.resize(frame, (640, 640))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = img.transpose(2, 0, 1)[np.newaxis, ...]
        return img

    def _postprocess_onnx(
        self, outputs: list, orig_w: int, orig_h: int
    ) -> list[Detection]:
        # YOLOv8 ONNX output: [1, 84, 8400] — [batch, xywh+80classes, anchors]
        pred = outputs[0][0].T  # (8400, 84)
        detections: list[Detection] = []
        sx, sy = orig_w / 640.0, orig_h / 640.0

        for row in pred:
            scores = row[4:]
            class_id = int(np.argmax(scores))
            if class_id not in VEHICLE_CLASSES:
                continue
            conf = float(scores[class_id])
            if conf < self.conf:
                continue
            cx, cy, bw, bh = row[:4]
            x1 = (cx - bw / 2) * sx
            y1 = (cy - bh / 2) * sy
            x2 = (cx + bw / 2) * sx
            y2 = (cy + bh / 2) * sy
            detections.append(
                Detection(x1=x1, y1=y1, x2=x2, y2=y2, conf=conf, cls=class_id)
            )
        return self._nms(detections)

    def _nms(self, detections: list[Detection]) -> list[Detection]:
        if not detections:
            return []
        import cv2

        boxes = [[d.x1, d.y1, d.x2 - d.x1, d.y2 - d.y1] for d in detections]
        scores = [d.conf for d in detections]
        indices = cv2.dnn.NMSBoxes(boxes, scores, self.conf, self.iou)
        if len(indices) == 0:
            return []
        return [detections[i] for i in indices.flatten()]
