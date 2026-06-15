from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ..analysis import AnalysisResult

VEHICLE_TYPES: tuple[str, ...] = (
    "sedan",
    "suv",
    "hatchback",
    "pickup",
    "minibus",
    "panelvan",
    "kamyon",
)

VEHICLE_COLORS: tuple[str, ...] = (
    "beyaz",
    "siyah",
    "gri",
    "kirmizi",
    "mavi",
    "sari",
    "yesil",
    "turuncu",
    "kahverengi",
)

DETECTION_LABELS_BY_CATEGORY: dict[str, tuple[str, ...]] = {
    "sofor_eylemi": (
        "arkaya_bakma",
        "esneme",
        "sigara_icme",
        "su_icme",
        "telefonla_konusma",
        "slalom",
        "etrafa_bakinma",
        "emniyet_kemeri_ihlali",
    ),
    "nesneler": (
        "teknocan",
        "bilgisayar",
    ),
    "yolcular": (
        "arka_koltuk_1",
        "arka_koltuk_2",
        "on_koltuk",
    ),
}

PLATE_PATTERN = re.compile(
    r"^(0[1-9]|[1-7][0-9]|8[01])"
    r"((\s?[a-zA-Z]\s?)(\d{4,5})|"
    r"(\s?[a-zA-Z]{2}\s?)(\d{3,4})|"
    r"(\s?[a-zA-Z]{3}\s?)(\d{2,3}))$"
)

ASCII_SAFE_PATTERN = re.compile(r"^[a-z0-9_]+$")

_INTERNAL_LABEL_TO_FTR_DRIVER_LABELS: dict[str, tuple[str, ...]] = {
    "smoking": ("sigara_icme",),
    "smoking_and_unsafe_scanning": ("sigara_icme", "etrafa_bakinma"),
    "phone_use": ("telefonla_konusma",),
    "phone_use_while_driving": ("telefonla_konusma",),
    "phone_right": ("telefonla_konusma",),
    "phone_left": ("telefonla_konusma",),
    "phonecall_right": ("telefonla_konusma",),
    "phonecall_left": ("telefonla_konusma",),
    "texting_right": ("telefonla_konusma",),
    "texting_left": ("telefonla_konusma",),
    "Using phone": ("telefonla_konusma",),
    "drinking": ("su_icme",),
    "yawning_with_hand": ("esneme",),
    "yawning_without_hand": ("esneme",),
    "Drowsiness": ("esneme",),
    "unsafe_scanning": ("etrafa_bakinma",),
    "No attention": ("etrafa_bakinma",),
    "drunk_like_erratic_driving": ("slalom",),
    "Smoking": ("sigara_icme",),
    "Unfastened belt": ("emniyet_kemeri_ihlali",),
}


def _require_text(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} must not be empty.")
    return cleaned


def _require_score(value: float, field_name: str) -> float:
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{field_name} must be between 0.0 and 1.0.")
    return value


def _require_ascii_label(value: str, field_name: str) -> str:
    cleaned = _require_text(value, field_name)
    if not ASCII_SAFE_PATTERN.fullmatch(cleaned):
        raise ValueError(f"{field_name} must be lowercase ASCII-safe text: {cleaned}")
    return cleaned


def normalize_plate(plate: str) -> str:
    """Normalize a Turkish plate candidate for FTR regex matching.

    If the plate cannot be read by OCR, pass ``"tespit_edilemedi"`` which is
    accepted as a sentinel (FTR spec: plates outside regex are scored as not detected).
    """
    cleaned = _require_text(plate, "plaka").upper().replace(" ", "")
    if cleaned == "TESPIT_EDILEMEDI":
        return "tespit_edilemedi"
    if not PLATE_PATTERN.fullmatch(cleaned):
        raise ValueError(
            "plaka must match the FTR Turkish plate regex after normalization."
        )
    return cleaned


@dataclass(frozen=True)
class VehicleInfo:
    tip: str
    plaka: str
    renk: str
    confidence_score: float

    def __post_init__(self) -> None:
        tip = _require_ascii_label(self.tip, "tip")
        if tip not in VEHICLE_TYPES:
            raise ValueError(f"Unsupported FTR vehicle type: {tip}")
        renk = _require_ascii_label(self.renk, "renk")
        if renk not in VEHICLE_COLORS:
            raise ValueError(f"Unsupported FTR vehicle color: {renk}")
        object.__setattr__(self, "tip", tip)
        object.__setattr__(self, "plaka", normalize_plate(self.plaka))
        object.__setattr__(
            self, "confidence_score", _require_score(self.confidence_score, "confidence_score")
        )
        object.__setattr__(self, "renk", renk)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "VehicleInfo":
        required = {"tip", "plaka", "renk", "confidence_score"}
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"arac_bilgisi is missing required keys: {', '.join(missing)}")
        return cls(
            tip=str(payload["tip"]),
            plaka=str(payload["plaka"]),
            renk=str(payload["renk"]),
            confidence_score=float(payload["confidence_score"]),
        )


@dataclass(frozen=True)
class DetectionEvent:
    zaman_saniye: float
    kategori: str
    etiket: str
    confidence_score: float

    def __post_init__(self) -> None:
        if self.zaman_saniye < 0:
            raise ValueError("zaman_saniye must be non-negative.")
        kategori = _require_ascii_label(self.kategori, "kategori")
        etiket = _require_ascii_label(self.etiket, "etiket")
        allowed_labels = DETECTION_LABELS_BY_CATEGORY.get(kategori)
        if allowed_labels is None:
            raise ValueError(f"Unsupported FTR detection category: {kategori}")
        if etiket not in allowed_labels:
            raise ValueError(
                f"Unsupported FTR detection label for {kategori}: {etiket}"
            )
        object.__setattr__(self, "kategori", kategori)
        object.__setattr__(self, "etiket", etiket)
        object.__setattr__(
            self, "confidence_score", _require_score(self.confidence_score, "confidence_score")
        )

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "DetectionEvent":
        required = {"zaman_saniye", "kategori", "etiket", "confidence_score"}
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"tespit entry is missing required keys: {', '.join(missing)}")
        return cls(
            zaman_saniye=float(payload["zaman_saniye"]),
            kategori=str(payload["kategori"]),
            etiket=str(payload["etiket"]),
            confidence_score=float(payload["confidence_score"]),
        )


@dataclass(frozen=True)
class FtrCompetitionResult:
    video_id: str
    arac_bilgisi: VehicleInfo
    tespitler: tuple[DetectionEvent, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "video_id", _require_text(self.video_id, "video_id"))

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "FtrCompetitionResult":
        required = {"video_id", "arac_bilgisi", "tespitler"}
        missing = sorted(required - payload.keys())
        if missing:
            raise ValueError(f"FTR result is missing required keys: {', '.join(missing)}")
        tespitler_payload = payload["tespitler"]
        if not isinstance(tespitler_payload, list):
            raise ValueError("tespitler must be a list.")
        return cls(
            video_id=str(payload["video_id"]),
            arac_bilgisi=VehicleInfo.from_dict(payload["arac_bilgisi"]),
            tespitler=tuple(DetectionEvent.from_dict(item) for item in tespitler_payload),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_ftr_result_payload(payload: dict[str, Any]) -> FtrCompetitionResult:
    return FtrCompetitionResult.from_dict(payload)


def read_ftr_result(path: str | Path) -> FtrCompetitionResult:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return validate_ftr_result_payload(payload)


def write_ftr_result(result: FtrCompetitionResult, output_path: str | Path) -> Path:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def map_internal_label_to_ftr_driver_labels(
    internal_label: str, notes: tuple[str, ...] = ()
) -> tuple[str, ...]:
    labels: list[str] = []
    candidates = (internal_label, *notes)
    for candidate in candidates:
        mapped = _INTERNAL_LABEL_TO_FTR_DRIVER_LABELS.get(candidate)
        if mapped is None:
            continue
        for value in mapped:
            if value not in labels:
                labels.append(value)
    if labels:
        return tuple(labels)
    raise ValueError(
        "No exact FTR label mapping exists for internal label "
        f"{internal_label!r}. Add a mapping or collect FTR-aligned labels."
    )


def build_ftr_result_from_analysis(
    analysis_result: AnalysisResult,
    video_id: str,
    vehicle_info: VehicleInfo,
    event_time_seconds: float = 0.0,
) -> FtrCompetitionResult:
    labels = map_internal_label_to_ftr_driver_labels(
        analysis_result.driver_risk_label,
        analysis_result.notes,
    )
    confidence = max(0.0, min(1.0, analysis_result.driver_risk_score))
    detections = tuple(
        DetectionEvent(
            zaman_saniye=event_time_seconds,
            kategori="sofor_eylemi",
            etiket=label,
            confidence_score=confidence,
        )
        for label in labels
    )
    return FtrCompetitionResult(
        video_id=video_id,
        arac_bilgisi=vehicle_info,
        tespitler=detections,
    )
