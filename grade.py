
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).parent
FILES = ["tests/planted.csv", "tests/clean.csv", "sample.csv", "Kisumu_Crop_County_Data_2014-2016.csv"]
MILESTONES = [
    (0, "padded_text", "Worked example (already written for you)"),
    (1, "placeholder", "Placeholders such as n/a and -"),
    (2, "empty_cell", "Empty cells"),
    (3, "duplicate_row", "Duplicate rows"),
    (4, "messy_header", "Messy headers"),
    (5, "label_variant", "One label written several ways"),
    (6, "text_in_numbers", "Text in a numeric column"),
    (7, "outlier", "Outliers"),
    (8, "mixed_dates", "Mixed date formats"),
]


def load_module(path):
    spec = importlib.util.spec_from_file_location("target", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def results(mod):
    """{file: {check: sorted [[column, count], ...]}}"""
    out = {}
    for name in FILES:
        df = mod.load(HERE / name)
        by = {}
        for f in mod.run_checks(df):
            by.setdefault(f["check"], []).append([f["column"], int(f["count"])])
        out[name] = {k: sorted(v) for k, v in by.items()}
    return out


def main():
    args = sys.argv[1:]
    if args and args[0] == "--make":                       # regenerate the answer key from the reference
        (HERE / "tests/expected.json").write_text(json.dumps(results(load_module(HERE / "validate.py")), indent=1))
        print("expected.json written")
        return

    target = Path(args[0]) if args else HERE / "rebuild" / "validate.py"
    expected = json.loads((HERE / "tests/expected.json").read_text())
    try:
        got = results(load_module(target))
    except Exception as e:                                 # a crash is a result too
        print(f"Your tool crashed before grading could finish:\n  {type(e).__name__}: {e}")
        sys.exit(1)

    print(f"Grading {target}\n")
    passed = 0
    for num, check, title in MILESTONES:
        problems = []
        for name in FILES:
            want, have = expected[name].get(check, []), got[name].get(check, [])
            if want != have:
                missed = [w for w in want if w not in have]
                extra = [h for h in have if h not in want]
                short = Path(name).name
                if missed:
                    problems.append(f"{short}: missed {len(missed)} finding(s), e.g. column '{missed[0][0]}' should report {missed[0][1]} cell(s)")
                if extra:
                    problems.append(f"{short}: {len(extra)} unexpected finding(s), e.g. column '{extra[0][0]}' reported {extra[0][1]} cell(s)")
        ok = not problems
        passed += ok
        print(f"{'PASS' if ok else 'FAIL'}  Milestone {num}: {title}  [{check}]")
        for p in problems[:4]:
            print(f"        {p}")

    known = {c for _, c, _ in MILESTONES}
    stray = sorted({c for f in got.values() for c in f} - known)
    if stray:
        print(f"\nNote: your tool reports check names the grader does not know: {stray}")
    clean = sum(len(v) for v in got["tests/clean.csv"].values())
    print(f"\nClean-file test: {'PASS' if clean == 0 else 'FAIL'} ({clean} findings on tests/clean.csv, should be 0)")
    pct = round(100 * passed / len(MILESTONES))
    grade = "S" if pct >= 95 else "A" if pct >= 80 else "B" if pct >= 60 else "C" if pct >= 40 else "D"
    print(f"\nScore: {passed} / {len(MILESTONES)} milestones  ({pct}%)  Grade {grade}")


if __name__ == "__main__":
    main()
