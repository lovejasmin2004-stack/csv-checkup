# csv-checkup

Point it at any CSV file and it reports the data-quality problems in it. No setup, and no rules to write first.

It was built for the first ten minutes of any data-cleaning job: finding out what is wrong before touching anything.

## What it checks

| Check | Catches |
|---|---|
| `messy_header` | Column names with stray spaces or a space inside brackets |
| `padded_text` | Cells with spaces before or after the value |
| `placeholder` | `n/a`, `-`, `Nil` and similar typed in place of a value |
| `empty_cell` | Cells with nothing in them |
| `duplicate_row` | Rows that repeat an earlier row |
| `label_variant` | One label written several ways (`Kenya`, `kenya `, `Kenya.`) |
| `text_in_numbers` | Words in a column that is otherwise numbers |
| `outlier` | Numbers far outside the rest of their column |
| `mixed_dates` | More than one date format in a column |

No check refers to a column by name, so the tool works on files it has never seen.

## Run it

Needs Python 3.10 or later and Pandas.

```
python -m pip install pandas
python validate.py yourfile.csv
python validate.py yourfile.csv --csv report.csv
```

The input file is never changed. The tool only reports.

## Try it in the browser

`index.html` runs the same checks in a web page. The file you drop in is read inside your own browser tab and is not uploaded anywhere.

To run the page locally on Windows, double-click `run_demo.bat`. On other systems:

```
python -m http.server 8000
```

Then open `http://localhost:8000/index.html`.

The page also works when opened directly as a file, because it carries its own copy of the checks and the example data. After changing `validate.py`, run `python build_page.py` to refresh that copy.

## Result on a real dataset

Test file: *Kenya – Kisumu county Crop production Data 2014–2016*, 408 rows and 11 columns of monthly county crop reports.

| Finding | Detail |
|---|---|
| 3 messy headers | `PRODUCTION ESTIMATES( Tonnes)` and two more with a space inside the bracket |
| 426 padded cells | Every crop name is padded, e.g. `' Maize       '` |
| 349 placeholders | `N/A` and `Nil` across three text columns |
| 6 empty cells | Including two number columns on the same row |
| 189 label variants | The county is written `Kisumu` 180 times and `Kisumu.` 228 times |
| 25 outliers | Large stock and production figures, flagged for review |

22 findings in total, covering 998 cells. On a tidy control file (`tests/clean.csv`) it reports nothing.

## What it does not do

- It does not decide which spelling of a label is correct. It reports that they disagree.
- An outlier is a value to look at, not an error. Large maize stocks after harvest are real.
- It does not catch near-miss typos such as `Harvested` and `Harvesyed`.
- It knows nothing about the subject. It cannot tell that a yield of 45 t/ha is implausible for sorghum; that needs dataset-specific rules.

## Tests

`grade.py` runs the checks on four files and compares the findings with a stored answer key.

```
python grade.py validate.py
```

## What I learned

*(Rewrite this section in your own words after the rebuild.)*

## Data credit

Kenya – Kisumu county Crop production Data 2014–2016. Source: Kenya National Bureau of Statistics, published by the Kenya Open Data Initiative on the Humanitarian Data Exchange. Licence: Creative Commons Attribution (CC BY).
