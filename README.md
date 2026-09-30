# CDSCO Hyderabad — 45 kWp Ballast-Type Rooftop MMS

Design package for the client request: *editable Excel design calculations + STAAD model/analysis file
for review and approval.*

- Client / EPC: M/s Sai Babuji Projects Pvt Ltd · Design & Engg: M/s JSP Solar Energy
- Site: CDSCO, Hyderabad · 3-storey RCC building roof · ballast (no roof penetration)
- Members: hot-rolled ISA 50x50x5 → **IS 800:2007 LSD**
- Loads: IS 875 Pt 1/2/3 (+ IS 1893:2016 Pt 1 for horizontal/sliding)
- Standing rule: every check cites its IS clause; inferences are flagged vs verified facts.

## Folder plan
| Path | Content |
|---|---|
| `inputs/` | Client drawing + hardware BOM (as received) |
| `docs/01_input_extraction.md` | Facts read from the drawings, cross-checks, open questions |
| `excel/` | Linked, formula-driven calc workbook (Inputs → Loads → Combos → Members → Connections → Ballast) |
| `staad/` | Generated `.std` model + run notes (analysis is run on Windows/STAAD) |
| `report/` | Load-calc document, STAAD XtraReport figures, design summary |

## Status
Inputs extracted; awaiting design-basis answers (wind terrain/height, module data, block size, roof finish, code basis for anchorage).
