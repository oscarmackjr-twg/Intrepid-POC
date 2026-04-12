import pandas as pd

xl = pd.ExcelFile("data/sample/files_required/Underwriting_Grids_COMAP.xlsx")

# Check Prime CoMAP - New for the program
prime_new = xl.parse("Prime CoMAP - New")
prog_prime = "Unsec Std - 1290 - 90"
print("=== Prime CoMAP - New columns:", list(prime_new.columns))
prime_new_cols = [c for c in prime_new.columns if c not in ["Applied for Program"]]
in_vals = prog_prime in prime_new[prime_new_cols].stack().unique()
in_applied = prog_prime in prime_new.iloc[:, 0].values
print(f"'{prog_prime}' in FICO-band values: {in_vals}")
print(f"'{prog_prime}' in Applied for Program: {in_applied}")

# Check SFY COMAP_ sheet
sfy_under = xl.parse("SFY COMAP_")
print("\n=== SFY COMAP_ columns:", list(sfy_under.columns))
print(sfy_under.head(10).to_string())
