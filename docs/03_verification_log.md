# Verification log (run 30-Sep-2026, all reproducible with `calc/make_all.sh`)

| # | Test | Result |
|---|---|---|
| 1 | Matrix solver self-test (SS beam, cantilever, 2-span UDL) | exact (deflection 1.04167 mm, 16.6667 mm; reactions 375/1250/375) |
| 2 | Closed-form frame statics vs matrix solver, 4 load cases (reactions, moments, axial, tip deflections) | worst relative difference 1.7e-11 |
| 3 | Equilibrium identities: sum R = sum P (base beam); inclined-member end axial = Cx cos - Cy sin | 0 to machine precision |
| 4 | Excel recalculated in LibreOffice 24.2 vs Python engine (218 cells, every sheet) | worst 1.2e-14; 0 formula errors in 1271 formulas |
| 5 | Live linkage: 7 inputs changed (k1, terrain, mu, block length, module weight, Vb, roof height) -> recalculated Excel vs engine (14 outputs) | worst 3.4e-15 |
| 6 | STAAD .std text re-parsed and solved for combos 11-18 vs workbook | worst 5.5e-8 (6-decimal print precision) |
| 7 | Triangle closure from drawn dimensions (1147.5 / 204.72 / 1165.62) | 0.0015 mm |
| 8 | ISA 50x50x5 from exact geometry vs IS 808 catalogue (A, Ixx, Iuu, Ivv) | within 1 %; search-snippet values rejected (Iuu+Ivv != Ixx+Iyy) |

NOT verified: an actual STAAD.Pro run; primary text of IS 875-3, IS 800, IS 456, IS 1893 (egress-blocked) - see Excel sheet `Register`.
