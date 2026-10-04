"""Stage 3: CRM data-quality checks.

Reads  data/accounts_clean.csv (after clean_data + territory_router)
Writes data/accounts_clean.csv (adds Flag_* columns, DQ_Issue_Count, DQ_Issues,
       Record_DQ_Score, Data_Quality_Status)
       data/dq_issues.csv (long format: one row per account x issue, with severity + action)

Scoring (documented in documentation/data_dictionary.md and README):
  Record_DQ_Score = max(0, 100 - sum(penalty per issue))
      penalties: Critical 40 | High 25 | Medium 10 | Low 5
  Data Quality Score % = average Record_DQ_Score across all accounts
  Clean Record Rate %  = % of accounts with Data_Quality_Status = 'Good'
  Data_Quality_Status  = worst severity on the record:
      Critical -> 'Critical' | High -> 'Needs Review' | Medium/Low -> 'Warning' | none -> 'Good'
"""
import pandas as pd
from config import *
from clean_data import is_valid_domain

ISSUES = [  # (flag column, issue label, default severity, recommended action)
    ("Is_Duplicate", "Duplicate Account", "Critical", "Merge into master record (Master_Account_ID) and re-point opportunities"),
    ("Flag_Missing_Country", "Missing Country", "Critical", "Enrich country from domain/billing address; routing is blocked until fixed"),
    ("Flag_Invalid_Country", "Invalid Country", "Critical", "Replace non-country value with the HQ country"),
    ("Flag_Missing_Owner", "Missing Owner", "Critical", "Assign owner per territory rules (Expected_Owner)"),
    ("Flag_Missing_Territory", "Missing Territory", "High", "Populate Sales_Territory from country mapping"),
    ("Flag_Invalid_Territory", "Invalid Territory", "High", "Correct territory to Expected_Territory and reassign owner"),
    ("Flag_Stale", "Stale Account", "Medium", "Sales to re-engage or mark Inactive; review open opportunities"),
    ("Flag_Missing_Employee", "Missing Employee Count", "Medium", "Enrich headcount (needed for tiering and India owner routing)"),
    ("Flag_Missing_Revenue", "Missing Annual Revenue", "Medium", "Enrich revenue from firmographic source"),
    ("Flag_Tier_Mismatch", "Tier Mismatch", "Medium", "Update Account_Tier to Expected_Tier; check owner"),
    ("Flag_Missing_Opp_Info", "Missing Opportunity Info", "Medium", "Sales to complete stage/value on the open opportunity"),
    ("Flag_Invalid_Domain", "Invalid Domain", "Low", "Correct or populate Website_Domain (also used for duplicate matching)"),
]


def add_flags(df):
    f = pd.DataFrame(index=df.index)
    f["Flag_Missing_Country"] = df.Country.isna()
    f["Flag_Invalid_Country"] = df.Country.notna() & ~df.Country.isin(COUNTRIES.keys())
    f["Flag_Missing_Employee"] = df.Employee_Count.isna()
    f["Flag_Missing_Revenue"] = df.Annual_Revenue.isna()
    f["Flag_Missing_Owner"] = df.Account_Owner.isna()
    f["Flag_Missing_Territory"] = df.Sales_Territory.isna()
    known = ~df.Expected_Territory.eq("Unknown")
    f["Flag_Invalid_Territory"] = df.Sales_Territory.notna() & (
        ~df.Sales_Territory.isin(TERRITORIES) | (known & df.Sales_Territory.ne(df.Expected_Territory)))
    f["Flag_Stale"] = df.Days_Since_Activity > STALE_ACCOUNT_DAYS
    f["Flag_Invalid_Domain"] = ~df.Website_Domain.map(is_valid_domain)
    stage, val = df.Opportunity_Stage.notna(), df.Opportunity_Value
    f["Flag_Missing_Opp_Info"] = (stage & (val.isna() | (val <= 0))) | (~stage & val.notna())
    f["Flag_Tier_Mismatch"] = df.Account_Tier.notna() & df.Expected_Tier.ne("Unknown") & df.Account_Tier.ne(df.Expected_Tier)
    for c in f:
        df[c] = f[c].astype(int)
    return df


def severity(row, label, default):
    has_pipe = pd.notna(row.Opportunity_Value) and row.Opportunity_Value > 0
    if label == "Stale Account" and has_pipe:
        return "High"
    if label == "Missing Employee Count" and row.Country == "India":
        return "High"          # blocks India Enterprise/Commercial owner routing
    return default


def main():
    df = pd.read_csv(DATA / "accounts_clean.csv")
    df = add_flags(df)

    long = []
    for flag, label, sev, action in ISSUES:
        sub = df[df[flag] == 1]
        for r in sub.itertuples():
            long.append((r.Account_ID, r.Company_Name, r.Country, r.Expected_Territory, r.Industry,
                         r.Expected_Tier, label, severity(r, label, sev), action,
                         r.Opportunity_Value if pd.notna(r.Opportunity_Value) else 0))
    iss = pd.DataFrame(long, columns=["Account_ID", "Company_Name", "Country", "Territory", "Industry",
                                      "Account_Tier", "Issue_Type", "Severity", "Recommended_Action",
                                      "Open_Pipeline_Value"])
    iss["Penalty"] = iss.Severity.map(SEVERITY_PENALTY)
    rank = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    iss["_r"] = iss.Severity.map(rank)
    iss = iss.sort_values(["_r", "Account_ID", "Issue_Type"]).drop(columns="_r")
    iss.to_csv(DATA / "dq_issues.csv", index=False)

    g = iss.groupby("Account_ID")
    df["DQ_Issue_Count"] = df.Account_ID.map(g.size()).fillna(0).astype(int)
    df["DQ_Issues"] = df.Account_ID.map(g.Issue_Type.agg("; ".join))
    df["Record_DQ_Score"] = (100 - df.Account_ID.map(g.Penalty.sum()).fillna(0)).clip(lower=0).astype(int)
    worst = df.Account_ID.map(iss.assign(_r=iss.Severity.map(rank)).groupby("Account_ID")._r.min())
    df["Data_Quality_Status"] = worst.map({0: "Critical", 1: "Needs Review", 2: "Warning", 3: "Warning"}).fillna("Good")
    df.to_csv(DATA / "accounts_clean.csv", index=False)

    n = len(df)
    print(f"Data Quality Score: {df.Record_DQ_Score.mean():.1f}% | Clean Record Rate: {100 * (df.Data_Quality_Status == 'Good').mean():.1f}%")
    print(df.Data_Quality_Status.value_counts().reindex(["Good", "Warning", "Needs Review", "Critical"]).to_string())
    s = iss.groupby(["Issue_Type", "Severity"]).agg(Accounts=("Account_ID", "nunique"), Pipeline=("Open_Pipeline_Value", "sum"))
    s["Pct"] = (100 * s.Accounts / n).round(2)
    print(s.sort_values("Accounts", ascending=False).to_string())


if __name__ == "__main__":
    main()
