# CDSCO Hyderabad - 45 kWp Ballast-Type Rooftop MMS (revision R1)

Client request: *editable Excel design calculations + STAAD model/analysis file for review and approval.*
**R1 (this revision):** module dead load applied as UDL on the rafters per client comment - see `docs/04_revision_R1.md` and Excel sheet `Revision`. R0 is preserved in git history at commit `09b5d58` (docs/R0_results.json holds the R0 numbers).
EPC: M/s Sai Babuji Projects Pvt Ltd - Design & Engg: M/s JSP Solar Energy - Drawing AL-001 R0 - Hardware BOM (82 tables).

## Deliverables
| File | What it is |
|---|---|
| `excel/CDSCO_45kW_Ballast_MMS_Design_Calc.xlsx` | 18-sheet formula-linked workbook (1641 formulas, 488 named cells). Change inputs only on `Inputs`. Flow: Inputs > Section > Geometry > Wind > Loads > Analysis > Combos > Members > Connections > Ballast > Anchorage > Deflection > Summary. `STAAD_Map` compares Excel vs STAAD; `Register`/`Notes` list every source, assumption and drawing observation. |
| `staad/CDSCO_45kW_Ballast_Frame.std` | STAAD.Pro plane-frame model (one frame, 12 nodes), module weight as UNI loads on the rafter, LSD combinations 11-18. **Not yet run in STAAD** (see `staad/REPORT_STEPS.md`). `staad/alt/` = bounding case with module wind also as UDL. |
| `staad/expected_results.csv` | Reactions / axial / displacements to match when STAAD is run. |
| `report/CDSCO_45kW_Ballast_MMS_Design_Report.docx` | Load-calculation and design report with figures, sensitivity, observations, verification register. |
| `report/CDSCO_45kW_Ballast_MMS_Design_Report.md` | Same report in Markdown (generated from the same engine; figures in `report/figures/`). |
| `calc/` | Python engine (single source of truth `inputs.py`), independent matrix solver, generators, verification scripts. `make_all.sh` rebuilds everything. |
| `docs/` | Drawing extraction, design-basis decisions, verification log. |

## Headline results (base case)
- Tilt 10.115 deg; pd = 0.910 kN/m2 (Vb 44, k1 0.91, Cat 2, z 12.5 m); uplift 2.13 kN / down 1.19 kN per module.
- Members, bolts, J-bolts, deflection: all PASS, UR <= 0.21 (bolts <= 0.05). R1: rafter peak moment 58.7 N.m (R0 28.2), rafter UR 0.12; everything else unchanged.
- **Ballast governs - sliding under uplift (mu 0.4): blocks 300 x 250 x 650 mm (119 kg), UR 0.93.** Block length is not on the drawing.
- M10 J-bolt is adequate (required length 140 mm); drawn M16 length 150 mm is adequate.
- **Drawing non-conformance:** Ø18 J-bolt holes have 22.5 mm edge distance < 27 mm (IS 800 cl 10.2.4.2).

## Decisive open inputs (one cell each; sensitivity in report Sec. 11)
k1 / design life (0.91 vs 1.0), terrain category & building height, roof friction, seismic Rp (Rp = 1 gives seismic sliding UR 1.04 for any block size), module data, steel grade.
