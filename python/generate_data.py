"""Generate the SYNTHETIC APJ CRM dataset (accounts, opportunities, territory mapping).

All companies are fictional. Output is deterministic (fixed seed).

Seeded business patterns (documented so nothing is hidden):
  * India accounts created since 2026-04-01 have a much higher missing-owner rate
    (simulates a rep vacancy / unassigned backlog).
  * Japan has a higher stale-account rate.
  * SEA and Korea have higher wrong-territory rates (reorg / neighbour confusion).
"""
import re
import numpy as np
import pandas as pd
import datetime as dt
from config import *

rng = np.random.default_rng(SEED)
D = dt.timedelta


def choice_w(weights: dict, n=None):
    keys = list(weights)
    p = np.array([weights[k] for k in keys], float)
    return rng.choice(keys, size=n, p=p / p.sum())


# ---------- fictional company names ----------
ONSET = ["k", "v", "m", "n", "t", "r", "s", "l", "d", "b", "z", "p", "h", "j", "f", "g", "c", "w", "y"]
VOWEL = ["a", "e", "i", "o", "u", "ai", "ei", "ia", "ou"]
CODA = ["", "", "n", "r", "x", "s", "m", "l"]
DESCRIPTORS = {
    "Software": ["Systems", "Labs", "Cloud", "Digital", "Technologies"],
    "Financial Services": ["Capital", "Financial", "Assurance", "Holdings"],
    "Healthcare": ["Health", "Medical", "Biosciences", "Care"],
    "Manufacturing": ["Industries", "Manufacturing", "Engineering", "Materials"],
    "Retail": ["Retail", "Mart", "Stores", "Commerce"],
    "Telecommunications": ["Telecom", "Networks", "Communications"],
    "Professional Services": ["Consulting", "Advisory", "Partners", "Solutions"],
    "Education": ["Education", "Academy", "Learning", "Institute"],
    "Government": ["Public Services Authority", "Regional Council", "Digital Services Board"],
    "Logistics": ["Logistics", "Freight", "Supply Chain", "Transport"],
}
used_brands, used_slugs = set(), set()


def brand():
    while True:
        b = "".join(rng.choice(ONSET) + rng.choice(VOWEL) for _ in range(int(rng.integers(2, 4)))) + rng.choice(CODA)
        b = b.capitalize()
        if b not in used_brands and len(b) >= 5:
            used_brands.add(b)
            return b


def company(country, industry):
    code, terr, sub, w, tld, gov, legal = COUNTRIES[country]
    b = brand()
    desc = str(rng.choice(DESCRIPTORS[industry]))
    slug = b.lower() + (desc.lower().replace(" ", "")[:8] if rng.random() < 0.35 and industry != "Government" else "")
    while slug in used_slugs:
        slug += str(int(rng.integers(2, 99)))
    used_slugs.add(slug)
    if industry == "Government":
        return f"{b} {desc}", slug + gov
    name = f"PT {b} {desc}" if legal == "PT" else f"{b} {desc} {legal}"
    return name, slug + tld


def owner_for(territory, tier):
    return OWNERS.get((territory, tier)) or OWNERS.get((territory, "*"))


def tier_of(emp):
    return "Enterprise" if emp >= ENTERPRISE_MIN else ("Mid-Market" if emp >= MIDMARKET_MIN else "SMB")


def main():
    n_dup = int(round(N_ACCOUNTS * DUPLICATE_RATE))
    n_base = N_ACCOUNTS - n_dup
    inj = {}

    # ---------- base accounts ----------
    countries = choice_w({c: v[3] for c, v in COUNTRIES.items()}, n_base)
    industries = choice_w(INDUSTRIES, n_base)
    shift = {"Telecommunications": 0.9, "Government": 0.9, "Manufacturing": 0.3, "Financial Services": 0.3,
             "Retail": 0.2, "Logistics": 0.1, "Education": 0.0, "Software": -0.1, "Healthcare": 0.1,
             "Professional Services": -0.3}
    emp = np.array([max(5, int(rng.lognormal(np.log(260) + shift[i], 1.75))) for i in industries])
    emp = np.minimum(emp, 150000)
    rev_pe = rng.lognormal(np.log(150000), 0.5, n_base)
    rev = np.round(np.maximum(emp * rev_pe, 150000) / 1000) * 1000

    names, domains = [], []
    for c, i in zip(countries, industries):
        n, d = company(c, i)
        names.append(n)
        domains.append(d)

    span = (AS_OF - D(10) - dt.date(2019, 1, 1)).days
    created = [dt.date(2019, 1, 1) + D(int(rng.beta(1.6, 1.0) * span)) for _ in range(n_base)]
    status = choice_w({"Customer": 30, "Prospect": 55, "Inactive": 10, "Churned": 5}, n_base)
    lead = choice_w(LEAD_SOURCES, n_base)

    base = pd.DataFrame({
        "Company_Name": names, "Website_Domain": domains, "Country": countries, "Industry": industries,
        "Employee_Count": emp, "Annual_Revenue": rev, "Lead_Source": lead, "CRM_Status": status,
        "Created_Date": created,
    })
    base["Region"] = base.Country.map(lambda c: COUNTRIES[c][2])
    base["True_Territory"] = base.Country.map(lambda c: COUNTRIES[c][1])
    base["True_Tier"] = base.Employee_Count.map(tier_of)

    # ---------- last activity (stale injected explicitly) ----------
    last = []
    stale_flag = []
    for i, r in base.iterrows():
        age = (AS_OF - r.Created_Date).days
        p_stale = 0.060 if r.Country == "Japan" else 0.026
        if age >= 200 and rng.random() < p_stale:
            d = int(rng.integers(185, min(700, age) + 1))
            last.append(AS_OF - D(d))
            stale_flag.append(1)
        else:
            d = min(170, int(rng.exponential(30)))
            la = AS_OF - D(d)
            if la < r.Created_Date:
                la = r.Created_Date + D(int(rng.integers(0, age + 1)))
            last.append(la)
            stale_flag.append(0)
    base["Last_Activity_Date"] = last
    inj["stale"] = int(sum(stale_flag))

    # ---------- IDs ----------
    ids = rng.permutation(np.arange(100001, 100001 + N_ACCOUNTS))
    base["Account_ID"] = [f"ACC-{x}" for x in ids[:n_base]]

    # ---------- opportunities ----------
    med = {"Enterprise": 200000, "Mid-Market": 60000, "SMB": 14000}
    cf = {"Japan": 1.15, "Australia": 1.15, "India": 0.85}
    stage_w = {"Prospecting": 25, "Qualification": 25, "Discovery": 20, "Proposal": 17, "Negotiation": 13}
    opps = []
    oid = 1

    def mk(acc, name, stage, val, ocreated, close, olast, otype, is_open):
        nonlocal oid
        opps.append(dict(Opportunity_ID=f"OPP-{oid:06d}", Account_ID=acc, Opportunity_Name=name, Stage=stage,
                         Is_Open=int(is_open), Opportunity_Value=val, Opportunity_Type=otype,
                         Created_Date=ocreated, Expected_Close_Date=close, Last_Activity_Date=olast))
        oid += 1

    open_stage, open_value = {}, {}
    for i, r in base.iterrows():
        acc = r.Account_ID
        span_a = (r.Last_Activity_Date - r.Created_Date).days
        p_open = {"Customer": 0.40, "Prospect": 0.50}.get(r.CRM_Status, 0.0)
        if stale_flag[i]:
            p_open *= 0.6
        if rng.random() < p_open:
            stage = str(choice_w(stage_w))
            val = float(np.round(rng.lognormal(np.log(med[r.True_Tier] * cf.get(r.Country, 1.0)), 0.6) / 500) * 500)
            oc = r.Last_Activity_Date - D(int(rng.integers(0, min(365, span_a) + 1)))
            lag = int(rng.exponential(15)) + (int(rng.integers(90, 150)) if rng.random() < 0.07 else 0)
            ol = max(oc, r.Last_Activity_Date - D(lag))
            stale = (AS_OF - ol).days > STALE_OPP_DAYS
            close = AS_OF - D(int(rng.integers(5, 120))) if stale else AS_OF + D(int(rng.integers(10, 180)))
            otype = "Expansion" if r.CRM_Status == "Customer" else "New Business"
            mk(acc, f"{r.Company_Name.split(' ')[0] if not r.Company_Name.startswith('PT ') else r.Company_Name.split(' ')[1]} - {otype}",
               stage, val, oc, close, ol, otype, True)
            open_stage[acc], open_value[acc] = stage, val
        p_closed = {"Customer": 0.70, "Prospect": 0.20}.get(r.CRM_Status, 0.35)
        if span_a >= 31 and rng.random() < p_closed:
            for _ in range(1 + int(rng.random() < 0.35)):
                oc = r.Created_Date + D(int(rng.integers(0, span_a - 30 + 1)))
                cl = min(oc + D(int(rng.integers(20, 100))), r.Last_Activity_Date)
                won = r.CRM_Status in ("Customer", "Churned", "Inactive") and rng.random() < 0.8 or rng.random() < 0.15
                val = float(np.round(rng.lognormal(np.log(med[r.True_Tier]), 0.6) / 500) * 500)
                mk(acc, f"{r.Company_Name.split(' ')[0]} - " + ("Closed Won" if won else "Closed Lost"),
                   "Closed Won" if won else "Closed Lost", val, oc, cl, cl,
                   "New Business", False)
    opp = pd.DataFrame(opps)

    # ---------- CRM assignment (territory / tier / owner) with seeded misrouting ----------
    tier_crm = base.True_Tier.copy()
    drift = rng.random(n_base) < 0.02
    nxt = {"Enterprise": "Mid-Market", "SMB": "Mid-Market"}
    for i in np.where(drift)[0]:
        tier_crm[i] = nxt.get(tier_crm[i], str(rng.choice(["Enterprise", "SMB"])))
    inj["tier_drift"] = int(drift.sum())

    neigh = {"SEA": "ANZ", "ANZ": "SEA", "Korea": "Japan", "Japan": "Korea", "India": "SEA"}
    p_wrong = {"SEA": 0.025, "Korea": 0.020, "ANZ": 0.010, "Japan": 0.010, "India": 0.008}
    terr_crm = base.True_Territory.copy()
    wrong = np.array([rng.random() < p_wrong[t] for t in base.True_Territory])
    for i in np.where(wrong)[0]:
        terr_crm[i] = neigh[base.True_Territory[i]]
    inj["wrong_territory"] = int(wrong.sum())
    owner = [owner_for(t, tc) for t, tc in zip(terr_crm, tier_crm)]

    base["Account_Tier"] = tier_crm
    base["Sales_Territory"] = terr_crm
    base["Account_Owner"] = owner

    # ---------- duplicates (copies with messy variations, new IDs, no opportunities) ----------
    src = base.sample(n=n_dup, random_state=SEED).copy()
    dups = []
    for k, (_, r) in enumerate(src.iterrows()):
        d = r.copy()
        d["Account_ID"] = f"ACC-{ids[n_base + k]}"
        nm = r.Company_Name
        v = int(rng.integers(0, 4))
        d["Company_Name"] = [nm.upper(), nm.replace("Pvt Ltd", "Private Limited").replace("Pty Ltd", "Pty. Ltd."),
                             re.sub(r"\s+(Pvt Ltd|Pty Ltd|Pte Ltd|Ltd|K\.K\.|Co\., Ltd\.|Sdn Bhd|Inc\.|JSC)$", "", nm),
                             nm.replace(" ", "  ")][v]
        u = rng.random()
        if u < 0.50:
            d["Website_Domain"] = ("www." + r.Website_Domain) if rng.random() < 0.5 else r.Website_Domain.upper()
        elif u < 0.75:
            d["Website_Domain"] = None
        else:
            d["Website_Domain"] = r.Website_Domain.replace(".", "-group.", 1)
        d["Created_Date"] = min(r.Created_Date + D(int(rng.integers(30, 900))), AS_OF - D(5))
        d["Last_Activity_Date"] = max(d["Created_Date"], AS_OF - D(min(170, int(rng.exponential(30)))))
        d["Lead_Source"] = str(choice_w(LEAD_SOURCES))
        dups.append(d)
    dups = pd.DataFrame(dups)
    inj["duplicates"] = len(dups)

    acc = pd.concat([base, dups], ignore_index=True)
    acc["Opportunity_Stage"] = acc.Account_ID.map(open_stage)
    acc["Opportunity_Value"] = acc.Account_ID.map(open_value)
    n = len(acc)

    def pick(rate, mask=None):
        m = rng.random(n) < rate
        return m if mask is None else (m & mask)

    # ---------- inject CRM problems ----------
    m = pick(0.03)
    acc.loc[m, ["Country", "Region"]] = None
    keep_terr = m & (rng.random(n) < 0.5)
    acc.loc[m & ~keep_terr, "Sales_Territory"] = None
    inj["missing_country"] = int(m.sum())

    m2 = pick(0.015) & acc.Country.notna()
    acc.loc[m2, "Country"] = [str(rng.choice(COUNTRY_ALIAS_OUT[c])) if c in COUNTRY_ALIAS_OUT else c for c in acc.loc[m2, "Country"]]
    m3 = pick(0.004) & acc.Country.notna() & ~m2
    acc.loc[m3, "Country"] = [str(rng.choice(INVALID_COUNTRY_VALUES)) for _ in range(int(m3.sum()))]
    acc.loc[m3, "Region"] = None
    inj["country_alias"] = int(m2.sum()); inj["invalid_country"] = int(m3.sum())

    m = pick(0.02)
    acc.loc[m, "Employee_Count"] = np.nan
    acc.loc[m & (rng.random(n) < 0.4), "Account_Tier"] = None
    inj["missing_employee"] = int(m.sum())
    m = pick(0.02)
    acc.loc[m, "Annual_Revenue"] = np.nan
    inj["missing_revenue"] = int(m.sum())

    recent_india = ((acc.True_Territory == "India") & (pd.to_datetime(acc.Created_Date) >= pd.Timestamp("2026-04-01"))).values
    p_own = np.where(recent_india, 0.018 + 0.09, 0.018)
    m = rng.random(n) < p_own
    acc.loc[m, "Account_Owner"] = None
    inj["missing_owner"] = int(m.sum())

    m = pick(0.010) & acc.Sales_Territory.notna()
    acc.loc[m, "Sales_Territory"] = None
    m = pick(0.003) & acc.Sales_Territory.notna()
    acc.loc[m, "Sales_Territory"] = [str(rng.choice(INVALID_TERRITORY_VALUES)) for _ in range(int(m.sum()))]

    # domains: blank / malformed / messy-but-valid
    dm = acc.Website_Domain.notna()
    m = pick(0.012) & dm
    acc.loc[m, "Website_Domain"] = None
    m_bad = pick(0.013) & acc.Website_Domain.notna()
    bad = lambda d: str(rng.choice([d.split(".")[0], d.replace(".", " ", 1), "N/A", "tbd", d.replace(".", "..", 1)]))
    acc.loc[m_bad, "Website_Domain"] = [bad(d) for d in acc.loc[m_bad, "Website_Domain"]]
    m_mess = pick(0.03) & acc.Website_Domain.notna() & ~m_bad & ~acc.Website_Domain.str.contains("www.|HTTP", na=False)
    acc.loc[m_mess, "Website_Domain"] = [str(rng.choice(["https://www.", "http://", "WWW."])) + d + str(rng.choice(["", "/"]))
                                         for d in acc.loc[m_mess, "Website_Domain"]]
    inj["domain_blank_or_malformed"] = int(acc.Website_Domain.isna().sum() + m_bad.sum())

    hasopp = acc.Opportunity_Value.notna()
    m = (rng.random(n) < 0.015) & hasopp
    acc.loc[m, "Opportunity_Value"] = np.nan
    opp.loc[opp.Account_ID.isin(acc.loc[m, "Account_ID"]) & (opp.Is_Open == 1), "Opportunity_Value"] = np.nan
    inj["missing_opp_value"] = int(m.sum())

    # ---------- output ----------
    acc["Expected_Territory"] = ""; acc["Routing_Status"] = ""; acc["Data_Quality_Status"] = ""
    acc = acc.sample(frac=1, random_state=SEED).reset_index(drop=True)
    cols = ["Account_ID", "Company_Name", "Website_Domain", "Country", "Region", "Industry", "Employee_Count",
            "Annual_Revenue", "Account_Tier", "Sales_Territory", "Account_Owner", "Lead_Source", "Opportunity_Stage",
            "Opportunity_Value", "Last_Activity_Date", "Created_Date", "CRM_Status", "Expected_Territory",
            "Routing_Status", "Data_Quality_Status"]
    out = acc[cols].copy()
    out["Employee_Count"] = out.Employee_Count.astype("Int64")
    out = out.sort_values("Account_ID").reset_index(drop=True)
    out.to_csv(DATA / "accounts_raw.csv", index=False)

    opp = opp.sort_values("Opportunity_ID")
    opp.to_csv(DATA / "opportunities.csv", index=False)

    tm = pd.DataFrame([
        dict(Country=c, Country_Code=v[0], Territory=v[1], Region=v[2],
             Enterprise_Owner=owner_for(v[1], "Enterprise"), MidMarket_Owner=owner_for(v[1], "Mid-Market"),
             SMB_Owner=owner_for(v[1], "SMB")) for c, v in COUNTRIES.items()])
    tm.to_csv(DATA / "territory_mapping.csv", index=False)

    print(f"accounts_raw.csv: {len(out):,} rows | opportunities.csv: {len(opp):,} rows "
          f"({int(opp.Is_Open.sum()):,} open) | territory_mapping.csv: {len(tm)} rows")
    print("Injected problems (counts):")
    for k, v in inj.items():
        print(f"  {k:28s}{v:>6,}  ({v / n:.1%})")


if __name__ == "__main__":
    main()
