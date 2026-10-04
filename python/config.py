"""Shared configuration for the APJ Revenue Operations project.

Everything in this repository is SYNTHETIC. No real customers, people or
companies are represented. Any resemblance is coincidental.
"""
from pathlib import Path
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DOCS = ROOT / "documentation"

SEED = 20260930                    # fixed seed -> reproducible dataset
AS_OF = dt.date(2026, 9, 30)       # "today" for all ageing calculations
N_ACCOUNTS = 5000                  # total CRM records incl. duplicates
DUPLICATE_RATE = 0.02

STALE_ACCOUNT_DAYS = 180           # no activity for > 180 days -> stale account
STALE_OPP_DAYS = 90                # open opp with no activity > 90 days -> stale opp
ENTERPRISE_MIN = 5000              # Employee_Count >= 5000
MIDMARKET_MIN = 500                # 500-4,999 ; below 500 = SMB

# country -> (code, territory, sub-region, weight, ccTLD, gov TLD, legal suffix)
COUNTRIES = {
    "India":       ("IN", "India",  "South Asia",     22, ".co.in",  ".gov.in",  "Pvt Ltd"),
    "Australia":   ("AU", "ANZ",    "Oceania",        16, ".com.au", ".gov.au",  "Pty Ltd"),
    "New Zealand": ("NZ", "ANZ",    "Oceania",         4, ".co.nz",  ".govt.nz", "Ltd"),
    "Singapore":   ("SG", "SEA",    "Southeast Asia",  8, ".com.sg", ".gov.sg",  "Pte Ltd"),
    "Japan":       ("JP", "Japan",  "North Asia",     14, ".co.jp",  ".go.jp",   "K.K."),
    "South Korea": ("KR", "Korea",  "North Asia",      9, ".co.kr",  ".go.kr",   "Co., Ltd."),
    "Indonesia":   ("ID", "SEA",    "Southeast Asia",  7, ".co.id",  ".go.id",   "PT"),
    "Malaysia":    ("MY", "SEA",    "Southeast Asia",  5, ".com.my", ".gov.my",  "Sdn Bhd"),
    "Thailand":    ("TH", "SEA",    "Southeast Asia",  5, ".co.th",  ".go.th",   "Co., Ltd."),
    "Philippines": ("PH", "SEA",    "Southeast Asia",  5, ".com.ph", ".gov.ph",  "Inc."),
    "Vietnam":     ("VN", "SEA",    "Southeast Asia",  5, ".com.vn", ".gov.vn",  "JSC"),
}

COUNTRY_ALIASES = {
    "au": "Australia", "aus": "Australia", "nz": "New Zealand", "sg": "Singapore",
    "in": "India", "jp": "Japan", "kr": "South Korea", "korea": "South Korea",
    "s. korea": "South Korea", "republic of korea": "South Korea",
    "viet nam": "Vietnam", "id": "Indonesia", "my": "Malaysia", "th": "Thailand",
    "ph": "Philippines", "vn": "Vietnam",
}
COUNTRY_ALIAS_OUT = {   # what the generator writes into the raw file
    "Australia": ["AU", "Aus"], "New Zealand": ["NZ"], "Singapore": ["SG"],
    "India": ["IN"], "Japan": ["JP"], "South Korea": ["Korea", "S. Korea", "Republic of Korea"],
    "Vietnam": ["Viet Nam"], "Indonesia": ["ID"], "Malaysia": ["MY"],
}
INVALID_COUNTRY_VALUES = ["APAC", "Asia Pacific", "Other"]

TERRITORIES = ["India", "ANZ", "SEA", "Japan", "Korea"]
INVALID_TERRITORY_VALUES = ["APAC", "ROW", "TBD-Unassigned"]

# Owner by (territory, tier). One fictional rep per territory except India,
# where Enterprise and Commercial (Mid-Market + SMB) are split.
OWNERS = {
    ("India", "Enterprise"): "Priya Sharma",
    ("India", "Mid-Market"): "Arjun Mehta",
    ("India", "SMB"):        "Arjun Mehta",
    ("ANZ", "*"):   "James Wilson",
    ("Japan", "*"): "Yuki Tanaka",
    ("Korea", "*"): "Min-Jun Park",
    ("SEA", "*"):   "Daniel Lim",
}

INDUSTRIES = {
    "Software": 20, "Financial Services": 14, "Healthcare": 9, "Manufacturing": 14,
    "Retail": 10, "Telecommunications": 5, "Professional Services": 12,
    "Education": 6, "Government": 4, "Logistics": 6,
}
LEAD_SOURCES = {"Inbound Web": 28, "Outbound SDR": 22, "Partner Referral": 14,
                "Event": 12, "Marketing Campaign": 12, "Customer Referral": 8, "Other": 4}
OPEN_STAGES = ["Prospecting", "Qualification", "Discovery", "Proposal", "Negotiation"]
CLOSED_STAGES = ["Closed Won", "Closed Lost"]

LEGAL_TOKENS = {"pvt", "ltd", "limited", "private", "pty", "pte", "kk", "co", "inc", "sdn",
                "bhd", "pt", "jsc", "corp", "llc", "company"}

# Data-quality severity model
SEVERITY_PENALTY = {"Critical": 40, "High": 25, "Medium": 10, "Low": 5}
