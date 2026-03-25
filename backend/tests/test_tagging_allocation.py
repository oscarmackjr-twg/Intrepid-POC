"""Unit tests for tagging allocation logic (allocate_sg function).

Tests use inline DataFrames following the Phase 12 pattern (test_comap.py).
"""

import pandas as pd
from scripts.tagging import allocate_sg


def _make_buy_df(rows):
    """Build a minimal buy_df with tags and Orig. Balance columns."""
    return pd.DataFrame(rows, columns=["tags", "Orig. Balance"])


class TestAllocateSg:
    """Tests for the allocate_sg allocation function."""

    def test_default_ratios_sfy(self):
        """SFY tags get 50% allocation by default (s=0.5)."""
        buy_df = _make_buy_df([
            {"tags": "SFYstandard", "Orig. Balance": 100_000},
            {"tags": "SFYstandard", "Orig. Balance": 100_000},
        ])
        grouped_sum = buy_df.groupby("tags")["Orig. Balance"].sum()
        result = allocate_sg(buy_df, grouped_sum)
        sg_total = result[result["final"] == "sg"]["Orig. Balance"].sum()
        # 50% of 200k = 100k budget => first loan (100k) fits, second doesn't
        assert sg_total == 100_000

    def test_default_ratios_prime(self):
        """PRIME tags get 32.5% allocation by default (p=0.325)."""
        buy_df = _make_buy_df([
            {"tags": "PRIMEstandard", "Orig. Balance": 100_000},
            {"tags": "PRIMEstandard", "Orig. Balance": 100_000},
            {"tags": "PRIMEstandard", "Orig. Balance": 100_000},
            {"tags": "PRIMEstandard", "Orig. Balance": 100_000},
        ])
        grouped_sum = buy_df.groupby("tags")["Orig. Balance"].sum()
        result = allocate_sg(buy_df, grouped_sum)
        sg_count = (result["final"] == "sg").sum()
        # 32.5% of 400k = 130k budget. Allocation assigns sg while budget > 0:
        # loan 1 (100k): budget=130k > 0 -> sg, budget=30k
        # loan 2 (100k): budget=30k > 0 -> sg, budget=-70k
        # loan 3 (100k): budget=-70k, not > 0 -> cibc
        # loan 4 (100k): cibc
        assert sg_count == 2

    def test_dynamic_dict_sfy_prefix(self):
        """Tags starting with SFY use s ratio."""
        buy_df = _make_buy_df([
            {"tags": "SFYepni", "Orig. Balance": 50_000},
            {"tags": "SFYwpdi", "Orig. Balance": 50_000},
        ])
        grouped_sum = buy_df.groupby("tags")["Orig. Balance"].sum()
        result = allocate_sg(buy_df, grouped_sum, s=1.0)  # 100% to SG
        assert all(result["final"] == "sg")

    def test_dynamic_dict_prime_prefix(self):
        """Tags starting with PRIME use p ratio."""
        buy_df = _make_buy_df([
            {"tags": "PRIMEhybrid", "Orig. Balance": 50_000},
            {"tags": "PRIMEninp", "Orig. Balance": 50_000},
        ])
        grouped_sum = buy_df.groupby("tags")["Orig. Balance"].sum()
        result = allocate_sg(buy_df, grouped_sum, p=1.0)  # 100% to SG
        assert all(result["final"] == "sg")

    def test_bd_suffix_always_cibc(self):
        """_bd-suffixed tags always get 0 allocation — all go to CIBC."""
        buy_df = _make_buy_df([
            {"tags": "SFYstandard_bd", "Orig. Balance": 50_000},
            {"tags": "SFYwpdi_bd", "Orig. Balance": 50_000},
        ])
        grouped_sum = buy_df.groupby("tags")["Orig. Balance"].sum()
        result = allocate_sg(buy_df, grouped_sum, s=1.0)  # even at 100%, _bd stays CIBC
        assert all(result["final"] == "cibc")

    def test_unknown_tag_no_keyerror(self):
        """Tags in buy_df but absent from grouped_sum do not raise KeyError."""
        buy_df = _make_buy_df([
            {"tags": "SFYstandard", "Orig. Balance": 50_000},
            {"tags": "UNKNOWNtype", "Orig. Balance": 50_000},
        ])
        # grouped_sum only has SFYstandard (UNKNOWNtype has 0 balance in groupby)
        grouped_sum = pd.Series({"SFYstandard": 50_000})
        result = allocate_sg(buy_df, grouped_sum, s=1.0)
        # SFYstandard should be sg, UNKNOWNtype should be cibc
        sfy_row = result[result["tags"] == "SFYstandard"]
        unk_row = result[result["tags"] == "UNKNOWNtype"]
        assert sfy_row["final"].iloc[0] == "sg"
        assert unk_row["final"].iloc[0] == "cibc"

    def test_budget_exhaustion(self):
        """Once SG budget is exhausted for a tag, remaining loans go to CIBC."""
        buy_df = _make_buy_df([
            {"tags": "SFYstandard", "Orig. Balance": 60_000},
            {"tags": "SFYstandard", "Orig. Balance": 60_000},
            {"tags": "SFYstandard", "Orig. Balance": 60_000},
        ])
        grouped_sum = buy_df.groupby("tags")["Orig. Balance"].sum()
        # s=0.5 => budget = 90k. Allocation assigns sg while budget > 0:
        # loan 1 (60k): budget=90k > 0 -> sg, budget=30k
        # loan 2 (60k): budget=30k > 0 -> sg, budget=-30k
        # loan 3 (60k): budget=-30k, not > 0 -> cibc
        result = allocate_sg(buy_df, grouped_sum, s=0.5)
        sg_count = (result["final"] == "sg").sum()
        cibc_count = (result["final"] == "cibc").sum()
        assert sg_count == 2
        assert cibc_count == 1
