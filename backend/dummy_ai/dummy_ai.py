import time
import json
import os

def main():
    print("Starting Dummy AI Inference Container...")
    # Simulate processing time
    time.sleep(3)
    
    output_dir = "/app/data/output"
    os.makedirs(output_dir, exist_ok=True)
    
    mock_result = {
        "arac_bilgisi": {"tip": "Sedan (Docker)", "plaka": "34DOCKER123", "renk": "Siyah", "confidence_score": 0.99},
        "tespitler": [
            {"zaman_saniye": 1, "kategori": "Risk", "etiket": "Emniyet Kemeri Yok (Docker)", "confidence_score": 0.90},
            {"zaman_saniye": 4, "kategori": "Dikkat", "etiket": "Telefona Bakıyor (Docker)", "confidence_score": 0.85}
        ]
    }
    
    result_path = os.path.join(output_dir, "results.json")
    with open(result_path, "w") as f:
        json.dump(mock_result, f)
        
    print(f"Results written to {result_path}")
    print("Dummy AI Inference Finished Successfully!")

if __name__ == "__main__":
    main()
