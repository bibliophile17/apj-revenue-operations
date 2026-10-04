-- =====================================================================
-- territory_analysis.sql  |  APJ Revenue Operations (SYNTHETIC DATA)
-- Tables: accounts, opportunities, territory_mapping  (see python/run_sql.py)
-- Territory reporting uses Expected_Territory (country-derived) so that a
-- mis-routed account is counted where it BELONGS. 'Unknown' = no usable country.
-- Pipeline = open opportunities only (opportunities.Is_Open = 1).
-- =====================================================================

-- Query 1: Accounts by territory (with coverage %)
SELECT
    Expected_Territory                                        AS territory,
    COUNT(*)                                                  AS accounts,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)        AS pct_of_accounts,
    SUM(Is_Covered)                                           AS covered_accounts,
    ROUND(100.0 * SUM(Is_Covered) / COUNT(*), 1)              AS coverage_pct
FROM accounts
GROUP BY Expected_Territory
ORDER BY accounts DESC;

-- Query 2: Accounts by country
SELECT
    COALESCE(Country, '(missing)')   AS country,
    Expected_Territory               AS territory,
    COUNT(*)                         AS accounts,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_accounts
FROM accounts
GROUP BY COALESCE(Country, '(missing)'), Expected_Territory
ORDER BY accounts DESC;

-- Query 3: Accounts by account tier (expected tier from Employee_Count)
SELECT
    Expected_Tier                    AS account_tier,
    COUNT(*)                         AS accounts,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct_of_accounts
FROM accounts
GROUP BY Expected_Tier
ORDER BY accounts DESC;

-- Query 4: Territory x tier matrix
SELECT
    Expected_Territory                                          AS territory,
    COUNT(*) FILTER (WHERE Expected_Tier = 'Enterprise')        AS enterprise,
    COUNT(*) FILTER (WHERE Expected_Tier = 'Mid-Market')        AS mid_market,
    COUNT(*) FILTER (WHERE Expected_Tier = 'SMB')               AS smb,
    COUNT(*) FILTER (WHERE Expected_Tier = 'Unknown')           AS unknown_tier,
    COUNT(*)                                                    AS total
FROM accounts
GROUP BY Expected_Territory
ORDER BY total DESC;

-- Query 5: Open pipeline by territory
SELECT
    a.Expected_Territory                                   AS territory,
    COUNT(*)                                               AS open_opportunities,
    SUM(o.Opportunity_Value)                               AS pipeline_usd,
    ROUND(100.0 * SUM(o.Opportunity_Value) / SUM(SUM(o.Opportunity_Value)) OVER (), 1) AS pct_of_pipeline
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1
GROUP BY a.Expected_Territory
ORDER BY pipeline_usd DESC;

-- Query 6: Open pipeline by country
SELECT
    COALESCE(a.Country, '(missing)')   AS country,
    COUNT(*)                           AS open_opportunities,
    SUM(o.Opportunity_Value)           AS pipeline_usd,
    ROUND(AVG(o.Opportunity_Value), 0) AS avg_opportunity_usd
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1
GROUP BY COALESCE(a.Country, '(missing)')
ORDER BY pipeline_usd DESC;

-- Query 7: Open pipeline by account tier
SELECT
    a.Expected_Tier                    AS account_tier,
    COUNT(*)                           AS open_opportunities,
    SUM(o.Opportunity_Value)           AS pipeline_usd,
    ROUND(100.0 * SUM(o.Opportunity_Value) / SUM(SUM(o.Opportunity_Value)) OVER (), 1) AS pct_of_pipeline
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1
GROUP BY a.Expected_Tier
ORDER BY pipeline_usd DESC;

-- Query 8: Coverage % by territory and creation year (is coverage slipping on newer accounts?)
SELECT
    Expected_Territory                                         AS territory,
    SUBSTR(CAST(Created_Date AS VARCHAR), 1, 4)                AS created_year,
    COUNT(*)                                                   AS accounts,
    ROUND(100.0 * SUM(Is_Covered) / COUNT(*), 1)               AS coverage_pct
FROM accounts
WHERE Expected_Territory <> 'Unknown'
GROUP BY Expected_Territory, SUBSTR(CAST(Created_Date AS VARCHAR), 1, 4)
ORDER BY territory, created_year;
