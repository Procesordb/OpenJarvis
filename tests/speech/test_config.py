"""Tests for speech configuration."""

from agi_procesor.core.config import AgiConfig, SpeechConfig


def test_speech_config_defaults():
    cfg = SpeechConfig()
    assert cfg.backend == "auto"
    assert cfg.model == "base"
    assert cfg.language == ""
    assert cfg.device == "auto"
    assert cfg.compute_type == "float16"


def test_agi_config_has_speech():
    cfg = AgiConfig()
    assert hasattr(cfg, "speech")
    assert isinstance(cfg.speech, SpeechConfig)
    assert cfg.speech.backend == "auto"


def test_agi_system_has_speech_backend():
    """AgiSystem has a speech_backend attribute."""
    from agi_procesor.system import AgiSystem

    assert "speech_backend" in AgiSystem.__dataclass_fields__
