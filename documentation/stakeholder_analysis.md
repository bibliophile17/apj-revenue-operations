# Stakeholder Analysis

> **Synthetic data.** Every figure below is calculated by `python/generate_insights.py` from the generated dataset (seed 20260930, as-of 2026-09-30). Re-running the pipeline regenerates this file. Some patterns (India owner vacancy on recent accounts, Japan stale rate, SEA/Korea misrouting) were deliberately seeded in the generator to create realistic analysis targets - see README > Synthetic Dataset.

## Headline metrics

| Metric | Value |
|---|---|
| Total CRM accounts | 5,000 |
| Open pipeline | $97.3M |
| Enterprise share of pipeline | 31.2% |
| Territory coverage | 94.9% |
| Routing accuracy | 94.7% |
| Data Quality Score | 94.7% |
| Clean record rate | 79.7% |
| Open routing exceptions | 536 |

## Business insights (calculated from the data)

1. **SEA holds the largest open pipeline** at $31.8M (32.6% of $97.3M); ANZ is next at $22.0M.
2. **Japan has the weakest data quality** - score 95.8% and only 80.6% clean records (best: Korea at 97.0% / 84.0%).
3. **SEA has the most routing exceptions** (124), but the highest *rate* is India at 9.9 exceptions per 100 accounts.
4. **12 of 329 Enterprise accounts are unassigned** (no owner and/or territory), exposing $0.7M of open Enterprise pipeline.
5. **Enterprise accounts generate 31.2% of open pipeline** while being 6.6% of accounts - ownership gaps on this tier are disproportionately costly.
6. **Japan has the largest stale-account problem**: 5.7% of its accounts have had no activity for >180 days (portfolio average 2.7%).
7. **$5.3M of open pipeline (5.5%) sits on accounts with no valid owner/territory**, and $11.1M (11.4%) sits on accounts rated Critical or Needs Review.
8. **286 open opportunities (15.1%) are stale** (>90 days without activity), holding $16.4M (16.8%) of pipeline - forecast risk.

## Scenario 1 - "Why has India territory coverage declined?"

**Finding.** India coverage on accounts created since 2026-04-01 is **88.0%** versus **96.3%** for older accounts (overall India: 95.5%). The gap is concentrated in newly created accounts.

**Evidence.** India coverage by account-creation quarter:

| Created quarter | Accounts | No owner | Coverage % |
|---|---|---|---|
| 2025Q1 | 38 | 1 | 94.7 |
| 2025Q2 | 58 | 1 | 96.6 |
| 2025Q3 | 47 | 0 | 100.0 |
| 2025Q4 | 52 | 1 | 98.1 |
| 2026Q1 | 46 | 1 | 93.5 |
| 2026Q2 | 54 | 7 | 87.0 |
| 2026Q3 | 46 | 5 | 89.1 |


India accounts created since April 2026 by tier (accounts without an owner):

| Tier | Accounts | No owner |
|---|---|---|
| Enterprise | 8 | 1 |
| Mid-Market | 27 | 1 |
| SMB | 64 | 10 |
| Unknown | 1 | 0 |


Uncovered India accounts: 47, of which 25.5% were created since April 2026; open pipeline on uncovered India accounts: $0.3M. For comparison, coverage on newer vs older accounts in other territories: ANZ 94.0% vs 97.0%; SEA 97.0% vs 96.6%; Japan 97.4% vs 95.0%; Korea 98.0% vs 97.4%.

**Likely cause.** New India accounts are being created without owner assignment (12 of 100 since April 2026; 10 of those are SMB, i.e. the India Commercial queue) - consistent with a rep vacancy or a broken assignment rule for new records rather than decay of the legacy book. (Hypothesis: validate against HR/territory-change logs.)

**Recommended action.** (1) Bulk-assign the uncovered India accounts using `Expected_Owner` (Enterprise to Priya Sharma, Commercial to Arjun Mehta), enterprise and pipeline-bearing first; (2) add a CRM validation/assignment rule so new India accounts cannot save without an owner; (3) add India new-account coverage to the weekly dashboard with a 48-hour SLA.

## Scenario 2 - "Which territories have the largest account-routing problems?"

**Finding.** Exceptions by territory (country-derived, excludes accounts with no usable country):

| Territory | Accounts | Exceptions | Per 100 accounts |
|---|---|---|---|
| SEA | 1696 | 124 | 7.3 |
| India | 1056 | 105 | 9.9 |
| ANZ | 948 | 62 | 6.5 |
| Japan | 702 | 53 | 7.5 |
| Korea | 432 | 26 | 6.0 |


Portfolio routing accuracy is **94.7%** on 4,715 routable accounts; a further 162 accounts are ambiguous (country missing/invalid) and 123 need manual review (duplicates, missing India headcount).

**Evidence.** Exception types by territory:

| Expected_Territory | Duplicate Account | Invalid Territory Value | Missing Employee Count | No Owner | No Territory | Owner Mismatch | Territory Mismatch |
|---|---|---|---|---|---|---|---|
| ANZ | 19 | 3 | 0 | 17 | 11 | 0 | 12 |
| India | 16 | 2 | 26 | 24 | 20 | 6 | 11 |
| Japan | 16 | 2 | 0 | 18 | 13 | 0 | 4 |
| Korea | 8 | 2 | 0 | 7 | 2 | 0 | 7 |
| SEA | 34 | 6 | 0 | 33 | 16 | 0 | 35 |


Largest territory-mismatch flows (current CRM territory -> where the country says it belongs):

| Current territory | Expected territory | Accounts |
|---|---|---|
| ANZ | SEA | 35 |
| SEA | ANZ | 12 |
| SEA | India | 11 |
| Japan | Korea | 7 |
| Korea | Japan | 4 |
| TBD-Unassigned | SEA | 3 |


**Likely cause.** Mismatches are dominated by ANZ->SEA (35) and SEA->ANZ (12) neighbour-region moves (manual territory edits or legacy regional alignment). Unassigned records (161: no owner and/or no territory) are a larger group than territory mismatches (84).

**Recommended action.** Auto-derive Sales_Territory from Country on create/update (remove manual edit), run the router weekly, and clear High-priority exceptions (Enterprise or >=$100K pipeline) first.

## Scenario 3 - "What CRM data-quality issues should we prioritise?"

**Finding.** Issues ranked by impact on the Data Quality Score (severity penalty x accounts affected):

| rank | Issue | Severity | Accounts | % of total score loss | Pipeline exposed |
|---|---|---|---|---|---|
| 1 | Missing Country | Critical | 150 | 22.6 | $3.3M |
| 2 | Missing Owner | Critical | 104 | 15.6 | $1.2M |
| 3 | Duplicate Account | Critical | 97 | 14.6 | $0.0M |
| 4 | Missing Territory | High | 138 | 13.0 | $3.8M |
| 5 | Invalid Territory | High | 87 | 8.2 | $1.6M |
| 6 | Stale Account | High/Medium | 137 | 7.4 | $2.6M |
| 7 | Missing Employee Count | High/Medium | 89 | 4.8 | $2.0M |
| 8 | Tier Mismatch | Medium | 105 | 3.9 | $2.7M |
| 9 | Missing Annual Revenue | Medium | 99 | 3.7 | $2.1M |
| 10 | Invalid Domain | Low | 135 | 2.5 | $2.8M |
| 11 | Invalid Country | Critical | 16 | 2.4 | $0.7M |
| 12 | Missing Opportunity Info | Medium | 34 | 1.3 | $0.0M |


**Likely cause.** The top three (Missing Country, Missing Owner, Duplicate Account) are all upstream entry/enrichment problems - missing required fields at record creation and no duplicate check - rather than data decay.

**Recommended action.** Prioritise in this order: (1) make Country and Owner required on create and enrich missing countries (unblocks routing); (2) merge duplicates monthly via the Master_Account_ID list; (3) run a stale-account sweep that routes pipeline-bearing stale accounts to their owners; (4) batch-enrich firmographics (employee count, revenue); (5) low-severity domain clean-up last (but it feeds duplicate detection).
