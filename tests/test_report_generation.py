from __future__ import annotations

import json
import sys
import zipfile
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.modeling import train_report_models
from smart_road_safety.reporting import build_final_report, extract_docx_text
from smart_road_safety.reporting.docx import DocxBlock, write_docx


class ReportModelTrainingTest(unittest.TestCase):
    def test_train_report_models_writes_reproducible_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_state_farm_fixture(root)
            self._write_driver_svt_fixture(root)

            bundle = train_report_models(
                data_root=root,
                output_dir=root / "out" / "model_artifacts",
                max_driver_svt_rows=6,
            )

            bundle_path = root / "out" / "model_artifacts" / "ktr_model_artifacts.json"
            self.assertTrue(bundle_path.exists())
            self.assertGreaterEqual(len(bundle.models), 2)
            model_ids = {model.model_id for model in bundle.models}
            self.assertIn("state_farm_driver_action_prior", model_ids)
            self.assertIn("driver_svt_telemetry_centroid", model_ids)

    def test_build_final_report_creates_docx_and_markdown_without_report_scope_leak(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            template = root / "template.docx"
            write_docx(
                tuple(
                    DocxBlock("heading", heading)
                    for heading in (
                        "PROJE ÖZETİ",
                        "VERİSETİ OLUŞTURULMASI",
                        "YAPAY ZEKÂ ÇÖZÜMÜ",
                        "Problemin Analizi",
                        "Çözüm Mimarisi",
                        "Çözüm Detayları",
                        "ÇÖZÜMÜN SINANMASI",
                        "KAYNAKÇA",
                    )
                ),
                template,
            )
            artifacts = root / "model_artifacts.json"
            artifacts.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-06-15T00:00:00+00:00",
                        "data_root": "data",
                        "max_driver_svt_rows": 10,
                        "dataset_notes": [],
                        "models": [
                            {
                                "model_id": "state_farm_driver_action_prior",
                                "model_family": "trained class-prior baseline",
                                "selected_final_architecture": "YOLO11/VideoMAE",
                                "training_source": "fixture.csv",
                                "sample_count": 4,
                                "split_strategy": "subject-grouped",
                                "labels": ["safe_driving", "texting_right"],
                                "metrics": {
                                    "validation_accuracy": 0.5,
                                    "macro_precision": 0.25,
                                    "macro_recall": 0.5,
                                    "macro_f1": 0.333,
                                    "validation_samples": 2,
                                },
                                "artifact_path": "artifact.json",
                                "repo_paths": ["src/smart_road_safety/modeling/report_models.py"],
                                "limitations": [],
                                "parameters": {},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            result = build_final_report(
                template_path=template,
                model_artifacts_path=artifacts,
                output_path=root / "report.docx",
                markdown_path=root / "report.md",
                evidence_path=root / "evidence.json",
            )

            self.assertTrue(Path(result.docx_path).exists())
            self.assertTrue(Path(result.markdown_path).exists())
            text = extract_docx_text(result.docx_path)
            markdown = Path(result.markdown_path).read_text(encoding="utf-8")
            self.assertIn("PROJE ÖZETİ", text)
            self.assertIn("YOLO11", text)
            self.assertIn("EK A. GÖRSEL KOD REFERANSLARI", text)
            with zipfile.ZipFile(result.docx_path) as archive:
                document = ET.fromstring(archive.read("word/document.xml"))
            namespace = {
                "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            }
            captions = [
                "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace))
                for paragraph in document.findall(".//w:p", namespace)
                if paragraph.find(
                    "./w:pPr/w:pStyle[@w:val='Caption']", namespace
                )
                is not None
            ]
            self.assertIn("Şekil 1. Uçtan uca yapay zekâ çıkarım hattı", captions)
            self.assertNotIn("docs/diagrams/ktr_ai_pipeline.mmd", text)
            self.assertNotIn(".mmd", text)
            self.assertIn("Ek A.1. Model ağırlık yükleme mantığı", text)
            self.assertIn("![Şekil 1. Uçtan uca yapay zekâ çıkarım hattı]", markdown)
            self.assertIn("docs/report_assets/code_snippets_v3/model_agirlik_yukleme.png", markdown)
            self.assertNotIn("```mermaid", markdown)
            self.assertNotIn("```python", markdown)
            self.assertNotIn("flowchart TD", text)
            self.assertNotIn("def build_final_report", text)
            self.assertNotIn("Quality on Demand", text)
            self.assertNotIn("Quality on Demand", markdown)
            with zipfile.ZipFile(result.docx_path) as zf:
                names = set(zf.namelist())
            self.assertTrue(any(name.startswith("word/media/image") for name in names))

    def _write_state_farm_fixture(self, root: Path) -> None:
        dataset_root = root / "datasets" / "state-farm-distracted-driver"
        dataset_root.mkdir(parents=True)
        (dataset_root / "manifest.json").write_text(
            json.dumps(
                {
                    "sample_unit": "frame",
                    "video_extensions": [],
                    "annotation_format": "folder_class_csv",
                    "includes_train_split": True,
                    "includes_validation_split": False,
                    "includes_test_split": True,
                    "targets": ["driver_behavior", "distraction"],
                    "has_frame_level_annotations": True,
                    "has_clip_level_annotations": False,
                    "has_plate_text": False,
                    "has_speed_ground_truth": False,
                    "has_in_cabin_annotations": True,
                    "has_driver_behavior_annotations": True,
                    "speed_unit": None,
                }
            ),
            encoding="utf-8",
        )
        (dataset_root / "driver_imgs_list.csv").write_text(
            "subject,classname,img\n"
            "p001,c0,img_1.jpg\n"
            "p001,c1,img_2.jpg\n"
            "p002,c1,img_3.jpg\n"
            "p003,c6,img_4.jpg\n",
            encoding="utf-8",
        )

    def _write_driver_svt_fixture(self, root: Path) -> None:
        dataset_root = root / "datasets" / "DriverSVT-teknofest"
        dataset_root.mkdir(parents=True)
        header = ",userid,dangerousstate,speed,gforce,lightlevel,perclos,mouth_open_ratio,heart_rate,acc_X,acc_Y,acc_Z\n"
        rows = [
            "0,u1,Normal,10,0.1,1,0.0,0.0,70,0,0,0",
            "1,u1,Using phone,12,0.2,1,0.1,0.0,72,0,0,1",
            "2,u2,Smoking,14,0.2,1,0.1,0.1,75,0,1,0",
            "3,u2,Drowsiness,8,0.1,1,0.5,0.2,68,1,0,0",
            "4,u3,Normal,9,0.1,1,0.0,0.0,71,0,0,0",
            "5,u3,Using phone,13,0.2,1,0.1,0.0,73,0,0,1",
        ]
        (dataset_root / "DriverSVT.csv").write_text(header + "\n".join(rows), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
