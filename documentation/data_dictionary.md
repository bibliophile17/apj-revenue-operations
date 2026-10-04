# Data Dictionary

> **Synthetic data only.** Companies, people and values are fictional. Regenerate with `python python/run_all.py` (fixed seed).

## accounts_raw.csv / accounts_clean.csv
`accounts_raw.csv` holds the first 20 fields as exported (calculated fields blank). `accounts_clean.csv` is standardised and adds the calculated fields. One row per CRM account record (duplicates included).

| Field | Description | Data type | Example | Required? | Business purpose |
|---|---|---|---|---|---|
| Account_ID | Unique CRM account key | Text | ACC-100001 | Yes | Join key across all tables |
| Company_Name | Fictional legal/trading name | Text | Tainousi Partners Ltd | Yes | Identification; duplicate matching |
| Website_Domain | Normalised web domain (lower-case, no scheme/www) | Text | tainousipartners.co.nz | Recommended | Duplicate matching; enrichment key |
| Country | APJ country (aliases standardised in clean data) | Text | New Zealand | Yes | Drives territory; blank/invalid blocks routing |
| Region | APJ sub-region (South Asia, Oceania, Southeast Asia, North Asia) | Text | Oceania | Yes | Regional rollups |
| Industry | One of 10 industries | Text | Healthcare | Yes | Segmentation and slicing |
| Employee_Count | Headcount | Integer | 234 | Yes | Determines tier (and India owner) |
| Annual_Revenue | Annual revenue, USD | Decimal | 19392000 | Recommended | Account sizing / prioritisation |
| Account_Tier | Tier as currently stored in CRM | Text | SMB | Yes | Compared with Expected_Tier to find tier drift |
| Sales_Territory | Territory currently assigned in CRM (India, ANZ, SEA, Japan, Korea) | Text | ANZ | Yes | Current state for routing validation |
| Account_Owner | Sales rep currently assigned (fictional) | Text | James Wilson | Yes | Current ownership; blank = uncovered |
| Lead_Source | How the account entered CRM | Text | Inbound Web | No | Source-quality analysis |
| Opportunity_Stage | Stage of the account's open opportunity (max one open opp per account); blank if none | Text | Discovery | No | Pipeline slicing |
| Opportunity_Value | Value of the open opportunity, USD; blank if none or missing | Decimal | 58500 | No | Pipeline reporting |
| Last_Activity_Date | Date of last logged activity | Date | 2026-09-12 | Yes | Stale-account detection |
| Created_Date | Date the record was created | Date | 2023-04-18 | Yes | Cohort analysis; duplicate master selection |
| CRM_Status | Customer, Prospect, Inactive or Churned | Text | Prospect | Yes | Lifecycle context |
| Expected_Territory | Territory derived from Country (`Unknown` if no valid country). Blank in raw export | Text | ANZ | Calculated | Reporting territory; routing comparison |
| Routing_Status | Correctly Routed / Incorrectly Routed / Unassigned / Ambiguous / Manual Review. Blank in raw | Text | Correctly Routed | Calculated | Routing accuracy and exception work-queue |
| Data_Quality_Status | Good / Warning / Needs Review / Critical (worst severity on the record). Blank in raw | Text | Warning | Calculated | Record-level hygiene status |
| Is_Duplicate | 1 if the record is a non-master duplicate | Integer 0/1 | 0 | Calculated | Duplicate management |
| Master_Account_ID | ACC ID of the surviving master record | Text | ACC-102840 | Calculated (duplicates only) | Merge target |
| Days_Since_Activity | As-of date (2026-09-30) minus Last_Activity_Date | Integer | 14 | Calculated | Ageing; stale test |
| Expected_Tier | Tier from Employee_Count (Enterprise/Mid-Market/SMB/Unknown) | Text | SMB | Calculated | Segmentation; India owner |
| Expected_Owner | Owner per territory + tier rules; null when not determinable | Text | James Wilson | Calculated | Target state for reassignment |
| Exception_Type | Reason a record is not Correctly Routed; null when correct | Text | Territory Mismatch | Calculated | Exception classification |
| Is_Covered | 1 if owner present and Sales_Territory valid | Integer 0/1 | 1 | Calculated | Territory Coverage % |
| Flag_Missing_Country | 1 if Country blank | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Invalid_Country | 1 if Country not an APJ country after standardising | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Missing_Employee | 1 if Employee_Count blank | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Missing_Revenue | 1 if Annual_Revenue blank | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Missing_Owner | 1 if Account_Owner blank | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Missing_Territory | 1 if Sales_Territory blank | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Invalid_Territory | 1 if territory is not valid or differs from the country mapping | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Stale | 1 if Days_Since_Activity > 180 | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Invalid_Domain | 1 if domain blank or fails the domain pattern | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Missing_Opp_Info | 1 if stage without value (or value without stage) | Integer 0/1 | 0 | Calculated | DQ check |
| Flag_Tier_Mismatch | 1 if CRM Account_Tier differs from Expected_Tier | Integer 0/1 | 0 | Calculated | DQ check |
| DQ_Issue_Count | Number of issues on the record | Integer | 2 | Calculated | Record complexity |
| DQ_Issues | Semicolon-separated issue names | Text | Stale Account; Invalid Domain | Calculated | Readable issue summary |
| Record_DQ_Score | 100 minus penalties (Critical 40, High 25, Medium 10, Low 5), floor 0 | Integer | 85 | Calculated | Averaged into Data Quality Score % |

## opportunities.csv
One row per opportunity (open and closed). Max one open opportunity per account.

| Field | Description | Data type | Example | Required? | Business purpose |
|---|---|---|---|---|---|
| Opportunity_ID | Unique opportunity key | Text | OPP-000123 | Yes | Primary key |
| Account_ID | Parent account | Text | ACC-100001 | Yes | Join to accounts |
| Opportunity_Name | Descriptive name | Text | Veltrix - Expansion | Yes | Readability |
| Stage | Prospecting, Qualification, Discovery, Proposal, Negotiation, Closed Won, Closed Lost | Text | Proposal | Yes | Funnel analysis |
| Is_Open | 1 if stage is an open stage | Integer 0/1 | 1 | Yes | Pipeline filter |
| Opportunity_Value | Value in USD (blank = missing value injected as a DQ problem) | Decimal | 60000 | Recommended | Pipeline measure |
| Opportunity_Type | New Business or Expansion | Text | Expansion | Yes | Pipeline mix |
| Created_Date | Opportunity creation date | Date | 2026-06-01 | Yes | Ageing |
| Expected_Close_Date | Forecast close date (past date on an open opp = overdue) | Date | 2026-11-15 | Yes | Forecasting |
| Last_Activity_Date | Last logged activity | Date | 2026-09-01 | Yes | Stale-opportunity test |
| Days_Since_Activity | As-of date minus Last_Activity_Date (added by clean_data.py) | Integer | 29 | Calculated | Ageing |
| Is_Stale_Opp | 1 if open and Days_Since_Activity > 90 | Integer 0/1 | 0 | Calculated | Forecast-risk flag |

## territory_mapping.csv
One row per country.

| Field | Description | Data type | Example | Required? | Business purpose |
|---|---|---|---|---|---|
| Country | APJ country | Text | Singapore | Yes | Lookup key |
| Country_Code | ISO-style 2-letter code | Text | SG | Yes | Mapping |
| Territory | Territory the country belongs to | Text | SEA | Yes | Routing |
| Region | Sub-region | Text | Southeast Asia | Yes | Rollups |
| Enterprise_Owner / MidMarket_Owner / SMB_Owner | Fictional rep for each tier in that country's territory | Text | Daniel Lim | Yes | Expected_Owner lookup |

## dq_issues.csv
Long format: one row per account x failed check.

| Field | Description | Data type | Example | Required? | Business purpose |
|---|---|---|---|---|---|
| Account_ID, Company_Name, Country, Territory, Industry, Account_Tier | Account attributes copied for reporting (Territory = Expected_Territory) | Text | ... | Yes | Slicing the issue log |
| Issue_Type | Name of the failed check | Text | Missing Country | Yes | Issue category |
| Severity | Critical / High / Medium / Low (stale-with-pipeline and India missing-headcount are raised to High) | Text | Critical | Yes | Prioritisation |
| Recommended_Action | Standard remediation text | Text | Enrich country from domain... | Yes | Work-queue guidance |
| Open_Pipeline_Value | Open pipeline on the account (0 if none) | Decimal | 58500 | Yes | Business impact |
| Penalty | Score penalty for this severity | Integer | 40 | Yes | Score maths |

## routing_exceptions.csv
One row per account whose Routing_Status is not 'Correctly Routed'.

| Field | Description | Data type | Example | Required? | Business purpose |
|---|---|---|---|---|---|
| Account_ID, Company_Name, Country, Industry, Expected_Tier | Account attributes | Text | ... | Yes | Context |
| Current_Territory / Expected_Territory | Territory in CRM vs derived | Text | ANZ / SEA | Yes | Mismatch visual |
| Current_Owner / Expected_Owner | Owner in CRM vs expected | Text | James Wilson / Daniel Lim | Yes | Reassignment target |
| Routing_Status, Exception_Type | Status and reason | Text | Incorrectly Routed / Territory Mismatch | Yes | Classification |
| Priority | High (Enterprise or >= $100K pipeline), Medium, Low | Text | High | Yes | Work ordering |
| Open_Pipeline_Value | Open pipeline on the account | Decimal | 120000 | No | Impact |
| Resolution_Status | Workflow state derived from exception type (Pending Merge Review, Awaiting Data Enrichment, Awaiting Assignment, Ready to Reassign). The synthetic data records no completed resolutions | Text | Ready to Reassign | Yes | Work-queue state |
| Is_Open | 1 while unresolved (always 1 in synthetic data) | Integer 0/1 | 1 | Yes | Open Exceptions KPI |

## Key definitions

| Metric | Definition |
|---|---|
| Open pipeline | Sum of Opportunity_Value where Is_Open = 1 |
| Territory Coverage % | Accounts with an owner and a valid Sales_Territory / total accounts |
| Routing Accuracy % | Correctly Routed / (Correctly + Incorrectly Routed + Unassigned) |
| Data Quality Score % | Average Record_DQ_Score (100 minus severity penalties) |
| Clean Record Rate % | Share of accounts with Data_Quality_Status = Good |
| Stale account | No activity for more than 180 days |
| Stale opportunity | Open opportunity with no activity for more than 90 days |
| As-of date | 2026-09-30 (fixed so results are reproducible) |
