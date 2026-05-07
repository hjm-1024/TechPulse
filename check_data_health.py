"""
TechPulse data health diagnostic.

Prints a domain × year matrix for papers and patents so you can quickly judge
whether collection is balanced and covers your target window (default ≥ 2020).

Examples:
    # Quick overview (default: from 2020)
    python check_data_health.py

    # Different cutoff year
    python check_data_health.py --since 2018

    # Show source breakdown per domain
    python check_data_health.py --by-source

    # Output as JSON (for UI/automation)
    python check_data_health.py --json

    # Highlight gaps (cells below threshold)
    python check_data_health.py --gap-threshold 50
"""

import argparse
import json
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from backend.config import DB_PATH


def _year(date_str: str | None) -> str:
    if not date_str:
        return "?"
    return date_str[:4] if len(date_str) >= 4 else "?"


def _connect(db_path: str) -> sqlite3.Connection:
    if not Path(db_path).exists():
        raise SystemExit(f"DB not found: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def collect_health(db_path: str, since_year: int) -> dict:
    """Returns a structured health report."""
    conn = _connect(db_path)

    out = {
        "db_path":  db_path,
        "since":    since_year,
        "as_of":    datetime.now().strftime("%Y-%m-%d %H:%M"),
        "papers":   _table_stats(conn, "papers",  "published_date",  since_year),
        "patents":  _table_stats(conn, "patents", "publication_date", since_year),
        "freshness": _freshness(conn),
        "quality":  _quality_breakdown(conn),
    }
    conn.close()
    return out


def _table_stats(conn: sqlite3.Connection, table: str, date_col: str,
                 since_year: int) -> dict:
    has_flag = _has_column(conn, table, "quality_flag")
    flag_col = "quality_flag" if has_flag else "NULL AS quality_flag"
    rows = conn.execute(
        f"SELECT domain_tag, source, {date_col} AS d, {flag_col} "
        f"FROM {table}"
    ).fetchall()

    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    by_source: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    total = 0
    in_window = 0
    excluded_short_or_dup = 0
    excluded_pre_window = 0
    no_date = 0

    for r in rows:
        total += 1
        if r["quality_flag"] in ("short_abstract", "duplicate"):
            excluded_short_or_dup += 1
            continue
        y = _year(r["d"])
        if y == "?":
            no_date += 1
            continue
        try:
            yi = int(y)
        except ValueError:
            no_date += 1
            continue
        if yi < since_year:
            excluded_pre_window += 1
            continue
        in_window += 1
        domain = r["domain_tag"] or "(none)"
        matrix[domain][y] += 1
        by_source[domain][r["source"] or "(unknown)"] += 1

    # Sort years
    all_years = sorted({y for d in matrix.values() for y in d})
    return {
        "total_rows":            total,
        "in_window":             in_window,
        "excluded_short_or_dup": excluded_short_or_dup,
        "excluded_pre_window":   excluded_pre_window,
        "no_date":               no_date,
        "domains":               sorted(matrix.keys()),
        "years":                 all_years,
        "matrix":                {d: dict(yc) for d, yc in matrix.items()},
        "by_source":             {d: dict(sc) for d, sc in by_source.items()},
    }


def _freshness(conn: sqlite3.Connection) -> dict:
    out: dict[str, dict] = {}
    for table, date_col in (("papers", "published_date"), ("patents", "publication_date")):
        per_source = conn.execute(
            f"SELECT source, MAX({date_col}) AS latest, COUNT(*) AS cnt "
            f"FROM {table} GROUP BY source"
        ).fetchall()
        global_latest = conn.execute(f"SELECT MAX({date_col}) AS m FROM {table}").fetchone()
        out[table] = {
            "latest_overall": global_latest["m"] if global_latest else None,
            "per_source": [
                {"source": r["source"], "latest": r["latest"], "count": r["cnt"]}
                for r in per_source
            ],
        }
    return out


def _has_column(conn: sqlite3.Connection, table: str, column: str) -> bool:
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
    return column in cols


def _quality_breakdown(conn: sqlite3.Connection) -> dict:
    out: dict[str, dict] = {}
    for table in ("papers", "patents"):
        if _has_column(conn, table, "quality_flag"):
            rows = conn.execute(
                f"SELECT COALESCE(quality_flag, 'ok') AS flag, COUNT(*) AS cnt "
                f"FROM {table} GROUP BY flag"
            ).fetchall()
            by_flag = {r["flag"]: r["cnt"] for r in rows}
        else:
            by_flag = {"(quality_flag column missing — run migration)": 0}

        if _has_column(conn, table, "embedding"):
            embedded = conn.execute(
                f"SELECT COUNT(*) AS n FROM {table} WHERE embedding IS NOT NULL"
            ).fetchone()["n"]
        else:
            embedded = 0

        total = conn.execute(f"SELECT COUNT(*) AS n FROM {table}").fetchone()["n"]
        out[table] = {
            "by_flag":   by_flag,
            "embedded":  embedded,
            "total":     total,
            "embed_pct": round(100 * embedded / total, 1) if total else 0,
        }
    return out


# ── pretty printing ──────────────────────────────────────────────────────────

def _print_matrix(title: str, stats: dict, gap_threshold: int, since_year: int) -> None:
    domains = stats["domains"]
    years   = stats["years"]
    if not domains or not years:
        print(f"\n## {title}\n  (no data in window)")
        return

    print(f"\n## {title}  (in_window: {stats['in_window']:,}  / total: {stats['total_rows']:,})")
    print(f"   excluded — short/duplicate: {stats['excluded_short_or_dup']:,}, "
          f"pre-{since_year}: {stats['excluded_pre_window']:,}, "
          f"no_date: {stats['no_date']:,}")

    # Header
    name_w = max(20, max(len(d) for d in domains) + 2)
    col_w  = 8
    head = f"  {'domain':<{name_w}}" + "".join(f"{y:>{col_w}}" for y in years) + f"{'TOTAL':>{col_w}}"
    print(head)
    print("  " + "─" * (len(head) - 2))

    # Rows
    for d in domains:
        cells = stats["matrix"][d]
        row_total = sum(cells.values())
        cells_str = ""
        for y in years:
            v = cells.get(y, 0)
            mark = " "
            if v == 0:
                mark = "·"  # gap
            elif gap_threshold and v < gap_threshold:
                mark = "↓"  # below threshold
            cells_str += f"{v:>{col_w-1}}{mark}"
        print(f"  {d:<{name_w}}{cells_str}{row_total:>{col_w}}")

    # Column totals
    col_totals = {y: sum(stats["matrix"][d].get(y, 0) for d in domains) for y in years}
    grand = sum(col_totals.values())
    print("  " + "─" * (len(head) - 2))
    totals_str = "".join(f"{col_totals[y]:>{col_w}}" for y in years)
    print(f"  {'TOTAL':<{name_w}}{totals_str}{grand:>{col_w}}")


def _print_freshness(fresh: dict) -> None:
    print("\n## Freshness")
    for table, info in fresh.items():
        print(f"  {table}: latest = {info['latest_overall']}")
        for s in info["per_source"]:
            print(f"    {s['source']:<20} latest={s['latest']}  count={s['count']:,}")


def _print_quality(quality: dict) -> None:
    print("\n## Quality flags")
    for table, info in quality.items():
        flags = ", ".join(f"{k}={v:,}" for k, v in sorted(info["by_flag"].items()))
        print(f"  {table}: {flags}  |  embedded {info['embedded']:,}/{info['total']:,} ({info['embed_pct']}%)")


def _print_recommendations(report: dict, gap_threshold: int) -> None:
    print("\n## Recommendations")
    suggestions: list[str] = []

    for table_key, table in (("papers", "papers"), ("patents", "patents")):
        stats = report[table_key]
        if not stats["domains"]:
            continue
        for d in stats["domains"]:
            cells = stats["matrix"][d]
            row_total = sum(cells.values())
            zero_years = [y for y in stats["years"] if cells.get(y, 0) == 0]
            low_years = [
                y for y in stats["years"]
                if 0 < cells.get(y, 0) < gap_threshold
            ]
            if row_total < gap_threshold * len(stats["years"]) // 2:
                suggestions.append(
                    f"  {table:<8} {d:<24} → 전반적으로 적음 ({row_total:,}건). "
                    f"`python run_collectors.py --type {table} --domain {d} --days 2300`"
                )
            elif zero_years:
                suggestions.append(
                    f"  {table:<8} {d:<24} → {','.join(zero_years)}년 0건. 보강 권장."
                )

    if not suggestions:
        print("  ✅ 도메인 × 연도 분포 양호")
    else:
        for s in suggestions[:15]:
            print(s)
        if len(suggestions) > 15:
            print(f"  ... (+{len(suggestions)-15} more)")


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect data coverage by domain × year",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--db",    default=DB_PATH, help=f"DB path (default: {DB_PATH})")
    parser.add_argument("--since", type=int, default=2020,
                        help="Cutoff year (default: 2020)")
    parser.add_argument("--gap-threshold", type=int, default=20,
                        help="Mark cells below this with ↓ and recommend refill (default: 20)")
    parser.add_argument("--by-source", action="store_true",
                        help="Print source breakdown per domain")
    parser.add_argument("--json",      action="store_true",
                        help="Emit JSON report only (machine-readable)")
    args = parser.parse_args()

    report = collect_health(args.db, args.since)

    if args.json:
        print(json.dumps(report, indent=2, default=str, ensure_ascii=False))
        return 0

    print(f"# TechPulse Data Health  ({report['as_of']})")
    print(f"  DB: {report['db_path']}    cutoff year: ≥ {report['since']}")

    _print_matrix("Papers",  report["papers"],  args.gap_threshold, args.since)
    _print_matrix("Patents", report["patents"], args.gap_threshold, args.since)

    if args.by_source:
        print("\n## Sources per domain")
        for table_key in ("papers", "patents"):
            stats = report[table_key]
            print(f"  [{table_key}]")
            for d, sc in stats["by_source"].items():
                src_str = ", ".join(f"{k}={v:,}" for k, v in sorted(sc.items()))
                print(f"    {d:<24} {src_str}")

    _print_freshness(report["freshness"])
    _print_quality(report["quality"])
    _print_recommendations(report, args.gap_threshold)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
