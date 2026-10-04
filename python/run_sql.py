"""Run the SQL analysis files with DuckDB and print results.

Usage:  python python/run_sql.py                      # all files
        python python/run_sql.py sql/routing_analysis.sql
        python python/run_sql.py --export             # also write CSVs to sql/output/
"""
import re, sys
import duckdb
from config import ROOT, DATA

TABLES = {"accounts": "accounts_clean.csv", "opportunities": "opportunities.csv",
          "territory_mapping": "territory_mapping.csv", "dq_issues": "dq_issues.csv",
          "routing_exceptions": "routing_exceptions.csv"}


def connect():
    con = duckdb.connect()
    for t, f in TABLES.items():
        con.execute(f"CREATE VIEW {t} AS SELECT * FROM read_csv_auto('{(DATA / f).as_posix()}', header=true)")
    return con


def run_file(con, path, export=False):
    text = path.read_text()
    blocks = re.split(r"(?m)^-- Query (\d+): (.*)$", text)
    for i in range(1, len(blocks), 3):
        num, title, body = blocks[i], blocks[i + 1], blocks[i + 2]
        sql = "\n".join(l for l in body.splitlines() if not l.startswith("-- ====")).strip().rstrip(";")
        df = con.execute(sql).df()
        print(f"\n[{path.name}] Query {num}: {title}\n{df.head(15).to_string(index=False)}")
        if export:
            out = ROOT / "sql" / "output"; out.mkdir(exist_ok=True)
            df.to_csv(out / f"{path.stem}_q{num}.csv", index=False)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    files = [ROOT / a for a in args] or sorted((ROOT / "sql").glob("*.sql"))
    con = connect()
    for f in files:
        run_file(con, f, export="--export" in sys.argv)
