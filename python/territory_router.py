"""Stage 2: deterministic territory routing.

Reads  data/accounts_clean.csv, data/territory_mapping.csv
Writes data/accounts_clean.csv (adds Expected_Territory, Expected_Tier, Expected_Owner,
       Routing_Status, Exception_Type, Is_Covered)
       data/routing_exceptions.csv (one row per non-correct account, with priority + workflow status)

Rule order matters - the first matching rule decides the status (see documentation/routing_logic.md).
"""
import pandas as pd
from config import *

STATUS_ORDER = ["Correctly Routed", "Incorrectly Routed", "Unassigned", "Ambiguous", "Manual Review"]
WORKFLOW = {
    "Duplicate Account": "Pending Merge Review",
    "Missing Country": "Awaiting Data Enrichment", "Invalid Country": "Awaiting Data Enrichment",
    "Missing Employee Count": "Awaiting Data Enrichment",
    "No Owner": "Awaiting Assignment", "No Territory": "Awaiting Assignment",
    "No Owner & No Territory": "Awaiting Assignment",
    "Territory Mismatch": "Ready to Reassign", "Invalid Territory Value": "Ready to Reassign",
    "Owner Mismatch": "Ready to Reassign",
}


def tier_for(emp):
    if pd.isna(emp):
        return "Unknown"
    return "Enterprise" if emp >= ENTERPRISE_MIN else ("Mid-Market" if emp >= MIDMARKET_MIN else "SMB")


def route_account(r, mapping):
    """Return (expected_territory, expected_tier, expected_owner, status, exception_type)."""
    tier = tier_for(r.Employee_Count)
    # Rule 2: country must resolve to a territory
    if pd.isna(r.Country) or r.Country not in mapping.index:
        exp_t, exp_o = "Unknown", None
    else:
        row = mapping.loc[r.Country]
        exp_t = row.Territory
        col = {"Enterprise": "Enterprise_Owner", "Mid-Market": "MidMarket_Owner", "SMB": "SMB_Owner"}.get(tier)
        exp_o = row[col] if col else (row.Enterprise_Owner if row.Enterprise_Owner == row.SMB_Owner else None)

    # Rule 1: non-master duplicates are never routed
    if r.Is_Duplicate == 1:
        return exp_t, tier, exp_o, "Manual Review", "Duplicate Account"
    # Rule 2: country problems -> ambiguous
    if exp_t == "Unknown":
        return exp_t, tier, None, "Ambiguous", ("Missing Country" if pd.isna(r.Country) else "Invalid Country")
    # Rule 3: India owner depends on tier; no headcount -> cannot decide
    if exp_o is None:
        return exp_t, tier, None, "Manual Review", "Missing Employee Count"
    # Rule 4: unassigned
    no_o, no_t = pd.isna(r.Account_Owner), pd.isna(r.Sales_Territory)
    if no_o or no_t:
        return exp_t, tier, exp_o, "Unassigned", ("No Owner & No Territory" if no_o and no_t else "No Owner" if no_o else "No Territory")
    # Rule 5/6: mismatches
    if r.Sales_Territory not in TERRITORIES:
        return exp_t, tier, exp_o, "Incorrectly Routed", "Invalid Territory Value"
    if r.Sales_Territory != exp_t:
        return exp_t, tier, exp_o, "Incorrectly Routed", "Territory Mismatch"
    if r.Account_Owner != exp_o:
        return exp_t, tier, exp_o, "Incorrectly Routed", "Owner Mismatch"
    return exp_t, tier, exp_o, "Correctly Routed", None


def priority(r):
    pipe = r.Opportunity_Value if pd.notna(r.Opportunity_Value) else 0
    if r.Expected_Tier == "Enterprise" or pipe >= 100000:
        return "High"
    if pipe > 0 or r.Expected_Tier == "Mid-Market":
        return "Medium"
    return "Low"


def routing_accuracy(df):
    """Correct / (Correct + Incorrect + Unassigned). Ambiguous & Manual Review are excluded
    because no deterministic expected route exists for them."""
    vc = df.Routing_Status.value_counts()
    routable = vc.get("Correctly Routed", 0) + vc.get("Incorrectly Routed", 0) + vc.get("Unassigned", 0)
    return 100 * vc.get("Correctly Routed", 0) / routable if routable else float("nan"), int(routable)


def main():
    df = pd.read_csv(DATA / "accounts_clean.csv")
    mapping = pd.read_csv(DATA / "territory_mapping.csv").set_index("Country")
    res = df.apply(lambda r: route_account(r, mapping), axis=1, result_type="expand")
    df["Expected_Territory"], df["Expected_Tier"], df["Expected_Owner"], df["Routing_Status"], df["Exception_Type"] = \
        res[0], res[1], res[2], res[3], res[4]
    df["Is_Covered"] = (df.Account_Owner.notna() & df.Sales_Territory.isin(TERRITORIES)).astype(int)
    df.to_csv(DATA / "accounts_clean.csv", index=False)

    ex = df[df.Routing_Status != "Correctly Routed"].copy()
    ex["Priority"] = ex.apply(priority, axis=1)
    ex["Resolution_Status"] = ex.Exception_Type.map(WORKFLOW)
    ex["Is_Open"] = 1
    ex = ex.rename(columns={"Sales_Territory": "Current_Territory", "Account_Owner": "Current_Owner",
                            "Opportunity_Value": "Open_Pipeline_Value"})
    cols = ["Account_ID", "Company_Name", "Country", "Industry", "Expected_Tier", "Current_Territory",
            "Expected_Territory", "Current_Owner", "Expected_Owner", "Routing_Status", "Exception_Type",
            "Priority", "Open_Pipeline_Value", "Resolution_Status", "Is_Open"]
    ex[cols].to_csv(DATA / "routing_exceptions.csv", index=False)

    acc, routable = routing_accuracy(df)
    print("Routing status:\n" + df.Routing_Status.value_counts().reindex(STATUS_ORDER).to_string())
    print(f"Routable accounts: {routable:,} | Routing accuracy: {acc:.2f}% | exceptions: {len(ex):,}")
    print(f"Territory coverage: {100 * df.Is_Covered.mean():.2f}%")


if __name__ == "__main__":
    main()
