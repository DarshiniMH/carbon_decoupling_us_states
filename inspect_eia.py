"""
Run this FIRST, once, to see your CO2 workbook's real layout. If the tidy output
from transform.load_co2_total() looks wrong, compare it to what this prints and
adjust the `sheet` argument (or the parser). Paste this output if you want help.

    python inspect_eia.py
"""

import glob

import pandas as pd

path = sorted(glob.glob("data/eia_co2/*/CO2_total.xlsx"))[-1]
xls = pd.ExcelFile(path)
print("file  :", path)
print("sheets:", xls.sheet_names)

for sheet in xls.sheet_names[:4]:
    print(f"\n==== sheet: {sheet} ====")
    print(pd.read_excel(path, sheet_name=sheet, header=None).head(12).to_string())
