# %%
#Importing Lib
import os
import pandas as pd
import numpy as np
import numpy_financial as npf
import warnings
from scipy.optimize import newton
from datetime import datetime
from pandas.tseries.offsets import DateOffset
from pathlib import Path



warnings.filterwarnings('ignore')
pd.options.display.max_columns = 200
pd.options.display.max_rows = 500

# %%
#Setting IRR
folder = Path(os.environ.get("FOLDER", ".")).resolve()
folderx = os.environ.get("BUY_NUM", '93rd')
irr_target = float(os.environ.get("IRR_TARGET", "7.9"))

# %%
# #Setting date (running on thursday)

# #for p date1
# from datetime import datetime, timedelta
# today = datetime.today()
# days_until_tuesday = (1 - today.weekday() + 7) % 7  # 1 is Tuesday
# days_until_tuesday = 7 if days_until_tuesday == 0 else days_until_tuesday
# next_tuesday = today + timedelta(days=days_until_tuesday)
# pdate=next_tuesday.strftime('%Y-%m-%d')


# #for sfy and buy

# curr_date=datetime.today()
# curr_date=curr_date.strftime('%m-%d-%Y')

# #for FX file
# today = datetime.today()
# first_day_of_current_month = datetime(today.year, today.month, 1)
# fd=first_day_of_current_month.strftime('%Y-%m-%d')
# last_day_previous_month = first_day_of_current_month - timedelta(days=1)
# last_end= f"{last_day_previous_month.year}_{last_day_previous_month.month:03}_{last_day_previous_month.day:02}"



# print("for pdate=",pdate)
# print("for curr date=",curr_date)
# print("for fx file=",last_end)
# print("first date of month for fx files",fd)

# %%
#manual dates (overridable via environment variables for regression testing)
pdate = os.environ.get("PDATE", '2026-02-24')
curr_date = os.environ.get("CURR_DATE", '02-19-2026')
last_end = os.environ.get("LAST_END", '2026_001_31')
fd = os.environ.get("FD", '2026-02-01')
yestarday = os.environ.get("YESTERDAY", '02-18-2026')

# %%
#file location and importing

#files_required
fx3_servicing_file = f"{folder}/files_required/FX3_{last_end}.xlsx"
fx4_servicing_file = f"{folder}/files_required/FX4_{last_end}.xlsx"
#fx4_servicing_file = f"C:/Users/gdehankar/TWG/Jagadish Balaji - SFC_Loans/78th_buy/files_required/FX4_2025_0010_31.xlsx"
loans = pd.read_csv(f"{folder}/files_required/Tape20Loans_{yestarday}.csv")
df_loans_types = pd.read_excel(f'{folder}/files_required/MASTER_SHEET.xlsx')
notes = pd.read_excel(f'{folder}/files_required/MASTER_SHEET - Notes.xlsx')
existing_file_ = pd.read_csv(f"{folder}/files_required/current_assets.csv") #do not change
sfy_file = f"{folder}/files_required/FX3_{curr_date}_ExhibitAtoFormofSaleNotice_sg.xlsx"
prime_file = f"{folder}/files_required/{curr_date} Exhibit A To Form Of Sale Notice_sg.xlsx"

#underwriting
underwriting_sfy = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'SFY')
underwriting_prime = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'Prime')
underwriting_sfy_notes = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'SFY - Notes')
underwriting_prime_notes = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'Prime - Notes')
sfy_comap = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'SFY COMAP')
sfy_comap2 = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'SFY COMAP2')
prime_comap = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'Prime COMAP')
prime_comap_new = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'Prime CoMAP - New')
notes_comap = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'Notes CoMAP')
prime_comap_oct25 = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'Prime CoMAP-Oct25')
prime_comap_oct25_2 = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'Prime CoMAP-Oct25-2')
sfy_comap_oct25 = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'SFY COMAP-Oct25')
sfy_comap_oct25_2 = pd.read_excel(f"{folder}/files_required/Underwriting_Grids_COMAP.xlsx", sheet_name = 'SFY COMAP-Oct25-2')

# %%
sfy_df = pd.read_excel(sfy_file)
sfy_df = sfy_df.drop(['Unnamed: 0', 'tags','final'], axis=1)
_sfy_promo = sfy_df['promo_term'].values if 'promo_term' in sfy_df.columns else None
sfy_df = sfy_df.loc[:, : 'Application Type']
if _sfy_promo is not None:
    sfy_df['promo_term'] = _sfy_promo
sfy_df.head(10)

# %%
prime_df = pd.read_excel(prime_file)
prime_df = prime_df.drop(['Unnamed: 0', 'tags','final'], axis=1)
_prime_promo = prime_df['promo_term'].values if 'promo_term' in prime_df.columns else None
prime_df = prime_df.loc[:, : 'Application Type']
if _prime_promo is not None:
    prime_df['promo_term'] = _prime_promo
prime_df.head(10)

# %%
if 'lender' in existing_file_.columns:
    existing_file_=existing_file_[existing_file_['lender']=='SG']
    existing_file_ = existing_file_.drop(['lender'], axis=1)

# %%
existing_file_

# %%
#df_loans_types
df_loans_types["Platform"] = df_loans_types.platform.str.upper()

#notes
notes['loan program'] = notes['loan program'].apply(lambda x: x + 'notes')
notes["Platform"] = notes.platform.str.upper()

#df_loans_types
df_loans_types = pd.concat([df_loans_types, notes])

#existing_file_
existing_file_['Submit Date'] = pd.to_datetime(existing_file_['Submit Date'])
existing_file_['Purchase_Date'] = pd.to_datetime(existing_file_['Purchase_Date'])
existing_file_['Monthly Payment Date'] = pd.to_datetime(existing_file_['Monthly Payment Date'])
existing_file = existing_file_.copy()
del existing_file_

print(existing_file.shape)
existing_file.Purchase_Date.value_counts().sort_index()

# %%
#For analysis ignore
import pandas as pd
def analyze_dataset(df):
    # Separate numeric and character columns
    numeric_cols = df.select_dtypes(include=['number']).columns
    character_cols = df.select_dtypes(include=['object', 'category']).columns

    # Analyze numeric columns
    print("=== Numeric Column Analysis ===")
    for col in numeric_cols:
        print(f"\nColumn: {col}")
        print(f"Total Count: {df[col].count()}")
        print(f"Missing Values: {df[col].isnull().sum()}")
        print(f"Mean: {df[col].mean()}")
        print(f"Median: {df[col].median()}")
        for p in range(10, 100, 10):
            print(f"{p}th Percentile: {df[col].quantile(p / 100)}")

    # Analyze character columns
    print("\n=== Character Column Analysis ===")
    for col in character_cols:
        print(f"\nColumn: {col}")
        print(f"Total Count: {df[col].count()}")
        print(f"Missing Values: {df[col].isnull().sum()}")
        print(df[col].value_counts())

analyze_dataset(df_loans_types)

# %%
loans['tagging'] = loans['Loan Group'].apply(lambda x:'SFY' if 'FX3' in x or 'FX1' in x else 'PRIME')
loans['Account Number'] = loans['Account Number'].astype(int)
loans['Status Codes'].fillna("", inplace = True)
loans['Repurchased'] = loans['Status Codes'].apply(lambda x: True if 'REPURCHASE' in [i.strip() for i in x.split(";")] else False)
loans['Open Date'] = pd.to_datetime(loans['Open Date'])
loans['maturityDate'] = pd.to_datetime(loans['maturityDate'])
print(loans['Repurchased'].value_counts())
loans['SELLER Loan #'] = loans['Account Number'].apply(lambda x:"SFC_" + str(x))
repurchased_loans = loans[loans['Repurchased'] == True]['SELLER Loan #'].values

existing_file.reset_index(drop = True, inplace = True)
existing_file.loc[existing_file['SELLER Loan #'].isin(repurchased_loans), 'Repurchase'] = True

print(repurchased_loans.shape)

# %%
existing_file.shape

# %%
sfy_df['Platform'] = "SFY"
prime_df['Platform'] = "PRIME"
#tuloans = sfy_df[sfy_df.TU144 == 1]['SELLER Loan #'].values
#sfy_df.drop(columns = "TU144", inplace = True)
buy_df = pd.concat([prime_df, sfy_df])
buy_df.rename(columns = {"Loan Program" : "loan program"}, inplace = True)
# buy_df['loan program'] = buy_df.apply(lambda x: x['loan program'] + 'notes' if x['Application Type'] == 'HD NOTE' else x['loan program'], axis = 1)
buy_df["Repurchase"] = False
buy_df["Repurchase_Date"] = None
buy_df["Purchase_Date"] = pd.to_datetime(pdate)
buy_df["Excess_Asset"] = False
buy_df["Borrowing_Base_eligible"] = True
buy_df["IRR Support Target"] = irr_target
buy_df['Submit Date'] = pd.to_datetime(buy_df['Submit Date'])
buy_df['Purchase_Date'] = pd.to_datetime(buy_df['Purchase_Date'])
buy_df['Monthly Payment Date'] = pd.to_datetime(buy_df['Monthly Payment Date'])
buy_df = buy_df.merge(df_loans_types, on = ['loan program', 'Platform'], how = 'left')
if 'Dealer Fee_x' in buy_df.columns:
    buy_df.rename(columns={'Dealer Fee_x': 'Dealer Fee'}, inplace=True)
    buy_df.drop(columns=['Dealer Fee_y'], inplace=True, errors='ignore')
buy_df = buy_df.loc[:, ~buy_df.columns.duplicated()]
if 'tagging' not in buy_df.columns:
    buy_df = buy_df.merge(loans[['SELLER Loan #', 'tagging']], on='SELLER Loan #', how='left')
assert sum(buy_df['SELLER Loan #'].duplicated()) == 0
#buy_df.loc[(buy_df['new_programs'] == True)&(buy_df['Repurchase'] == False) & (buy_df['platform'] == 'sfy'), 'Excess_Asset'] = True
#buy_df.loc[(buy_df['new_programs'] == True)&(buy_df['Repurchase'] == False) & (buy_df['platform'] == 'sfy'), 'Borrowing_Base_eligible'] = False
# buy_df['Dealer Fee'] = buy_df['Dealer Fee'] / 100
final_df = pd.concat([buy_df, existing_file[existing_file['Purchase_Date'] > '2025-09-30']])
final_df_all = pd.concat([buy_df, existing_file])
buy_df.shape, final_df[final_df['Orig. Balance'] > 50000].shape, final_df.shape, final_df['SELLER Loan #'].nunique(), buy_df[buy_df['tagging'] != 'BD']['Orig. Balance'].sum()

# %%
buy_df

# %% [markdown]
# ## Mark excess and borrowing file

# %%
final_df_all[["SELLER Loan #", 'Orig. Balance', "tagging", 'Repurchase',
              'platform','Excess_Asset']].to_excel(f"{folder}/output/EveryLoan_sg.xlsx")

# %%
# del rkdf, rkdf1, rkdf2
rkdf1 = pd.read_excel(fx3_servicing_file)
rkdf2 = pd.read_excel(fx4_servicing_file)
rkdf = pd.concat([rkdf1.iloc[:-1], rkdf2.iloc[:-1]])
rkdf['SELLER Loan #'] = rkdf['Trial Balance'].apply(lambda x: "SFC_" + str(int(x)))
rkdf['Current Purchase Price'] = (rkdf["Principal Balance"] * rkdf["PP%"]) / 100
print(final_df[final_df["SELLER Loan #"].isin(rkdf["SELLER Loan #"])].shape, rkdf.shape)
rkdf = rkdf[rkdf["SELLER Loan #"].isin(final_df["SELLER Loan #"])].copy()
rkdf.sort_values("SELLER Loan #", inplace = True)
rkdf.head(2)

# %%
# del still_exist, paid, check_final_df, repurchased
final_df.reset_index(drop = True, inplace = True)
final_df.sort_values("SELLER Loan #", inplace = True)
still_exist = final_df[final_df["SELLER Loan #"].isin(rkdf['SELLER Loan #'])].copy()
still_exist.sort_values("SELLER Loan #", inplace = True)
still_exist["Current Balance"] = rkdf["Principal Balance"].values
still_exist["Purchase Price"] = rkdf["Current Purchase Price"].values

paid = final_df[(~final_df["SELLER Loan #"].isin(list(rkdf['SELLER Loan #']))) & (final_df.Purchase_Date < fd)].copy()
paid["Current Balance"] = 0
paid["Purchase Price"] = 0

rest = final_df[~final_df['SELLER Loan #'].isin(list(still_exist['SELLER Loan #']) + list(paid['SELLER Loan #']) )].copy()
check_final_df = pd.concat([still_exist, paid, rest])
check_final_df.loc[check_final_df.Repurchase == True, 'Current Balance'] = 0
check_final_df.loc[check_final_df.Repurchase == True, 'Purchase Price'] = 0
check_final_df.shape, final_df.shape

# %%
still_exist.shape, paid.shape, check_final_df.shape

# %%
check_final_df['Orig. Balance'].sum(), final_df['Orig. Balance'].sum(), check_final_df['Current Balance'].sum(), final_df['Current Balance'].sum()

# %%

check_final_df.reset_index(drop = True, inplace = True)

check_final_df[["Purchase_Date","SELLER Loan #","tagging","Platform","Excess_Asset","Borrowing_Base_eligible",'Orig. Balance',"Purchase Price","Current Balance","Repurchase",
                "Application Type"]].to_excel(f"{folder}/output/borrowing_file_sg.xlsx")

# %% [markdown]
# ## Check Purchase Price

# %%
if 'modeled_purchase_price' in existing_file.columns:
    existing_file['purchase_price_check'] = existing_file['Lender Price(%)'] == round(existing_file['modeled_purchase_price']*100, 2)
elif 'purchase_price_check' not in existing_file.columns:
    existing_file['purchase_price_check'] = True
existing_file.shape, existing_file.purchase_price_check.sum()

# %%
if 'modeled_purchase_price' in buy_df.columns:
    buy_df['purchase_price_check'] = buy_df['Lender Price(%)'] == round(buy_df['modeled_purchase_price']*100, 2)
elif 'purchase_price_check' not in buy_df.columns:
    buy_df['purchase_price_check'] = True
buy_df.shape, buy_df.purchase_price_check.sum()

# %%
if 'modeled_purchase_price' in final_df.columns:
    final_df['purchase_price_check'] = final_df['Lender Price(%)'] == round(final_df['modeled_purchase_price']*100, 2)
elif 'purchase_price_check' not in final_df.columns:
    final_df['purchase_price_check'] = True
final_df.shape, final_df.purchase_price_check.sum()

# %%
#extra checks as russ mentioned should be close to 0
buy_df['Lender Price(%)_x']=buy_df['Lender Price(%)'].astype(float)/100
buy_df['modeled_price']=buy_df['Lender Price(%)_x']*buy_df['Orig. Balance']
buy_df[['modeled_price','Purchase Price']]
buy_df['modeled_price'].sum()-buy_df['Purchase Price'].sum()

# %%
if 'modeled_purchase_price' in buy_df.columns:
    buy_df['modeled_price']=buy_df['modeled_purchase_price']*buy_df['Orig. Balance'].astype(float)
    buy_df[['modeled_price','Purchase Price']]
    buy_df['modeled_price'].sum()-buy_df['Purchase Price'].sum()

# %% [markdown]
# ## Underwriting_checks

# %%
#just run it wont affect code
final_df_all['FICO Borrower']=final_df_all['FICO Borrower'].astype(int)
final_df['FICO Borrower']=final_df['FICO Borrower'].astype(int)
buy_df['FICO Borrower']=buy_df['FICO Borrower'].astype(int)

# %%
# del underwriting_sfy, underwriting_prime

loan_ids = []
min_oncome = []
for row in buy_df[buy_df['Application Type'] != 'HD NOTE'].iterrows():
    if row[1]['platform'] == 'sfy':
        underwriting = underwriting_sfy.copy()
    else:
        underwriting = underwriting_prime.copy()
    #if row[1]['SELLER Loan #'] in tuloans or row[1]['SELLER Loan #'] in buy_df[buy_df['Application Type'] == 'HD NOTE']['SELLER Loan #'].values:
    #    continue
    prog = row[1]['loan program']
    mth_income = row[1]['Income'] / 12
    fico = row[1]['FICO Borrower']
    dti = row[1]['DTI']*100
    pti = row[1]['PTI']
    reason = ""
    balance = row[1]['Orig. Balance'] - row[1]['Stamp fee']
    # (underwriting.approval_high >= balance) & (underwriting.approval_low <= balance)
    filter_one = underwriting[(underwriting.finance_type_name_nls == prog) & (underwriting.monthly_income_min <= mth_income) & (underwriting.fico_min <= fico)].sort_values("approval_high").reset_index(drop = True)
    meet_crit = False
    for i in filter_one.iterrows():
        if balance <= i[1]['approval_high'] and dti<= i[1]['dti_max']:
            meet_crit = True
    if not meet_crit:
        if fico > 700:
            filter_one = underwriting[(underwriting.finance_type_name_nls == prog) & (underwriting.fico_min <= fico)].sort_values("approval_high").reset_index(drop = True)
            for i in filter_one.iterrows():
                if balance <= i[1]['approval_high'] and dti<= i[1]['dti_max'] and pti <= i[1]["pti_ratio"]:
                    meet_crit = True
            if meet_crit:
                min_oncome.append(row[1]['SELLER Loan #'])
    if not meet_crit:
        loan_ids.append(row[1]['SELLER Loan #'])
    del underwriting
    # break

len(loan_ids), len(min_oncome)

# %%
# del underwriting_sfy_notes, underwriting_prime_notes

loan_ids_notes = []
min_oncome_notes = []
for row in buy_df[buy_df['Application Type'] == 'HD NOTE'].iterrows():
    if row[1]['platform'] == 'sfy':
        underwriting = underwriting_sfy_notes.copy()
    else:
        underwriting = underwriting_prime_notes.copy()
    #if row[1]['SELLER Loan #'] in tuloans:
    #    continue
    prog = row[1]['loan program'].replace('notes', '')
    mth_income = row[1]['Income'] / 12
    fico = row[1]['FICO Borrower']
    dti = row[1]['DTI']*100
    pti = row[1]['PTI']
    reason = ""
    balance = row[1]['Orig. Balance'] - row[1]['Stamp fee']
    filter_one = underwriting[(underwriting.finance_type_name_nls == prog) & (underwriting.monthly_income_min <= mth_income) & (underwriting.fico_min <= fico)].sort_values("approval_high").reset_index(drop = True)
    meet_crit = False
    for i in filter_one.iterrows():
        if balance <= i[1]['approval_high'] and dti <= i[1]['dti_max']:
            meet_crit = True
    if not meet_crit:
        if fico > 700:
            filter_one = underwriting[(underwriting.finance_type_name_nls == prog) & (underwriting.fico_min <= fico)].sort_values("approval_high").reset_index(drop = True)
            for i in filter_one.iterrows():
                if balance <= i[1]['approval_high'] and dti <= i[1]['dti_max'] and pti <= i[1]["pti_ratio"]:
                    meet_crit = True
            if meet_crit:
                min_oncome_notes.append(row[1]['SELLER Loan #'])
    if not meet_crit:
        loan_ids_notes.append(row[1]['SELLER Loan #'])
    del underwriting
    # break

len(loan_ids_notes), len(min_oncome_notes)

# %%
def _build_comap_lookup(df):
    """Return {prog: min_fico} supporting two COMAP sheet formats.
    New format: 'loan program' and 'Min FICO' columns.
    Old format: FICO band columns (e.g. '660-699', '700-739') with program names as cell values.
    """
    if 'loan program' in df.columns and 'Min FICO' in df.columns:
        result = {}
        for _, r in df[['loan program', 'Min FICO']].dropna(subset=['loan program']).iterrows():
            p = str(r['loan program']).strip()
            if p:
                result[p] = int(r['Min FICO']) if pd.notna(r['Min FICO']) else 0
        return result
    fico_cols = {c: int(str(c)[:3]) for c in df.columns if str(c)[:3].isdigit()}
    result = {}
    for col, min_f in fico_cols.items():
        for p in df[col].dropna():
            p = str(p).strip()
            if p:
                result[p] = min(result.get(p, 9999), min_f)
    return result

_lu_prime_oct25   = _build_comap_lookup(prime_comap_oct25)
_lu_prime_oct25_2 = _build_comap_lookup(prime_comap_oct25_2)
_lu_prime_new     = _build_comap_lookup(prime_comap_new)
_lu_prime         = _build_comap_lookup(prime_comap)
_lu_sfy_oct25     = _build_comap_lookup(sfy_comap_oct25)
_lu_sfy_oct25_2   = _build_comap_lookup(sfy_comap_oct25_2)
_lu_sfy           = _build_comap_lookup(sfy_comap)
_lu_sfy2          = _build_comap_lookup(sfy_comap2)
_lu_notes         = _build_comap_lookup(notes_comap)

# %%
loan_not_in_comap = []
for row in buy_df[(buy_df['Application Type'] != 'HD NOTE') & (buy_df['purchase_price_check'] == True)].iterrows():
    fico = row[1]['FICO Borrower']
    prog = row[1]['loan program']
    found = False
    if row[1]['platform'] == 'prime':
        if row[1]['Submit Date'] > pd.to_datetime('2025-10-24'):
            if prog not in _lu_prime_oct25 and prog not in _lu_prime_oct25_2:
                continue
            if prog in _lu_prime_oct25:
                found = fico >= _lu_prime_oct25[prog]
            elif prog in _lu_prime_oct25_2:
                found = fico >= _lu_prime_oct25_2[prog]
        elif row[1]['Submit Date'] > pd.to_datetime('2024-06-11'):
            if prog not in _lu_prime:
                continue
            found = prog in _lu_prime_new and fico >= _lu_prime_new[prog]
        else:
            if prog not in _lu_prime:
                continue
            found = fico >= _lu_prime[prog]
        if not found:
            loan_not_in_comap.append((row[1]["SELLER Loan #"], prog, "PRIME"))
    else:
        if row[1]['Submit Date'] > pd.to_datetime('2025-10-24'):
            if prog not in _lu_sfy_oct25 and prog not in _lu_sfy_oct25_2:
                continue
            if prog in _lu_sfy_oct25:
                found = fico >= _lu_sfy_oct25[prog]
            elif prog in _lu_sfy_oct25_2:
                found = fico >= _lu_sfy_oct25_2[prog]
        else:
            if prog not in _lu_sfy and prog not in _lu_sfy2:
                continue
            if prog in _lu_sfy:
                found = fico >= _lu_sfy[prog]
            elif prog in _lu_sfy2:
                found = fico >= _lu_sfy2[prog]
        if not found:
            loan_not_in_comap.append((row[1]["SELLER Loan #"], prog, "SFY"))

len(loan_not_in_comap)

# %%
loan_not_in_comap_notes = []
for row in buy_df[(buy_df['Application Type'] == 'HD NOTE') & (buy_df['purchase_price_check'] == True)].iterrows():
    fico = row[1]['FICO Borrower']
    prog = row[1]['loan program']
    found = False
    if prog not in _lu_notes:
        continue
    found = fico >= _lu_notes[prog]
    if not found:
        loan_not_in_comap_notes.append((row[1]["SELLER Loan #"], prog, "NOTES"))

len(loan_not_in_comap_notes)

# %%
#FOR Ourself
final_df[final_df['purchase_price_check'] == False].to_excel(f"{folder}/output/purchase_price_mismatch.xlsx")
buy_df[buy_df["SELLER Loan #"].isin(loan_ids)].to_excel(f"{folder}/output/flagged_loans_{folderx}.xlsx")
buy_df[buy_df["SELLER Loan #"].isin(loan_ids_notes)].to_excel(f"{folder}/output/NOTES_flagged_loans_{folderx}.xlsx")
buy_df[buy_df["SELLER Loan #"].isin([i[0] for i in loan_not_in_comap])].to_excel(f"{folder}/output/comap_not_passed.xlsx")

# %%
#sharing file generation
purchase=final_df[final_df['purchase_price_check'] == False]
flag=buy_df[buy_df["SELLER Loan #"].isin(loan_ids)]
note_flag=buy_df[buy_df["SELLER Loan #"].isin(loan_ids_notes)]
comap=buy_df[buy_df["SELLER Loan #"].isin([i[0] for i in loan_not_in_comap])]
purchase = purchase.iloc[:, :30]
flag = flag.iloc[:, :30]
note_flag = note_flag.iloc[:, :30]
comap = comap.iloc[:, :30]
purchase.to_excel(f"{folder}/output_share/purchase_price_mismatch.xlsx")
flag.to_excel(f"{folder}/output_share/flagged_loans_{folderx}.xlsx")
note_flag.to_excel(f"{folder}/output_share/NOTES_flagged_loans_{folderx}.xlsx")
comap.to_excel(f"{folder}/output_share/comap_not_passed.xlsx")

# %%
#final_df_all=

# %%


# %%


if 'promo_term' not in final_df_all.columns:
    final_df_all['promo_term'] = 0
final_df_all[["SELLER Loan #","Orig. Balance","Purchase Price","promo_term","Current Balance","APR","Term","Property State","FICO Borrower",
              "loan program","Total Dealer $","Lender Price(%)","Dealer Fee","Income","Repurchase",	"Purchase_Date","Excess_Asset",
              "Borrowing_Base_eligible","Platform","tagging","type","new_programs"]].to_excel(f"{folder}/output/concentration_final_sg.xlsx")

# %% [markdown]
# ## Eligibility Checks

# %% [markdown]
# #### Check A

# %%
a1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.Term <= 144) & (final_df_all.type == 'standard') & (final_df_all['FICO Borrower'] < 700)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(a1,a1<0.05)

# %%
# final_df_all[(final_df_all['SELLER Loan #'] != 'SFC_4731527') & (final_df_all.platform == 'prime') & (final_df_all.Term <= 144) & (final_df_all.type == 'standard') & (final_df_all['FICO Borrower'] < 700)]['Orig. Balance'].sum() / final_df_all[(final_df_all.platform == 'prime')]['Orig. Balance'].sum()

# %%
# final_df_all[(final_df_all.platform == 'prime') & (final_df_all.Term <= 144) & (final_df_all.type == 'standard') & (final_df_all['FICO Borrower'] < 700)]['Orig. Balance'].sum()

# %% [markdown]
# #### Check B

# %%
b1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.Term > 144) & (final_df_all.type == 'standard') & (final_df_all['FICO Borrower'] < 700)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) &(final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(b1,b1<0.03)

# %%
# b2=final_df_all[(final_df_all.platform == 'prime') & (final_df_all.Term > 144) & (final_df_all.type == 'standard') & (final_df_all['FICO Borrower'] < 700)]['Orig. Balance'].sum()
# print(b2)

# %%
# b3=final_df_all[(final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.Term > 144) & (final_df_all.type == 'standard') & (final_df_all['FICO Borrower'] < 700)]['Orig. Balance'].shape[0] / final_df_all[(final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].shape[0]
# print(b3,b3<0.03)

# %% [markdown]
# #### Check C

# %%
c1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.Term > 144) & (final_df_all.type == 'standard') & (final_df_all['FICO Borrower'] >= 700)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(c1,c1<0.35)

# %% [markdown]
# #### Check D

# %%
d1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.type == 'hybrid')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(d1,d1<0.35)

# %% [markdown]
# #### Check E

# %%
e1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.type == 'ninp')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(e1,e1<0.50)

# %%
e1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.type == 'ninp')& (final_df_all.promo_term >= 12)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(e1,e1<0.15)

# %% [markdown]
# #### Check F

# %%
f1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.type == 'epni')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(f1,f1<0.20)

# %% [markdown]
# #### Check G

# %%
g1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.type == 'wpdi')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(g1,g1<0.20)

# %% [markdown]
# #### Check H

# %%
#Ignore
h1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Lender Price(%)'].max()
print(h1,h1<=101.25)

# %%
h2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all['Lender Price(%)'] > 100) & (final_df_all['Lender Price(%)'] <= 103)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(h2,h2<0.10)

# %%
h3=np.sum((final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Dealer Fee'] * final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'])/final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum())
print(h3,h3<0.15)

# %% [markdown]
# #### Check I

# %%
i1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all['Orig. Balance'] > 50000)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(i1,i1<0.38)

# %%
i2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].mean()
print(i2,i2<20000)

# %% [markdown]
# #### Check J

# %%
(pd.pivot_table(final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')], values = 'Orig. Balance', aggfunc = 'sum', columns='Property State') / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()).T.sort_values("Orig. Balance", ascending = False)

# %% [markdown]
# #### Check L

# %%
l1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all['FICO Borrower'] < 680)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(l1,l1<0.5)

# %%
l2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all['FICO Borrower'] < 700)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(l2,l2<0.7)

# %%
l3=np.sum((final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'] * final_df_all[(final_df_all.platform == 'prime')]['FICO Borrower'] ) / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum())
print(l3,l3>700)

# %%
final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['FICO Borrower'].mean()

# %% [markdown]
# ### SFY

# %% [markdown]
# #### Check A

# %%
a1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'hybrid')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(a1,a1<0.85)

# %%
a2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'hybrid')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(a2,a2<0.20)

# %% [markdown]
# #### Check B

# %%
b1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'ninp')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(b1,b1<0.5)

# %%
b2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'ninp') & (final_df_all.promo_term > 12)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(b2,b2<0.20)

# %%
b4=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'ninp') & (final_df_all.Term > 84)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(b4,b4<=0)

# %% [markdown]
# #### Check C

# %%
c1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'epni')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(c1,c1<=0.10)

# %% [markdown]
# #### Check D

# %%
d1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'wpdi')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(d1,d1<=0.60)

# %%
d2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type.isin([ 'wpdi', 'wpdi_bd']))]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(d2,d2<=0.60)

# %%
d3=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'wpdi') & (final_df_all.promo_term >= 12)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(d3,d3<=0.12)

# %%
d4=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type.isin([ 'wpdi', 'wpdi_bd'])) & (final_df_all.promo_term >= 12)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(d4,d4<=0.12)

# %% [markdown]
# #### Check E

# %%
final_df_all.shape

# %%
e1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'standard') & (final_df_all.Term > 120)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(e1,e1<=0.1)

# %%
e2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type.isin([ 'standard', 'standard_bd'])) & (final_df_all.Term > 120)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(e2,e2<=0.1)

# %%
e3=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'standard') & (final_df_all.Term > 144)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(e3,e3<=0.10)

# %%
e4=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type.isin([ 'standard', 'standard_bd'])) & (final_df_all.Term > 144)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(e4,d4<=0.10)

# %% [markdown]
# #### Check F

# %%
f1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Lender Price(%)'].max()
print(f1,f1<=101.07)

# %%
f2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all['Lender Price(%)'] > 100) & (final_df_all['Lender Price(%)'] <= 103)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(f2,f2<=0.25)

# %%
f3=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all['Lender Price(%)'] > 100) & (final_df_all['Lender Price(%)'] <= 103) & (final_df_all['loan program'] != "Unsec Std - 999 - 120")]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(f3,f3<=0.20)

# %%
f4=np.sum(final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Dealer Fee'] * final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'])/final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(f4,f4<=0.15)

# %% [markdown]
# #### Check G

# %%
g1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all['Orig. Balance'] > 50000)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(g1,g1<=0.25)

# %%
g2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].mean()
print(g2,g2<=20000)

# %% [markdown]
# #### Check H

# %%
(pd.pivot_table(final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) &(final_df_all.platform == 'sfy')], values = 'Orig. Balance', aggfunc = 'sum', columns='Property State') / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) &(final_df_all.platform == 'sfy')]['Orig. Balance'].sum()).T.sort_values("Orig. Balance", ascending = False)

# %% [markdown]
# #### Check J

# %%
j1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all['FICO Borrower'] < 680)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(j1,j1<=0.5)

# %%
j2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all['FICO Borrower'] < 700)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(j2,j2<=0.7)

# %%
j3=np.sum((final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'] * final_df_all[(final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['FICO Borrower'] ) / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum())
print(j3,j3>=700)

# %%
j4=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['FICO Borrower'].mean()
print(j4,j4>=700)

# %% [markdown]
# #### Check L

# %%
l1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'wpdi_bd')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(l1,l1<=0.00)

# %%
l2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'standard_bd')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(l2<=0.00)

# %%
_pp_total = final_df_all['Purchase Price'].sum() if 'Purchase Price' in final_df_all.columns else 0
l3 = final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.type.isin( ['standard_bd', 'wpdi_bd']))]['Purchase Price'].sum() / _pp_total if _pp_total else 0
print(l3<=0.00)

# %%
l4 = final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.Repurchase == False) & (final_df_all.type.isin( ['standard_bd', 'wpdi_bd'])) & (final_df_all.Excess_Asset != True)]['Purchase Price'].sum() / _pp_total if _pp_total else 0
print(l4<=0.00)

# %%
#special asset
s1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.new_programs == True)&(final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(s1,s1<0.02)

# %%
s1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.new_programs == True)&(final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(s1,s1<0.02)

# %%
#--------------------------------------------------End--------------------------------------

# %%


# %%


# %%


