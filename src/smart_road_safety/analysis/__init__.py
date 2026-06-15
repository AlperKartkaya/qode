"""Internal analysis boundary.

The FTR/KTR submission contract is intentionally kept in
``smart_road_safety.competition``.  The analysis package remains the
support/demo boundary that feeds orchestration and the FTR bridge.

``PlaceholderSceneAnalyzer`` is retained only as a compatibility alias for
older tests/examples; new code should use ``RuleBasedSceneAnalyzer`` or a real
model-backed analyzer.
"""

from .models import (
    AnalysisResult,
    AnalysisSessionRequest,
    AnalysisSessionResult,
    AnalyzerInput,
    DatasetSelection,
    SceneAnalyzer,
)
from .observations import ObservationRegistry, ObservedEvent, VideoObservation
from .placeholder import (
    PlaceholderSceneAnalyzer,
    RuleBasedSceneAnalyzer,
    run_analysis_session,
)

__all__ = [
    "AnalysisResult",
    "AnalysisSessionRequest",
    "AnalysisSessionResult",
    "AnalyzerInput",
    "DatasetSelection",
    "PlaceholderSceneAnalyzer",
    "RuleBasedSceneAnalyzer",
    "ObservationRegistry",
    "ObservedEvent",
    "SceneAnalyzer",
    "VideoObservation",
    "run_analysis_session",
]
