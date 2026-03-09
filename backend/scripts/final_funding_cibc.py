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
# NOTE: Date variables below (pdate, curr_date, etc.) are set to 93rd buy dates.
# For a new buy cycle, update these to match the filenames in files_required/.
# Known limitation: these must be manually updated per buy cycle.
folderx = '93rd'
irr_target = 7.9

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
#manual dates
yestarday='02-18-2026'
pdate='2026-02-24'
curr_date='02-19-2026'
last_end='2026_001_31'
fd='2026-02-01'

# %%
#file location and importing

#files_required
fx3_servicing_file = f"{folder}/files_required/FX3_{last_end}.xlsx"
fx4_servicing_file = f"{folder}/files_required/FX4_{last_end}.xlsx"
#fx4_servicing_file = f"C:/Users/gdehankar/TWG/Jagadish Balaji - SFC_Loans/78th_buy/files_required/FX4_2025_0010_31.xlsx"
loans = pd.read_csv(f"{folder}/files_required/Tape20Loans_{yestarday}.csv") #change days
#loans = pd.read_csv(f"{folder}/files_required/Tape20Loans_{(pd.to_datetime('today') - pd.DateOffset(days = 1)).strftime("%m-%d-%Y")}.csv")
df_loans_types = pd.read_excel(f'{folder}/files_required/MASTER_SHEET.xlsx')
notes = pd.read_excel(f'{folder}/files_required/MASTER_SHEET - Notes.xlsx')
existing_file_ = pd.read_csv(f"{folder}/files_required/current_assets.csv") #do not change
sfy_file = f"{folder}/files_required/FX3_{curr_date}_ExhibitAtoFormofSaleNotice_cibc.xlsx"
prime_file = f"{folder}/files_required/{curr_date} Exhibit A To Form Of Sale Notice_cibc.xlsx"

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
sfy_df = sfy_df.loc[::-1, : 'Application Type']
sfy_df.head(1)

# %%
sfy_df.tail(2)

# %%
prime_df = pd.read_excel(prime_file)
prime_df = prime_df.drop(['Unnamed: 0', 'tags','final'], axis=1)
prime_df = prime_df.loc[:, : 'Application Type']
prime_df.head(1)

# %%
prime_df.tail(2)

# %%
existing_file_=existing_file_[existing_file_['lender']=='CIBC']
existing_file_ = existing_file_.drop(['lender'], axis=1)

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
assert sum(buy_df['SELLER Loan #'].duplicated()) == 0
#buy_df.loc[(buy_df['new_programs'] == True)&(buy_df['Repurchase'] == False) & (buy_df['platform'] == 'sfy'), 'Excess_Asset'] = True
#buy_df.loc[(buy_df['new_programs'] == True)&(buy_df['Repurchase'] == False) & (buy_df['platform'] == 'sfy'), 'Borrowing_Base_eligible'] = False
# buy_df['Dealer Fee'] = buy_df['Dealer Fee'] / 100
final_df = pd.concat([buy_df, existing_file[existing_file['Purchase_Date'] > '2026-01-07']])
final_df_all = pd.concat([buy_df, existing_file])
final_df_all2 = pd.concat([buy_df, existing_file[((existing_file['Purchase_Date'] > '2026-01-07') | (existing_file['Purchase_Date'] < '2025-10-01'))]])
buy_df.shape, final_df[final_df['Orig. Balance'] > 50000].shape, final_df.shape, final_df['SELLER Loan #'].nunique(), buy_df[buy_df['tagging'] != 'BD']['Orig. Balance'].sum()

# %%
buy_df['Orig. Balance'].sum()

# %% [markdown]
# ## Mark excess and borrowing file

# %%
final_df_all2[["SELLER Loan #", 'Orig. Balance', "tagging", 'Repurchase',
              'platform','Excess_Asset']].to_excel(f"{folder}/output/EveryLoan_cibc.xlsx")

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
                "Application Type"]].to_excel(f"{folder}/output/borrowing_file_cibc.xlsx")

# %% [markdown]
# ## Check Purchase Price

# %%
existing_file['purchase_price_check'] = existing_file['Lender Price(%)'] == round(existing_file['modeled_purchase_price']*100, 2)
existing_file.shape, existing_file.purchase_price_check.sum()

# %%
buy_df['purchase_price_check'] = buy_df['Lender Price(%)'] == round(buy_df['modeled_purchase_price']*100, 2)
buy_df.shape, buy_df.purchase_price_check.sum()

# %%
final_df['purchase_price_check'] = final_df['Lender Price(%)'] == round(final_df['modeled_purchase_price']*100, 2)
final_df.shape, final_df.purchase_price_check.sum()

# %%
#extra checks as russ mentioned should be close to 0
buy_df['Lender Price(%)_x']=buy_df['Lender Price(%)'].astype(float)/100
buy_df['modeled_price']=buy_df['Lender Price(%)_x']*buy_df['Orig. Balance']
buy_df[['modeled_price','Purchase Price']]
buy_df['modeled_price'].sum()-buy_df['Purchase Price'].sum()

# %%
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
    (underwriting.approval_high >= balance) & (underwriting.approval_low <= balance)
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
prime_comap_cols_min_fico = {j:int(j[:3]) for i,j in enumerate(['660-699', '700-739', '740-749', '750-769', '770+'])}
prime_comap_cols_min_fico2 = {j:int(j[:3]) for i,j in enumerate(['660-699', '700-739', '740-749', '750+'])}
sfy_comap_cols_min_fico = {j:int(j[:3]) for i,j in enumerate(['660-719', '720-779', '780-799', '800+'])}
sfy_comap_cols_min_fico2 = {j:int(j[:3]) for i,j in enumerate(['660-699', '700-739', '740-749', '750-769','770+'])}
sfy_comap_cols_min_fico3 = {j:int(j[:3]) for i,j in enumerate(['660-719', '720-779', '780+'])}
notes_comap_cols_min_fico = {j:int(j[:3]) for i,j in enumerate(['680-749', '750-769', '770-789', '790+'])}

# %%
print(sfy_comap_cols_min_fico3)

# %%
loan_not_in_comap = []
for row in buy_df[(buy_df['Application Type'] != 'HD NOTE') & (buy_df['purchase_price_check'] == True)].iterrows():
    fico = row[1]['FICO Borrower']
    prog = row[1]['loan program']
    found = False
    if row[1]['platform'] == 'prime':
        if row[1]['Submit Date'] > pd.to_datetime('2025-10-24'):
            if (prog not in prime_comap_oct25[['660-699', '700-739', '740-749', '750+']].stack().unique()) & (prog not in prime_comap_oct25_2[['660-699', '700-739', '740-749', '750-769', '770+']].stack().unique()):
                continue
            else:
                pass
        elif prog not in prime_comap[['660-699', '700-739', '740-749', '750-769', '770+']].stack().unique():
            continue
        else:
            pass
        if row[1]['Submit Date'] > pd.to_datetime('2025-10-24'):
            if prog in prime_comap_oct25[['660-699', '700-739', '740-749', '750+']].stack().unique():
                for col in ['660-699', '700-739', '740-749', '750+']:
                    if prog in prime_comap_oct25[col].values and fico >= prime_comap_cols_min_fico2[col]:
                        found = True
                        break
            elif prog in prime_comap_oct25_2[['660-699', '700-739', '740-749', '750-769', '770+']].stack().unique():
                for col in ['660-699', '700-739', '740-749', '750-769', '770+']:
                    if prog in prime_comap_oct25_2[col].values and fico >= prime_comap_cols_min_fico[col]:
                        found = True
                        break
            else:
                pass
        elif row[1]['Submit Date'] > pd.to_datetime('2024-06-11'):
            for col in ['660-699', '700-739', '740-749', '750-769', '770+']:
                if prog in prime_comap_new[col].values and fico >= prime_comap_cols_min_fico[col]:
                    found = True
                    break
        else:
            for col in ['660-699', '700-739', '740-749', '750-769', '770+']:
                if prog in prime_comap[col].values and fico >= prime_comap_cols_min_fico[col]:
                    found = True
                    break
        if not found:
            loan_not_in_comap.append((row[1]["SELLER Loan #"], prog, "PRIME"))
    else:
        if row[1]['Submit Date'] > pd.to_datetime('2025-10-24'):
            if (prog not in sfy_comap_oct25[['660-719', '720-779', '780+']].stack().unique()) & (prog not in sfy_comap_oct25_2[['660-699', '700-739', '740-749', '750-769','770+']].stack().unique()):
                continue
            else:
                pass
        elif (prog not in sfy_comap[['660-719', '720-779', '780-799', '800+']].stack().unique()) & (prog not in sfy_comap2[['660-699', '700-739', '740-749', '750-769','770+']].stack().unique()):
            continue
        else:
            pass
        if row[1]['Submit Date'] > pd.to_datetime('2025-10-24'):
            if prog in sfy_comap_oct25[['660-719', '720-779', '780+']].stack().unique():
                for col in ['660-719', '720-779', '780+']:
                    if prog in sfy_comap_oct25[col].values and fico >= sfy_comap_cols_min_fico3[col]:
                        found = True
                        break
            elif prog in sfy_comap_oct25_2[['660-699', '700-739', '740-749', '750-769', '770+']].stack().unique():
                for col in ['660-699', '700-739', '740-749', '750-769', '770+']:
                    if prog in sfy_comap_oct25_2[col].values and fico >= sfy_comap_cols_min_fico2[col]:
                        found = True
                        break
            else:
                pass
        elif prog in sfy_comap[['660-719', '720-779', '780-799', '800+']].stack().unique():
            for col in ['660-719', '720-779', '780-799', '800+']:
                if prog in sfy_comap[col].values and fico >= sfy_comap_cols_min_fico[col]:
                    found = True
                    break
        elif prog in sfy_comap2[['660-699', '700-739', '740-749', '750-769','770+']].stack().unique():
            for col in ['660-699', '700-739', '740-749', '750-769','770+']:
                if prog in sfy_comap2[col].values and fico >= sfy_comap_cols_min_fico2[col]:
                    found = True
                    break
        if not found:
            loan_not_in_comap.append((row[1]["SELLER Loan #"], prog, "SFY"))

len(loan_not_in_comap)

# %%
loan_not_in_comap_notes = []
for row in buy_df[(buy_df['Application Type'] == 'HD NOTE') & (buy_df['purchase_price_check'] == True)].iterrows():
    fico = row[1]['FICO Borrower']
    prog = row[1]['loan program']
    found = False
    if prog not in notes_comap[['680-749', '750-769', '770-789', '790+']].stack().unique():
        continue
    for col in ['680-749', '750-769', '770-789', '790+']:
        if prog in notes_comap[col].values and fico >= notes_comap_cols_min_fico[col]:
            found = True
            break
    if not found:
        # reason = f"PRIME loan prog not in fico band - 660-699 - available - {fico}"
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
note_flag.to_excel(f"{folder}/output_share/NOTES_flagged_loanxs_{folderx}.xlsx")
comap.to_excel(f"{folder}/output_share/comap_not_passed.xlsx")

# %%
#final_df_all=

# %%


# %%


final_df_all[["SELLER Loan #","Orig. Balance","Purchase Price","promo_term","Current Balance","APR","Term","Property State","FICO Borrower",
              "loan program","Total Dealer $","Lender Price(%)","Dealer Fee","Income","Repurchase",	"Purchase_Date","Excess_Asset",
              "Borrowing_Base_eligible","Platform","tagging","type","new_programs"]].to_excel(f"{folder}/output/concentration_final_cibc.xlsx")

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
print(e1,e1<0.15)

# %% [markdown]
# #### Check F

# %%
f1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.type == 'epni')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(f1,f1<0.18)

# %% [markdown]
# #### Check G

# %%
g1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all.type == 'wpdi')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(g1,g1<0.15)

# %% [markdown]
# #### Check H

# %%
#Ignore
h1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Lender Price(%)'].max()
print(h1,h1<=102.0)

# %%
h2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime') & (final_df_all['Lender Price(%)'] > 100) & (final_df_all['Lender Price(%)'] <= 103)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'prime')]['Orig. Balance'].sum()
print(h2,h2<0.35)

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
a2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'hybrid') & (final_df_all.APR < 7.0)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(a2,a2<0.25)

# %% [markdown]
# #### Check B

# %%
b1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'ninp')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(b1,b1<0.3)

# %%
b2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'ninp') & (final_df_all.promo_term > 6)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(b2,b2<0.27)

# %%
b3=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'ninp') & (final_df_all.promo_term > 12)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(b3,b3<0.15)

# %%
b4=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'ninp') & (final_df_all.Term > 84)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(b4,b4<=0)

# %% [markdown]
# #### Check C

# %%
c1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'epni')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(c1,c1<=0.25)

# %% [markdown]
# #### Check D

# %%
d1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'wpdi')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(d1,d1<=0.17)

# %%
d2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type.isin([ 'wpdi', 'wpdi_bd']))]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(d2,d2<=0.17)

# %%
d3=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'wpdi') & (final_df_all.promo_term >= 12)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(d3,d3<=0.09)

# %%
d4=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type.isin([ 'wpdi', 'wpdi_bd'])) & (final_df_all.promo_term >= 12)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(d4,d4<=0.09)

# %% [markdown]
# #### Check E

# %%
e1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'standard') & (final_df_all.Term > 120)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(e1,e1<=0.3)

# %%
e2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type.isin([ 'standard', 'standard_bd'])) & (final_df_all.Term > 120)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(e2,e2<=0.3)

# %%
e3=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'standard') & (final_df_all.Term > 144)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(e3,e3<=0.28)

# %%
e4=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type.isin([ 'standard', 'standard_bd'])) & (final_df_all.Term > 144)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(e4,d4<=0.28)

# %% [markdown]
# #### Check F

# %%
f1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Lender Price(%)'].max()
print(f1,f1<=101.25)

# %%
f2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all['Lender Price(%)'] > 100) & (final_df_all['Lender Price(%)'] <= 103)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(f2,f2<=0.4)

# %%
f3=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all['Lender Price(%)'] > 100) & (final_df_all['Lender Price(%)'] <= 103) & (final_df_all['loan program'] != "Unsec Std - 999 - 120")]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(f3,f3<=0.37)

# %%
f4=np.sum(final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Dealer Fee'] * final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'])/final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(f4,f4<=0.15)

# %% [markdown]
# #### Check G

# %%
g1=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all['Orig. Balance'] > 50000)]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(g1,g1<=0.38)

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
print(l1,l1<=0.01)

# %%
l2=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy') & (final_df_all.type == 'standard_bd')]['Orig. Balance'].sum() / final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.platform == 'sfy')]['Orig. Balance'].sum()
print(l2)

# %%
l3=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.type.isin( ['standard_bd', 'wpdi_bd']))]['Purchase Price'].sum() / final_df_all['Purchase Price'].sum()
print(l3)

# %%
l4=final_df_all[(final_df_all["Excess_Asset"] == False) & (final_df_all.Repurchase == False) & (final_df_all.Repurchase == False) & (final_df_all.type.isin( ['standard_bd', 'wpdi_bd'])) & (final_df_all.Excess_Asset != True)]['Purchase Price'].sum() / final_df_all['Purchase Price'].sum()
print(l4)

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


