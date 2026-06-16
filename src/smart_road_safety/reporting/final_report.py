from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

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


@dataclass(frozen=True)
class ReportImage:
    title: str
    source_path: str
    image_path: str


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

MERMAID_DIAGRAM_IMAGES: tuple[tuple[str, str, str], ...] = (
    (
        "Şekil 1. Uçtan uca yapay zekâ çıkarım hattı",
        "docs/diagrams/ktr_ai_pipeline.mmd",
        "docs/diagrams/rendered/ktr_ai_pipeline.png",
    ),
    (
        "Şekil 2. FTR doğrulama ve sonuç üretim akışı",
        "docs/diagrams/ftr_validation_flow.mmd",
        "docs/diagrams/rendered/ftr_validation_flow.png",
    ),
    (
        "Şekil 3. Model eğitimi ve ağırlık yönetimi akışı",
        "docs/diagrams/model_training_weights_flow.mmd",
        "docs/diagrams/rendered/model_training_weights_flow.png",
    ),
    (
        "Şekil 4. Rapor kanıt izi ve kaynak bağları",
        "docs/diagrams/report_evidence_trace.mmd",
        "docs/diagrams/rendered/report_evidence_trace.png",
    ),
)

CODE_SNIPPET_IMAGES: tuple[tuple[str, str, str], ...] = (
    (
        "Ek A.1. Model ağırlık yükleme mantığı",
        "src/smart_road_safety/analysis/model_inference.py",
        "docs/report_assets/code_snippets_v3/model_agirlik_yukleme.png",
    ),
    (
        "Ek A.2. Tek kare analiz mantığı",
        "src/smart_road_safety/analysis/model_inference.py",
        "docs/report_assets/code_snippets_v3/kare_analizi.png",
    ),
    (
        "Ek A.3. Sürücü olayı üretim mantığı",
        "src/smart_road_safety/analysis/model_inference.py",
        "docs/report_assets/code_snippets_v3/surucu_olaylari.png",
    ),
    (
        "Ek A.4. Video örnekleme ve tekilleştirme mantığı",
        "main.py",
        "docs/report_assets/code_snippets_v3/video_tekillestirme.png",
    ),
)

MODEL_SELECTION_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "Araç, kişi ve kabin nesnesi algılama",
        "YOLO11x çalışma zamanı; YOLO11s eğitim hattı",
        "Tek geçişli algılama ile araç, kişi, telefon ve bilgisayar adayları aynı kare üzerinden çıkarılır.",
    ),
    (
        "Araç rengi ve gövde tipi",
        "K-Means FTR renk paleti + EfficientNet-B0 araç tipi sınıflandırıcısı",
        "Açık kaynak ağırlık yoksa COCO sınıf eşlemesi kontrollü yedek yol olarak çalışır; sahte üst veri üretilmez.",
    ),
    (
        "Plaka okuma",
        "Araç kırpımı alt bölgesi + EasyOCR + Türk plaka regex doğrulaması",
        "Birebir plaka çıktısı için OCR sonucu biçim doğrulamasından geçmeden kabul edilmez.",
    ),
    (
        "Şoför eylemleri ve emniyet kemeri",
        "EfficientNet-B2/MobileNetV3 sınıflandırıcı + Canny/Hough çizgi sezgisel yöntemi",
        "State Farm/DMD destekli sınıflandırıcı davranışları üretir; emniyet kemeri başlangıç modeli geometrik kanıt verir.",
    ),
    (
        "Yolcu ve zamansal olay mantığı",
        "Kabin bölge geometrisi + 3 saniye tekilleştirme/yumuşatma + DriverSVT ayrıştırma",
        "Tekrarlı karelerden gelen olaylar tekil tespitlere indirilir; hız/risk şartname hedefi iç metrik olarak izlenir.",
    ),
)

REFERENCE_ITEMS: tuple[str, ...] = (
    "FTR Aşaması Teslim Dokümanı",
    "2026 Yarışma Şartnamesi",
    "Final rapor şablonu",
    "Ön Tasarım Raporu",
    "State Farm Distracted Driver veri seti",
    "Driver Monitoring Dataset",
    "DriverSVT veri seti",
    "Ultralytics YOLO11 — https://docs.ultralytics.com/models/yolo11/",
    "EasyOCR — https://github.com/JaidedAI/EasyOCR",
    "PyTorch ve TorchVision — https://docs.pytorch.org/vision/",
    "OpenCV — https://docs.opencv.org/",
    "Hugging Face Hub — https://huggingface.co/docs/huggingface_hub",
    "EfficientNet — https://arxiv.org/abs/1905.11946",
    "MobileNetV3 — https://arxiv.org/abs/1905.02244",
)



def build_final_report(
    template_path: str | Path = "final_report_template.docx",
    model_artifacts_path: str | Path = "out/model_artifacts/ktr_model_artifacts.json",
    output_path: str | Path = "ktr_v1.docx",
    markdown_path: str | Path = "out/ktr_v1.md",
    evidence_path: str | Path = "out/ktr_v1_evidence.json",
    team_name: str = "QoDe",
    team_id: str = "886046",
    application_id: str = "4865671",
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
    diagrams = _read_report_images(MERMAID_DIAGRAM_IMAGES)
    snippets = _read_report_images(CODE_SNIPPET_IMAGES)

    evidence = {
        "template_path": str(template_path),
        "model_artifacts_path": str(model_artifacts_path),
        "source_documents": [
            "5G_ve_Yapay_Zeka_ile_Akıllı_Yol_Güvenliği_Yarışması_-_FTR_Aşaması_Teslim_D.pdf",
            "2026_5G_YAPAY_ZEKA_İLE_AKILLI_YOL_GÜVENLİĞİ_YARISMASI_SARTNAMESI_2_PORZ6.pdf",
            "final_report_template.docx",
            "QoDe_On_Tasarim_Raporu.pdf",
        ],
        "style_rules": {
            "body_font": "Arial 12 pt",
            "heading_font": "Arial Black 14 pt",
            "line_spacing": "1.15",
            "alignment": "justified",
            "margins_cm": {"top": 2.8, "right": 2.5, "bottom": 2.5, "left": 2.5},
            "raw_code_or_mermaid_in_docx": False,
        },
        "datasets": dataset_rows,
        "gaps": gap_rows,
        "models": [asdict(model) for model in bundle.models],
        "repo_trace": repo_rows,
        "mermaid_diagrams": [asdict(diagram) for diagram in diagrams],
        "code_snippet_images": [asdict(snippet) for snippet in snippets],
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
        diagrams=diagrams,
        snippets=snippets,
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
        diagrams=diagrams,
        snippets=snippets,
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
                "veri_seti": str(manifest.extra_fields.get("dataset_name", path.stem)),
                "birim": manifest.sample_unit,
                "bicim": manifest.annotation_format,
                "hedefler": ", ".join(manifest.targets),
                "ftr_aileleri": ", ".join(
                    str(value)
                    for value in manifest.extra_fields.get(
                        "ftr_output_families_covered", []
                    )
                )
                or "destek/gap",
                "repo_yolu": manifest_path,
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
                    "veri_seti": str(manifest.extra_fields.get("dataset_name", path.stem)),
                    "gap": message,
                    "action": action,
                }
            )
    return rows


def _turkish_gap(message: str, action: str) -> tuple[str, str]:
    if "plate text" in message:
        return (
            "Birebir plaka metni etiketi yok.",
            (
                "Plaka OCR veri seti/adaptörü veya manuel Türk plaka anotasyonu "
                "eklenene kadar birebir plaka eşleşme metriği iddia edilmemeli."
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
                "aile": model.model_family,
                "final_mimari": model.selected_final_architecture,
                "ornek": str(model.sample_count),
                "bolme": model.split_strategy,
                "kanıt dosyası": model.artifact_path,
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
                "dogruluk": _metric(metrics, "validation_accuracy", "session_prior_accuracy"),
                "kesinlik": _metric(metrics, "macro_precision"),
                "duyarlilik": _metric(metrics, "macro_recall"),
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
        {"alan": "arac_bilgisi.tip", "izin_verilen": ", ".join(VEHICLE_TYPES)},
        {"alan": "arac_bilgisi.renk", "izin_verilen": ", ".join(VEHICLE_COLORS)},
    ]
    for category, labels in DETECTION_LABELS_BY_CATEGORY.items():
        rows.append({"alan": f"tespitler.{category}", "izin_verilen": ", ".join(labels)})
    return rows


def _repo_trace_rows(bundle: ReportModelBundle) -> list[dict[str, str]]:
    paths = {
        "FTR şema doğrulama": "src/smart_road_safety/competition/ftr.py",
        "Docker/FTR giriş noktası": "main.py",
        "Veri seti manifest kontrolü": "src/smart_road_safety/manifest.py",
        "Veri seti adaptörleri": "src/smart_road_safety/data/real_adapters.py",
        "Rapor modeli eğitimi": "src/smart_road_safety/modeling/report_models.py",
        "Rapor üretimi": "src/smart_road_safety/reporting/final_report.py",
        "DOCX yazıcı": "src/smart_road_safety/reporting/docx.py",
        "Render edilmiş diyagramlar": "rapor içinde görsel olarak kullanılır",
        "Görsel kod ekleri": "docs/report_assets/code_snippets/*.png",
    }
    for model in bundle.models:
        for path in model.repo_paths:
            paths.setdefault(f"Model kanıtı: {model.model_id}", path)
    return [{"amac": key, "kanit": value} for key, value in paths.items()]


def _read_report_images(specs: tuple[tuple[str, str, str], ...]) -> tuple[ReportImage, ...]:
    images: list[ReportImage] = []
    for title, source_path, image_path in specs:
        if Path(source_path).exists() and Path(image_path).exists():
            images.append(ReportImage(title=title, source_path=source_path, image_path=image_path))
    return tuple(images)


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
    diagrams: tuple[ReportImage, ...],
    snippets: tuple[ReportImage, ...],
) -> list[DocxBlock]:
    blocks: list[DocxBlock] = [
        DocxBlock("title", "5G & YAPAY ZEKÂ İLE AKILLI YOL GÜVENLİĞİ YARIŞMASI"),
        DocxBlock("title", "FİNAL TASARIM RAPORU"),
        DocxBlock("subtitle", f"Takım Adı: {team_name}"),
        DocxBlock("subtitle", f"Takım ID: {team_id}"),
        DocxBlock("subtitle", f"Başvuru ID: {application_id}"),
        DocxBlock("caption", "Arial 12 / Arial Black 14, 1.15 satır aralığı ve şablon kenar boşluklarıyla üretilmiştir."),
        DocxBlock("page_break"),
        DocxBlock("heading", "İÇİNDEKİLER"),
        DocxBlock("paragraph", "1. PROJE ÖZETİ"),
        DocxBlock("paragraph", "2. VERİSETİ OLUŞTURULMASI"),
        DocxBlock("paragraph", "3. YAPAY ZEKÂ ÇÖZÜMÜ"),
        DocxBlock("paragraph", "4. ÇÖZÜMÜN SINANMASI"),
        DocxBlock("paragraph", "5. KAYNAKÇA"),
        DocxBlock("paragraph", "EK A. GÖRSEL KOD REFERANSLARI"),
        DocxBlock("page_break"),
    ]
    blocks.extend(_section_blocks(dataset_rows, gap_rows, model_rows, metrics_rows, ftr_rows, repo_rows, diagrams, snippets))
    return blocks


def _section_blocks(
    dataset_rows: list[dict[str, str]],
    gap_rows: list[dict[str, str]],
    model_rows: list[dict[str, str]],
    metrics_rows: list[dict[str, str]],
    ftr_rows: list[dict[str, str]],
    repo_rows: list[dict[str, str]],
    diagrams: tuple[ReportImage, ...],
    snippets: tuple[ReportImage, ...],
) -> list[DocxBlock]:
    blocks = [
        DocxBlock("heading", "1. PROJE ÖZETİ"),
        DocxBlock("paragraph", _project_summary()),
        DocxBlock("heading", "2. VERİSETİ OLUŞTURULMASI"),
        DocxBlock("paragraph", _dataset_text()),
        DocxBlock("table", rows=_table_rows(dataset_rows, ["veri_seti", "birim", "bicim", "ftr_aileleri"])),
        DocxBlock("paragraph", "Eksik aileler ve kapatma aksiyonları aşağıdaki tabloda izlenir."),
        DocxBlock("table", rows=_table_rows(gap_rows[:10], ["veri_seti", "bosluk", "aksiyon"])),
        DocxBlock("heading", "3. YAPAY ZEKÂ ÇÖZÜMÜ"),
        DocxBlock("heading", "3.1. Problemin Analizi", level=2),
        DocxBlock("paragraph", _problem_analysis_text()),
        DocxBlock("heading", "3.2. Çözüm Mimarisi", level=2),
        DocxBlock("paragraph", _architecture_text()),
    ]
    for diagram in diagrams:
        blocks.append(DocxBlock("image", diagram.image_path))
        blocks.append(DocxBlock("caption", diagram.title))
    blocks.extend(
        [
            DocxBlock("table", rows=_table_rows(repo_rows, ["amac", "kanit"])),
            DocxBlock("heading", "3.3. Çözüm Detayları", level=2),
            DocxBlock("paragraph", _solution_details_text()),
            DocxBlock("table", rows=MODEL_SELECTION_ROWS),
            DocxBlock("paragraph", "FTR çıktı ailesi aşağıdaki birebir değerlerle sınırlandırılmıştır."),
            DocxBlock("table", rows=_table_rows(ftr_rows, ["alan", "izin_verilen"])),
            DocxBlock("heading", "4. ÇÖZÜMÜN SINANMASI"),
            DocxBlock("paragraph", _testing_text()),
            DocxBlock("table", rows=_table_rows(model_rows, ["model", "aile", "ornek", "kanıt dosyası"])),
            DocxBlock("table", rows=_table_rows(metrics_rows, ["model", "dogruluk", "kesinlik", "duyarlilik", "f1", "n"])),
            DocxBlock("heading", "5. KAYNAKÇA"),
            *(DocxBlock("numbered", f"{index}. {item}") for index, item in enumerate(REFERENCE_ITEMS, start=1)),
            DocxBlock("page_break"),
            DocxBlock("heading", "EK A. GÖRSEL KOD REFERANSLARI"),
            DocxBlock("paragraph", _appendix_intro_text()),
        ]
    )
    for snippet in snippets:
        blocks.append(DocxBlock("image", snippet.image_path))
        blocks.append(DocxBlock("caption", snippet.title))
    return blocks


def _project_summary() -> str:
    return (
        "QoDe final tasarımı, trafikte güvenliği artırmak için araç içi ve araç dışı video akışlarını "
        "çok görevli yapay zekâ bileşenleriyle analiz eden modüler bir sistemdir. Ham video; araç, plaka, "
        "araç içi nesne, yolcu konumu ve sürücü davranışı bulgularına ayrıştırılır; her bulgu zaman bilgisi "
        "ve güven skoru ile doğrulanmış sonuç çıktısına dönüştürülür. Bu KTR sürümünde odak, QoD yerine "
        "açık kaynak veri setleriyle desteklenen model hattı, tekrar üretilebilir ağırlık yönetimi, Docker "
        "üzerinde çalışabilen çıkarım akışı ve repo kanıtlarıyla izlenebilen değerlendirme düzenidir. "
        "Böylece çözüm, hangi model bileşeninin hangi kararı ürettiği ve hangi çıktının otomatik "
        "doğrulandığı izlenebilen uçtan uca bir prototip olarak sunulur."
    )


def _dataset_text() -> str:
    return (
        "Veri hattı tek bir veri setine bağımlı değildir. State Farm görüntüleri şoför eylemleri için, "
        "DMD OpenLABEL videoları zamansal kabin davranışları için, DriverSVT telemetri satırları hız/risk "
        "ayrıştırma kanıtı için, üç yerel video ise FTR JSON hızlı doğrulaması için kullanılır. Bölmeler "
        "sızıntıyı azaltmak amacıyla kişi/oturum/kullanıcı seviyesinde ele alınır. Mevcut açık kaynak "
        "veriler; telefon, su içme, esneme, sigara ve dikkat dağınıklığı gibi eylemleri destekler; plaka "
        "metni, araç renk/gövde tipi, yolcu konumu ve özel nesne sınıfları için ise ek FTR hizalı anotasyon "
        "gerekir."
    )


def _problem_analysis_text() -> str:
    return (
        "Temel zorluklar; plakanın küçük görüntü alanı kaplaması, hareket bulanıklığı, far/parlama, kabin "
        "yansıması, el-nesne oklüzyonu, yolcu/nesne etiketlerinin seyrekliği ve slalom gibi olayların tek "
        "kareyle değil zaman penceresiyle anlaşılmasıdır. FTR şeması ayrıca Türkçe karakter içermeyen birebir "
        "etiketler, normalize plaka regex'i ve her olay için zaman damgası ister. Bu nedenle çözüm, algılama, "
        "OCR, zamansal eylem tanıma, hareket izleme ve şema doğrulamayı ayrı fakat denetlenebilir parçalara "
        "ayırır."
    )


def _architecture_text() -> str:
    return (
        "Mimari akış şu bileşenlerden oluşur: video girişi, manifest destekli veri doğrulama, model çıkarım "
        "katmanı, FTR etiket eşleme, şema doğrulama ve results.json yazımı. Repo içinde competition/ftr.py "
        "birebir şemayı korur; modeling/report_models.py eğitim kanıtı üretir; reporting/final_report.py bu "
        "kanıtları final_report_template.docx başlıklarına yerleştirir. Diyagram kaynakları repoda tutulur; "
        "raporda ise yalnızca render edilmiş görseller kullanılır."
    )


def _solution_details_text() -> str:
    return (
        "Seçilen final mimarisi görev bazlıdır. YOLO11x çalışma zamanı modeli araç, kişi, telefon ve bilgisayar "
        "adaylarını üretir; YOLO11s eğitim hattı FTR'ye özgü ek anotasyonlar geldiğinde aynı ailede ince ayar "
        "edilebilir. Araç kırpımı K-Means renk paletine, EasyOCR plaka okuma ve Türk plaka regex doğrulamasına, "
        "EfficientNet-B0 araç tipi sınıflandırıcısına aktarılır. Sürücü bölgesi kişi çakışması veya ön cam "
        "yedek bölgesi ile çıkarılır; EfficientNet-B2/MobileNetV3 kontrol noktaları davranışı, Canny/Hough sezgisel yöntemi "
        "emniyet kemeri ihlalini, kabin geometrisi ise yolcu konumlarını üretir. main.py olayları 3 saniyelik "
        "yumuşatma ile tekilleştirir ve competition/ftr.py geçmeden sonuç dosyası yazmaz. Ağırlıklar git'e "
        "konmadan Hugging Face tabanlı indirme/yükleme akışıyla yönetilir."
    )


def _testing_text() -> str:
    return (
        "Test kanıtı dört seviyede tutulur: veri manifest/adaptör kontrolleri, tekrar üretilebilir rapor-model "
        "kanıt dosyaları, FTR şema doğrulaması ve Docker giriş/çıkış sınırı. Mevcut model raporu State Farm, DMD "
        "ve DriverSVT kaynaklarının bölme mantığını ve sınıf kapsamını ölçer; çalışma zamanı tarafında YOLO/OCR/"
        "sınıflandırıcı ağırlıkları varsa gerçek çıkarım yapılır, yoksa sistem sessiz yer tutucu üretmek yerine "
        "kontrollü hata veya açık yedek yol davranışı gösterir. Derin model testleri genişletildiğinde aynı kanıt "
        "tablosuna mAP, OCR birebir eşleşme, zamansal F1, FPS ve Docker çalışma süresi eklenir."
    )


def _appendix_intro_text() -> str:
    return (
        "Bu ek, rapordaki teknik iddiaların hangi dosyalarla kanıtlandığını gösterir. Kodlar ham metin olarak "
        "yerleştirilmemiş; okunabilirliği ve şablon bütünlüğünü korumak için görsel ek olarak verilmiştir."
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
    diagrams: tuple[ReportImage, ...],
    snippets: tuple[ReportImage, ...],
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
        _markdown_table(dataset_rows, ["veri_seti", "birim", "bicim", "ftr_aileleri"]),
        "",
        "### Veri boşlukları ve kapatma planı",
        _markdown_table(gap_rows[:10], ["veri_seti", "bosluk", "aksiyon"]),
        "",
        "## 3. YAPAY ZEKÂ ÇÖZÜMÜ",
        "",
        "### 3.1. Problemin Analizi",
        _problem_analysis_text(),
        "",
        "### 3.2. Çözüm Mimarisi",
        _architecture_text(),
        "",
    ]
    for diagram in diagrams:
        lines.extend([f"![{diagram.title}]({diagram.image_path})", f"{diagram.title}", ""])
    lines.extend(
        [
            _markdown_table(repo_rows, ["amac", "kanit"]),
            "",
            "### 3.3. Çözüm Detayları",
            _solution_details_text(),
            "",
            _markdown_table(
                [
                    {"gorev": row[0], "model": row[1], "gerekce": row[2]}
                    for row in MODEL_SELECTION_ROWS
                ],
                ["gorev", "model", "gerekce"],
            ),
            "",
            "#### FTR çıktı alanları",
            _markdown_table(ftr_rows, ["alan", "izin_verilen"]),
            "",
            "## 4. ÇÖZÜMÜN SINANMASI",
            _testing_text(),
            "",
            _markdown_table(model_rows, ["model", "aile", "ornek", "kanıt dosyası"]),
            "",
            _markdown_table(metrics_rows, ["model", "dogruluk", "kesinlik", "duyarlilik", "f1", "n"]),
            "",
            "## 5. KAYNAKÇA",
            "\n".join(f"{index}. {item}" for index, item in enumerate(REFERENCE_ITEMS, start=1)),
            "",
            "## EK A. GÖRSEL KOD REFERANSLARI",
            _appendix_intro_text(),
            "",
        ]
    )
    for snippet in snippets:
        lines.extend([f"![{snippet.title}]({snippet.image_path})", f"{snippet.title}", ""])
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
