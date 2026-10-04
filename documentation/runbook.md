# Operations Runbook - Weekly APJ Territory & CRM Data Quality Cycle

**Owner:** Revenue Operations (APJ) | **Cadence:** weekly (Monday AM) + month-end close | **Data:** synthetic in this repo

```
CRM Export -> Data Validation -> Duplicate Detection -> Data Quality Checks -> Territory Assignment
 -> Routing Validation -> Exception Review -> Dashboard Refresh -> Stakeholder Reporting -> Issue Documentation
```

## Purpose
Keep account ownership, territory assignment and CRM hygiene accurate so that pipeline reporting, quota coverage and lead routing can be trusted.

## Inputs
| Input | Source | Notes |
|---|---|---|
| Account export | CRM report (CSV) | In this project: `data/accounts_raw.csv` |
| Opportunity export | CRM report (CSV) | `data/opportunities.csv` |
| Territory mapping | RevOps-owned reference | `data/territory_mapping.csv`; change-controlled |
| Rule thresholds | `python/config.py` | Tier thresholds, stale-days |

## Process
| # | Step | Command / action | Output | Check before moving on |
|---|---|---|---|---|
| 1 | CRM export | Export accounts + opportunities | raw CSVs | Row count within +/-5% of last week |
| 2 | Data validation | `python python/clean_data.py` | `accounts_clean.csv` | No schema errors; dates parse |
| 3 | Duplicate detection | (same script) | `Is_Duplicate`, `Master_Account_ID` | Every duplicate points at an existing master |
| 4 | Territory assignment | `python python/territory_router.py` | Expected_* columns | Unknown territory < 5% of accounts |
| 5 | Routing validation | (same script) | `routing_exceptions.csv` | Status counts sum to total accounts |
| 6 | Data quality checks | `python python/data_quality.py` | `dq_issues.csv`, scores | Score change vs last week explained |
| 7 | Exception review | Work the Routing Exceptions sheet / Power BI page 4 | Resolution_Status updates | All High-priority exceptions have an owner |
| 8 | SQL cross-check | `python python/run_sql.py` | query output | Routing accuracy matches Python |
| 9 | Dashboard refresh | Power BI: Home > Refresh | updated report | KPI totals match Excel `Data Quality` sheet |
| 10 | Stakeholder reporting | Weekly summary to Sales leadership | email / slide | See template below |
| 11 | Issue documentation | Log new issues / rule changes | change log | Each issue has an owner and due date |

One-shot alternative: `python python/run_all.py`.

## Outputs
`accounts_clean.csv`, `routing_exceptions.csv`, `dq_issues.csv`, refreshed Power BI report, weekly stakeholder summary, updated issue log.

## Quality checks (gates)
* Total accounts after cleaning = total accounts exported (cleaning never deletes records).
* Routing statuses are mutually exclusive and sum to total accounts.
* Excel KPIs (`Data Quality` sheet) = Python = SQL for accuracy, coverage and DQ score.
* New Critical issues are explained (e.g. bulk import, rep departure).

## Escalation rules
| Trigger | Escalate to | SLA |
|---|---|---|
| Enterprise account unassigned | Regional Sales Director | 2 business days |
| Routing accuracy falls > 2 pts week on week | RevOps Manager | Same day |
| Territory coverage < 95% in any territory | Territory Sales Manager + RevOps Manager | 2 business days |
| Duplicates > 2% of accounts | CRM Admin | 5 business days |
| Open pipeline on uncovered accounts > $1M | VP Sales Ops | Same day |

## Common exceptions
| Exception | Typical cause | Resolution |
|---|---|---|
| Missing Country | Lead import without country | Enrich from domain/billing address; re-run router |
| Territory Mismatch | Manual territory edit; regional realignment | Reset territory from country; reassign owner |
| No Owner | Rep departure; new-record assignment rule not firing | Bulk assign per Expected_Owner |
| Owner Mismatch | Tier drift (headcount grew) | Update tier, reassign India owner |
| Duplicate Account | Web-form and event imports | Merge into master; re-point opportunities |
| Stale Account | Lost contact; no activity logged | Re-engage or mark Inactive |

## Resolution process
1. Triage by priority (High first), then pipeline value.
2. Fix at source in CRM (not in the export), recording the change.
3. Re-run the pipeline; confirm the account leaves the exception list.
4. If a rule caused the problem (not data entry), raise a rule-change request and record it in the issue log.

## Weekly stakeholder summary (template)
1. KPIs: coverage %, routing accuracy %, DQ score, open exceptions (with week-on-week change).
2. Top 3 risks (territory, count, pipeline exposed).
3. Actions completed / planned with owners and dates.

## Issue log (template)
| Date | Issue | Territory | Accounts affected | Root cause | Fix | Owner | Status |
|---|---|---|---|---|---|---|---|
