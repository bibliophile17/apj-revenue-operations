-- =====================================================================
-- data_quality.sql  |  APJ Revenue Operations (SYNTHETIC DATA)
-- Flags (Flag_*, Is_Duplicate) are produced by python/data_quality.py.
-- Each query below is also re-derivable from the raw fields shown.
-- =====================================================================

-- Query 1: Duplicate accounts (non-master records) with their master
SELECT d.Account_ID, d.Company_Name, d.Country, d.Created_Date,
       d.Master_Account_ID, m.Company_Name AS master_company_name
FROM accounts d
JOIN accounts m ON m.Account_ID = d.Master_Account_ID
WHERE d.Is_Duplicate = 1
ORDER BY d.Master_Account_ID, d.Created_Date;

-- Query 2: Missing or invalid country (routing is blocked for these)
SELECT Account_ID, Company_Name, Country, Sales_Territory, Account_Owner, Opportunity_Value
FROM accounts
WHERE Flag_Missing_Country = 1 OR Flag_Invalid_Country = 1
ORDER BY Opportunity_Value DESC NULLS LAST, Account_ID
LIMIT 25;

-- Query 3: Missing annual revenue by tier
SELECT Expected_Tier AS account_tier,
       COUNT(*) FILTER (WHERE Flag_Missing_Revenue = 1)                         AS missing_revenue,
       COUNT(*)                                                                 AS accounts,
       ROUND(100.0 * COUNT(*) FILTER (WHERE Flag_Missing_Revenue = 1) / COUNT(*), 2) AS missing_pct
FROM accounts
GROUP BY Expected_Tier
ORDER BY missing_revenue DESC;

-- Query 4: Missing owner - by territory and tier, with pipeline exposed
SELECT Expected_Territory AS territory, Expected_Tier AS account_tier,
       COUNT(*)                         AS accounts_without_owner,
       SUM(Opportunity_Value)           AS open_pipeline_without_owner_usd
FROM accounts
WHERE Flag_Missing_Owner = 1
GROUP BY Expected_Territory, Expected_Tier
ORDER BY accounts_without_owner DESC;

-- Query 5: Stale accounts (> 180 days since last activity) by country
SELECT COALESCE(Country, '(missing)') AS country,
       COUNT(*)                                                AS accounts,
       COUNT(*) FILTER (WHERE Flag_Stale = 1)                  AS stale_accounts,
       ROUND(100.0 * COUNT(*) FILTER (WHERE Flag_Stale = 1) / COUNT(*), 2) AS stale_pct
FROM accounts
GROUP BY COALESCE(Country, '(missing)')
ORDER BY stale_pct DESC;

-- Query 6: Invalid territories (value is not a valid territory, or does not match the country)
SELECT Sales_Territory AS current_territory, Expected_Territory AS expected_territory,
       COUNT(*) AS accounts
FROM accounts
WHERE Flag_Invalid_Territory = 1
GROUP BY Sales_Territory, Expected_Territory
ORDER BY accounts DESC;

-- Query 7: Issues by territory and severity (from the long-format issue log)
SELECT COALESCE(NULLIF(Territory, ''), 'Unknown') AS territory,
       COUNT(*) FILTER (WHERE Severity = 'Critical') AS critical,
       COUNT(*) FILTER (WHERE Severity = 'High')     AS high,
       COUNT(*) FILTER (WHERE Severity = 'Medium')   AS medium,
       COUNT(*) FILTER (WHERE Severity = 'Low')      AS low,
       COUNT(*)                                      AS total_issues
FROM dq_issues
GROUP BY COALESCE(NULLIF(Territory, ''), 'Unknown')
ORDER BY total_issues DESC;

-- Query 8: Data-quality score and clean-record rate by territory
SELECT Expected_Territory AS territory,
       COUNT(*)                                                         AS accounts,
       ROUND(AVG(Record_DQ_Score), 1)                                   AS dq_score_pct,
       ROUND(100.0 * COUNT(*) FILTER (WHERE Data_Quality_Status = 'Good') / COUNT(*), 1) AS clean_record_pct,
       COUNT(*) FILTER (WHERE Data_Quality_Status = 'Critical')         AS critical_accounts
FROM accounts
GROUP BY Expected_Territory
ORDER BY dq_score_pct;

-- Query 9: Issue ranking by volume and pipeline exposed
SELECT Issue_Type, Severity,
       COUNT(DISTINCT Account_ID)  AS accounts_affected,
       SUM(Open_Pipeline_Value)    AS pipeline_exposed_usd
FROM dq_issues
GROUP BY Issue_Type, Severity
ORDER BY accounts_affected DESC;
