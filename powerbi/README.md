# Power BI Dashboard Guide

Power BI is the presentation layer. This guide takes you from the generated CSVs to a four-page report.
Power BI Desktop is free (Windows). **All data is synthetic.**

> I could not run Power BI Desktop while building this repo, so this guide has not been click-tested in Power BI.
> The expected values below come from the Python/SQL/Excel pipeline, which all agree - use them to check your report.

## 0. Prepare data
```bash
pip install -r requirements.txt
python python/run_all.py          # regenerates every CSV
```
Files used (in `data/`): `accounts_clean.csv`, `opportunities.csv`, `routing_exceptions.csv`, `dq_issues.csv`, `territory_mapping.csv`.

## 1. Load the data
1. Power BI Desktop > **Get data > Text/CSV**. Load each of the five files (no transformation needed; `Load`).
2. Rename the queries to short names: `accounts`, `opportunities`, `routing_exceptions`, `dq_issues`, `territory_mapping`.
3. Check data types (Transform data):

| Table | Column | Type |
|---|---|---|
| accounts | Last_Activity_Date, Created_Date | Date |
| accounts | Employee_Count, Days_Since_Activity, Is_*, Flag_*, DQ_Issue_Count, Record_DQ_Score | Whole number |
| accounts | Annual_Revenue, Opportunity_Value | Decimal |
| opportunities | Created_Date, Expected_Close_Date, Last_Activity_Date | Date |
| opportunities | Opportunity_Value | Decimal; Is_Open, Is_Stale_Opp = Whole number |
| routing_exceptions / dq_issues | Open_Pipeline_Value | Decimal |

4. View > Themes > Browse for themes > select `powerbi/apj_revops_theme.json`.

## 2. Data model (Model view)
| From (one side) | To (many side) | Cardinality | Filter direction |
|---|---|---|---|
| accounts[Account_ID] | opportunities[Account_ID] | 1:* | Single (accounts -> opportunities) |
| accounts[Account_ID] | routing_exceptions[Account_ID] | 1:* | Single |
| accounts[Account_ID] | dq_issues[Account_ID] | 1:* | Single |
| territory_mapping[Country] | accounts[Country] | 1:* | Single (optional) |

Because filters flow from `accounts` outwards, a slicer on any `accounts` column (Country, Industry, Expected_Territory,
Expected_Tier, Opportunity_Stage) filters pipeline, exceptions and issues consistently.

Add calculated columns:
```DAX
-- dq_issues
Severity Rank = SWITCH(dq_issues[Severity], "Critical", 1, "High", 2, "Medium", 3, "Low", 4)   -- then Sort by column: Severity -> Severity Rank
-- accounts
Reporting Territory = accounts[Expected_Territory]
Created Quarter = FORMAT(accounts[Created_Date], "YYYY") & " Q" & ROUNDUP(MONTH(accounts[Created_Date]) / 3, 0)
```
> Territory reporting uses **Expected_Territory** (where the account belongs per its country). Use *Sales_Territory* only on the routing page, to show the current state.

## 3. Measures
Create a table with *Enter data* named `_Measures` and add:
```DAX
Total Accounts          = COUNTROWS(accounts)
Total Pipeline          = CALCULATE(SUM(opportunities[Opportunity_Value]), opportunities[Is_Open] = 1)
Avg Opportunity Value   = CALCULATE(AVERAGE(opportunities[Opportunity_Value]), opportunities[Is_Open] = 1)
Enterprise Pipeline     = CALCULATE([Total Pipeline], accounts[Expected_Tier] = "Enterprise")
Enterprise Pipeline %   = DIVIDE([Enterprise Pipeline], [Total Pipeline])
Stale Pipeline          = CALCULATE(SUM(opportunities[Opportunity_Value]), opportunities[Is_Stale_Opp] = 1)

Covered Accounts        = CALCULATE([Total Accounts], accounts[Is_Covered] = 1)
Territory Coverage %    = DIVIDE([Covered Accounts], [Total Accounts])

Correctly Routed        = CALCULATE([Total Accounts], accounts[Routing_Status] = "Correctly Routed")
Incorrectly Routed      = CALCULATE([Total Accounts], accounts[Routing_Status] = "Incorrectly Routed")
Unassigned Accounts     = CALCULATE([Total Accounts], accounts[Routing_Status] = "Unassigned")
Total Routable Accounts = [Correctly Routed] + [Incorrectly Routed] + [Unassigned Accounts]
Routing Accuracy %      = DIVIDE([Correctly Routed], [Total Routable Accounts])
Open Exceptions         = CALCULATE(COUNTROWS(routing_exceptions), routing_exceptions[Is_Open] = 1)

Data Quality %          = DIVIDE(AVERAGE(accounts[Record_DQ_Score]), 100)
Clean Record Rate %     = DIVIDE(CALCULATE([Total Accounts], accounts[Data_Quality_Status] = "Good"), [Total Accounts])
Duplicate Accounts      = SUM(accounts[Is_Duplicate])
Missing Country         = SUM(accounts[Flag_Missing_Country])
Missing Revenue         = SUM(accounts[Flag_Missing_Revenue])
Missing Owner           = SUM(accounts[Flag_Missing_Owner])
Stale Accounts          = SUM(accounts[Flag_Stale])
Invalid Territory       = SUM(accounts[Flag_Invalid_Territory])
```
Format: `%` measures as Percentage (1 decimal); `Total Pipeline` as Currency ($, 0 or 1 decimal, display units Millions).

**Reconciliation check (no filters):** Total Accounts 5,000 | Total Pipeline $97.3M | Territory Coverage 94.9% | Routing Accuracy 94.7% |
Data Quality 94.7% | Open Exceptions 536 | Duplicate Accounts 97 | Missing Country 150 | Missing Owner 104 | Stale Accounts 137.

## 4. Pages

Canvas 16:9. Title bar (navy `#1F3864`, white text), page navigator with the four pages. Sync the slicers across pages
(View > Sync slicers) for Country, Territory and Account Tier.

### Page 1 - Executive Overview
| Visual | Fields |
|---|---|
| 6 x **Card** | Total Accounts, Total Pipeline, Territory Coverage %, Routing Accuracy %, Data Quality %, Open Exceptions |
| **Clustered bar** - Pipeline by Territory | Y: accounts[Expected_Territory]; X: [Total Pipeline]; data labels on |
| **Bar** - Accounts by Country | Y: accounts[Country]; X: [Total Accounts]; sort descending (blank = missing country) |
| **Funnel / column** - Pipeline by Stage | Axis: opportunities[Stage]; Values: [Total Pipeline]; visual filter `Is_Open = 1` (open stages only); sort by stage order |
| **Donut or column** - Accounts by Tier | Legend: accounts[Expected_Tier]; Values: [Total Accounts] |
| **Slicers** | Expected_Territory (tile), Industry (dropdown), Expected_Tier (tile) |
Card tips: turn the *category label* on, colour Routing Accuracy / Coverage / DQ with conditional formatting (green >= 95%, amber 90-95%, red < 90%) using *Format > Callout value > fx > Rules*.

### Page 2 - Territory Performance
| Visual | Fields |
|---|---|
| **Clustered column** Accounts by Territory | Axis Expected_Territory; Values [Total Accounts] |
| **Clustered column** Pipeline by Territory | Axis Expected_Territory; Values [Total Pipeline] |
| **Bar** Pipeline by Country | Axis Country; Values [Total Pipeline] |
| **Bar** Accounts by Country | Axis Country; Values [Total Accounts] |
| **Clustered column / gauge** Territory Coverage % | Axis Expected_Territory; Values [Territory Coverage %]; constant line at 95% (Analytics pane) |
| **Stacked column** Exceptions by Territory | Axis Expected_Territory; Legend routing_exceptions[Exception_Type]; Values [Open Exceptions] |
| **Slicers** | Country, Expected_Territory, Industry, Expected_Tier, Opportunity_Stage (accounts[Opportunity_Stage]) |
| **Matrix** (optional) | Rows Expected_Territory; Columns Expected_Tier; Values [Total Accounts] with a blue colour scale |
Add a small **line chart** of `[Territory Coverage %]` by `Created Quarter` filtered to India to show the new-account coverage dip (see `documentation/stakeholder_analysis.md`, Scenario 1).

### Page 3 - CRM Data Quality
| Visual | Fields |
|---|---|
| 6 x **Card** | Duplicate Accounts, Missing Country, Missing Revenue, Missing Owner, Stale Accounts, Invalid Territory |
| **Gauge / large card** | Data Quality % (target 98%, min 0, max 100) |
| **Bar** Issues by type | dq_issues[Issue_Type] by count of Account_ID, legend Severity |
| **Column** DQ score by territory | Axis Expected_Territory; Values [Data Quality %] |
| **Table** Exception list | dq_issues: Account_ID, Company_Name, Issue_Type, Severity, Recommended_Action (sort by Severity Rank) |
| **Slicers** | Severity, Issue_Type, Territory |
**Conditional formatting (table):** Severity column > Cell elements > Background colour > *Rules*: Critical `#F8CBAD`, High `#FCE4D6`,
Medium `#FFF2CC`, Low `#E2EFDA`. Add data bars on `Open_Pipeline_Value` if you include it.

### Page 4 - Routing & Exceptions
| Visual | Fields |
|---|---|
| 5 x **Card** | Total Routable Accounts, Correctly Routed, Incorrectly Routed, Unassigned Accounts, Routing Accuracy % |
| **Matrix (heat map)** Current vs Expected | Rows routing_exceptions[Current_Territory]; Columns routing_exceptions[Expected_Territory]; Values [Open Exceptions]; background colour scale (white -> red). Off-diagonal cells = misrouted flows |
| **Stacked bar** Exceptions by territory | Axis Expected_Territory; Legend Exception_Type; Values [Open Exceptions] |
| **Table** Exception work-queue | Account (Company_Name), Current_Territory, Expected_Territory, Current_Owner, Expected_Owner, Exception_Type, Priority, Resolution_Status |
| **Slicers** | Exception_Type, Priority, Resolution_Status, Expected_Territory |
Priority colouring: High red, Medium amber, Low green (same rules approach as page 3).

## 5. Refresh
Re-run `python python/run_all.py`, then **Home > Refresh** in Power BI. The CSV paths are absolute on your machine; if you move the repo,
use *Transform data > Data source settings > Change source*.

## 6. Publishing to GitHub
Save the report as `powerbi/APJ_RevOps_Dashboard.pbix` (optional - fine to omit if > 100 MB; this one is small) and add screenshots of
each page to `screenshots/` (see `screenshots/README.md`).
