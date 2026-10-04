-- =====================================================================
-- pipeline_analysis.sql  |  APJ Revenue Operations (SYNTHETIC DATA)
-- Open pipeline = opportunities.Is_Open = 1. Stale opportunity = open and
-- no activity for more than 90 days (opportunities.Is_Stale_Opp = 1).
-- =====================================================================

-- Query 1: Pipeline by stage (funnel order)
SELECT
    Stage                                   AS stage,
    COUNT(*)                                AS open_opportunities,
    SUM(Opportunity_Value)                  AS pipeline_usd,
    ROUND(AVG(Opportunity_Value), 0)        AS avg_opportunity_usd
FROM opportunities
WHERE Is_Open = 1
GROUP BY Stage
ORDER BY CASE Stage WHEN 'Prospecting' THEN 1 WHEN 'Qualification' THEN 2 WHEN 'Discovery' THEN 3
                    WHEN 'Proposal' THEN 4 WHEN 'Negotiation' THEN 5 END;

-- Query 2: Pipeline by territory and stage
SELECT
    a.Expected_Territory                                            AS territory,
    SUM(o.Opportunity_Value) FILTER (WHERE o.Stage = 'Prospecting')   AS prospecting,
    SUM(o.Opportunity_Value) FILTER (WHERE o.Stage = 'Qualification') AS qualification,
    SUM(o.Opportunity_Value) FILTER (WHERE o.Stage = 'Discovery')     AS discovery,
    SUM(o.Opportunity_Value) FILTER (WHERE o.Stage = 'Proposal')      AS proposal,
    SUM(o.Opportunity_Value) FILTER (WHERE o.Stage = 'Negotiation')   AS negotiation,
    SUM(o.Opportunity_Value)                                          AS total_pipeline_usd
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1
GROUP BY a.Expected_Territory
ORDER BY total_pipeline_usd DESC;

-- Query 3: Pipeline by account tier
SELECT
    a.Expected_Tier                         AS account_tier,
    COUNT(*)                                AS open_opportunities,
    SUM(o.Opportunity_Value)                AS pipeline_usd
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1
GROUP BY a.Expected_Tier
ORDER BY pipeline_usd DESC;

-- Query 4: Average opportunity value by tier and territory
SELECT
    a.Expected_Territory                                                     AS territory,
    ROUND(AVG(o.Opportunity_Value) FILTER (WHERE a.Expected_Tier = 'Enterprise'), 0) AS avg_enterprise_usd,
    ROUND(AVG(o.Opportunity_Value) FILTER (WHERE a.Expected_Tier = 'Mid-Market'), 0) AS avg_mid_market_usd,
    ROUND(AVG(o.Opportunity_Value) FILTER (WHERE a.Expected_Tier = 'SMB'), 0)        AS avg_smb_usd,
    ROUND(AVG(o.Opportunity_Value), 0)                                       AS avg_all_usd
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1
GROUP BY a.Expected_Territory
ORDER BY avg_all_usd DESC;

-- Query 5: Enterprise pipeline - share of total and top 10 deals
SELECT
    ROUND(SUM(o.Opportunity_Value) FILTER (WHERE a.Expected_Tier = 'Enterprise'), 0)          AS enterprise_pipeline_usd,
    ROUND(SUM(o.Opportunity_Value), 0)                                                         AS total_pipeline_usd,
    ROUND(100.0 * SUM(o.Opportunity_Value) FILTER (WHERE a.Expected_Tier = 'Enterprise')
          / SUM(o.Opportunity_Value), 1)                                                       AS enterprise_share_pct
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1;

-- Query 6: Top 10 enterprise open opportunities
SELECT
    o.Opportunity_ID, a.Company_Name, a.Country, a.Expected_Territory AS territory,
    o.Stage, o.Opportunity_Value, a.Account_Owner AS current_owner, a.Routing_Status
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1 AND a.Expected_Tier = 'Enterprise' AND o.Opportunity_Value IS NOT NULL
ORDER BY o.Opportunity_Value DESC
LIMIT 10;

-- Query 7: Stale opportunities by territory (open, no activity > 90 days)
SELECT
    a.Expected_Territory                                         AS territory,
    COUNT(*)                                                     AS open_opportunities,
    SUM(o.Is_Stale_Opp)                                          AS stale_opportunities,
    ROUND(100.0 * SUM(o.Is_Stale_Opp) / COUNT(*), 1)             AS stale_pct,
    SUM(o.Opportunity_Value) FILTER (WHERE o.Is_Stale_Opp = 1)   AS stale_pipeline_usd
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 1
GROUP BY a.Expected_Territory
ORDER BY stale_pipeline_usd DESC;

-- Query 8: Largest stale opportunities (re-engage or close out)
SELECT
    o.Opportunity_ID, a.Company_Name, a.Expected_Territory AS territory, o.Stage,
    o.Opportunity_Value, o.Days_Since_Activity, o.Expected_Close_Date
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Stale_Opp = 1 AND o.Opportunity_Value IS NOT NULL
ORDER BY o.Opportunity_Value DESC
LIMIT 15;

-- Query 9: Win rate by territory (closed opportunities only)
SELECT
    a.Expected_Territory                                              AS territory,
    COUNT(*) FILTER (WHERE o.Stage = 'Closed Won')                    AS won,
    COUNT(*) FILTER (WHERE o.Stage = 'Closed Lost')                   AS lost,
    ROUND(100.0 * COUNT(*) FILTER (WHERE o.Stage = 'Closed Won') / COUNT(*), 1) AS win_rate_pct
FROM opportunities o
JOIN accounts a ON a.Account_ID = o.Account_ID
WHERE o.Is_Open = 0
GROUP BY a.Expected_Territory
ORDER BY win_rate_pct DESC;
