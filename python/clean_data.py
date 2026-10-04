"""Stage 1 of the pipeline: standardise the raw CRM export and flag duplicates.

Reads  data/accounts_raw.csv, data/opportunities.csv
Writes data/accounts_clean.csv   (standardised; downstream stages add routing + DQ columns)
       data/opportunities.csv    (enriched in place with Days_Since_Activity, Is_Stale_Opp)

Cleaning never deletes a record - problems are flagged, not hidden.
"""
import re
import pandas as pd
from config import *

DOMAIN_RE = re.compile(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)+$")


def norm_text(s):
    return None if pd.isna(s) else re.sub(r"\s+", " ", str(s)).strip() or None


def norm_country(s):
    s = norm_text(s)
    if s is None:
        return None
    if s in COUNTRIES:
        return s
    return COUNTRY_ALIASES.get(s.lower().rstrip("."), COUNTRY_ALIASES.get(s.lower(), s))


def norm_domain(s):
    s = norm_text(s)
    if s is None:
        return None
    s = s.lower()
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"^www\.", "", s)
    return s.split("/")[0] or None


def is_valid_domain(d):
    return isinstance(d, str) and bool(DOMAIN_RE.match(d)) and ".." not in d


def name_key(name, country):
    toks = re.sub(r"[^a-z0-9 ]", " ", str(name).lower()).split()
    toks = [t for t in toks if t not in LEGAL_TOKENS]
    return " ".join(toks)


def flag_duplicates(df):
    """Union-find on (a) shared valid domain, (b) shared normalised name + country."""
    parent = {i: i for i in df.index}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for key_fn in (lambda r: r.Website_Domain if is_valid_domain(r.Website_Domain) else None,
                   lambda r: (name_key(r.Company_Name, r.Country), r.Country) if pd.notna(r.Country) else None):
        seen = {}
        for i, r in df.iterrows():
            k = key_fn(r)
            if k is None:
                continue
            if k in seen:
                union(seen[k], i)
            else:
                seen[k] = i

    groups = {}
    for i in df.index:
        groups.setdefault(find(i), []).append(i)
    is_dup = pd.Series(0, index=df.index)
    master = pd.Series(None, index=df.index, dtype=object)
    for members in groups.values():
        if len(members) > 1:
            ordered = sorted(members, key=lambda i: (df.at[i, "Created_Date"], df.at[i, "Account_ID"]))
            for i in ordered[1:]:
                is_dup[i] = 1
                master[i] = df.at[ordered[0], "Account_ID"]
    return is_dup, master


def main():
    df = pd.read_csv(DATA / "accounts_raw.csv", dtype=str)
    for c in ["Company_Name", "Industry", "Account_Tier", "Sales_Territory", "Account_Owner", "Lead_Source",
              "Opportunity_Stage", "CRM_Status", "Region"]:
        df[c] = df[c].map(norm_text)
    df["Country"] = df["Country"].map(norm_country)
    df["Website_Domain"] = df["Website_Domain"].map(norm_domain)
    df["Employee_Count"] = pd.to_numeric(df["Employee_Count"], errors="coerce").astype("Int64")
    df["Annual_Revenue"] = pd.to_numeric(df["Annual_Revenue"], errors="coerce")
    df["Opportunity_Value"] = pd.to_numeric(df["Opportunity_Value"], errors="coerce")
    for c in ["Last_Activity_Date", "Created_Date"]:
        df[c] = pd.to_datetime(df[c], errors="coerce")

    df["Is_Duplicate"], df["Master_Account_ID"] = flag_duplicates(df)
    df["Days_Since_Activity"] = (pd.Timestamp(AS_OF) - df["Last_Activity_Date"]).dt.days
    for c in ["Last_Activity_Date", "Created_Date"]:
        df[c] = df[c].dt.date
    df.to_csv(DATA / "accounts_clean.csv", index=False)

    opp = pd.read_csv(DATA / "opportunities.csv")
    d = (pd.Timestamp(AS_OF) - pd.to_datetime(opp["Last_Activity_Date"])).dt.days
    opp["Days_Since_Activity"] = d
    opp["Is_Stale_Opp"] = ((opp["Is_Open"] == 1) & (d > STALE_OPP_DAYS)).astype(int)
    opp.to_csv(DATA / "opportunities.csv", index=False)

    print(f"accounts_clean.csv: {len(df):,} rows | duplicates flagged: {int(df.Is_Duplicate.sum())} "
          f"| stale open opps: {int(opp.Is_Stale_Opp.sum())}")


if __name__ == "__main__":
    main()
