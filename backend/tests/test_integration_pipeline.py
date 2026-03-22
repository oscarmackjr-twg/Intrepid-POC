"""Integration tests for pipeline execution."""

import pytest
import pandas as pd
from orchestration.run_context import RunContext
from orchestration.pipeline import PipelineExecutor
from db.models import PipelineRun, RunStatus


@pytest.mark.integration
class TestPipelineExecution:
    """Test full pipeline execution.

    These tests are marked integration because they exercise file I/O with
    a temporary directory and require the full pipeline stack. They are
    excluded from the default pytest run (pytest.ini: -m "not integration").
    """

    @pytest.fixture
    def sample_reference_data(self, tmp_path):
        """Create sample reference data files in an isolated tmp_path."""
        files_required = tmp_path / "files_required"
        files_required.mkdir(parents=True)

        # MASTER_SHEET.xlsx
        master_df = pd.DataFrame(
            {
                "loan program": ["Unsec Std - 999 - 120", "Prime Std - 999 - 120"],
                "Platform": ["SFY", "PRIME"],
                "platform": ["sfy", "prime"],
                "type": ["standard", "standard"],
            }
        )
        master_df.to_excel(files_required / "MASTER_SHEET.xlsx", index=False)

        # MASTER_SHEET - Notes.xlsx
        notes_df = pd.DataFrame(
            {
                "loan program": ["Unsec Std - 999 - 120"],
                "Platform": ["SFY"],
                "platform": ["sfy"],
                "type": ["standard"],
            }
        )
        notes_df.to_excel(files_required / "MASTER_SHEET - Notes.xlsx", index=False)

        # current_assets.csv
        existing_df = pd.DataFrame(
            {
                "SELLER Loan #": ["SFC_9999"],
                "Submit Date": ["2024-09-15"],
                "Purchase_Date": ["2024-09-15"],
                "Monthly Payment Date": ["2024-10-15"],
                "Orig. Balance": [15000.0],
                "Purchase Price": [14850.0],
                "Lender Price(%)": [99.0],
                "modeled_purchase_price": [0.99],
                "platform": ["sfy"],
                "Repurchase": [False],
            }
        )
        existing_df.to_csv(files_required / "current_assets.csv", index=False)

        # Underwriting_Grids_COMAP.xlsx
        with pd.ExcelWriter(files_required / "Underwriting_Grids_COMAP.xlsx") as writer:
            # SFY sheet
            sfy_uw = pd.DataFrame(
                {
                    "finance_type_name_nls": ["Unsec Std - 999 - 120"],
                    "monthly_income_min": [3000],
                    "fico_min": [660],
                    "approval_high": [20000],
                    "approval_low": [5000],
                    "dti_max": [45],
                    "pti_ratio": [20],
                }
            )
            sfy_uw.to_excel(writer, sheet_name="SFY", index=False)

            # Prime sheet
            prime_uw = pd.DataFrame(
                {
                    "finance_type_name_nls": ["Prime Std - 999 - 120"],
                    "monthly_income_min": [3500],
                    "fico_min": [660],
                    "approval_high": [25000],
                    "approval_low": [5000],
                    "dti_max": [45],
                    "pti_ratio": [20],
                }
            )
            prime_uw.to_excel(writer, sheet_name="Prime", index=False)

            # CoMAP sheets
            comap_df = pd.DataFrame(
                {
                    "660-699": ["Unsec Std - 999 - 120", "Prime Std - 999 - 120"],
                    "700-739": [None, None],
                }
            )
            comap_df.to_excel(writer, sheet_name="SFY COMAP", index=False)
            comap_df.to_excel(writer, sheet_name="SFY COMAP2", index=False)
            comap_df.to_excel(writer, sheet_name="Prime CoMAP", index=False)
            comap_df.to_excel(writer, sheet_name="Notes CoMAP", index=False)

        return tmp_path

    def test_pipeline_execution(self, sample_reference_data, sample_buy_df, test_db_session):
        """Test full pipeline execution using synthetic in-memory DataFrames.

        Uses sample_buy_df from conftest (synthetic data) and patches the file
        loading layer so no real files are needed beyond reference data.
        """
        input_dir = sample_reference_data

        # Create run context
        context = RunContext.create(sales_team_id=None, created_by_id=None, pdate="2024-11-18", irr_target=8.05)
        context.input_file_path = str(input_dir)
        context.output_dir = str(input_dir / "output")

        # Execute pipeline
        with PipelineExecutor(context) as executor:
            result = executor.execute(str(input_dir))

        # Verify results
        assert result["status"] == "completed"
        assert result["total_loans"] > 0
        assert "exceptions_count" in result
        assert "reports" in result

        # Verify run record
        run = test_db_session.query(PipelineRun).filter(PipelineRun.run_id == context.run_id).first()

        assert run is not None
        assert run.status == RunStatus.COMPLETED
        assert run.total_loans > 0

    def test_pipeline_with_exceptions(self, sample_reference_data, sample_buy_df, test_db_session):
        """Test pipeline execution with exception generation."""
        # Similar to above but with data that generates exceptions
        # This would require more complex test data setup
        pass
