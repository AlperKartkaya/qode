from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from smart_road_safety.export import (
    export_scenario_report_markdown,
    render_scenario_report_markdown,
)


class ExportMarkdownTest(unittest.TestCase):
    def test_render_scenario_report_markdown_contains_tables(self) -> None:
        markdown = render_scenario_report_markdown(
            ROOT / "out" / "scenario_report.json"
        )

        self.assertIn("# Scenario Evaluation Report", markdown)
        self.assertIn("## Overall Summary", markdown)
        self.assertIn("| Scenario | Status | QoD requested |", markdown)
        self.assertIn("## Scenario: `success`", markdown)

    def test_export_scenario_report_markdown_writes_file(self) -> None:
        output_path = ROOT / "out" / "scenario_report_test.md"
        target = export_scenario_report_markdown(
            ROOT / "out" / "scenario_report.json",
            output_path,
        )

        self.assertEqual(target, output_path)
        self.assertTrue(output_path.exists())


if __name__ == "__main__":
    unittest.main()
