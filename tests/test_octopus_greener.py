"""Tests for Octopus greener nights carbon score classification (no Home Assistant required)."""

from __future__ import annotations

import unittest

GREEN_THRESHOLD_GCO2 = 99.0
CARBON_SCORE_BASE = 60.0
CARBON_SCORE_SCALE = 25.0


def low_carbon_score_from_gco2(value: float | None) -> int | None:
    if value is None:
        return None
    score = round(10 - (float(value) - CARBON_SCORE_BASE) / CARBON_SCORE_SCALE)
    return max(1, min(10, score))


def low_carbon_score_green_min() -> int:
    return low_carbon_score_from_gco2(GREEN_THRESHOLD_GCO2) or 8


def is_low_carbon_green(*, gco2: float | None = None, score: int | None = None) -> bool:
    if score is None:
        score = low_carbon_score_from_gco2(gco2)
    if score is None:
        return False
    return score >= low_carbon_score_green_min()


class TestOctopusGreenerScore(unittest.TestCase):
    def test_national_threshold_maps_to_score_eight(self) -> None:
        self.assertEqual(low_carbon_score_from_gco2(GREEN_THRESHOLD_GCO2), 8)
        self.assertEqual(low_carbon_score_green_min(), 8)

    def test_score_eight_and_above_are_green(self) -> None:
        self.assertTrue(is_low_carbon_green(score=8))
        self.assertTrue(is_low_carbon_green(score=9))
        self.assertTrue(is_low_carbon_green(score=10))
        self.assertFalse(is_low_carbon_green(score=7))

    def test_national_threshold_gco2_is_green(self) -> None:
        self.assertTrue(is_low_carbon_green(gco2=GREEN_THRESHOLD_GCO2))
        self.assertTrue(is_low_carbon_green(gco2=98))
        self.assertFalse(is_low_carbon_green(gco2=123))


if __name__ == "__main__":
    unittest.main()
