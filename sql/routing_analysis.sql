-- =====================================================================
-- routing_analysis.sql  |  APJ Revenue Operations (SYNTHETIC DATA)
-- Routing_Status: Correctly Routed | Incorrectly Routed | Unassigned | Ambiguous | Manual Review
-- Routing accuracy = Correctly Routed / (Correctly + Incorrectly + Unassigned)
-- (Ambiguous and Manual Review have no deterministic expected route and are excluded.)
-- =====================================================================

-- Query 1: Routing status summary
SELECT Routing_Status,
       COUNT(*)                                                 AS accounts,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1)       AS pct_of_accounts
FROM accounts
GROUP BY Routing_Status
ORDER BY accounts DESC;

-- Query 2: Routing accuracy (overall)
SELECT COUNT(*) FILTER (WHERE Routing_Status IN ('Correctly Routed','Incorrectly Routed','Unassigned')) AS routable_accounts,
       COUNT(*) FILTER (WHERE Routing_Status = 'Correctly Routed')   AS correctly_routed,
       COUNT(*) FILTER (WHERE Routing_Status = 'Incorrectly Routed') AS incorrectly_routed,
       COUNT(*) FILTER (WHERE Routing_Status = 'Unassigned')         AS unassigned,
       ROUND(100.0 * COUNT(*) FILTER (WHERE Routing_Status = 'Correctly Routed')
             / COUNT(*) FILTER (WHERE Routing_Status IN ('Correctly Routed','Incorrectly Routed','Unassigned')), 2) AS routing_accuracy_pct
FROM accounts;

-- Query 3: Routing accuracy by territory
SELECT Expected_Territory AS territory,
       COUNT(*) FILTER (WHERE Routing_Status IN ('Correctly Routed','Incorrectly Routed','Unassigned')) AS routable,
       COUNT(*) FILTER (WHERE Routing_Status = 'Correctly Routed')   AS correct,
       COUNT(*) FILTER (WHERE Routing_Status = 'Incorrectly Routed') AS incorrect,
       COUNT(*) FILTER (WHERE Routing_Status = 'Unassigned')         AS unassigned,
       ROUND(100.0 * COUNT(*) FILTER (WHERE Routing_Status = 'Correctly Routed')
             / NULLIF(COUNT(*) FILTER (WHERE Routing_Status IN ('Correctly Routed','Incorrectly Routed','Unassigned')), 0), 2) AS accuracy_pct
FROM accounts
WHERE Expected_Territory <> 'Unknown'
GROUP BY Expected_Territory
ORDER BY accuracy_pct;

-- Query 4: Incorrectly routed accounts
SELECT Account_ID, Company_Name, Country, Sales_Territory AS current_territory,
       Expected_Territory, Account_Owner AS current_owner, Expected_Owner, Exception_Type
FROM accounts
WHERE Routing_Status = 'Incorrectly Routed'
ORDER BY Expected_Territory, Account_ID;

-- Query 5: Unassigned accounts (no owner and/or no territory) - enterprise first
SELECT Account_ID, Company_Name, Country, Expected_Territory, Expected_Tier, Expected_Owner,
       Exception_Type, Opportunity_Value AS open_pipeline_usd
FROM accounts
WHERE Routing_Status = 'Unassigned'
ORDER BY CASE Expected_Tier WHEN 'Enterprise' THEN 1 WHEN 'Mid-Market' THEN 2 ELSE 3 END,
         Opportunity_Value DESC NULLS LAST
LIMIT 25;

-- Query 6: Current territory vs expected territory (crosstab; off-diagonal = problems)
SELECT COALESCE(Sales_Territory, '(blank)') AS current_territory,
       Expected_Territory,
       COUNT(*) AS accounts
FROM accounts
WHERE Routing_Status <> 'Correctly Routed' OR Sales_Territory <> Expected_Territory
GROUP BY COALESCE(Sales_Territory, '(blank)'), Expected_Territory
ORDER BY accounts DESC;

-- Query 7: Territory exception counts by exception type
SELECT Expected_Territory AS territory,
       COUNT(*) FILTER (WHERE Exception_Type = 'Territory Mismatch')       AS territory_mismatch,
       COUNT(*) FILTER (WHERE Exception_Type = 'Invalid Territory Value')  AS invalid_territory_value,
       COUNT(*) FILTER (WHERE Exception_Type = 'Owner Mismatch')           AS owner_mismatch,
       COUNT(*) FILTER (WHERE Exception_Type IN ('No Owner','No Territory','No Owner & No Territory')) AS unassigned,
       COUNT(*) FILTER (WHERE Exception_Type IN ('Missing Country','Invalid Country')) AS country_problem,
       COUNT(*) FILTER (WHERE Exception_Type = 'Missing Employee Count')   AS missing_headcount,
       COUNT(*) FILTER (WHERE Exception_Type = 'Duplicate Account')        AS duplicates,
       COUNT(*) FILTER (WHERE Exception_Type IS NOT NULL)                  AS total_exceptions
FROM accounts
GROUP BY Expected_Territory
ORDER BY total_exceptions DESC;

-- Query 8: Open exceptions by workflow status and priority
SELECT Resolution_Status, Priority, COUNT(*) AS exceptions, SUM(Open_Pipeline_Value) AS pipeline_usd
FROM routing_exceptions
WHERE Is_Open = 1
GROUP BY Resolution_Status, Priority
ORDER BY CASE Priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END, exceptions DESC;
