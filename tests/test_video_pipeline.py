import unittest

from smart_road_safety.inference.video_pipeline import VideoInferenceConfig, run_video_inference


class Frame:
    shape = (100, 200, 3)


class CV2:
    CAP_PROP_FPS = 1
    CAP_PROP_POS_MSEC = 2


class Capture:
    def __init__(self, timestamps):
        self.timestamps = timestamps
        self.index = -1
        self.released = False

    def isOpened(self): return True
    def read(self):
        self.index += 1
        return (self.index < len(self.timestamps), Frame() if self.index < len(self.timestamps) else None)
    def get(self, prop):
        if prop == CV2.CAP_PROP_FPS: return 10.0
        if prop == CV2.CAP_PROP_POS_MSEC and 0 <= self.index < len(self.timestamps): return self.timestamps[self.index] * 1000
        return 0
    def release(self): self.released = True


class Engine:
    def __init__(self, events=None, centers=None):
        self.calls = []
        self.events = events or {}
        self.centers = centers or {}
    def analyze_frame(self, frame, timestamp):
        self.calls.append(timestamp)
        center = self.centers.get(round(timestamp, 1), 100)
        return {
            "vehicle_detected": True, "vehicle_type": "suv", "vehicle_color": "siyah",
            "vehicle_confidence": 0.9, "plate_text": "34TC8532",
            "vehicle_box": [center - 20, 0, center + 20, 50],
            "driver_events": self.events.get(round(timestamp, 1), []),
        }


def event(label="sigara_icme", category="sofor_eylemi", confidence=0.8):
    return {"zaman_saniye": 0, "kategori": category, "etiket": label, "confidence_score": confidence}


class VideoPipelineTests(unittest.TestCase):
    def test_pts_sampling_uses_configurable_four_fps(self):
        capture = Capture([i / 10 for i in range(11)])
        engine = Engine()
        result = run_video_inference(capture, engine, CV2, VideoInferenceConfig(sample_fps=4))
        self.assertEqual(engine.calls, [0.0, 0.3, 0.5, 0.8, 1.0])
        self.assertEqual(result.processed_samples, 5)
        self.assertTrue(capture.released)

    def test_label_specific_state_preserves_two_episodes(self):
        events = {0.0: [event()], 0.3: [event(confidence=0.9)], 1.5: [event()], 1.8: [event()]}
        result = run_video_inference(Capture([0.0, 0.3, 0.6, 1.0, 1.5, 1.8]), Engine(events), CV2)
        smoking = [item for item in result.events if item.etiket == "sigara_icme"]
        self.assertEqual([item.zaman_saniye for item in smoking], [0.0, 1.5])
        self.assertEqual(smoking[0].confidence_score, 0.9)

    def test_non_monotonic_pts_fails(self):
        with self.assertRaisesRegex(RuntimeError, "non-monotonic"):
            run_video_inference(Capture([0.0, 0.4, 0.2]), Engine(), CV2)

    def test_slalom_requires_temporal_direction_reversals(self):
        centers = {0.0: 50, 0.3: 80, 0.5: 40, 0.8: 90}
        result = run_video_inference(Capture([0.0, 0.3, 0.5, 0.8]), Engine(centers=centers), CV2)
        labels = [item.etiket for item in result.events]
        self.assertIn("slalom", labels)


if __name__ == "__main__":
    unittest.main()
