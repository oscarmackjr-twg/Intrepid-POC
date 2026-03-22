"""Unit tests for cashflow.compute.amortization module."""
import pytest

from cashflow.compute.amortization import level_pay_schedule, bullet_schedule, custom_schedule


@pytest.mark.unit
class TestLevelPaySchedule:
    """Tests for level_pay_schedule function."""

    def test_final_balance_is_zero(self):
        """Final remaining_balance must be zero (fully amortized)."""
        schedule = level_pay_schedule(100_000, 0.05, 360, 12)
        assert schedule[-1]["remaining_balance"] == pytest.approx(0.0, abs=1e-6)

    def test_period_count_matches_term(self):
        """Number of periods in schedule matches num_periods argument."""
        schedule = level_pay_schedule(50_000, 0.06, 60, 12)
        assert len(schedule) == 60

    def test_constant_payment_amount(self):
        """Every period has the same payment amount (level pay)."""
        schedule = level_pay_schedule(200_000, 0.045, 180, 12)
        first_payment = schedule[0]["payment"]
        for row in schedule:
            assert row["payment"] == pytest.approx(first_payment, rel=1e-9)

    def test_zero_interest_rate_equal_principal_no_interest(self):
        """At 0% rate, each period has equal principal payment and zero interest."""
        principal = 12_000.0
        num_periods = 12
        schedule = level_pay_schedule(principal, 0.0, num_periods, 12)

        expected_principal = principal / num_periods
        for row in schedule:
            assert row["interest"] == pytest.approx(0.0, abs=1e-9)
            assert row["principal"] == pytest.approx(expected_principal, rel=1e-9)

    def test_single_period_loan(self):
        """Single period: entire principal paid in period 1, balance is 0."""
        schedule = level_pay_schedule(1_000.0, 0.12, 1, 12)
        assert len(schedule) == 1
        assert schedule[0]["remaining_balance"] == pytest.approx(0.0, abs=1e-9)
        # Payment = principal + one period's interest
        expected_interest = 1_000.0 * (0.12 / 12)
        assert schedule[0]["interest"] == pytest.approx(expected_interest, rel=1e-9)

    def test_negative_principal_raises_value_error(self):
        """Negative principal must raise ValueError."""
        with pytest.raises(ValueError, match="Principal must be positive"):
            level_pay_schedule(-1000.0, 0.05, 12, 12)

    def test_zero_principal_raises_value_error(self):
        """Zero principal must raise ValueError."""
        with pytest.raises(ValueError, match="Principal must be positive"):
            level_pay_schedule(0.0, 0.05, 12, 12)

    def test_period_numbers_are_sequential(self):
        """Period numbers must run from 1 to num_periods."""
        schedule = level_pay_schedule(10_000.0, 0.08, 24, 12)
        expected_periods = list(range(1, 25))
        actual_periods = [row["period"] for row in schedule]
        assert actual_periods == expected_periods

    def test_principal_plus_interest_equals_payment(self):
        """For each period: principal + interest == payment."""
        schedule = level_pay_schedule(75_000.0, 0.065, 120, 12)
        for row in schedule:
            assert row["principal"] + row["interest"] == pytest.approx(row["payment"], rel=1e-9)

    def test_balance_decreases_monotonically(self):
        """Remaining balance never increases period over period."""
        schedule = level_pay_schedule(20_000.0, 0.07, 48, 12)
        for i in range(1, len(schedule)):
            assert schedule[i]["remaining_balance"] <= schedule[i - 1]["remaining_balance"]


@pytest.mark.unit
class TestBulletSchedule:
    """Tests for bullet_schedule function."""

    def test_only_last_period_has_principal(self):
        """Bullet loan: all intermediate periods have zero principal."""
        schedule = bullet_schedule(50_000, 0.05, 10, 1)
        for row in schedule[:-1]:
            assert row["principal"] == pytest.approx(0.0, abs=1e-9)
        assert schedule[-1]["principal"] == pytest.approx(50_000.0, rel=1e-9)

    def test_final_balance_is_zero(self):
        """Final remaining_balance must be zero for bullet schedule."""
        schedule = bullet_schedule(100_000, 0.04, 20, 2)
        assert schedule[-1]["remaining_balance"] == pytest.approx(0.0, abs=1e-6)

    def test_negative_principal_raises(self):
        """Negative principal raises ValueError."""
        with pytest.raises(ValueError):
            bullet_schedule(-5_000, 0.05, 5, 12)


@pytest.mark.unit
class TestCustomSchedule:
    """Tests for custom_schedule function."""

    def test_remaining_balance_calculates_correctly(self):
        """Remaining balances step down by principal payment each period."""
        specs = [
            {"period": 1, "principal": 1_000, "interest": 50},
            {"period": 2, "principal": 1_000, "interest": 45},
            {"period": 3, "principal": 1_000, "interest": 40},
        ]
        schedule = custom_schedule(specs)
        assert schedule[0]["remaining_balance"] == pytest.approx(2_000.0, abs=1e-9)
        assert schedule[1]["remaining_balance"] == pytest.approx(1_000.0, abs=1e-9)
        assert schedule[2]["remaining_balance"] == pytest.approx(0.0, abs=1e-9)

    def test_empty_specs_raises(self):
        """Empty cashflow specs must raise ValueError."""
        with pytest.raises(ValueError):
            custom_schedule([])

    def test_missing_period_raises(self):
        """Skipping a period raises ValueError."""
        specs = [
            {"period": 1, "principal": 500, "interest": 25},
            {"period": 3, "principal": 500, "interest": 20},  # period 2 missing
        ]
        with pytest.raises(ValueError):
            custom_schedule(specs)

    def test_out_of_order_input_is_handled(self):
        """Out-of-order specs are sorted by period before processing."""
        specs = [
            {"period": 2, "principal": 500, "interest": 10},
            {"period": 1, "principal": 500, "interest": 20},
        ]
        schedule = custom_schedule(specs)
        assert schedule[0]["period"] == 1
        assert schedule[1]["period"] == 2
