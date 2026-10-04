"""Compute business insights + stakeholder scenarios from the generated data and write
documentation/stakeholder_analysis.md.  Every number in that file is calculated here."""
import pandas as pd
from config import *


def md(df, index=False):
    df = df.reset_index() if index else df
    head = "| " + " | ".join(map(str, df.columns)) + " |\n|" + "|".join(["---"] * len(df.columns)) + "|\n"
    rows = "\n".join("| " + " | ".join(str(v) for v in r) + " |" for r in df.itertuples(index=False))
    return head + rows + "\n"


M = lambda x: f"${x / 1e6:,.1f}M"
P = lambda x: f"{x:.1f}%"


def main():
    a = pd.read_csv(DATA / "accounts_clean.csv")
    o = pd.read_csv(DATA / "opportunities.csv")
    iss = pd.read_csv(DATA / "dq_issues.csv")
    op = o[o.Is_Open == 1].merge(a[["Account_ID", "Country", "Expected_Territory", "Expected_Tier", "Is_Covered",
                                    "Data_Quality_Status", "Routing_Status", "Account_Owner"]], on="Account_ID")
    N = len(a)
    pipe_total = op.Opportunity_Value.sum()
    routable = a.Routing_Status.isin(["Correctly Routed", "Incorrectly Routed", "Unassigned"])
    acc = 100 * (a.Routing_Status == "Correctly Routed").sum() / routable.sum()
    dq = a.Record_DQ_Score.mean()
    clean = 100 * (a.Data_Quality_Status == "Good").mean()
    cov = 100 * a.Is_Covered.mean()

    terr = a[a.Expected_Territory != "Unknown"]
    pt = op.groupby("Expected_Territory").Opportunity_Value.sum().sort_values(ascending=False)
    top_t = pt.index[0]
    dqt = terr.groupby("Expected_Territory").agg(accounts=("Account_ID", "count"), dq_score=("Record_DQ_Score", "mean"),
            clean_pct=("Data_Quality_Status", lambda s: 100 * (s == "Good").mean())).sort_values("dq_score")
    worst_dq = dqt.index[0]
    ex = a[a.Routing_Status != "Correctly Routed"]
    ext = terr.assign(is_ex=(terr.Routing_Status != "Correctly Routed")).groupby("Expected_Territory").agg(
        accounts=("Account_ID", "count"), exceptions=("is_ex", "sum"))
    ext["per_100"] = (100 * ext.exceptions / ext.accounts).round(1)
    ext = ext.sort_values("exceptions", ascending=False)
    ent = a[a.Expected_Tier == "Enterprise"]
    ent_un = ent[ent.Routing_Status == "Unassigned"]
    ent_un_pipe = op[(op.Expected_Tier == "Enterprise") & (op.Routing_Status == "Unassigned")].Opportunity_Value.sum()
    ent_share = 100 * op[op.Expected_Tier == "Enterprise"].Opportunity_Value.sum() / pipe_total
    stale_c = a[a.Country.isin(COUNTRIES)].groupby("Country").agg(n=("Account_ID", "count"), stale=("Flag_Stale", "sum"))
    stale_c["pct"] = (100 * stale_c.stale / stale_c.n).round(2)
    stale_c = stale_c.sort_values("pct", ascending=False)
    unc_pipe = op[op.Is_Covered == 0].Opportunity_Value.sum()
    crit_pipe = op[op.Data_Quality_Status.isin(["Critical", "Needs Review"])].Opportunity_Value.sum()
    stale_opp = o[(o.Is_Open == 1) & (o.Is_Stale_Opp == 1)]
    stale_opp_pipe = stale_opp.Opportunity_Value.sum()

    # ---- Scenario 1: India coverage ----
    ind = a[a.Expected_Territory == "India"].copy()
    ind["cohort"] = pd.to_datetime(ind.Created_Date).dt.to_period("Q").astype(str)
    q = ind.groupby("cohort").agg(accounts=("Account_ID", "count"), no_owner=("Flag_Missing_Owner", "sum"),
                                  coverage=("Is_Covered", lambda s: round(100 * s.mean(), 1)))
    q = q[q.index >= "2025Q1"]
    cut = pd.Timestamp("2026-04-01")
    def cohort_cov(df):
        d = pd.to_datetime(df.Created_Date) >= cut
        return round(100 * df[~d].Is_Covered.mean(), 1), round(100 * df[d].Is_Covered.mean(), 1), int(d.sum())
    c_old, c_new, n_new = cohort_cov(ind)
    other = {t: cohort_cov(terr[terr.Expected_Territory == t]) for t in TERRITORIES}
    ind_new = ind[pd.to_datetime(ind.Created_Date) >= cut]
    ind_new_tier = ind_new.groupby("Expected_Tier").agg(accounts=("Account_ID", "count"), no_owner=("Flag_Missing_Owner", "sum"))
    ind_unc = ind[ind.Is_Covered == 0]
    ind_unc_pipe = op[(op.Expected_Territory == "India") & (op.Is_Covered == 0)].Opportunity_Value.sum()
    ind_unc_new_share = 100 * (pd.to_datetime(ind_unc.Created_Date) >= cut).mean()

    # ---- Scenario 2: routing flows ----
    flows = a[a.Exception_Type.isin(["Territory Mismatch", "Invalid Territory Value"])].groupby(
        ["Sales_Territory", "Expected_Territory"]).size().reset_index(name="accounts").sort_values("accounts", ascending=False).head(6)
    types_by_t = pd.crosstab(terr.Expected_Territory, terr.Exception_Type.fillna("—")).drop(columns="—", errors="ignore")

    # ---- Scenario 3: issue ranking ----
    r = iss.groupby(["Issue_Type"]).agg(accounts=("Account_ID", "nunique"), penalty=("Penalty", "sum"),
                                        pipeline=("Open_Pipeline_Value", "sum"),
                                        severity=("Severity", lambda s: "/".join(sorted(set(s), key=["Critical", "High", "Medium", "Low"].index)))).reset_index()
    r["share_of_score_loss_pct"] = (100 * r.penalty / r.penalty.sum()).round(1)
    r = r.sort_values("penalty", ascending=False).reset_index(drop=True)
    r.insert(0, "rank", range(1, len(r) + 1))
    r["pipeline"] = r.pipeline.map(M)

    L = []
    L.append("# Stakeholder Analysis\n")
    L.append("> **Synthetic data.** Every figure below is calculated by `python/generate_insights.py` from the generated "
             f"dataset (seed {SEED}, as-of {AS_OF}). Re-running the pipeline regenerates this file. "
             "Some patterns (India owner vacancy on recent accounts, Japan stale rate, SEA/Korea misrouting) were "
             "deliberately seeded in the generator to create realistic analysis targets - see README > Synthetic Dataset.\n")
    L.append("## Headline metrics\n")
    L.append(md(pd.DataFrame({"Metric": ["Total CRM accounts", "Open pipeline", "Enterprise share of pipeline", "Territory coverage",
                                         "Routing accuracy", "Data Quality Score", "Clean record rate", "Open routing exceptions"],
                              "Value": [f"{N:,}", M(pipe_total), P(ent_share), P(cov), P(acc), P(dq), P(clean), f"{len(ex):,}"]})))
    L.append("## Business insights (calculated from the data)\n")
    L.append(f"1. **{top_t} holds the largest open pipeline** at {M(pt.iloc[0])} ({P(100 * pt.iloc[0] / pipe_total)} of {M(pipe_total)}); "
             f"{pt.index[1]} is next at {M(pt.iloc[1])}.")
    L.append(f"2. **{worst_dq} has the weakest data quality** - score {dqt.dq_score.iloc[0]:.1f}% and only {dqt.clean_pct.iloc[0]:.1f}% clean records "
             f"(best: {dqt.index[-1]} at {dqt.dq_score.iloc[-1]:.1f}% / {dqt.clean_pct.iloc[-1]:.1f}%).")
    L.append(f"3. **{ext.index[0]} has the most routing exceptions** ({int(ext.exceptions.iloc[0])}), but the highest *rate* is "
             f"{ext.per_100.idxmax()} at {ext.per_100.max():.1f} exceptions per 100 accounts.")
    L.append(f"4. **{len(ent_un)} of {len(ent)} Enterprise accounts are unassigned** (no owner and/or territory), exposing {M(ent_un_pipe)} of open Enterprise pipeline.")
    L.append(f"5. **Enterprise accounts generate {P(ent_share)} of open pipeline** while being {P(100 * len(ent) / N)} of accounts - "
             "ownership gaps on this tier are disproportionately costly.")
    L.append(f"6. **{stale_c.index[0]} has the largest stale-account problem**: {stale_c.pct.iloc[0]}% of its accounts have had no activity for >{STALE_ACCOUNT_DAYS} days "
             f"(portfolio average {P(100 * a.Flag_Stale.mean())}).")
    L.append(f"7. **{M(unc_pipe)} of open pipeline ({P(100 * unc_pipe / pipe_total)}) sits on accounts with no valid owner/territory**, "
             f"and {M(crit_pipe)} ({P(100 * crit_pipe / pipe_total)}) sits on accounts rated Critical or Needs Review.")
    L.append(f"8. **{len(stale_opp)} open opportunities ({P(100 * len(stale_opp) / len(op))}) are stale** (>{STALE_OPP_DAYS} days without activity), "
             f"holding {M(stale_opp_pipe)} ({P(100 * stale_opp_pipe / pipe_total)}) of pipeline - forecast risk.\n")

    L.append("## Scenario 1 - \"Why has India territory coverage declined?\"\n")
    L.append(f"**Finding.** India coverage on accounts created since 2026-04-01 is **{c_new}%** versus **{c_old}%** for older accounts "
             f"(overall India: {round(100 * ind.Is_Covered.mean(), 1)}%). The gap is concentrated in newly created accounts.\n")
    L.append("**Evidence.** India coverage by account-creation quarter:\n")
    L.append(md(q.reset_index().rename(columns={"cohort": "Created quarter", "accounts": "Accounts", "no_owner": "No owner", "coverage": "Coverage %"})))
    L.append(f"\nIndia accounts created since April 2026 by tier (accounts without an owner):\n")
    L.append(md(ind_new_tier.reset_index().rename(columns={"Expected_Tier": "Tier", "accounts": "Accounts", "no_owner": "No owner"})))
    L.append(f"\nUncovered India accounts: {len(ind_unc)}, of which {P(ind_unc_new_share)} were created since April 2026; open pipeline on uncovered India accounts: {M(ind_unc_pipe)}. "
             "For comparison, coverage on newer vs older accounts in other territories: " +
             "; ".join(f"{t} {other[t][1]}% vs {other[t][0]}%" for t in TERRITORIES if t != "India") + ".\n")
    smb_no = int(ind_new_tier.loc["SMB", "no_owner"]) if "SMB" in ind_new_tier.index else 0
    tot_no = int(ind_new_tier.no_owner.sum())
    L.append(f"**Likely cause.** New India accounts are being created without owner assignment ({tot_no} of {len(ind_new)} since April 2026; {smb_no} of those are SMB, "
             "i.e. the India Commercial queue) - consistent with a rep vacancy or a broken assignment rule for new records rather than decay of the legacy book. "
             "(Hypothesis: validate against HR/territory-change logs.)\n")
    L.append("**Recommended action.** (1) Bulk-assign the uncovered India accounts using `Expected_Owner` (Enterprise to Priya Sharma, Commercial to Arjun Mehta), "
             "enterprise and pipeline-bearing first; (2) add a CRM validation/assignment rule so new India accounts cannot save without an owner; "
             "(3) add India new-account coverage to the weekly dashboard with a 48-hour SLA.\n")

    L.append("## Scenario 2 - \"Which territories have the largest account-routing problems?\"\n")
    L.append("**Finding.** Exceptions by territory (country-derived, excludes accounts with no usable country):\n")
    L.append(md(ext.reset_index().rename(columns={"Expected_Territory": "Territory", "accounts": "Accounts", "exceptions": "Exceptions", "per_100": "Per 100 accounts"})))
    L.append(f"\nPortfolio routing accuracy is **{P(acc)}** on {int(routable.sum()):,} routable accounts; a further {int((a.Routing_Status == 'Ambiguous').sum())} accounts "
             f"are ambiguous (country missing/invalid) and {int((a.Routing_Status == 'Manual Review').sum())} need manual review (duplicates, missing India headcount).\n")
    L.append("**Evidence.** Exception types by territory:\n")
    L.append(md(types_by_t, index=True))
    L.append("\nLargest territory-mismatch flows (current CRM territory -> where the country says it belongs):\n")
    L.append(md(flows.rename(columns={"Sales_Territory": "Current territory", "Expected_Territory": "Expected territory", "accounts": "Accounts"})))
    f1, f2 = flows.iloc[0], flows.iloc[1]
    n_un = int(a.Routing_Status.eq("Unassigned").sum()); n_mis = int(a.Exception_Type.isin(["Territory Mismatch", "Invalid Territory Value"]).sum())
    L.append(f"\n**Likely cause.** Mismatches are dominated by {f1.Sales_Territory}->{f1.Expected_Territory} ({f1.accounts}) and {f2.Sales_Territory}->{f2.Expected_Territory} ({f2.accounts}) "
             f"neighbour-region moves (manual territory edits or legacy regional alignment). Unassigned records ({n_un}: no owner and/or no territory) are a larger group than territory mismatches ({n_mis}).\n")
    L.append("**Recommended action.** Auto-derive Sales_Territory from Country on create/update (remove manual edit), run the router weekly, "
             "and clear High-priority exceptions (Enterprise or >=$100K pipeline) first.\n")

    L.append("## Scenario 3 - \"What CRM data-quality issues should we prioritise?\"\n")
    L.append("**Finding.** Issues ranked by impact on the Data Quality Score (severity penalty x accounts affected):\n")
    L.append(md(r[["rank", "Issue_Type", "severity", "accounts", "share_of_score_loss_pct", "pipeline"]].rename(
        columns={"Issue_Type": "Issue", "severity": "Severity", "accounts": "Accounts", "share_of_score_loss_pct": "% of total score loss", "pipeline": "Pipeline exposed"})))
    top3 = ", ".join(r.Issue_Type.head(3))
    L.append(f"\n**Likely cause.** The top three ({top3}) are all upstream entry/enrichment problems - missing required fields at record creation and no duplicate "
             "check - rather than data decay.\n")
    L.append("**Recommended action.** Prioritise in this order: (1) make Country and Owner required on create and enrich missing countries (unblocks routing); "
             "(2) merge duplicates monthly via the Master_Account_ID list; (3) run a stale-account sweep that routes pipeline-bearing stale accounts to their owners; "
             "(4) batch-enrich firmographics (employee count, revenue); (5) low-severity domain clean-up last (but it feeds duplicate detection).\n")
    (DOCS / "stakeholder_analysis.md").write_text("\n".join(L))
    print("wrote documentation/stakeholder_analysis.md")


if __name__ == "__main__":
    main()
