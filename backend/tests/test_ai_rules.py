from pathlib import Path

import pytest

from raspberry.ai.expert_system import Decision, ExpertRules
from raspberry.ai.inference import MockBottleClassifier, ModelLoadError, TFLiteBottleClassifier
from raspberry.ai.labels import LabelMapping


def test_expert_confidence_boundaries():
    rules = ExpertRules()
    assert rules.decide(0.90) is Decision.ACCEPTED
    assert rules.decide(0.70) is Decision.RECAPTURE
    assert rules.decide(0.40) is Decision.UNKNOWN


def test_real_mode_fails_safely_without_tflite():
    with pytest.raises(ModelLoadError, match="No existe el modelo"):
        TFLiteBottleClassifier("missing.tflite", "raspberry/ai/models/labels.json", "1.0.0", ExpertRules())


def test_mock_requires_explicit_flag():
    with pytest.raises(ModelLoadError, match="AI_MOCK_MODE=true"):
        MockBottleClassifier("plastic", 0.9, "1.0.0", ExpertRules(), enabled=False)
    result = MockBottleClassifier("glass", 0.9, "1.0.0", ExpertRules(), enabled=True).classify()
    assert result.material == "glass"
    assert result.model_version.startswith("mock-")
    assert result.labels_validated is False


def test_labels_json_loads_in_safe_unvalidated_mode():
    labels = LabelMapping.load(Path("raspberry/ai/models/labels.json"))
    assert labels.classes == {0: "plastic", 1: "glass"}
    assert labels.validated is False
