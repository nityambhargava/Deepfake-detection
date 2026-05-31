"""
=============================================================================
DEEPFAKE DETECTION ENGINE
=============================================================================
Classifies images into:
  - REAL          : Unaltered/raw image        → fakeness < 10%
  - FAKE          : Partially altered image    → 50% ≤ fakeness < 90%
  - AI_GENERATED  : Wholly AI-generated image  → fakeness ≥ 90%

Analysis pipeline (6 independent forensic probes):
  1. Error Level Analysis   (ELA)          – JPEG recompression artifact deltas
  2. Frequency Domain       (FFT)          – GAN spectral fingerprints
  3. Noise Consistency      (PRNU-like)    – Sensor-noise uniformity
  4. JPEG Ghost Detection                  – Multi-quality ghost artifacts
  5. Metadata Forensics     (EXIF)         – Camera/software provenance
  6. Colour & Gradient Stats              – Smoothness / entropy anomalies

Author  : Deepfake Detection Engine
Version : 1.0.0
=============================================================================
"""

# ── Standard library ──────────────────────────────────────────────────────
import io
import os
import sys
import json
import math
import warnings
import logging
import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

# ── Third-party ───────────────────────────────────────────────────────────
import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance, ImageFilter
from scipy.fft import fft2, fftshift
from scipy.ndimage import uniform_filter
from skimage.feature import graycomatrix, graycoprops

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
log = logging.getLogger("DeepfakeDetector")


# ══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ProbeScore:
    """
    Individual score from a single forensic probe.

    raw_score   – normalised score in [0, 1] where 1 = most suspicious
    weight      – contribution weight in final aggregation
    description – human-readable interpretation
    """
    name: str
    raw_score: float        # 0 → real / pristine,  1 → fake / AI-generated
    weight: float
    description: str


@dataclass
class AlteredRegion:
    """Bounding box of a detected tampered region (pixels)."""
    region_id: int
    x: int
    y: int
    width: int
    height: int
    area_px: int
    confidence: float       # 0–1


@dataclass
class AnalysisResult:
    """Complete output of the DeepfakeDetector pipeline."""
    image_path: str
    classification: str             # REAL | FAKE | AI_GENERATED
    fakeness_percentage: float      # 0–100
    verdict_summary: str
    probe_scores: list              # List[ProbeScore]
    altered_regions: list           # List[AlteredRegion]   (FAKE only)
    highlighted_image_path: str     # Saved path or ""
    metadata: dict                  # Raw EXIF key-values


# ══════════════════════════════════════════════════════════════════════════════
# PROBE IMPLEMENTATIONS
# ══════════════════════════════════════════════════════════════════════════════

class ELAProbe:
    """
    Error Level Analysis (ELA)
    --------------------------
    Re-compresses the image at a known JPEG quality and measures the pixel
    difference (error level).

    • Authentic images have *uniform* low error (consistent re-compression).
    • Manipulated regions were last saved at a different quality/tool, so they
      show *elevated* error levels compared with surrounding intact areas.
    • AI-generated images often exhibit globally elevated and uniform ELA maps
      because every pixel was "written" by the model at the same fidelity.
    """

    QUALITY    = 95      # Re-compression quality
    AMPLIFY    = 12      # Visual amplification factor for saved ELA map

    def run(self, pil_img: Image.Image) -> tuple[float, np.ndarray]:
        """
        Returns
        -------
        ela_score : float in [0, 1]
        ela_map   : uint8 numpy array (H x W x 3) – amplified ELA image
        """
        buf = io.BytesIO()
        pil_img.save(buf, format="JPEG", quality=self.QUALITY)
        buf.seek(0)
        recomp = Image.open(buf).convert("RGB")

        diff = ImageChops.difference(pil_img.convert("RGB"), recomp)
        diff_arr = np.array(diff, dtype=np.float32)

        # ---------- score -------------------------------------------------
        # Mean absolute error, normalised by theoretical max per-channel
        mean_err = diff_arr.mean()
        ela_score = float(np.clip(mean_err / 20.0, 0.0, 1.0))

        # ---------- amplified map for visualisation -----------------------
        scale = 255.0 / (diff_arr.max() + 1e-6) * self.AMPLIFY
        ela_map = np.clip(diff_arr * scale, 0, 255).astype(np.uint8)

        return ela_score, ela_map


class FrequencyProbe:
    """
    FFT Frequency-Domain Analysis
    ------------------------------
    GAN / diffusion models produce characteristic artefacts in the frequency
    spectrum:

    • Real camera images have a natural 1/f ("pink noise") power spectrum
      with smooth roll-off.
    • AI-generated images often show spectral peaks at regular grid positions
      (upsampling artefacts) and an anomalously flat high-frequency floor.
    • The probe measures two things:
        1. High-to-low frequency energy ratio  – AI images have a relatively
           *elevated* high-frequency floor.
        2. Spectral regularity (peak clustering) – GAN grids create periodic
           spikes detectable as a high coefficient of variation in the spectrum.
    """

    def run(self, cv_img: np.ndarray) -> float:
        gray  = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY).astype(np.float64)
        h, w  = gray.shape
        ch, cw = h // 2, w // 2

        fmag = np.abs(fftshift(fft2(gray)))
        fmag = np.log1p(fmag)

        # ── Ring masks ────────────────────────────────────────────────────
        Y, X = np.ogrid[:h, :w]
        dist = np.sqrt((X - cw) ** 2 + (Y - ch) ** 2)

        r_lo = min(ch, cw) * 0.05
        r_hi = min(ch, cw) * 0.45

        low_mask  = dist < r_lo
        high_mask = (dist > r_hi) & (dist < min(ch, cw) * 0.50)

        lo_energy = fmag[low_mask].mean()  + 1e-9
        hi_energy = fmag[high_mask].mean() + 1e-9
        ratio = hi_energy / lo_energy

        # ── Spectral uniformity (GAN grid indicator) ──────────────────────
        # Sample the mid-frequency annulus and measure its CoV
        mid_mask  = (dist > r_lo) & (dist < r_hi)
        mid_vals  = fmag[mid_mask]
        cov       = mid_vals.std() / (mid_vals.mean() + 1e-9)

        # ── Compose score ─────────────────────────────────────────────────
        # Real images → ratio low, cov high (varied texture)
        # AI images   → ratio elevated, cov low (uniform spectrum)
        ratio_score     = float(np.clip(ratio / 0.6, 0, 1))
        regularity_score = float(np.clip(1.0 - cov / 1.5, 0, 1))

        freq_score = 0.5 * ratio_score + 0.5 * regularity_score
        return float(np.clip(freq_score, 0.0, 1.0))


class NoiseConsistencyProbe:
    """
    Noise / PRNU Consistency Analysis
    -----------------------------------
    Real cameras imprint a unique Photo Response Non-Uniformity (PRNU) pattern
    on every image.  When part of an image is replaced (Photoshop clone-stamp,
    in-painting, GAN face-swap) the noise pattern in the swapped region differs
    from the rest of the image.

    Method
    ------
    1. Extract the noise residual via a high-pass filter (Gaussian subtraction).
    2. Tile the image into 32 × 32 non-overlapping blocks.
    3. Compute local noise variance per block.
    4. Measure the coefficient of variation (σ/μ) of those variances.
       • Real images  → moderate, spatially *varied* noise (different textures,
         lighting conditions across the frame → moderate CoV).
       • AI images    → suspiciously *uniform* noise (low CoV).
       • Fake images  → *elevated* CoV because the spliced region has different
         noise statistics from the authentic background.
    """

    BLOCK = 32

    def run(self, cv_img: np.ndarray) -> tuple[float, np.ndarray]:
        gray  = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY).astype(np.float64)
        blur  = cv2.GaussianBlur(gray, (5, 5), 0)
        noise = gray - blur

        h, w   = noise.shape
        bh, bw = h // self.BLOCK, w // self.BLOCK

        block_vars = []
        variance_map = np.zeros_like(noise)

        for i in range(bh):
            for j in range(bw):
                r0, r1 = i * self.BLOCK, (i + 1) * self.BLOCK
                c0, c1 = j * self.BLOCK, (j + 1) * self.BLOCK
                patch  = noise[r0:r1, c0:c1]
                v = float(np.var(patch))
                block_vars.append(v)
                variance_map[r0:r1, c0:c1] = v

        if not block_vars:
            return 0.5, variance_map

        bv  = np.array(block_vars)
        mu  = bv.mean() + 1e-9
        cov = bv.std() / mu

        # CoV calibration
        # • Very low  CoV (<0.3) → AI-like uniformity → score → high
        # • Moderate  CoV (0.3–1.5) → natural variability → score → low
        # • Very high CoV (>1.5) → inconsistent (splice) → score → medium-high
        if cov < 0.3:
            noise_score = 0.80    # suspiciously uniform → AI-generated
        elif cov < 1.5:
            noise_score = float(np.clip(cov / 4.0, 0.05, 0.40))
        else:
            noise_score = float(np.clip(0.40 + (cov - 1.5) / 5.0, 0.40, 0.75))

        return float(np.clip(noise_score, 0, 1)), variance_map


class JPEGGhostProbe:
    """
    JPEG Ghost Detection
    --------------------
    If a region was copy-pasted from an image saved at a different JPEG quality,
    it will show a characteristic "ghost" when the composite image is
    re-compressed at multiple quality levels and differenced against the original.

    Steps
    -----
    1. Re-save the image at several quality levels {60, 70, 80, 90}.
    2. Compute pixel-wise MSE against the original at each quality.
    3. The quality at which each pixel has minimum error tells us the
       "native quality" of that pixel.
    4. If significant spatial variation exists in native quality → manipulation.
    """

    QUALITIES = [60, 70, 80, 90]

    def run(self, pil_img: Image.Image) -> float:
        orig = np.array(pil_img.convert("RGB"), dtype=np.float32)
        quality_maps = []

        for q in self.QUALITIES:
            buf = io.BytesIO()
            pil_img.save(buf, format="JPEG", quality=q)
            buf.seek(0)
            rq = np.array(Image.open(buf).convert("RGB"), dtype=np.float32)
            mse_map = np.mean((orig - rq) ** 2, axis=2)
            quality_maps.append(mse_map)

        # Stack → (Q, H, W)
        qstack = np.stack(quality_maps, axis=0)
        # Index of minimum error per pixel
        best_q_idx = np.argmin(qstack, axis=0)

        # Spatial entropy of the best-quality map
        h_hist, _ = np.histogram(best_q_idx.flatten(), bins=len(self.QUALITIES))
        h_prob = h_hist / h_hist.sum()
        h_prob = h_prob[h_prob > 0]
        entropy = -np.sum(h_prob * np.log2(h_prob))

        # Max entropy ≈ log2(len(QUALITIES)) for uniform dist
        max_ent = math.log2(len(self.QUALITIES))
        ghost_score = float(np.clip(entropy / max_ent, 0, 1))

        return ghost_score


class MetadataProbe:
    """
    EXIF / Metadata Forensics
    --------------------------
    Authentic camera images carry rich EXIF: camera make/model, lens, GPS,
    capture timestamps, and proprietary manufacturer tags.

    AI-generated images are born as synthetic pixels – they have *no* EXIF
    unless one is artificially injected (which is rare and detectable by
    inconsistencies).

    Edited images may retain partial EXIF from the original but lose GPS data
    or show software tags like "Adobe Photoshop".
    """

    # EXIF tag IDs for key camera fields
    CAMERA_TAGS  = {271: "Make", 272: "Model", 305: "Software"}
    CAPTURE_TAGS = {36867: "DateTimeOriginal", 36868: "DateTimeDigitized"}
    GPS_TAG      = 34853   # GPSInfo

    def run(self, image_path: str) -> tuple[float, dict]:
        meta = {}
        try:
            img    = Image.open(image_path)
            exif   = img._getexif() if hasattr(img, "_getexif") else None
        except Exception:
            return 0.60, meta

        if exif is None:
            return 0.70, {"exif": "absent"}

        # Collect readable tags
        for tag_id, label in {**self.CAMERA_TAGS, **self.CAPTURE_TAGS,
                               self.GPS_TAG: "GPSInfo"}.items():
            if tag_id in exif:
                meta[label] = str(exif[tag_id])[:120]

        score = 0.70   # default: no useful tags

        has_camera  = any(t in exif for t in self.CAMERA_TAGS)
        has_capture = any(t in exif for t in self.CAPTURE_TAGS)
        has_gps     = self.GPS_TAG in exif

        if has_camera and has_capture and has_gps:
            score = 0.05   # strong evidence of real camera origin
        elif has_camera and has_capture:
            score = 0.15
        elif has_camera:
            score = 0.30
        elif exif:
            score = 0.50   # EXIF present but stripped of camera data

        # Penalise if editing software is detected in EXIF
        sw_tag = exif.get(305, "") or ""
        editing_keywords = ["photoshop", "lightroom", "gimp",
                            "capture one", "affinity", "luminar",
                            "midjourney", "stable diffusion", "dall-e",
                            "firefly", "canva"]
        for kw in editing_keywords:
            if kw in str(sw_tag).lower():
                score = min(score + 0.35, 0.95)
                meta["detected_software"] = str(sw_tag)
                break

        return float(np.clip(score, 0, 1)), meta


class ColourGradientProbe:
    """
    Colour Distribution & Gradient Coherence
    -----------------------------------------
    Real photographic images exhibit:
    • Rich, high-entropy colour histograms (lots of colour variety).
    • Gradient magnitude distributions that follow natural scene statistics.
    • Non-trivial GLCM texture energy (fabric, foliage, skin all have
      characteristic second-order statistics).

    AI generators:
    • Can produce unnaturally smooth gradients (especially in backgrounds,
      skin, sky) – low gradient variance.
    • Sometimes over-saturate or under-saturate specific hue ranges.
    • GLCM energy can be anomalously high (too uniform) or too low (too random).
    """

    def run(self, cv_img: np.ndarray) -> float:
        hsv  = cv2.cvtColor(cv_img, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        # ── 1. Colour histogram entropy ───────────────────────────────────
        def channel_entropy(img_ch: np.ndarray, bins: int = 64) -> float:
            hist, _ = np.histogram(img_ch.flatten(), bins=bins,
                                   range=(0, 256), density=True)
            hist = hist[hist > 0]
            return float(-np.sum(hist * np.log2(hist + 1e-12)))

        h_ent = channel_entropy(hsv[:, :, 0], 36)
        s_ent = channel_entropy(hsv[:, :, 1])
        v_ent = channel_entropy(hsv[:, :, 2])
        avg_ent = (h_ent + s_ent + v_ent) / 3.0
        # Real images: avg_ent typically 3–6 bits; AI can be < 2 or anomalously high
        ent_score = float(np.clip(1.0 - avg_ent / 6.0, 0, 1))

        # ── 2. Gradient coherence ─────────────────────────────────────────
        gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
        gm = np.sqrt(gx ** 2 + gy ** 2)

        grad_mean = gm.mean() + 1e-9
        grad_cv   = gm.std() / grad_mean
        # High CoV (>1) = natural edges; Low CoV (<0.6) = overly smooth (AI)
        grad_score = float(np.clip(1.0 - grad_cv / 2.5, 0, 1))

        # ── 3. GLCM texture ───────────────────────────────────────────────
        small   = cv2.resize(gray, (128, 128))
        glcm    = graycomatrix(small, distances=[1], angles=[0, np.pi / 4,
                               np.pi / 2, 3 * np.pi / 4],
                               levels=256, symmetric=True, normed=True)
        energy  = float(graycoprops(glcm, "energy").mean())
        # energy: 0→random texture,  1→uniform texture
        # AI images can sit at either extreme; moderate energy is most natural
        tex_score = float(np.clip(abs(energy - 0.15) / 0.15, 0, 1))

        # Weighted combine
        colour_score = 0.35 * ent_score + 0.40 * grad_score + 0.25 * tex_score
        return float(np.clip(colour_score, 0, 1))


# ══════════════════════════════════════════════════════════════════════════════
# REGION HIGHLIGHTER
# ══════════════════════════════════════════════════════════════════════════════

class RegionHighlighter:
    """
    Identifies and marks the tampered regions on a FAKE image.

    Strategy
    --------
    Uses the ELA map as the primary localisation signal (amplified per-pixel
    error) combined with the noise variance map.  Threshold → morphological
    clean-up → contour extraction → bounding boxes.
    """

    ELA_THRESHOLD   = 40      # Min ELA grey value to consider suspicious
    MIN_AREA_PX     = 200     # Minimum contour area (pixels²) to keep
    OVERLAY_ALPHA   = 0.30    # Semi-transparent red fill

    def run(self,
            pil_img  : Image.Image,
            ela_map  : np.ndarray,
            noise_map: np.ndarray
            ) -> tuple[Image.Image, list[AlteredRegion]]:

        # ── Combine signals ───────────────────────────────────────────────
        ela_gray = cv2.cvtColor(ela_map, cv2.COLOR_RGB2GRAY) \
            if ela_map.ndim == 3 else ela_map

        # Normalise noise map to 0-255
        nmap_norm = cv2.normalize(noise_map.astype(np.float32),
                                  None, 0, 255, cv2.NORM_MINMAX).astype(np.uint8)

        combined = cv2.addWeighted(ela_gray, 0.7, nmap_norm, 0.3, 0)

        # ── Threshold & morphological clean-up ────────────────────────────
        _, thresh = cv2.threshold(combined,
                                  self.ELA_THRESHOLD, 255, cv2.THRESH_BINARY)
        k1     = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        k2     = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN,  k1)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, k2)
        thresh = cv2.dilate(thresh, k1, iterations=2)

        # ── Contours ──────────────────────────────────────────────────────
        contours, _ = cv2.findContours(thresh,
                                       cv2.RETR_EXTERNAL,
                                       cv2.CHAIN_APPROX_SIMPLE)

        canvas   = np.array(pil_img.convert("RGB"))
        regions  = []
        rid      = 1

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < self.MIN_AREA_PX:
                continue

            x, y, bw, bh = cv2.boundingRect(cnt)

            # Confidence: ratio of mean ELA inside box vs global mean
            roi_ela  = ela_gray[y:y + bh, x:x + bw]
            conf     = float(np.clip(roi_ela.mean() / (ela_gray.mean() + 1e-6)
                                     / 3.0, 0, 1))

            # Draw bounding rectangle
            cv2.rectangle(canvas, (x, y), (x + bw, y + bh), (220, 30, 30), 2)

            # Semi-transparent red fill
            overlay = canvas.copy()
            cv2.rectangle(overlay, (x, y), (x + bw, y + bh), (220, 30, 30), -1)
            cv2.addWeighted(overlay, self.OVERLAY_ALPHA,
                            canvas,  1 - self.OVERLAY_ALPHA, 0, canvas)

            # Label
            label    = f"R{rid} ({conf:.0%})"
            font_scl = max(0.4, min(bw, bh) / 100)
            cv2.putText(canvas, label, (x + 4, y - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, font_scl,
                        (255, 255, 80), 1, cv2.LINE_AA)

            regions.append(AlteredRegion(
                region_id   = rid,
                x=int(x), y=int(y),
                width=int(bw), height=int(bh),
                area_px=int(area),
                confidence=round(conf, 3)
            ))
            rid += 1

        # Legend
        self._draw_legend(canvas)

        return Image.fromarray(canvas), regions

    @staticmethod
    def _draw_legend(canvas: np.ndarray) -> None:
        h, w = canvas.shape[:2]
        legend_h = 28
        cv2.rectangle(canvas, (0, h - legend_h), (w, h), (20, 20, 20), -1)
        cv2.putText(canvas,
                    "RED boxes = detected altered regions",
                    (8, h - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45,
                    (220, 180, 80), 1, cv2.LINE_AA)


# ══════════════════════════════════════════════════════════════════════════════
# SCORE AGGREGATOR
# ══════════════════════════════════════════════════════════════════════════════

class ScoreAggregator:
    """
    Combines probe scores into a single fakeness percentage.

    Probes have different inherent sensitivities to each image class:

    +-----------------------+-------------+--------+--------+
    | Probe                 | AI-gen bias | Fake   | Real   |
    +-----------------------+-------------+--------+--------+
    | ELA                   | ✓           | ✓✓     | –      |
    | Frequency (FFT)       | ✓✓          | ✓      | –      |
    | Noise Consistency     | ✓✓          | ✓      | –      |
    | JPEG Ghost            | –           | ✓✓     | –      |
    | Metadata              | ✓✓          | ✓      | –      |
    | Colour / Gradient     | ✓           | ✓      | –      |
    +-----------------------+-------------+--------+--------+

    The weights below reflect these biases so that a genuine FAKE
    and a genuine AI image can both reach their respective thresholds.
    """

    WEIGHTS = {
        "ELA"              : 0.28,
        "Frequency"        : 0.18,
        "NoiseConsistency" : 0.18,
        "JPEGGhost"        : 0.14,
        "Metadata"         : 0.12,
        "ColourGradient"   : 0.10,
    }

    def aggregate(self, probes: list[ProbeScore]) -> float:
        total_w, weighted = 0.0, 0.0
        for p in probes:
            w = self.WEIGHTS.get(p.name, 0.0)
            weighted += p.raw_score * w
            total_w  += w
        raw = weighted / max(total_w, 1e-9)
        # Stretch to fill [0, 100] range more naturally
        return float(round(np.clip(raw * 100, 0, 100), 2))

    @staticmethod
    def classify(fakeness: float) -> tuple[str, str]:
        if fakeness >= 90.0:
            cls = "AI_GENERATED"
            summary = (f"Image appears to be entirely AI-generated "
                       f"(fakeness {fakeness:.1f}%). "
                       "No authentic camera traces detected.")
        elif fakeness >= 50.0:
            cls = "FAKE"
            summary = (f"Image appears to have been partially altered "
                       f"(fakeness {fakeness:.1f}%). "
                       "Inconsistencies in noise, ELA, or ghost patterns "
                       "indicate manual or AI-assisted manipulation.")
        else:
            cls = "REAL"
            summary = (f"Image appears to be authentic "
                       f"(fakeness {fakeness:.1f}%). "
                       "Forensic indicators are consistent with an "
                       "unmodified camera capture.")
        return cls, summary


# ══════════════════════════════════════════════════════════════════════════════
# MAIN DETECTOR
# ══════════════════════════════════════════════════════════════════════════════

class DeepfakeDetector:
    """
    End-to-end deepfake / image-manipulation detection.

    Usage
    -----
        detector = DeepfakeDetector()
        result   = detector.analyze("path/to/image.jpg")
        print(result.classification, result.fakeness_percentage)
    """

    def __init__(self, output_dir: str = "detector_output"):
        self.output_dir   = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Instantiate probes
        self._ela       = ELAProbe()
        self._freq      = FrequencyProbe()
        self._noise     = NoiseConsistencyProbe()
        self._ghost     = JPEGGhostProbe()
        self._meta      = MetadataProbe()
        self._colour    = ColourGradientProbe()
        self._highliter = RegionHighlighter()
        self._agg       = ScoreAggregator()

    # ── Public API ────────────────────────────────────────────────────────

    def analyze(self, image_path: str) -> AnalysisResult:
        """
        Run the full detection pipeline on a single image.

        Parameters
        ----------
        image_path : str
            Path to the input image (JPEG, PNG, WEBP, BMP supported).

        Returns
        -------
        AnalysisResult
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image not found: {image_path}")

        log.info("Loading image: %s", path.name)

        # ── Resize large images before analysis ──────────────────────
        # Keeps analysis under 30s on free-tier servers
        pil_img = Image.open(path).convert("RGB")
        MAX_DIM = 800
        w, h = pil_img.size
        if max(w, h) > MAX_DIM:
            ratio = MAX_DIM / max(w, h)
            new_w, new_h = int(w * ratio), int(h * ratio)
            pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)
            pil_img.save(str(path))   # overwrite with resized version
            log.info("Resized %dx%d → %dx%d for analysis", w, h, new_w, new_h)
        
        cv_img  = cv2.imread(str(path))
        if cv_img is None:
            raise ValueError(f"OpenCV could not decode: {image_path}")

        # ── Run probes ────────────────────────────────────────────────────
        log.info("Running ELA probe …")
        ela_score, ela_map = self._ela.run(pil_img)

        log.info("Running frequency probe …")
        freq_score = self._freq.run(cv_img)

        log.info("Running noise-consistency probe …")
        noise_score, noise_map = self._noise.run(cv_img)

        log.info("Running JPEG-ghost probe …")
        ghost_score = self._ghost.run(pil_img)

        log.info("Running metadata probe …")
        meta_score, meta_dict = self._meta.run(str(path))

        log.info("Running colour/gradient probe …")
        colour_score = self._colour.run(cv_img)

        # ── Build probe list ──────────────────────────────────────────────
        probes = [
            ProbeScore("ELA",              ela_score,    0.28,
                       "JPEG re-compression error levels"),
            ProbeScore("Frequency",        freq_score,   0.18,
                       "FFT spectral fingerprint anomaly"),
            ProbeScore("NoiseConsistency", noise_score,  0.18,
                       "PRNU-based noise uniformity"),
            ProbeScore("JPEGGhost",        ghost_score,  0.14,
                       "Multi-quality ghost artefacts"),
            ProbeScore("Metadata",         meta_score,   0.12,
                       "EXIF provenance analysis"),
            ProbeScore("ColourGradient",   colour_score, 0.10,
                       "Colour entropy & gradient coherence"),
        ]

        # ── Aggregate ─────────────────────────────────────────────────────
        fakeness       = self._agg.aggregate(probes)
        classification, summary = self._agg.classify(fakeness)

        # ── Region highlighting (FAKE only) ───────────────────────────────
        highlighted_path = ""
        regions: list[AlteredRegion] = []

        if classification == "FAKE":
            log.info("Highlighting altered regions …")
            hi_img, regions = self._highliter.run(pil_img, ela_map, noise_map)
            stem = path.stem
            out  = self.output_dir / f"{stem}_highlighted.jpg"
            hi_img.save(str(out), quality=92)
            highlighted_path = str(out)
            log.info("Highlighted image saved → %s", out)

        # ── Save analysis artefacts ───────────────────────────────────────
        self._save_ela_map(ela_map, path.stem)
        json_path = self._save_json(
            image_path, classification, fakeness,
            summary, probes, regions, highlighted_path, meta_dict
        )
        log.info("JSON report saved → %s", json_path)

        return AnalysisResult(
            image_path           = str(path),
            classification       = classification,
            fakeness_percentage  = fakeness,
            verdict_summary      = summary,
            probe_scores         = probes,
            altered_regions      = regions,
            highlighted_image_path = highlighted_path,
            metadata             = meta_dict,
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _save_ela_map(self, ela_map: np.ndarray, stem: str) -> None:
        ela_path = self.output_dir / f"{stem}_ela.jpg"
        Image.fromarray(ela_map).save(str(ela_path), quality=92)
        log.info("ELA map saved        → %s", ela_path)

    def _save_json(self, image_path, classification, fakeness,
                   summary, probes, regions, hl_path, meta) -> Path:
        report = {
            "image_path"           : image_path,
            "classification"       : classification,
            "fakeness_percentage"  : fakeness,
            "verdict_summary"      : summary,
            "highlighted_image"    : hl_path,
            "probe_scores": [
                {
                    "probe"      : p.name,
                    "raw_score"  : round(p.raw_score, 4),
                    "weight"     : p.weight,
                    "description": p.description,
                }
                for p in probes
            ],
            "altered_regions": [asdict(r) for r in regions],
            "metadata_exif"        : meta,
        }
        stem     = Path(image_path).stem
        out_path = self.output_dir / f"{stem}_report.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        return out_path

    # ── Pretty-print ──────────────────────────────────────────────────────

    @staticmethod
    def print_result(result: AnalysisResult) -> None:
        """Console-friendly summary of AnalysisResult."""
        W = 64
        print("\n" + "═" * W)
        print(f"  DEEPFAKE DETECTION REPORT")
        print("═" * W)
        print(f"  Image      : {Path(result.image_path).name}")
        print(f"  Class      : {result.classification}")
        print(f"  Fakeness   : {result.fakeness_percentage:.1f}%")
        print(f"  Verdict    : {result.verdict_summary}")
        print("─" * W)
        print("  PROBE BREAKDOWN")
        print("─" * W)
        print(f"  {'Probe':<22} {'Score':>7}  {'Weight':>7}  {'Bar'}")
        print(f"  {'─'*22}  {'─'*7}  {'─'*7}  {'─'*20}")
        for p in result.probe_scores:
            bar_len = int(p.raw_score * 20)
            bar     = "█" * bar_len + "░" * (20 - bar_len)
            print(f"  {p.name:<22} {p.raw_score:>7.4f}  {p.weight:>7.2f}  {bar}")
        print("─" * W)
        if result.altered_regions:
            print(f"  ALTERED REGIONS  ({len(result.altered_regions)} detected)")
            print("─" * W)
            for r in result.altered_regions:
                print(f"   R{r.region_id}: "
                      f"({r.x},{r.y}) {r.width}×{r.height}px  "
                      f"area={r.area_px}px²  conf={r.confidence:.0%}")
        if result.metadata:
            print("─" * W)
            print("  EXIF METADATA")
            for k, v in result.metadata.items():
                print(f"   {k:<22}: {v}")
        if result.highlighted_image_path:
            print("─" * W)
            print(f"  Highlighted image  : {result.highlighted_image_path}")
        print("═" * W + "\n")


# ══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def build_cli() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog        = "deepfake_detector",
        description = "Deepfake / Image-Manipulation Detection Engine",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples
            --------
              python deepfake_detector.py photo.jpg
              python deepfake_detector.py photo.jpg --output results/
              python deepfake_detector.py photo.jpg --json-only
        """)
    )
    p.add_argument("image",       help="Path to input image")
    p.add_argument("--output",    default="detector_output",
                   help="Directory for output artefacts (default: detector_output)")
    p.add_argument("--json-only", action="store_true",
                   help="Suppress console report, print JSON to stdout")
    return p


if __name__ == "__main__":
    import textwrap

    parser = build_cli()
    args   = parser.parse_args()

    detector = DeepfakeDetector(output_dir=args.output)
    result   = detector.analyze(args.image)

    if args.json_only:
        # Machine-readable output
        out = {
            "classification"      : result.classification,
            "fakeness_percentage" : result.fakeness_percentage,
            "verdict_summary"     : result.verdict_summary,
            "probe_scores"        : [
                {"probe": p.name, "score": p.raw_score, "weight": p.weight}
                for p in result.probe_scores
            ],
            "altered_regions": [asdict(r) for r in result.altered_regions],
            "highlighted_image"   : result.highlighted_image_path,
        }
        print(json.dumps(out, indent=2))
    else:
        DeepfakeDetector.print_result(result)
