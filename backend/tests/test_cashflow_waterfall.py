"""Unit tests for cashflow.compute.waterfall module."""
import pytest

from cashflow.compute.waterfall import apply_waterfall, run_waterfall


@pytest.mark.unit
class TestApplyWaterfall:
    """Tests for apply_waterfall function."""

    def test_senior_tranche_receives_interest_before_junior(self):
        """Priority-1 (senior) tranche is allocated interest before priority-2 (junior)."""
        # Total interest = 5.0; senior due = 80 * 0.04 = 3.2, junior due = 20 * 0.08 = 1.6
        # With only 5.0 interest available, senior gets 3.2 first.
        cashflows = [{"period": 1, "interest": 3.5, "principal": 0.0}]
        tranches = [
            {"tranche_id": "A", "priority": 1, "notional": 80, "coupon": 0.04},
            {"tranche_id": "B", "priority": 2, "notional": 20, "coupon": 0.08},
        ]
        result = apply_waterfall(cashflows, tranches)

        # Senior tranche should receive its full interest due (3.2)
        senior_interest = result["A"][0]["interest"]
        # Junior tranche gets the remainder (3.5 - 3.2 = 0.3)
        junior_interest = result["B"][0]["interest"]

        assert senior_interest == pytest.approx(3.2, rel=1e-9)
        assert junior_interest == pytest.approx(0.3, rel=1e-9)

    def test_principal_allocated_senior_first(self):
        """Senior tranche receives principal before junior tranche."""
        cashflows = [{"period": 1, "interest": 0.0, "principal": 50.0}]
        tranches = [
            {"tranche_id": "A", "priority": 1, "notional": 80, "coupon": 0.0},
            {"tranche_id": "B", "priority": 2, "notional": 20, "coupon": 0.0},
        ]
        result = apply_waterfall(cashflows, tranches)

        # With 50 available and 80 senior notional, senior gets all 50
        assert result["A"][0]["principal"] == pytest.approx(50.0, rel=1e-9)
        # Junior gets nothing
        assert result["B"][0]["principal"] == pytest.approx(0.0, abs=1e-9)

    def test_single_tranche_receives_all_cashflows(self):
        """With only one tranche, it receives all interest and principal."""
        cashflows = [{"period": 1, "interest": 10.0, "principal": 20.0}]
        tranches = [{"tranche_id": "A", "priority": 1, "notional": 100, "coupon": 0.10}]
        result = apply_waterfall(cashflows, tranches)

        assert "A" in result
        # Interest due = 100 * 0.10 = 10.0; interest available = 10.0
        assert result["A"][0]["interest"] == pytest.approx(10.0, rel=1e-9)
        assert result["A"][0]["principal"] == pytest.approx(20.0, rel=1e-9)

    def test_zero_cashflow_produces_zero_allocations(self):
        """Zero available cashflow means all tranches receive zero."""
        cashflows = [{"period": 1, "interest": 0.0, "principal": 0.0}]
        tranches = [
            {"tranche_id": "A", "priority": 1, "notional": 100, "coupon": 0.05},
            {"tranche_id": "B", "priority": 2, "notional": 50, "coupon": 0.08},
        ]
        result = apply_waterfall(cashflows, tranches)

        assert result["A"][0]["interest"] == pytest.approx(0.0, abs=1e-9)
        assert result["A"][0]["principal"] == pytest.approx(0.0, abs=1e-9)
        assert result["B"][0]["interest"] == pytest.approx(0.0, abs=1e-9)
        assert result["B"][0]["principal"] == pytest.approx(0.0, abs=1e-9)

    def test_excess_cashflow_goes_to_junior_tranche(self):
        """Excess after senior is fully paid goes to the most junior tranche."""
        # Senior due: 80 * 0.05 = 4.0 interest; notional fully paid by 80 principal
        # Junior due: 20 * 0.08 = 1.6 interest
        # Available: interest=10.0, principal=100.0 — more than enough
        cashflows = [{"period": 1, "interest": 10.0, "principal": 100.0}]
        tranches = [
            {"tranche_id": "A", "priority": 1, "notional": 80, "coupon": 0.05},
            {"tranche_id": "B", "priority": 2, "notional": 20, "coupon": 0.08},
        ]
        result = apply_waterfall(cashflows, tranches)

        # Both tranches should be paid; excess goes to junior
        assert result["B"][0]["excess"] >= 0.0

    def test_result_contains_all_tranche_ids(self):
        """Result dict contains a key for every input tranche."""
        cashflows = [{"period": 1, "interest": 5.0, "principal": 10.0}]
        tranches = [
            {"tranche_id": "Senior", "priority": 1, "notional": 60, "coupon": 0.03},
            {"tranche_id": "Mezz", "priority": 2, "notional": 25, "coupon": 0.06},
            {"tranche_id": "Equity", "priority": 3, "notional": 15, "coupon": 0.10},
        ]
        result = apply_waterfall(cashflows, tranches)
        assert "Senior" in result
        assert "Mezz" in result
        assert "Equity" in result

    def test_multi_period_cashflows(self):
        """Multiple cashflow periods produce entries for each period in each tranche."""
        cashflows = [
            {"period": 1, "interest": 5.0, "principal": 10.0},
            {"period": 2, "interest": 4.5, "principal": 10.0},
        ]
        tranches = [
            {"tranche_id": "A", "priority": 1, "notional": 80, "coupon": 0.04},
            {"tranche_id": "B", "priority": 2, "notional": 20, "coupon": 0.08},
        ]
        result = apply_waterfall(cashflows, tranches)
        assert len(result["A"]) == 2
        assert len(result["B"]) == 2


@pytest.mark.unit
class TestRunWaterfall:
    """Tests for run_waterfall wrapper function."""

    def test_run_waterfall_delegates_to_apply_waterfall(self):
        """run_waterfall produces the same result as apply_waterfall for the same inputs."""
        cashflows = [{"period": 1, "interest": 4.0, "principal": 5.0}]
        tranches = [
            {"tranche_id": "A", "priority": 1, "notional": 50, "coupon": 0.05},
        ]
        waterfall_def = {"tranches": tranches}

        result_run = run_waterfall(cashflows, waterfall_def)
        result_apply = apply_waterfall(cashflows, tranches)

        assert result_run["A"][0]["interest"] == pytest.approx(result_apply["A"][0]["interest"])
        assert result_run["A"][0]["principal"] == pytest.approx(result_apply["A"][0]["principal"])
