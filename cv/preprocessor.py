import cv2
import numpy as np


class Preprocessor:
    """Enhances low-contrast / bad-light frames before detection.

    CLAHE on the L channel of LAB keeps color channels intact while
    boosting local contrast — better than histogram-equalizing RGB directly.
    Adaptive gamma handles under/over-exposed feeds without blowing out.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

    def apply(self, frame: np.ndarray) -> np.ndarray:
        if not self.enabled:
            return frame
        frame = self._clahe_lab(frame)
        frame = self._adaptive_gamma(frame)
        return frame

    def _clahe_lab(self, frame: np.ndarray) -> np.ndarray:
        lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        l = self._clahe.apply(l)
        lab = cv2.merge([l, a, b])
        return cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    def _adaptive_gamma(self, frame: np.ndarray) -> np.ndarray:
        mean = float(np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)))
        if mean < 80:
            gamma = 0.5   # exponent < 1 lifts dark pixels: 30→78, 50→100
        elif mean > 180:
            gamma = 1.8   # exponent > 1 compresses bright pixels
        else:
            return frame
        table = np.array(
            [((i / 255.0) ** gamma) * 255 for i in range(256)], dtype=np.uint8
        )
        return cv2.LUT(frame, table)
