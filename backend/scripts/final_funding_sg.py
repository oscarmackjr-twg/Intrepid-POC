"""
Final Funding SG script. Uses the same input/output convention as the main pipeline:
- Input: folder/files_required/
- Output: folder/output/
- Output shared: folder/output_share/

Set FOLDER via environment (runner sets this). Example: folder = Path(os.environ.get("FOLDER")).
"""
import os
from pathlib import Path

folder = Path(os.environ.get("FOLDER", ".")).resolve()
input_dir = folder / "files_required"
output_dir = folder / "output"
output_share_dir = folder / "output_share"

output_dir.mkdir(parents=True, exist_ok=True)
output_share_dir.mkdir(parents=True, exist_ok=True)

# Stub: list inputs and write a manifest so outputs exist. Replace with real workbook logic.
inputs_list = list(input_dir.iterdir()) if input_dir.is_dir() else []
(output_dir / "final_funding_sg_done.txt").write_text(
    f"Final Funding SG run complete. Input files seen: {len(inputs_list)}\n",
    encoding="utf-8",
)
(output_share_dir / "final_funding_sg_share_done.txt").write_text(
    "Final Funding SG output_share placeholder.\n",
    encoding="utf-8",
)
