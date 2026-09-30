# Design-basis decisions (confirmed by user) and package plan

## Confirmed decisions
| # | Topic | Decision | Justification |
|---|---|---|---|
| 1 | Wind Cp | IS 875 (Pt 3) Table 7 free-roof (mono-slope), linear interpolation at tilt 10.115° | Same chain as ground-mount reports; code-traceable. **Limit:** IS 875-3 has no roof edge/corner zoning or rooftop-PV clause → stated in report [inference: acceptable to client]. |
| 2 | J-bolt | **M16 primary (as drawn/BOM) + M10 alternate** side by side | Drawing Ø18 holes and BOM fix M16; alternate shows if M10 works before any drawing revision. |
| 3 | Anchorage | IS-only: IS 800:2007 cl.10.3.5/10.3.6 bolt tension + IS 456:2000 cl.26.2 bond/hook + block-weight uplift | No IS covers concrete-cone breakout → gap declared in report, no non-IS check added. |
| 4 | STAAD joints | Pinned in-plane at all bolted joints; base member = beam on 2 block supports | 1 bolt/joint cannot transfer moment (cl.10 lap joints); conservative for inclined member. |
| 5 | Design method | IS 800:2007 LSD, service-check deflection with unfactored loads | Per brief (hot-rolled members). |

## Workbook plan (`excel/`, all cross-sheet formulas, yellow = input)
1. Inputs · 2. Geometry (nodes from tilt/holes) · 3. Sections (IS 808 ISA 50x50x5) · 4. Wind (IS 875-3: Vb→Vz→pz→pd, Cp) ·
5. Loads (DL, LL/maintenance, IS 1893:2016 EQ) · 6. Combinations (IS 800 Table 4; stabilising DL 0.9) ·
7. STAAD paste-in (envelope forces, reactions) · 8. Member checks (IS 800 cl.6, 7, 8, 9/10.7; single-angle rules) ·
9. Bolt checks (cl.10.3 shear/bearing/tension/combined; oversize-hole reduction) · 10. Ballast stability (uplift, sliding, overturning) ·
11. J-bolt anchorage (M16 & M10) · 12. Deflection (IS 800 Table 6) · 13. Summary (UR, PASS/FAIL, clause column)

## Cross-verification plan (cannot run STAAD in this Linux sandbox)
- Generate `staad/*.std` (INPUT WIDTH 79, LOAD LIST on combinations, PRINT ALL).
- Independent Python 2D frame solve of the same model → expected reactions/forces in `docs/`, so the user's STAAD run has a hand-check to match.
- User runs STAAD on Windows → returns `.ANL` → parse → paste-in sheet → XtraReport figures.

## Still needed from user
Module data + frame spacing · block length/grade · roof finish (μ), RL, parapet, access · terrain cat + building height ·
steel grade/coating · seismic zone/importance · ENG no./livery/rev/initials.
