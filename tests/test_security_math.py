#!/usr/bin/env python3

from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "analysis"))

from importance_sampling import estimate_capture
from security_math import (
    Profile,
    controlled_count,
    hypergeom_tail_fraction,
    wilson_interval,
)


class SecurityMathTests(unittest.TestCase):
    def test_controlled_count_uses_half_up_rounding(self) -> None:
        self.assertEqual(controlled_count(150, Decimal("33.33")), 50)
        self.assertEqual(controlled_count(300, Decimal("33.33")), 100)

    def test_known_hypergeometric_probability(self) -> None:
        # N=5, K=2, n=2, P(X>=1) = 1 - C(3,2)/C(5,2) = 7/10.
        self.assertEqual(hypergeom_tail_fraction(5, 2, 2, 1), Fraction(7, 10))

    def test_impossible_capture_is_zero(self) -> None:
        self.assertEqual(hypergeom_tail_fraction(150, 15, 60, 41), 0)

    def test_wilson_zero_observation_has_positive_upper_bound(self) -> None:
        low, high = wilson_interval(0, 10000)
        self.assertEqual(low, 0.0)
        self.assertGreater(high, 0.0)

    def test_importance_estimate_tracks_exact_nonrare_case(self) -> None:
        result = estimate_capture(
            population=150,
            controlled=60,
            profile=Profile("test", 25, 22, 17),
            samples=20000,
            seed=12345,
        )
        exact = float(result["exact_probability"])
        estimate = result["importance_estimate"]
        self.assertLess(abs(estimate - exact), max(0.01, exact * 0.25))
        self.assertGreater(result["targeted_event_count"], 0)


if __name__ == "__main__":
    unittest.main()
