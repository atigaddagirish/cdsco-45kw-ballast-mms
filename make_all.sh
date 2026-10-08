#!/usr/bin/env bash
# Rebuilds every deliverable from the single source of truth (calc/inputs.py). Needs: python3 + openpyxl matplotlib python-docx numpy; LibreOffice (calc) for recalculation/verification.
set -euo pipefail
cd "$(dirname "$0")/calc"
python3 verify_udl.py                   # 1. closed-form (UDL zones) vs matrix-solver cross-check, both wind modes
python3 build_excel.py                  # 2. formula workbook
python3 verify_excel.py                 # 3. LibreOffice recalculation, 218 cells vs engine
python3 test_linked.py                  # 4. live-linkage test (inputs changed -> outputs follow)
python3 staad_gen.py && python3 verify_std.py && python3 verify_std.py ../staad/alt/CDSCO_45kW_Ballast_Frame_R1_windUDL.std   # 5. STAAD input (+alt) + round-trip check
python3 figures.py && python3 build_report.py   # 6. figures + Word report
# 7. ship the recalculated workbook (cached values visible in any viewer)
cp "${RECALC_DIR:-/tmp/recalc}/CDSCO_45kW_Ballast_MMS_Design_Calc.xlsx" ../excel/ 2>/dev/null || true
