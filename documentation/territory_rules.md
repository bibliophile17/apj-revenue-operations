# Territory Rules

> **All data in this repository is synthetic.** Sales reps, companies and accounts are fictional.

These rules define how APJ accounts are segmented and assigned. They are implemented in
`python/territory_router.py` and driven by `data/territory_mapping.csv`.

## 1. APJ territory definitions

| Territory | Countries | Sub-region | Owner(s) |
|---|---|---|---|
| **India** | India | South Asia | Priya Sharma (Enterprise), Arjun Mehta (Commercial = Mid-Market + SMB) |
| **ANZ** | Australia, New Zealand | Oceania | James Wilson |
| **SEA** | Singapore, Indonesia, Malaysia, Thailand, Philippines, Vietnam | Southeast Asia | Daniel Lim |
| **Japan** | Japan | North Asia | Yuki Tanaka |
| **Korea** | South Korea | North Asia | Min-Jun Park |

A country belongs to exactly one territory. Territory is **derived from Country** - it is never a free-text decision.

## 2. Account segmentation

Segment is derived from `Employee_Count` only (not revenue):

| Tier | Rule | Notes |
|---|---|---|
| **Enterprise** | Employee_Count >= 5,000 | Named-account coverage |
| **Mid-Market** | 500 <= Employee_Count <= 4,999 | Commercial coverage |
| **SMB** | Employee_Count < 500 | Commercial coverage |
| **Unknown** | Employee_Count missing | Cannot be tiered; flagged for enrichment |

Thresholds live in `python/config.py` (and in the `Territory Mapping` sheet of the Excel workbook).

## 3. Routing / ownership rules

| Territory | Tier | Expected owner | Queue |
|---|---|---|---|
| India | Enterprise | Priya Sharma | India Enterprise |
| India | Mid-Market | Arjun Mehta | India Commercial |
| India | SMB | Arjun Mehta | India Commercial |
| ANZ | Any | James Wilson | ANZ |
| SEA | Any | Daniel Lim | SEA |
| Japan | Any | Yuki Tanaka | Japan |
| Korea | Any | Min-Jun Park | Korea |

Only India splits ownership by tier, so only India accounts need a known tier to be routed.

## 4. Ownership rules

1. Every non-duplicate account must have exactly one owner and one valid territory.
2. `Sales_Territory` must equal the territory derived from `Country`.
3. `Account_Owner` must equal the Expected_Owner for (territory, tier).
4. Duplicate records are never routed; the **master** (earliest-created) record keeps ownership.
5. Territory reporting uses **Expected_Territory** (where the account belongs), so mis-routed accounts do not distort territory totals.

## 5. Exception handling

| Situation | Routing status | Exception type | Resolution path |
|---|---|---|---|
| Country blank | Ambiguous | Missing Country | Enrich country, then re-run router |
| Country not an APJ country | Ambiguous | Invalid Country | Replace with HQ country |
| Non-master duplicate | Manual Review | Duplicate Account | Merge into master |
| India, no employee count | Manual Review | Missing Employee Count | Enrich headcount |
| Owner and/or territory blank | Unassigned | No Owner / No Territory / both | Assign per Expected_Owner |
| Territory not valid | Incorrectly Routed | Invalid Territory Value | Correct territory + owner |
| Territory differs from country | Incorrectly Routed | Territory Mismatch | Reassign to expected territory/owner |
| Owner differs from expected | Incorrectly Routed | Owner Mismatch | Reassign (often tier drift) |

Priority: **High** = Enterprise or >= $100K open pipeline; **Medium** = any open pipeline or Mid-Market; **Low** = everything else.

## 6. Country-name standardisation

Common variants are normalised before routing (e.g. `AU`/`Aus` -> Australia, `NZ` -> New Zealand,
`Korea`/`S. Korea`/`Republic of Korea` -> South Korea, `Viet Nam` -> Vietnam). Values that cannot be mapped
(e.g. `APAC`) are treated as Invalid Country.
