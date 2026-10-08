# Revision R1 - module dead load as UDL on the rafters (client comment)

**Client comment (verbatim intent):** no purlins are provided and the PV modules are directly supported by the rafters, so the module self-weight shall not be taken as concentrated/point loads at the joints; apply it as an appropriate UDL on the supporting rafters from the actual module dimensions, support arrangement and tributary length; revise STAAD, analysis/design and load calculations.

## What changed
| Item | R0 | R1 |
|---|---|---|
| Module dead load | 2 point loads Wm/4 at the module-bolt nodes | UDL on each rafter, w = (Wm / (L x W)) x (L/2) = Wm/(2W) = 0.12587 N/mm over the 1134 mm contact zone (16.5 ... 1150.5 mm from bolt B) |
| Rafter self-weight | lumped at the module bolts | UDL 0.03953 N/mm over B-C (total weight conserved) |
| Seismic mass (module, rafter) | point loads | horizontal UDL (Ah x w) |
| STAAD | 10 nodes / 10 members | 12 nodes / 12 members (Pa, Pb delimit the zone); UNI GY on members 8-11 and 7-12 |
| Excel | rafter statics for point loads | closed form with UDL zones, exact zero-shear peak moment, module-bolt demand rows, tributary derivation (sheet Loads), sheet **Revision** |
| B-C working length | drawn 1165.62 | hypot(AC, AB) = 1165.6185 (closure -0.0015 mm kept as a check; removes a 1e-6 inconsistency) |

## Tributary derivation (support arrangement)
Module 2279 x 1134 mm, 29.1 kg (285.5 N) -> 0.1105 kN/m2. Two rafters 1400 mm c/c, centred -> 439.5 mm overhang each side carried by the module; each rafter takes half the module (tributary width 1139.5 mm). Module parallel to the rafter and bearing over its full width 1134 mm. w = 0.1105 kN/m2 x 1.1395 m = 0.1259 kN/m; w x 1134 = 142.7 N = Wm/2 per rafter (check cell `l_udl_chk` = 0).

## Module wind (decision recorded)
Wind suction/pressure reaches the rafter through the 4 M8 bolts, so it stays as bolt point loads (wind_mode 0). A bounding alternative with wind also as a UDL (wind_mode 1; `staad/alt/...windUDL.std`) is provided: rafter |M| 213.9 N.m, utilisation 0.41, deflection 1.29 mm - passes. Reactions and ballast are identical in both.

## Effect on results
Only the rafter changes: peak moment 28.2 -> 58.7 N.m, N+M utilisation 0.058 -> 0.116, deflection 0.20 -> 0.41 mm (limit 6.48). Reactions J1..J4, J-bolt tension, base member, bolts and ballast length (633 mm -> 650 mm adopted, sliding governs) are unchanged to 0.1 N.

## Verification (all reproducible)
- closed form vs matrix solver (rafter split at Pa, Pb): 2e-10, both wind modes; peak moment vs dense scan 2e-5
- Excel recalculated in LibreOffice vs engine: 308 cells, 1.7e-13, 0 errors; live linkage (10 inputs incl. module width and wind_mode): 3e-15
- STAAD text round-trip (both files): 5e-8
- NOT done: STAAD.Pro run (check LC1 reaction sum = 243.5 N)
