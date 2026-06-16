#!/usr/bin/env python3
"""
visualize_inference.py — Çıkarım (Inference) Motorunu Görsel Olarak Test Etme

Bu script, YOLO, Sürücü Modeli ve EasyOCR'ı çalıştırır ve
tespit edilen etiketleri doğrudan videonun veya kameranın üzerine çizerek
`out_visual.mp4` dosyasına kaydeder. İsteğe bağlı olarak ekranda da gösterir.

Kullanım:
    PYTHONPATH=src python visualize_inference.py --input data/input/video.mp4
    # Web kamerası için:
    PYTHONPATH=src python visualize_inference.py --input 0
"""

import sys
import argparse
from pathlib import Path
import cv2

# Proje modüllerini yüklemek için
sys.path.insert(0, str(Path(__file__).parent / "src"))

from smart_road_safety.analysis.model_inference import SceneAnalysisEngine

def visualize(input_path: str, show: bool = True):
    print("[Vis] Model motoru yükleniyor (M4 Pro / GPU hızlandırma aktif)...")
    engine = SceneAnalysisEngine(
        yolo_model_name="yolo11x.pt",
        driver_model_path="data/weights/driver_classifier.pt",
        vehicle_type_model_path="data/weights/vehicle_type_classifier.pt",
    )

    # Kamera (0) veya dosya
    if input_path == "0":
        cap = cv2.VideoCapture(0)
    else:
        if not Path(input_path).exists():
            print(f"[!] Hata: {input_path} dosyası bulunamadı.")
            sys.exit(1)
        cap = cv2.VideoCapture(input_path)

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))
    if fps == 0: fps = 30

    out_path = "out_visual.mp4"
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(out_path, fourcc, fps, (width, height))

    print(f"\n[Vis] Analiz başlıyor: {input_path}")
    print(f"[Vis] Çıktı buraya kaydedilecek: {out_path}\n")

    frame_count = 0
    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            frame_count += 1
            timestamp = frame_count / fps

            # ── 1. Model Çıkarımı ──────────────────────────────────────────────
            results = engine.analyze_frame(frame, timestamp)
            
            # ── 2. Ekrana Çizdirme (Dashboard) ─────────────────────────────────
            # Koyu gri arka plan paneli
            cv2.rectangle(frame, (20, 20), (500, 300), (40, 40, 40), -1)
            cv2.rectangle(frame, (20, 20), (500, 300), (200, 200, 200), 2)
            
            y_offset = 60
            cv2.putText(frame, "QoDe Akilli Yol Guvenligi", (40, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 255), 2)
            y_offset += 40

            # Araç ve Plaka Bilgisi
            v_info = results.get("vehicle_info", {})
            v_type = v_info.get("arac_tipi", "Yok")
            v_color = v_info.get("arac_renk", "Yok")
            plate = v_info.get("plaka", "tespit_edilemedi")
            
            cv2.putText(frame, f"Arac: {v_color} {v_type}", (40, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 30
            cv2.putText(frame, f"Plaka: {plate}", (40, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            y_offset += 40

            # Sürücü Davranışları ve Olaylar
            events = results.get("driver_events", [])
            cv2.putText(frame, "Tespitler:", (40, y_offset), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            y_offset += 30
            
            if not events:
                cv2.putText(frame, "- Normal Surus", (60, y_offset), 
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)
            else:
                for ev in events:
                    cat = ev['kategori']
                    label = ev['etiket']
                    conf = ev['confidence_score']
                    text = f"- {cat}: {label} ({conf:.2f})"
                    
                    # Riskli durumlarda kırmızı yap
                    color = (0, 0, 255) if label in ["telefonla_konusma", "arkaya_bakma"] else (255, 255, 255)
                    cv2.putText(frame, text, (60, y_offset), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
                    y_offset += 25

            # ── 3. Çıktı Kaydet ve Göster ──────────────────────────────────────
            writer.write(frame)
            
            if show:
                # Görüntü büyükse küçült (M4 Pro ekrana sığsın diye)
                display_frame = cv2.resize(frame, (1280, 720)) if width > 1280 else frame
                cv2.imshow("QoDe AI Inference", display_frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("[Vis] 'q' basıldı, çıkılıyor...")
                    break

    except KeyboardInterrupt:
        print("\n[Vis] Kullanıcı tarafından durduruldu.")
    finally:
        cap.release()
        writer.release()
        cv2.destroyAllWindows()
        print(f"[Vis] Tamamlandı! Video başarıyla kaydedildi: {out_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=str, default="data/input/video.mp4", 
                        help="Test edilecek video yolu veya kamera (0)")
    parser.add_argument("--no-show", action="store_true", 
                        help="Video oynatım penceresini gizle (sadece kaydet)")
    args = parser.parse_args()
    
    visualize(args.input, not args.no_show)
