"""Unit tests for cashflow.compute.prepayment module."""
import pytest

from cashflow.compute.prepayment import cpr_to_smm, psa_speed, apply_psa_prepayment, apply_cpr_prepayment


@pytest.mark.unit
class TestCprToSmm:
    """Tests for cpr_to_smm conversion function."""

    def test_zero_cpr_returns_zero_smm(self):
        """0% CPR should produce 0% SMM (no prepayment)."""
        assert cpr_to_smm(0.0) == pytest.approx(0.0, abs=1e-12)

    def test_full_cpr_returns_full_smm(self):
        """100% CPR (all loans prepay in year) should yield SMM of 1.0."""
        # (1 - 1.0)^(1/12) = 0; SMM = 1 - 0 = 1.0
        assert cpr_to_smm(1.0) == pytest.approx(1.0, abs=1e-12)

    def test_six_percent_cpr_midrange(self):
        """6% CPR (PSA benchmark plateau) converts to expected SMM."""
        # SMM = 1 - (1 - 0.06)^(1/12) = 1 - 0.94^(1/12)
        import math
        expected = 1.0 - math.pow(0.94, 1.0 / 12.0)
        assert cpr_to_smm(0.06) == pytest.approx(expected, rel=1e-9)

    def test_smm_less_than_cpr(self):
        """SMM should always be less than equivalent CPR for rates between 0 and 1."""
        for cpr_pct in [0.02, 0.06, 0.10, 0.20, 0.50]:
            assert cpr_to_smm(cpr_pct) < cpr_pct

    def test_smm_is_non_negative(self):
        """SMM result is always >= 0 for valid CPR inputs."""
        for cpr_pct in [0.0, 0.01, 0.06, 0.50, 1.0]:
            assert cpr_to_smm(cpr_pct) >= 0.0


@pytest.mark.unit
class TestPsaSpeed:
    """Tests for psa_speed function."""

    def test_month_1_ramp_start(self):
        """Month 1 CPR = 0.2% (6% / 30 months) at PSA 100%."""
        # base_cpr = min(1 * 0.002, 0.06) = 0.002; CPR = 0.002 * 1.0 = 0.002
        assert psa_speed(1) == pytest.approx(0.002, rel=1e-9)

    def test_month_30_plateau_begins(self):
        """Month 30 reaches 6% CPR plateau at PSA 100%."""
        # base_cpr = min(30 * 0.002, 0.06) = 0.06
        assert psa_speed(30) == pytest.approx(0.06, rel=1e-9)

    def test_month_beyond_30_stays_at_plateau(self):
        """Months > 30 remain at 6% CPR plateau (PSA 100%)."""
        assert psa_speed(31) == pytest.approx(0.06, rel=1e-9)
        assert psa_speed(60) == pytest.approx(0.06, rel=1e-9)
        assert psa_speed(360) == pytest.approx(0.06, rel=1e-9)

    def test_psa_200_doubles_cpr(self):
        """PSA 200% doubles the CPR relative to PSA 100% for same month."""
        cpr_100 = psa_speed(15, psa_multiplier=100.0)
        cpr_200 = psa_speed(15, psa_multiplier=200.0)
        assert cpr_200 == pytest.approx(cpr_100 * 2.0, rel=1e-9)

    def test_psa_50_halves_cpr(self):
        """PSA 50% halves the CPR relative to PSA 100%."""
        cpr_100 = psa_speed(20, psa_multiplier=100.0)
        cpr_50 = psa_speed(20, psa_multiplier=50.0)
        assert cpr_50 == pytest.approx(cpr_100 * 0.5, rel=1e-9)

    def test_default_multiplier_is_100(self):
        """Default psa_multiplier should be 100.0."""
        assert psa_speed(10) == pytest.approx(psa_speed(10, psa_multiplier=100.0), rel=1e-12)

    def test_ramp_is_linear_before_plateau(self):
        """CPR ramp is linear from month 1 to 30 (before plateau)."""
        month_10 = psa_speed(10, psa_multiplier=100.0)
        month_20 = psa_speed(20, psa_multiplier=100.0)
        # At PSA 100% before plateau: CPR = month * 0.002
        assert month_10 == pytest.approx(0.020, rel=1e-9)
        assert month_20 == pytest.approx(0.040, rel=1e-9)


@pytest.mark.unit
class TestApplyPsaPrepayment:
    """Tests for apply_psa_prepayment function."""

    def test_prepayment_field_added_to_each_period(self):
        """apply_psa_prepayment adds 'prepayment' key to every cashflow dict."""
        schedule = [
            {"month": 1, "remaining_principal": 100_000.0},
            {"month": 2, "remaining_principal": 98_000.0},
        ]
        result = apply_psa_prepayment(schedule, psa_speed=100.0)
        assert all("prepayment" in row for row in result)

    def test_zero_remaining_principal_yields_zero_prepayment(self):
        """Zero remaining principal produces zero prepayment amount."""
        schedule = [{"month": 5, "remaining_principal": 0.0}]
        result = apply_psa_prepayment(schedule)
        assert result[0]["prepayment"] == pytest.approx(0.0, abs=1e-9)

    def test_input_not_mutated(self):
        """Original schedule dicts are not modified (function returns copies)."""
        original = {"month": 10, "remaining_principal": 50_000.0}
        schedule = [original]
        apply_psa_prepayment(schedule)
        assert "prepayment" not in original

    def test_prepayment_positive_for_positive_balance(self):
        """Positive remaining principal at any PSA speed yields positive prepayment."""
        schedule = [{"month": 15, "remaining_principal": 25_000.0}]
        result = apply_psa_prepayment(schedule, psa_speed=100.0)
        assert result[0]["prepayment"] > 0.0


@pytest.mark.unit
class TestApplyCprPrepayment:
    """Tests for apply_cpr_prepayment function."""

    def test_zero_cpr_produces_zero_prepayment(self):
        """0% CPR means no prepayment at any balance."""
        schedule = [{"remaining_principal": 100_000.0}]
        result = apply_cpr_prepayment(schedule, cpr=0.0)
        assert result[0]["prepayment"] == pytest.approx(0.0, abs=1e-9)

    def test_full_cpr_prepays_entire_balance(self):
        """100% CPR (SMM=1.0) prepays the entire remaining principal."""
        schedule = [{"remaining_principal": 50_000.0}]
        result = apply_cpr_prepayment(schedule, cpr=1.0)
        assert result[0]["prepayment"] == pytest.approx(50_000.0, rel=1e-6)

    def test_constant_rate_applied_uniformly(self):
        """With constant CPR, same SMM applied to each period's balance."""
        schedule = [
            {"remaining_principal": 100_000.0},
            {"remaining_principal": 90_000.0},
        ]
        result = apply_cpr_prepayment(schedule, cpr=0.06)
        smm = cpr_to_smm(0.06)
        assert result[0]["prepayment"] == pytest.approx(100_000.0 * smm, rel=1e-9)
        assert result[1]["prepayment"] == pytest.approx(90_000.0 * smm, rel=1e-9)

    def test_prepayment_field_added_to_all_periods(self):
        """'prepayment' key is present in every row of result."""
        schedule = [
            {"remaining_principal": 10_000.0},
            {"remaining_principal": 9_500.0},
            {"remaining_principal": 0.0},
        ]
        result = apply_cpr_prepayment(schedule, cpr=0.10)
        assert all("prepayment" in row for row in result)
