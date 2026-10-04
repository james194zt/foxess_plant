"""Control keys must match entity ids exactly; panel keys tolerate longer EVO ids."""

from custom_components.foxess_plant.discovery import (
    _entity_id_matches_exact_suffix,
    _entity_id_matches_panel_suffix,
)


def test_max_soc_does_not_match_max_soc_from_grid() -> None:
    assert _entity_id_matches_exact_suffix("number.evo_10_max_soc", "max_soc")
    assert not _entity_id_matches_exact_suffix("number.evo_10_max_soc_from_grid", "max_soc")
    assert _entity_id_matches_exact_suffix("number.evo_10_max_soc_from_grid", "max_soc_from_grid")


def test_panel_suffix_still_matches_long_evo_ids() -> None:
    assert _entity_id_matches_panel_suffix("sensor.foxess_pv_power_evo_10", "pv_power")
