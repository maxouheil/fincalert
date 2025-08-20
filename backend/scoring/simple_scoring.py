"""
Simple Combined Scoring (V1)

- Three criteria (each 1/3/5 points):
  - Luminosité nocturne (VIIRS): faible/moyen/fort
  - Activité radar (Sentinel-1 VV, dB): faible/moyen/fort
  - Entretien végétation (NDVI): faible/moyen/fort

- Total = sum of criteria out of 15
- Classification:
  - total < 5      => "Inactive"
  - 5 <= total <10 => "Moderate"
  - total >= 10    => "Active"

Notes:
- Higher points mean lower abandonment risk (aligned with frontend wording)
- Thresholds can be tuned later; these are sensible defaults based on current data
"""

from dataclasses import dataclass
from typing import Dict, Tuple


def _safe_cv(std_dev: float | None, median: float | None) -> float:
    if std_dev is None or median is None or median <= 0:
        return 0.0
    return float(std_dev) / float(median)


@dataclass(frozen=True)
class ViirsThresholds:
    # nW/cm²/sr — low luminosity implies higher abandonment risk
    low_max: float = 0.700
    medium_max: float = 1.209
    # high is > medium_max


@dataclass(frozen=True)
class RadarThresholds:
    # Sentinel-1 VV backscatter in dB — Seuils ajustés pour 20/50/30
    low_max_db: float = -11.404     # ≤ -11.404 dB → Faible (1 pt)
    medium_max_db: float = -10.066   # ≤ -10.066 dB → Moyen (3 pts); > -10.066 → Fort (5 pts)


@dataclass(frozen=True)
class NdviThresholds:
    # Use NDVI abandonment score from existing pipeline (0-100; higher = more abandoned)
    # Map to vegetation maintenance points (inverse relationship)
    active_max: float = 35.0   # ≤ 35 → Fort (5 pts)
    moderate_max: float = 65.0 # (35, 65] → Moyen (3 pts); > 65 → Faible (1 pt)


def score_viirs(mean_luminosity: float, thresholds: ViirsThresholds = ViirsThresholds()) -> Tuple[int, str]:
    if mean_luminosity is None:
        return 1, "Faible"
    if mean_luminosity <= thresholds.low_max:
        return 1, "Faible"
    if mean_luminosity <= thresholds.medium_max:
        return 3, "Moyen"
    return 5, "Fort"


def score_radar(vv_db: float, thresholds: RadarThresholds = RadarThresholds()) -> Tuple[int, str]:
    if vv_db is None:
        return 1, "Faible"
    if vv_db <= thresholds.low_max_db:
        return 1, "Faible"
    if vv_db <= thresholds.medium_max_db:
        return 3, "Moyen"
    return 5, "Fort"


def score_vegetation(ndvi_abandon_score: float, thresholds: NdviThresholds = NdviThresholds()) -> Tuple[int, str]:
    if ndvi_abandon_score is None:
        return 1, "Faible"
    if ndvi_abandon_score <= thresholds.active_max:
        return 5, "Fort"
    if ndvi_abandon_score <= thresholds.moderate_max:
        return 3, "Moyen"
    return 1, "Faible"


def score_vegetation_from_ndvi_summary(median_ndvi: float | None, std: float | None) -> Tuple[int, str]:
    """
    Map NDVI summary (median, std) to 1/3/5 points using CV thresholds.
    Higher variability (higher CV) -> more maintenance -> higher points.
    
    Entretien végétation basé sur la variation NDVI:
    - Faible (1pt): Peu d'entretien, variation faible (CV < 12%)
    - Moyen (3pt): Entretien modéré, variation moyenne (CV 12-25%)
    - Fort (5pt): Beaucoup d'entretien, variation forte (CV ≥ 25%)
    """
    if median_ndvi is None or std is None:
        return 1, "Faible"
    cv = _safe_cv(std, median_ndvi)  # e.g., 0.25 means 25%
    if cv >= 0.25:
        return 5, "Fort"      # Beaucoup d'entretien, variation forte
    if cv >= 0.12:
        return 3, "Moyen"     # Entretien modéré, variation moyenne
    return 1, "Faible"        # Peu d'entretien, variation faible


def classify_total(total_points: int) -> str:
    if total_points < 5:
        return "Inactive"
    if total_points < 10:
        return "Moderate"
    return "Active"


def compute_simple_score(
    viirs_mean_luminosity: float | None,
    sentinel1_vv_db: float | None,
    ndvi_abandon_score: float | None = None,
    ndvi_median: float | None = None,
    ndvi_std: float | None = None,
) -> Dict:
    viirs_points, viirs_level = score_viirs(viirs_mean_luminosity)
    radar_points, radar_level = score_radar(sentinel1_vv_db)
    if ndvi_abandon_score is not None:
        ndvi_points, ndvi_level = score_vegetation(ndvi_abandon_score)
    else:
        ndvi_points, ndvi_level = score_vegetation_from_ndvi_summary(ndvi_median, ndvi_std)

    total = viirs_points + radar_points + ndvi_points
    classification = classify_total(total)

    return {
        "criteria": {
            "luminosite": {"level": viirs_level, "points": viirs_points},
            "radar": {"level": radar_level, "points": radar_points},
            "entretien_vegetation": {"level": ndvi_level, "points": ndvi_points},
        },
        "total_points": total,
        "out_of": 15,
        "classification": classification,
        "thresholds": {
            "viirs": ViirsThresholds().__dict__,
            "radar": RadarThresholds().__dict__,
            "ndvi": NdviThresholds().__dict__,
        },
    }
