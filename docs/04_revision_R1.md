# Revision R1 - module dead load and wind as UDL on the rafters

**Client comment (intent):** no purlins are provided and the PV modules are directly supported by the rafters, so the module self-weight shall not be taken as concentrated/point loads at the joints; apply it as an appropriate UDL on the supporting rafters from the actual module dimensions, support arrangement and tributary length; revise STAAD, analysis/design and load calculations.
**Instruction (JSP):** apply UDL for wind too. (An earlier R1 draft kept wind at the module bolts; it is superseded and survives only as the alternate `wind_mode 0` / `staad/alt/..._windBolts.std`.)

## What changed
| Item | R0 | R1 |
|---|---|---|
| Module dead load | 2 point loads Wm/4 at the module-bolt nodes | UDL on each rafter, w = (Wm / (L x W)) x (L/2) = Wm/(2W) = 0.12587 N/mm over the 1134 mm contact zone (16.5 ... 1150.5 mm from bolt B) |
| Module wind | 2 point loads N/4 at the module-bolt nodes | UDL over the same zone, q = (N_module/2)/W normal to the rafter: 0.9380 N/mm uplift, 0.5233 N/mm downward |
| Rafter self-weight | lumped at the module bolts | UDL 0.03953 N/mm over B-C (total weight conserved) |
| Seismic mass (module, rafter) | point loads | horizontal UDL (Ah x w) |
| STAAD | 10 nodes / 10 members | 12 nodes / 12 members (Pa, Pb delimit the zone); UNI GY/GX on members 8-11 (module, wind) and 7-12 (rafter) |
| Excel | rafter statics for point loads | closed form with UDL zones, exact zero-shear peak moment, module-bolt demand rows, tributary derivation (sheet Loads), `wind_mode` switch (1 = UDL, 0 = bolts), sheet **Revision** |
| B-C working length | drawn 1165.62 | hypot(AC, AB) = 1165.6185 (closure -0.0015 mm kept as a check) |

## Tributary derivation (support arrangement)
Module 2279 x 1134 mm, 29.1 kg (285.5 N) -> 0.1105 kN/m2. Two rafters 1400 mm c/c, centred -> 439.5 mm overhang each side carried by the module; each rafter takes half the module (tributary width 1139.5 mm). Module parallel to the rafter and bearing over its full width 1134 mm. w = 0.1105 kN/m2 x 1.1395 m = 0.1259 kN/m; w x 1134 = 142.7 N = Wm/2 per rafter (check cell `l_udl_chk` = 0). Wind pressure acts on the module surface and is carried with the same tributary: q = pd x |Cp| x L/2 = (N_module/2)/W.
The four M8 bolts still make the module-to-rafter connection: bolt demand = module wind force / 4 (tension) and Wm sin(tilt)/4 + Ah terms (shear) - unchanged.

## Effect on results
| | R0 | R1 (dead + wind UDL) |
|---|---|---|
| Rafter peak moment (strength combos) | 28.2 N.m | **213.9 N.m**, governing combination C2 = 0.9DL + 1.5WL(uplift) (C1: 174.7) |
| Rafter N+M utilisation (T / C) | 0.054 / 0.058 | **0.402 / 0.406** (Md = 534 N.m) |
| Rafter deflection (service) | 0.20 mm | **1.29 mm** (limit L/180 = 6.48 mm) |
| Rafter shear / axial | 715 N / 104-157 N | 716 N / 104-157 N |
| Reactions J1..J4, J-bolt tension, base member, M8/M10/M12 bolts, ballast length | - | **unchanged** (resultant and line of action of the module loads are the same; reactions agree to 0.1 N) |

Alternate (wind at the 4 bolts): rafter |M| 58.7 N.m, UR 0.116, deflection 0.41 mm - bounded by the design basis above.

## Verification (all reproducible with make_all.sh)
- closed form vs matrix solver (rafter split at Pa, Pb): 2e-10, both wind modes; peak moment vs dense scan 2e-5
- Excel recalculated in LibreOffice vs engine: 308 cells, 6e-15, 0 errors; live linkage (10 inputs incl. module width, wind_mode): 4e-15
- STAAD text round-trip (primary and alternate file): 5e-8
- NOT done: STAAD.Pro run (checks: LC1 reaction sum 243.5 N; LC2 -1047.2 N)
