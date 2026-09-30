# Input extraction — drawing AL-001 R0 (10.09.2026, "FOR INFORMATION") + hardware BOM

Legend: **[V]** verified (drawn value, cross-checked) · **[I]** inference (needs confirmation)

## 1. Geometry (one frame, side elevation)
| Item | Value | Basis |
|---|---|---|
| All members | ISA 50x50x5 (base, vertical, inclined) | [V] drawing |
| Base member | 1200 mm; Ø18 holes @175/325/875/1025 (J-bolts); Ø14 @27.5 (L end) & @25 (R end) | [V] |
| Vertical member | 249.72 mm; Ø14 @22.5 both ends (204.72 c/c) | [V] |
| Inclined member | 1222.01 mm; Ø14 @27.47 / 28.92 (1165.62 c/c); 9x14 slots @67 from each end (1088 c/c) | [V] |
| Bolt-centre triangle | base 1147.5, rise 204.72, hyp = 1165.6185 vs drawn 1165.62 (Δ 0.002 mm) | [V] closes exactly |
| **Tilt** | **atan(204.72/1147.5) = 10.115°** (NOT 250/1200 = 11.77°, which ignores hole offsets) | [V] |
| Blocks | 300 wide × 250 high (slope direction); **c/c 700**; 2 J-bolts/block @150 c/c, Ø16 | [V] drawing dims; block-height reading = [I] |
| Block length (across frame) | **unknown** | open |
| Load points on inclined member | two module bolts @1088 c/c; support holes @1165.62 c/c | [V] |
| Base-member overhang (support centre → connection bolt) | 250−27.5 = 222.5 mm (high end), 1175−950 = 225 mm (low end) | [V] derived |

## 2. Hardware BOM (82 tables)
| # | Item | Grade | Size | L | Qty/table | Total (82) |
|---|---|---|---|---|---|---|
| 1 | Base→Inclined | HDG 8.8 | M12 | 30 | 2 | 164 |
| 2 | Base→Vertical | HDG 8.8 | M10 | 30 | 2 | 164 |
| 3 | Vertical→Inclined | HDG 8.8 | M10 | 30 | 2 | 164 |
| 4 | Module→Inclined | SS 304 | M8 | 25 | 4 | 328 |
| 5 | J-bolt | HDG 8.8 | **M16** | 150 | 8 | 656 |

(BOM "Total Qty" column prints `#####` — column too narrow; totals above are 82 × qty/table.)

## 3. Inferences
- [I] 1 table = 1 module: 45 kWp / 82 = 548.8 Wp ≈ 550 Wp module.
- [I] 1 table = 2 frames (BOM: 2 bolts per joint-type per table, 4 module bolts = 2 frames × 2 slots) and 4 blocks
  (8 J-bolts = 4 blocks × 2). Frame-to-frame spacing not on the drawing.
- [I] One bolt per member-to-member joint → pin-type joints in-plane.

## 4. Discrepancies / flags
1. **J-bolt size**: drawing/BOM = M16 (Ø18 holes); brief says "check with M10". Which governs?
2. **M10 bolts in Ø14 holes** (BOM #2, #3): 4 mm clearance = oversized → IS 800:2007 Table 19 / cl. 10.3.4 bearing reduction (verify clause text before use).
3. Drawing note says "dimensions in meters" but all values are mm — cosmetic, ask drafter to fix.
4. Members only labelled "L-50X50X5"; steel grade & coating not stated (assume IS 2062 E250, HDG — [I]).
