"""SOC block model detection for EVO / H3 Pro / H3 Smart."""

from custom_components.foxess_plant.discovery import _model_uses_h3_pro_soc_block


def test_evo_full_model_uses_soc_block() -> None:
    assert _model_uses_h3_pro_soc_block("EVO 10-5.0-H") is True
    assert _model_uses_h3_pro_soc_block("EVO 10-10.0-H") is True


def test_evo_base_enum_uses_soc_block() -> None:
    assert _model_uses_h3_pro_soc_block("EVO") is True


def test_h3_pro_full_model_uses_soc_block() -> None:
    assert _model_uses_h3_pro_soc_block("H3-Pro-5.0") is True
    assert _model_uses_h3_pro_soc_block("P3-Pro-12.0") is True


def test_h3_smart_full_model_uses_soc_block() -> None:
    assert _model_uses_h3_pro_soc_block("H3-5.0-Smart") is True
    assert _model_uses_h3_pro_soc_block("H3-8.0-M") is True


def test_h1_models_do_not_use_soc_block() -> None:
    assert _model_uses_h3_pro_soc_block("H1-5.0-E-G2") is False
    assert _model_uses_h3_pro_soc_block("H3-5.0") is False
