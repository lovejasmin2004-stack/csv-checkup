"""csv-checkup: Reports data-quality problems.

    python validate.py some_file.csv
    python validate.py some_file.csv --csv report.csv     (also save the report)
"""
import re
import sys

import pandas as pd


PLACEHOLDERS = {"n/a", "na", "nan", "nil", "null", "none", "-", "--", "?"}

DATE_SHAPES = {
    "YYYY-MM-DD": r"\d{4}-\d{1,2}-\d{1,2}",
    "DD.MM.YYYY": r"\d{1,2}\.\d{1,2}\.\d{4}",
    "DD/MM/YYYY": r"\d{1,2}/\d{1,2}/\d{2,4}",
    "Mon-YYYY": r"[A-Za-z]{3,9}-\d{4}",
    "Mon-YY": r"[A-Za-z]{3,9}-\d{2}",
    "DD-Mon": r"\d{1,2}-[A-Za-z]{3,9}",
}
TIME_PART = r"([ T]\d{1,2}:\d{2}(:\d{2})?)?"


# ---------------------------------------------------------------- helpers
def load(source):
    """Read every cell as text, exactly as typed, so nothing is hidden or converted."""
    try:
        return pd.read_csv(source, dtype=str, keep_default_na=False)
    except UnicodeDecodeError:                             # older files are often not UTF-8
        return pd.read_csv(source, dtype=str, keep_default_na=False, encoding="latin-1")


def finding(check, col, bad, df, message):
    """Build one line of the report. `bad` marks the problem cells in column `col`."""
    return {
        "check": check,
        "column": col,
        "count": int(bad.sum()),
        "rows": (df.index[bad] + 2).tolist()[:5],          # +2 = row number in a spreadsheet
        "examples": df.loc[bad, col].unique()[:3].tolist(),
        "message": message,
    }


def has_value(series):
    """True for cells that hold real content (not empty, not a placeholder)."""
    clean = series.str.strip()
    return (clean != "") & ~clean.str.lower().isin(PLACEHOLDERS)


def as_numbers(series):
    """Turn text into numbers where possible ('1,200' -> 1200). Anything else becomes NaN."""
    return pd.to_numeric(series.str.strip().str.replace(",", "", regex=False), errors="coerce")


def is_numeric_column(series):
    """A column counts as numeric when at least 80% of its real values are numbers."""
    real = has_value(series)
    if real.sum() == 0:
        return False
    return as_numbers(series[real]).notna().mean() >= 0.8


# ---------------------------------------------------------------- checks
# Every check takes the whole table and returns a list of findings.

def check_messy_headers(df):
    """Column names with stray spaces, e.g. ' date' or 'RAIN( mm)'."""
    out = []
    for col in df.columns:
        name = str(col)
        problems = []
        if name != " ".join(name.split()):
            problems.append("stray or doubled spaces")
        if re.search(r"\(\s|\s\)", name):
            problems.append("space inside brackets")
        if name.startswith("Unnamed:") or name.strip() == "":
            problems.append("no name")
        if problems:
            out.append({"check": "messy_header", "column": name, "count": 1, "rows": [1],
                        "examples": [name], "message": "Header has " + " and ".join(problems)})
    return out


def check_padded_text(df):
    """Cells with spaces before or after the value, like ' Maize  '."""
    out = []
    for col in df.columns:
        bad = df[col] != df[col].str.strip()
        if bad.any():
            out.append(finding("padded_text", col, bad, df, "Spaces before or after the value"))
    return out


def check_placeholders(df):
    """Cells holding a stand-in for 'no value', like n/a or -."""
    out = []
    for col in df.columns:
        bad = df[col].str.strip().str.lower().isin(PLACEHOLDERS)
        if bad.any():
            out.append(finding("placeholder", col, bad, df, "Placeholder instead of a value"))
    return out


def check_empty_cells(df):
    """Cells with nothing in them."""
    out = []
    for col in df.columns:
        bad = df[col].str.strip() == ""
        if bad.any():
            out.append(finding("empty_cell", col, bad, df, "Empty cell"))
    return out


def check_duplicate_rows(df):
    """Rows that repeat an earlier row exactly."""
    bad = df.duplicated(keep="first")
    if not bad.any():
        return []
    return [{"check": "duplicate_row", "column": "(whole row)", "count": int(bad.sum()),
             "rows": (df.index[bad] + 2).tolist()[:5], "examples": [],
             "message": "Row repeats an earlier row"}]


def check_label_variants(df):
    """One label written several ways: 'Kenya', 'kenya ', 'Kenya.'"""
    out = []
    for col in df.columns:
        if is_numeric_column(df[col]):
            continue
        real = has_value(df[col])
        # The "key" is the label with case, spacing and end punctuation ignored.
        key = df[col].str.lower().str.split().str.join(" ").str.strip(" .,;:")
        bad = pd.Series(False, index=df.index)
        for _, group in df.loc[real, col].groupby(key[real]):
            if group.nunique() > 1:
                most_common = group.value_counts().idxmax()
                bad |= real & (key == key[group.index[0]]) & (df[col] != most_common)
        if bad.any():
            out.append(finding("label_variant", col, bad, df, "Same label written in more than one way"))
    return out


def check_text_in_numbers(df):
    """Text sitting in a column that is otherwise numbers."""
    out = []
    for col in df.columns:
        if not is_numeric_column(df[col]):
            continue
        bad = has_value(df[col]) & as_numbers(df[col]).isna()
        if bad.any():
            out.append(finding("text_in_numbers", col, bad, df, "Text in a numeric column"))
    return out


def check_outliers(df):
    """Numbers far outside the rest of their column (beyond 3 x the interquartile range)."""
    out = []
    for col in df.columns:
        if not is_numeric_column(df[col]):
            continue
        nums = as_numbers(df[col])
        base = nums[nums.notna() & (nums != 0)]            # zeros often mean "none", so leave them out
        if len(base) < 5:
            continue
        q1, q3 = base.quantile(0.25), base.quantile(0.75)
        spread = q3 - q1
        if spread == 0:
            continue
        bad = nums.notna() & (nums != 0) & ((nums < q1 - 3 * spread) | (nums > q3 + 3 * spread))
        if bad.any():
            out.append(finding("outlier", col, bad, df, "Value far outside the rest of the column"))
    return out


def check_mixed_dates(df):
    """A date column that uses more than one date format."""
    out = []
    for col in df.columns:
        real = has_value(df[col])
        if real.sum() == 0:
            continue
        shape = pd.Series("", index=df.index)
        for name, pattern in DATE_SHAPES.items():
            hit = real & (shape == "") & df[col].str.strip().str.fullmatch(pattern + TIME_PART)
            shape[hit] = name
        if (shape[real] != "").mean() < 0.8 or shape[real].nunique() < 2:
            continue                                       # not a date column, or only one format
        usual = shape[real & (shape != "")].value_counts().idxmax()
        bad = real & (shape != usual)
        out.append(finding("mixed_dates", col, bad, df, f"Date not in the column's usual format ({usual})"))
    return out


CHECKS = [
    check_messy_headers,
    check_padded_text,
    check_placeholders,
    check_empty_cells,
    check_duplicate_rows,
    check_label_variants,
    check_text_in_numbers,
    check_outliers,
    check_mixed_dates,
]


def run_checks(df):
    findings = []
    for check in CHECKS:
        findings += check(df)
    return findings


# ---------------------------------------------------------------- run
def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print("Usage: python validate.py yourfile.csv [--csv report.csv]")
        sys.exit(1)
    path = args[0]
    df = load(path)
    findings = run_checks(df)

    print(f"{path}: {len(df)} rows, {len(df.columns)} columns\n")
    for f in findings:
        print(f"[{f['check']}] column '{f['column']}': {f['count']} cells. {f['message']}.")
        print(f"    rows {f['rows']}  examples {f['examples']}")
    cells = sum(f["count"] for f in findings)
    print(f"\n{len(findings)} findings covering {cells} cells")

    if "--csv" in args:
        out = args[args.index("--csv") + 1]
        pd.DataFrame(findings).to_csv(out, index=False)
        print(f"Report saved to {out}")


if __name__ == "__main__":
    main()
