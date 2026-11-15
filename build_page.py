"""Copies validate.py and the example CSV into index.html, so the page also
works when it is opened by double-clicking (no web server needed).

Run this after changing validate.py:

    python build_page.py
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
EXAMPLE = "Kisumu_Crop_County_Data_2014-2016.csv"

data = {
    "py": (HERE / "validate.py").read_text(encoding="utf-8"),
    "csv": (HERE / EXAMPLE).read_text(encoding="utf-8"),
}
blob = json.dumps(data).replace("</", "<\\/")
block = f"<!--EMBED-->\n<script>window.EMBED = {blob};</script>\n<!--/EMBED-->"

page = HERE / "index.html"
html = page.read_text(encoding="utf-8")
if "<!--EMBED-->" in html:
    html = re.sub(r"<!--EMBED-->.*?<!--/EMBED-->", lambda m: block, html, flags=re.S)
else:
    html = html.replace("<script>", block + "\n<script>", 1)
page.write_text(html, encoding="utf-8", newline="\n")
print(f"index.html updated ({len(data['py'])} characters of Python, {len(data['csv'])} of example data)")
