from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

from ..competition import DETECTION_LABELS_BY_CATEGORY, VEHICLE_COLORS, VEHICLE_TYPES
from ..manifest import DatasetManifest, compare_manifest_to_assumptions
from ..modeling import ReportModelBundle, load_report_model_bundle
from .docx import DocxBlock, extract_docx_text, write_docx


@dataclass(frozen=True)
class FinalReportBuildResult:
    docx_path: str
    markdown_path: str
    evidence_path: str
    section_count: int
    model_count: int


REQUIRED_TEMPLATE_HEADINGS: tuple[str, ...] = (
    "PROJE ÖZETİ",
    "VERİSETİ OLUŞTURULMASI",
    "YAPAY ZEKÂ ÇÖZÜMÜ",
    "Problemin Analizi",
    "Çözüm Mimarisi",
    "Çözüm Detayları",
    "ÇÖZÜMÜN SINANMASI",
    "KAYNAKÇA",
)

DATASET_MANIFESTS: tuple[str, ...] = (
    "data/real_dataset_manifest.json",
    "data/datasets/state-farm-distracted-driver/manifest.json",
    "data/datasets/dmd-distraction/manifest.json",
    "data/datasets/dmd-drowsiness/manifest.json",
    "data/datasets/DriverSVT-teknofest/manifest.json",
)

MODEL_SELECTION_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "Araç, plaka ve nesne algılama",
        "YOLO11n/s birincil; RT-DETR doğruluk ablation adayı",
        "Tek geçişli gerçek zamanlı çıkarım, T4 bütçesine uygun ağırlık/latency dengesi.",
    ),
    (
        "Plaka okuma",
        "YOLO plaka kırpımı + PaddleOCR tabanlı OCR + FTR regex sonrası işleme",
        "Plaka metni exact-match gerektirdiği için görüntü modeli kadar format validasyonu da kritik.",
    ),
    (
        "Şoför eylemleri",
        "VideoMAE/SlowFast temporal başlık + State Farm/DMD ön eğitim desteği",
        "Telefon, sigara, su içme, esneme ve bakış yönü zaman penceresiyle daha güvenilir ayrılır.",
    ),
    (
        "Hız ve slalom",
        "ByteTrack izleme + kamera geometrisi/homography + DriverSVT telemetry ablation",
        "FTR JSON hız alanı içermese de şartname hız/risk kanıtı istediği için iç metrik olarak tutulur.",
    ),
)

REFERENCE_ROWS: tuple[tuple[str, str], ...] = (
    (
        "FTR Teslim Dokümanı",
        "5G_ve_Yapay_Zeka_ile_Akıllı_Yol_Güvenliği_Yarışması - FTR Aşaması Teslim Dokümanı.",
    ),
    ("Rapor Şablonu", "final_report_template.docx, Final Tasarım Raporu bölüm ve format yönergesi."),
    ("State Farm", "State Farm Distracted Driver Detection veri seti, driver_imgs_list.csv."),
    ("DMD", "Driver Monitoring Dataset distraction/drowsiness OpenLABEL anotasyonları."),
    ("DriverSVT", "Smartphone-Measured Vehicle Telemetry Data for Driver State Identification."),
    ("YOLO11", "Ultralytics YOLO11 model dokümantasyonu."),
    ("PaddleOCR", "PaddleOCR OCR toolkit dokümantasyonu."),
    ("MMAction2", "OpenMMLab video action recognition model zoo."),
    ("ByteTrack", "FoundationVision ByteTrack multi-object tracking implementation."),
)


def build_final_report(
    template_path: str | Path = "final_report_template.docx",
    model_artifacts_path: str | Path = "out/model_artifacts/ktr_model_artifacts.json",
    output_path: str | Path = "out/ktr_final_report.docx",
    markdown_path: str | Path = "out/ktr_final_report.md",
    evidence_path: str | Path = "out/ktr_report_evidence.json",
    team_name: str = "Doldurulacak",
    team_id: str = "Doldurulacak",
    application_id: str = "Doldurulacak",
) -> FinalReportBuildResult:
    template_text = extract_docx_text(template_path)
    missing_headings = [
        heading for heading in REQUIRED_TEMPLATE_HEADINGS if heading not in template_text
    ]
    if missing_headings:
        raise ValueError(
            "final_report_template.docx is missing required headings: "
            + ", ".join(missing_headings)
        )

    bundle = load_report_model_bundle(model_artifacts_path)
    dataset_rows = _dataset_rows()
    gap_rows = _gap_rows()
    model_rows = _model_rows(bundle)
    metrics_rows = _metrics_rows(bundle)
    ftr_rows = _ftr_schema_rows()
    repo_rows = _repo_trace_rows(bundle)

    evidence = {
        "template_path": str(template_path),
        "model_artifacts_path": str(model_artifacts_path),
        "source_documents": [
            "5G_ve_Yapay_Zeka_ile_Akıllı_Yol_Güvenliği_Yarışması_-_FTR_Aşaması_Teslim_D.pdf",
            "final_report_template.docx",
        ],
        "datasets": dataset_rows,
        "gaps": gap_rows,
        "models": [asdict(model) for model in bundle.models],
        "generated_on": date.today().isoformat(),
    }
    Path(evidence_path).parent.mkdir(parents=True, exist_ok=True)
    Path(evidence_path).write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    markdown = _render_markdown(
        team_name=team_name,
        team_id=team_id,
        application_id=application_id,
        dataset_rows=dataset_rows,
        gap_rows=gap_rows,
        model_rows=model_rows,
        metrics_rows=metrics_rows,
        ftr_rows=ftr_rows,
        repo_rows=repo_rows,
    )
    Path(markdown_path).parent.mkdir(parents=True, exist_ok=True)
    Path(markdown_path).write_text(markdown, encoding="utf-8")

    blocks = _build_docx_blocks(
        team_name=team_name,
        team_id=team_id,
        application_id=application_id,
        dataset_rows=dataset_rows,
        gap_rows=gap_rows,
        model_rows=model_rows,
        metrics_rows=metrics_rows,
        ftr_rows=ftr_rows,
        repo_rows=repo_rows,
    )
    write_docx(tuple(blocks), output_path)
    return FinalReportBuildResult(
        docx_path=str(output_path),
        markdown_path=str(markdown_path),
        evidence_path=str(evidence_path),
        section_count=len(REQUIRED_TEMPLATE_HEADINGS),
        model_count=len(bundle.models),
    )


def _dataset_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for manifest_path in DATASET_MANIFESTS:
        path = Path(manifest_path)
        if not path.exists():
            continue
        manifest = DatasetManifest.from_path(path)
        rows.append(
            {
                "dataset": str(manifest.extra_fields.get("dataset_name", path.stem)),
                "unit": manifest.sample_unit,
                "format": manifest.annotation_format,
                "targets": ", ".join(manifest.targets),
                "ftr_families": ", ".join(
                    str(value)
                    for value in manifest.extra_fields.get(
                        "ftr_output_families_covered", []
                    )
                )
                or "destek/gap",
                "repo_path": manifest_path,
            }
        )
    return rows


def _gap_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for manifest_path in DATASET_MANIFESTS:
        path = Path(manifest_path)
        if not path.exists():
            continue
        manifest = DatasetManifest.from_path(path)
        for gap in compare_manifest_to_assumptions(manifest):
            if gap.assumption_id not in {"DS-004", "DS-005"}:
                continue
            message, action = _turkish_gap(gap.message, gap.action)
            rows.append(
                {
                    "dataset": str(manifest.extra_fields.get("dataset_name", path.stem)),
                    "gap": message,
                    "action": action,
                }
            )
    return rows


def _turkish_gap(message: str, action: str) -> tuple[str, str]:
    if "plate text" in message:
        return (
            "Exact plaka metni etiketi yok.",
            (
                "Plaka OCR veri seti/adapteri veya manuel Türk plaka anotasyonu "
                "eklenene kadar plate exact-match metriği iddia edilmemeli."
            ),
        )
    if "FTR output family" in message:
        missing = message.split(":", 1)[-1].strip()
        return (
            f"FTR çıktı ailesi eksik: {missing}.",
            (
                "Bu veri seti destek/eğitim verisi olarak kullanılmalı; eksik "
                "aileler için FTR hizalı anotasyon veya ek veri eklenmeli."
            ),
        )
    return message, action


def _model_rows(bundle: ReportModelBundle) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for model in bundle.models:
        rows.append(
            {
                "model": model.model_id,
                "family": model.model_family,
                "final_architecture": model.selected_final_architecture,
                "samples": str(model.sample_count),
                "split": model.split_strategy,
                "artifact": model.artifact_path,
            }
        )
    return rows


def _metrics_rows(bundle: ReportModelBundle) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for model in bundle.models:
        metrics = model.metrics
        rows.append(
            {
                "model": model.model_id,
                "accuracy": _metric(metrics, "validation_accuracy", "session_prior_accuracy"),
                "precision": _metric(metrics, "macro_precision"),
                "recall": _metric(metrics, "macro_recall"),
                "f1": _metric(metrics, "macro_f1"),
                "n": _metric(metrics, "validation_samples", "sessions"),
            }
        )
    return rows


def _metric(metrics: dict[str, float], *names: str) -> str:
    for name in names:
        if name in metrics:
            value = metrics[name]
            if name in {"validation_samples", "sessions"}:
                return str(int(value))
            return f"{value:.3f}"
    return "-"


def _ftr_schema_rows() -> list[dict[str, str]]:
    rows = [
        {"field": "arac_bilgisi.tip", "allowed": ", ".join(VEHICLE_TYPES)},
        {"field": "arac_bilgisi.renk", "allowed": ", ".join(VEHICLE_COLORS)},
    ]
    for category, labels in DETECTION_LABELS_BY_CATEGORY.items():
        rows.append({"field": f"tespitler.{category}", "allowed": ", ".join(labels)})
    return rows


def _repo_trace_rows(bundle: ReportModelBundle) -> list[dict[str, str]]:
    paths = {
        "FTR şema doğrulama": "src/smart_road_safety/competition/ftr.py",
        "Dataset manifest kontrolü": "src/smart_road_safety/manifest.py",
        "Dataset adapterleri": "src/smart_road_safety/data/real_adapters.py",
        "Rapor modeli eğitimi": "src/smart_road_safety/modeling/report_models.py",
        "Rapor üretimi": "src/smart_road_safety/reporting/final_report.py",
        "DOCX yazıcı": "src/smart_road_safety/reporting/docx.py",
    }
    for model in bundle.models:
        for path in model.repo_paths:
            paths.setdefault(f"Model kanıtı: {model.model_id}", path)
    return [{"purpose": key, "path": value} for key, value in paths.items()]


def _build_docx_blocks(
    team_name: str,
    team_id: str,
    application_id: str,
    dataset_rows: list[dict[str, str]],
    gap_rows: list[dict[str, str]],
    model_rows: list[dict[str, str]],
    metrics_rows: list[dict[str, str]],
    ftr_rows: list[dict[str, str]],
    repo_rows: list[dict[str, str]],
) -> list[DocxBlock]:
    blocks: list[DocxBlock] = [
        DocxBlock("title", "5G & YAPAY ZEKÂ İLE AKILLI YOL GÜVENLİĞİ YARIŞMASI"),
        DocxBlock("title", "FİNAL TASARIM RAPORU"),
        DocxBlock("subtitle", f"Takım Adı: {team_name}"),
        DocxBlock("subtitle", f"Takım ID: {team_id}"),
        DocxBlock("subtitle", f"Başvuru ID: {application_id}"),
        DocxBlock("page_break"),
        DocxBlock("heading", "İÇİNDEKİLER"),
        DocxBlock("paragraph", "1. PROJE ÖZETİ"),
        DocxBlock("paragraph", "2. VERİSETİ OLUŞTURULMASI"),
        DocxBlock("paragraph", "3. YAPAY ZEKÂ ÇÖZÜMÜ"),
        DocxBlock("paragraph", "4. ÇÖZÜMÜN SINANMASI"),
        DocxBlock("paragraph", "5. KAYNAKÇA"),
        DocxBlock("page_break"),
    ]
    blocks.extend(_section_blocks(dataset_rows, gap_rows, model_rows, metrics_rows, ftr_rows, repo_rows))
    return blocks


def _section_blocks(
    dataset_rows: list[dict[str, str]],
    gap_rows: list[dict[str, str]],
    model_rows: list[dict[str, str]],
    metrics_rows: list[dict[str, str]],
    ftr_rows: list[dict[str, str]],
    repo_rows: list[dict[str, str]],
) -> list[DocxBlock]:
    return [
        DocxBlock("heading", "1. PROJE ÖZETİ"),
        DocxBlock("paragraph", _project_summary()),
        DocxBlock("heading", "2. VERİSETİ OLUŞTURULMASI"),
        DocxBlock("paragraph", _dataset_text()),
        DocxBlock("table", rows=_table_rows(dataset_rows, ["dataset", "unit", "format", "ftr_families"])),
        DocxBlock("paragraph", "Eksik aileler ve kapatma aksiyonları aşağıdaki tabloda izlenir."),
        DocxBlock("table", rows=_table_rows(gap_rows[:10], ["dataset", "gap", "action"])),
        DocxBlock("heading", "3. YAPAY ZEKÂ ÇÖZÜMÜ"),
        DocxBlock("heading", "3.1. Problemin Analizi", level=2),
        DocxBlock("paragraph", _problem_analysis_text()),
        DocxBlock("heading", "3.2. Çözüm Mimarisi", level=2),
        DocxBlock("paragraph", _architecture_text()),
        DocxBlock("table", rows=_table_rows(repo_rows, ["purpose", "path"])),
        DocxBlock("heading", "3.3. Çözüm Detayları", level=2),
        DocxBlock("paragraph", _solution_details_text()),
        DocxBlock("table", rows=MODEL_SELECTION_ROWS),
        DocxBlock("paragraph", "FTR çıktı ailesi aşağıdaki exact değerlerle sınırlandırılmıştır."),
        DocxBlock("table", rows=_table_rows(ftr_rows, ["field", "allowed"])),
        DocxBlock("heading", "4. ÇÖZÜMÜN SINANMASI"),
        DocxBlock("paragraph", _testing_text()),
        DocxBlock("table", rows=_table_rows(model_rows, ["model", "family", "samples", "artifact"])),
        DocxBlock("table", rows=_table_rows(metrics_rows, ["model", "accuracy", "precision", "recall", "f1", "n"])),
        DocxBlock("heading", "5. KAYNAKÇA"),
        DocxBlock("table", rows=REFERENCE_ROWS),
    ]


def _project_summary() -> str:
    return (
        "Bu rapor, akıllı yol güvenliği yarışmasının FTR çıktı şemasına uyumlu "
        "görü tabanlı analiz hattını açıklar. Sistem, ham videodan araç bilgisi, "
        "plaka uygunluğu ve zaman damgalı risk/nesne/yolcu tespitleri üretmek için "
        "dataset adapterleri, FTR şema doğrulayıcısı, eğitilmiş rapor baseline modelleri "
        "ve DOCX rapor üretim katmanını birleştirir. Odak, final_report_template.docx "
        "başlıklarına uygun biçimde veri seti, model, mimari, metrik ve kaynak kanıtını "
        "repo dosyalarıyla izlenebilir hale getirmektir."
    )


def _dataset_text() -> str:
    return (
        "Veri hattı tek bir veri setine bağımlı değildir. State Farm görüntüleri "
        "şoför eylemleri için, DMD OpenLABEL videoları temporal kabin davranışları için, "
        "DriverSVT telemetry satırları hız/risk ablation kanıtı için, üç yerel video ise "
        "FTR JSON smoke doğrulaması için kullanılır. Bölmeler sızıntıyı azaltmak için "
        "subject/session/user seviyesinde tanımlanır; FTR ailelerini tam karşılamayan "
        "alanlar manifest gap çıktısıyla rapora taşınır."
    )


def _problem_analysis_text() -> str:
    return (
        "Temel zorluklar plakanın küçük alan kaplaması, hareket bulanıklığı, far/parlama, "
        "kabin içi yansıma, el-nesne oklüzyonu, yolcu/nesne etiketlerinin seyrekliği ve "
        "slalom gibi olayların tek kare yerine zaman penceresi gerektirmesidir. Bu nedenle "
        "çözüm; hızlı nesne algılama, OCR sonrası format kontrolü, temporal eylem tanıma "
        "ve iz tabanlı hız/slalom analizi olarak ayrıştırılmıştır."
    )


def _architecture_text() -> str:
    return (
        "Mimari akış şu bileşenlerden oluşur: video girişi, dataset/manifest doğrulama, "
        "model çıkarım katmanı, FTR etiket eşleme ve results.json yazıcı. Repo içinde "
        "competition/ftr.py exact şemayı korur; modeling/report_models.py eğitim kanıtı "
        "üretir; reporting/final_report.py bu kanıtları şablon başlıklarına yerleştirir."
    )


def _solution_details_text() -> str:
    return (
        "Seçilen final mimarisi modülerdir: YOLO11 küçük/orta modelleri araç, plaka ve "
        "nesne algılama için birincil adaydır; RT-DETR doğruluk ablation için tutulur. "
        "Plaka metni YOLO ile kırpılıp PaddleOCR ile okunur ve FTR Türk plaka regex'iyle "
        "temizlenir. Şoför eylemleri için VideoMAE/SlowFast tarzı temporal ağlar, State "
        "Farm ve DMD destek verisiyle eğitilir. Hız ve slalom için ByteTrack izleri, kamera "
        "geometrisi ve DriverSVT telemetry ablation hattı birlikte kullanılır."
    )


def _testing_text() -> str:
    return (
        "Bu aşamada rapora giren metrikler, yerel olarak tekrar üretilebilir baseline "
        "eğitimlerinden ve FTR şema doğrulama komutlarından gelir. Deep-learning ağırlıkları "
        "eklendiğinde aynı tabloya mAP, OCR exact-match, temporal F1, FPS ve Docker çalışma "
        "süresi ölçümleri eklenecektir. Mevcut çıktı, hangi sonuçların ölçüldüğünü ve hangi "
        "alanların hâlâ anotasyon veya ağırlık beklediğini açıkça ayırır."
    )


def _render_markdown(
    team_name: str,
    team_id: str,
    application_id: str,
    dataset_rows: list[dict[str, str]],
    gap_rows: list[dict[str, str]],
    model_rows: list[dict[str, str]],
    metrics_rows: list[dict[str, str]],
    ftr_rows: list[dict[str, str]],
    repo_rows: list[dict[str, str]],
) -> str:
    lines = [
        "# 5G & Yapay Zekâ ile Akıllı Yol Güvenliği Yarışması Final Tasarım Raporu",
        "",
        f"Takım Adı: {team_name}",
        f"Takım ID: {team_id}",
        f"Başvuru ID: {application_id}",
        "",
        "## 1. PROJE ÖZETİ",
        _project_summary(),
        "",
        "## 2. VERİSETİ OLUŞTURULMASI",
        _dataset_text(),
        "",
        _markdown_table(dataset_rows, ["dataset", "unit", "format", "ftr_families"]),
        "",
        "### Veri boşlukları ve kapatma planı",
        _markdown_table(gap_rows[:10], ["dataset", "gap", "action"]),
        "",
        "## 3. YAPAY ZEKÂ ÇÖZÜMÜ",
        "",
        "### 3.1. Problemin Analizi",
        _problem_analysis_text(),
        "",
        "### 3.2. Çözüm Mimarisi",
        _architecture_text(),
        "",
        _markdown_table(repo_rows, ["purpose", "path"]),
        "",
        "### 3.3. Çözüm Detayları",
        _solution_details_text(),
        "",
        _markdown_table(
            [
                {"task": row[0], "model": row[1], "rationale": row[2]}
                for row in MODEL_SELECTION_ROWS
            ],
            ["task", "model", "rationale"],
        ),
        "",
        "#### FTR çıktı alanları",
        _markdown_table(ftr_rows, ["field", "allowed"]),
        "",
        "## 4. ÇÖZÜMÜN SINANMASI",
        _testing_text(),
        "",
        _markdown_table(model_rows, ["model", "family", "samples", "artifact"]),
        "",
        _markdown_table(metrics_rows, ["model", "accuracy", "precision", "recall", "f1", "n"]),
        "",
        "## 5. KAYNAKÇA",
        _markdown_table(
            [{"source": row[0], "detail": row[1]} for row in REFERENCE_ROWS],
            ["source", "detail"],
        ),
        "",
    ]
    return "\n".join(lines)


def _table_rows(rows: list[dict[str, str]], keys: list[str]) -> tuple[tuple[str, ...], ...]:
    if not rows:
        return (tuple(keys), tuple("-" for _ in keys))
    return (tuple(keys), *(tuple(str(row.get(key, "")) for key in keys) for row in rows))


def _markdown_table(rows: list[dict[str, str]], keys: list[str]) -> str:
    table_rows = _table_rows(rows, keys)
    lines = ["| " + " | ".join(table_rows[0]) + " |"]
    lines.append("| " + " | ".join("---" for _ in table_rows[0]) + " |")
    for row in table_rows[1:]:
        lines.append("| " + " | ".join(_escape_cell(value) for value in row) + " |")
    return "\n".join(lines)


def _escape_cell(value: str) -> str:
    return value.replace("|", "/").replace("\n", " ")
