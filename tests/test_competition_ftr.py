from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.analysis import (
    AnalysisResult,
    AnalysisSessionRequest,
    run_analysis_session,
)
from smart_road_safety.competition import (
    DetectionEvent,
    FtrCompetitionResult,
    VehicleInfo,
    build_ftr_result_from_analysis,
    normalize_plate,
    validate_ftr_result_payload,
)


class FtrCompetitionContractTest(unittest.TestCase):
    def test_vehicle_info_normalizes_turkish_plate(self) -> None:
        info = VehicleInfo(
            tip="suv",
            plaka="34 abc 123",
            renk="mavi",
            confidence_score=0.94,
        )

        self.assertEqual(info.plaka, "34ABC123")
        self.assertEqual(normalize_plate("06aa1234"), "06AA1234")

    def test_result_schema_rejects_unsupported_turkish_labels(self) -> None:
        with self.assertRaises(ValueError):
            DetectionEvent(
                zaman_saniye=1.0,
                kategori="şoför_eylemi",
                etiket="telefonla_konusma",
                confidence_score=0.9,
            )

    def test_payload_validation_accepts_source_of_truth_shape(self) -> None:
        result = validate_ftr_result_payload(
            {
                "video_id": "video_001.mp4",
                "arac_bilgisi": {
                    "tip": "sedan",
                    "plaka": "34ABC123",
                    "renk": "beyaz",
                    "confidence_score": 0.94,
                },
                "tespitler": [
                    {
                        "zaman_saniye": 14.5,
                        "kategori": "sofor_eylemi",
                        "etiket": "telefonla_konusma",
                        "confidence_score": 0.89,
                    }
                ],
            }
        )

        self.assertIsInstance(result, FtrCompetitionResult)
        self.assertEqual(result.tespitler[0].etiket, "telefonla_konusma")

    def test_analysis_result_can_build_ftr_output_with_explicit_vehicle_info(self) -> None:
        request = AnalysisSessionRequest.from_path(
            ROOT / "examples" / "analysis_session_request.json"
        )
        session_result = run_analysis_session(request)
        ftr_result = build_ftr_result_from_analysis(
            analysis_result=session_result.analysis_result,
            video_id="video_1.mp4",
            vehicle_info=VehicleInfo.from_dict(
                {
                    "tip": "suv",
                    "plaka": "34ABC123",
                    "renk": "mavi",
                    "confidence_score": 0.94,
                }
            ),
            event_time_seconds=1.5,
        )

        labels = {event.etiket for event in ftr_result.tespitler}
        self.assertEqual(ftr_result.video_id, "video_1.mp4")
        self.assertEqual(labels, {"sigara_icme", "etrafa_bakinma"})

    def test_unmapped_internal_label_fails_loudly(self) -> None:
        with self.assertRaises(ValueError):
            build_ftr_result_from_analysis(
                analysis_result=AnalysisResult(
                    source_ref="test://sample",
                    quality_profile="standard",
                    target_vehicle_detected=False,
                    target_vehicle_confidence=0.0,
                    plate_candidate_detected=False,
                    plate_visibility_score=0.0,
                    driver_risk_score=0.5,
                    driver_risk_label="unknown",
                    distance_meters=None,
                    summary_message="Synthetic unsupported label test.",
                ),
                video_id="video_unknown.mp4",
                vehicle_info=VehicleInfo(
                    tip="suv",
                    plaka="34ABC123",
                    renk="mavi",
                    confidence_score=0.94,
                ),
            )


if __name__ == "__main__":
    unittest.main()

class AtomicFtrWriteTests(unittest.TestCase):
    def test_atomic_timeline_write_is_deterministic(self):
        import tempfile
        from pathlib import Path
        from smart_road_safety.competition import (
            DetectionEvent, VehicleInfo, build_ftr_result_from_timeline,
            read_ftr_result, write_ftr_result_atomic,
        )
        vehicle = VehicleInfo("suv", "34TC8532", "siyah", 0.9)
        events = [
            DetectionEvent(2.0, "nesneler", "teknocan", 0.8),
            DetectionEvent(1.0, "sofor_eylemi", "esneme", 0.7),
        ]
        result = build_ftr_result_from_timeline("video.mp4", vehicle, events)
        with tempfile.TemporaryDirectory() as temp:
            target = write_ftr_result_atomic(result, Path(temp) / "results.json")
            self.assertEqual([e.zaman_saniye for e in read_ftr_result(target).tespitler], [1.0, 2.0])
            self.assertFalse(any(Path(temp).glob("*.tmp")))
