"""Builds the linked Excel calculation workbook (formulas only). Run: python3 build_excel.py [out.xlsx]"""
import re, sys, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.formatting.rule import CellIsRule
from openpyxl.utils import get_column_letter as CL
from inputs import INPUTS, T7, K2, TAUBD, BOLTS, SEC

NAVY, LBLUE, YEL, GRN, RED, GREY = "1F3864", "D9E2F3", "FFF2CC", "C6EFCE", "FFC7CE", "F2F2F2"
thin = Side(style="thin", color="BFBFBF"); BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
STATUS_TXT = {"V": "Verified", "I": "Inference/assumption"}


class Book:
    def __init__(self):
        self.wb = Workbook(); self.wb.remove(self.wb.active); self.names = {}

    def name(self, nm, sheet, ref):
        assert nm not in self.names, "duplicate name " + nm
        assert nm.lower() not in {k.lower() for k in self.names}, "case-insensitive duplicate name " + nm
        self.names[nm] = f"{sheet}!{ref}"
        self.wb.defined_names[nm] = DefinedName(nm, attr_text=f"{sheet}!{ref}")


class Sh:
    """One worksheet with a running row pointer. Columns: A step | B item | C name | D value | E unit | F basis | G status | H remarks"""
    def __init__(self, bk, title, widths=(6, 46, 16, 16, 9, 58, 9, 40), tab=None):
        self.bk, self.title = bk, title
        self.ws = bk.wb.create_sheet(title); self.r = 1; self.n = 0; self.cells = {}
        for i, w in enumerate(widths, 1): self.ws.column_dimensions[CL(i)].width = w
        if tab: self.ws.sheet_properties.tabColor = tab
        self.ws.sheet_view.showGridLines = False

    def banner(self, text, sub=""):
        ws = self.ws
        ws.cell(self.r, 1, text).font = Font(bold=True, size=14, color="FFFFFF")
        for c in range(1, 9): ws.cell(self.r, c).fill = PatternFill("solid", fgColor=NAVY)
        self.r += 1
        if sub:
            ws.cell(self.r, 1, sub).font = Font(italic=True, size=9, color="595959"); self.r += 1
        self.r += 1

    def section(self, text):
        ws = self.ws
        for c in range(1, 9): ws.cell(self.r, c).fill = PatternFill("solid", fgColor=LBLUE)
        ws.cell(self.r, 1, text).font = Font(bold=True, color=NAVY); self.r += 1

    def header(self, cols, start=1):
        for i, t in enumerate(cols):
            c = self.ws.cell(self.r, start + i, t); c.font = Font(bold=True, color="FFFFFF", size=9)
            c.fill = PatternFill("solid", fgColor="44546A"); c.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
            c.border = BORDER
        self.r += 1

    def std_header(self):
        self.header(["#", "Item", "Name", "Value", "Unit", "Formula / clause / basis", "Status", "Remarks"])

    def row(self, name, label, val, unit="", basis="", status="", fmt="0.000", inp=False, note=""):
        ws, r = self.ws, self.r; self.n += 1
        ws.cell(r, 1, self.n).font = Font(size=8, color="7F7F7F")
        ws.cell(r, 2, label); ws.cell(r, 3, name or "").font = Font(size=8, color="7F7F7F", italic=True)
        d = ws.cell(r, 4, val); d.number_format = fmt; d.border = BORDER
        d.alignment = Alignment(horizontal="right")
        if inp: d.fill = PatternFill("solid", fgColor=YEL); d.font = Font(color="0000FF", bold=True)
        ws.cell(r, 5, unit).font = Font(size=9)
        b = ws.cell(r, 6, basis); b.font = Font(size=9, color="404040"); b.alignment = Alignment(wrap_text=True, vertical="top")
        s = ws.cell(r, 7, status); s.font = Font(size=9, bold=True)
        s.alignment = Alignment(horizontal="center")
        ws.cell(r, 8, note).font = Font(size=9, italic=True, color="595959")
        if name: self.bk.name(name, self.title, f"$D${r}")
        self.cells[name or f"_r{r}"] = f"$D${r}"
        self.r += 1
        return f"{self.title}!$D${r}"

    def check(self, name, label, ur_formula, basis="", note=""):
        """UR row followed by PASS/FAIL"""
        a = self.row(name, label, ur_formula, "-", basis, fmt="0.000", note=note)
        r = self.r
        self.row(name + "_ok", "   status", f'=IF({name}<=1,"PASS","FAIL")', "", "", fmt="@")
        return a

    def blank(self, n=1): self.r += n

    def finish(self):
        red, grn = PatternFill("solid", fgColor=RED), PatternFill("solid", fgColor=GRN)
        rng = f"A1:{CL(14)}{self.r + 5}"
        self.ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"PASS"'], fill=grn, font=Font(color="006100", bold=True)))
        self.ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=['"FAIL"'], fill=red, font=Font(color="9C0006", bold=True)))
        self.ws.freeze_panes = "A4"


def absmax(rng): return f"MAX(MAX({rng}),-MIN({rng}))"


# ============================================================ sheet builders ==========================
def sh_inputs(bk):
    s = Sh(bk, "Inputs", widths=(6, 58, 16, 14, 9, 52, 9, 30), tab="FFC000")
    s.banner("1  INPUTS  -  all design inputs (yellow = editable)",
             "Every other sheet is linked to these cells by name. Status: V = verified fact, I = inference/assumption (flagged in report).")
    s.std_header()
    groups = [("Geometry - drawing AL-001 R0 (mm)", ["base_len", "base_end_A", "base_end_C", "vert_len", "vert_end", "incl_len",
               "incl_end_B", "incl_end_C", "slot_end", "slot_cc_dwg", "J_off", "J_pair", "J_mid", "J_gauge", "edge_min", "block_w",
               "block_h", "block_L", "bolt_h", "e_mod"]),
              ("Module & layout", ["mod_L", "mod_W", "mod_t", "mod_kg", "frame_sp", "wind_mode"]),
              ("Wind - IS 875 (Part 3)", ["Vb", "k1_risk", "terrain", "k3_topo", "k4_imp", "Kd_dir", "Ka_area", "Kc_comb", "z_bldg"]),
              ("Seismic - IS 1893 (Part 1):2016", ["Zf", "I_imp", "SaG", "Rp", "zh"]),
              ("Steel & bolts - IS 800:2007", ["fy", "fu", "Es", "gamma_m0", "gamma_m1", "gamma_mb", "gam_s", "gacc", "fub88", "fyb88",
               "fub_ss", "fyb_ss", "k_over", "d0_14", "d0_J", "d0_M8", "defl_div"]),
              ("Concrete / ballast - IS 875-1, IS 456", ["gam_c", "fck", "mu_f", "dl_stab", "ll_fac"])]
    fm = {"terrain": "0", "fck": "0", "Vb": "0.0", "wind_mode": "0"}
    for title, keys in groups:
        s.section(title)
        for k in keys:
            v, u, d, src, st = INPUTS[k]
            s.row(k, d, v, u, src, st, fmt=fm.get(k, "0.000"), inp=True)
    s.blank()
    s.section("Code tables (used by interpolation formulas)")
    s.header(["", "IS 875-3 Table 7  mono-slope free roof, solidity 0", "", "angle (deg)", "Cp down", "Cp uplift", "", ""])
    t7r0 = s.r
    for a, dn, up in T7:
        s.ws.cell(s.r, 4, a).number_format = "0"; s.ws.cell(s.r, 5, dn); s.ws.cell(s.r, 6, up)
        for c in (4, 5, 6): s.ws.cell(s.r, c).fill = PatternFill("solid", fgColor=YEL)
        s.r += 1
    bk.name("T7_ang", "Inputs", f"$D${t7r0}:$D${s.r-1}"); bk.name("T7_dn", "Inputs", f"$E${t7r0}:$E${s.r-1}"); bk.name("T7_up", "Inputs", f"$F${t7r0}:$F${s.r-1}")
    s.blank()
    s.header(["", "IS 875-3 Table 2  k2 (Cat 2 verified at 10 m; others recalled)", "", "height (m)", "Cat 2", "Cat 3", "", ""])
    k2r0 = s.r
    for h, dct in K2:
        s.ws.cell(s.r, 4, h); s.ws.cell(s.r, 5, dct[2]); s.ws.cell(s.r, 6, dct[3])
        for c in (4, 5, 6): s.ws.cell(s.r, c).fill = PatternFill("solid", fgColor=YEL)
        s.r += 1
    bk.name("K2_h", "Inputs", f"$D${k2r0}:$D${s.r-1}"); bk.name("K2_tab", "Inputs", f"$E${k2r0}:$F${s.r-1}")
    s.blank()
    s.header(["", "IS 456 Table 26.2.1.1  design bond stress, plain bars, tension", "", "fck (MPa)", "tau_bd", "", "", ""])
    tr0 = s.r
    for f, t in TAUBD.items():
        s.ws.cell(s.r, 4, f); s.ws.cell(s.r, 5, t)
        for c in (4, 5): s.ws.cell(s.r, c).fill = PatternFill("solid", fgColor=YEL)
        s.r += 1
    bk.name("TAU_tab", "Inputs", f"$D${tr0}:$E${s.r-1}")
    s.finish(); return s


def sh_section(bk):
    s = Sh(bk, "Section", tab="8EA9DB")
    s.banner("2  SECTION  -  ISA 50x50x5 (IS 808)", "Properties from exact polygon integration incl. root r1=7 / toe r2=3.5 (calc/section_isa.py); agree with IS 808 catalogue to <1%.")
    s.std_header(); s.section("Section properties (heel at origin; horizontal leg along +x, vertical leg along +y)")
    for k, lab, u, fm in [("A", "Area", "mm2", "0.0"), ("cx", "Centroid distance from back of each leg", "mm", "0.00"), ("Ixx", "Ixx (axis // horizontal leg)", "mm4", "#,##0"),
                          ("Iyy", "Iyy (axis // vertical leg)", "mm4", "#,##0"), ("Ixy", "Product of inertia Ixy", "mm4", "#,##0"),
                          ("b", "Leg length", "mm", "0.0"), ("t", "Thickness", "mm", "0.0"), ("r1", "Root radius", "mm", "0.0"), ("r2", "Toe radius", "mm", "0.0")]:
        s.row("sec_" + k, lab, SEC[k], u, "computed - exact polygon integration", "I", fmt=fm, inp=True)
    s.section("Derived")
    s.row("sec_Iuu", "Iuu (major principal)", "=(sec_Ixx+sec_Iyy)/2+SQRT(((sec_Ixx-sec_Iyy)/2)^2+sec_Ixy^2)", "mm4", "Mohr's circle", fmt="#,##0")
    s.row("sec_Ivv", "Ivv (minor principal)", "=(sec_Ixx+sec_Iyy)/2-SQRT(((sec_Ixx-sec_Iyy)/2)^2+sec_Ixy^2)", "mm4", "Mohr's circle", fmt="#,##0")
    s.row("sec_ruu", "ruu", "=SQRT(sec_Iuu/sec_A)", "mm", "", fmt="0.00"); s.row("sec_rvv", "rvv (min radius of gyration)", "=SQRT(sec_Ivv/sec_A)", "mm", "", fmt="0.00")
    s.row("sec_mass", "Mass per metre (gamma_s=78.5 kN/m3)", "=sec_A*1E-6*gam_s/gacc*1000", "kg/m", "catalogue 3.77-3.8", fmt="0.000")
    s.row("sec_D", "D = Ixx*Iyy - Ixy^2", "=sec_Ixx*sec_Iyy-sec_Ixy^2", "mm8", "", fmt="0.000E+00")
    s.row("sec_Ieff", "I_eff: in-plane stiffness, section free to deflect sideways", "=sec_D/sec_Iyy", "mm4", "angle loaded in plane of legs -> oblique deflection", fmt="#,##0",
          note="Used for deflections and STAAD IZ")
    s.section("Elastic modulus for in-plane bending (unsymmetric bending) - stress/unit M = (Iyy*y - Ixy*x)/D at each vertex")
    s.header(["", "vertex", "x (mm)", "y (mm)", "x-cx", "y-cy", "s=sigma/M gross", "Z=1/|s|", "s net", "Z net"][:8])
    sh0 = s.r
    verts = [("heel", "0", "0"), ("toe-h bottom", "sec_b", "0"), ("toe-h top", "sec_b", "sec_t"), ("inner corner", "sec_t", "sec_t"), ("toe-v inner", "sec_t", "sec_b"), ("toe-v outer", "0", "sec_b")]
    # net-section block (J-bolt hole in horizontal leg) defined first so vertex rows can use it
    for i, (nm, x, y) in enumerate(verts):
        r = s.r; ws = s.ws
        ws.cell(r, 2, nm); ws.cell(r, 3, f"={x}"); ws.cell(r, 4, f"={y}")
        ws.cell(r, 5, f"=C{r}-sec_cx"); ws.cell(r, 6, f"=D{r}-sec_cx")
        ws.cell(r, 7, f"=(sec_Iyy*F{r}-sec_Ixy*E{r})/sec_D")
        ws.cell(r, 8, f"=1/ABS(G{r})")
        s.r += 1
    sh1 = s.r - 1
    s.row("sec_Zg", "Z_eff gross = MIN(Z)", f"=MIN(H{sh0}:H{sh1})", "mm3", "critical fibre over all vertices, either moment sign", fmt="#,##0")
    s.section("Net section at J-bolt hole (hole in horizontal leg; centroid shift neglected)")
    s.row("sec_Ah", "Hole area = d0_J * t", "=d0_J*sec_t", "mm2", "", fmt="0.0")
    s.row("sec_xh", "Hole centre x from centroid", "=J_gauge-sec_cx", "mm", "", fmt="0.00"); s.row("sec_yh", "Hole centre y from centroid", "=sec_t/2-sec_cx", "mm", "", fmt="0.00")
    s.row("sec_Ixx_n", "Ixx net", "=sec_Ixx-sec_Ah*sec_yh^2", "mm4", "", fmt="#,##0"); s.row("sec_Iyy_n", "Iyy net", "=sec_Iyy-sec_Ah*sec_xh^2", "mm4", "", fmt="#,##0")
    s.row("sec_Ixy_n", "Ixy net", "=sec_Ixy-sec_Ah*sec_xh*sec_yh", "mm4", "", fmt="#,##0"); s.row("sec_D_n", "D net", "=sec_Ixx_n*sec_Iyy_n-sec_Ixy_n^2", "mm8", "", fmt="0.000E+00")
    for i in range(len(verts)):
        r = sh0 + i; s.ws.cell(r, 9, f"=(sec_Iyy_n*F{r}-sec_Ixy_n*E{r})/sec_D_n"); s.ws.cell(r, 10, f"=1/ABS(I{r})")
        s.ws.cell(r, 9).number_format = "0.0000E+00"; s.ws.cell(r, 10).number_format = "#,##0"; s.ws.cell(r, 7).number_format = "0.0000E+00"; s.ws.cell(r, 8).number_format = "#,##0"
    s.row("sec_Zn", "Z_eff net (at J-bolt sections) = MIN(Z net)", f"=MIN(J{sh0}:J{sh1})", "mm3", "", fmt="#,##0")
    s.ws.column_dimensions["I"].width = 16; s.ws.column_dimensions["J"].width = 12
    s.finish(); return s


def sh_geometry(bk):
    s = Sh(bk, "Geometry", tab="8EA9DB")
    s.banner("3  GEOMETRY  -  bolt-centre frame from drawing AL-001 R0", "Origin at joint A (base-vertical bolt), x along base, y up from ROOF surface. All STAAD nodes derive from here.")
    s.std_header(); s.section("Frame triangle A-B-C (bolt centres)")
    s.row("g_AC", "A-C: base bolt c/c", "=base_len-base_end_A-base_end_C", "mm", "1200-27.5-25", "V", fmt="0.00")
    s.row("g_AB", "A-B: vertical member bolt c/c", "=vert_len-2*vert_end", "mm", "249.72-2*22.5", "V", fmt="0.00")
    s.row("g_BCdwg", "B-C: inclined member bolt c/c AS DRAWN", "=incl_len-incl_end_B-incl_end_C", "mm", "1222.01-27.47-28.92", "V", fmt="0.00")
    s.row("g_BC", "B-C working length = hypot(AC, AB)", "=SQRT(g_AC^2+g_AB^2)", "mm", "triangle closes exactly (R1: removes 1.3e-6 rounding inconsistency)", "V", fmt="0.0000")
    s.row("g_closure", "Closure check  working - drawn B-C  (must be ~0)", "=g_BC-g_BCdwg", "mm", "drawn dims close the triangle to 0.002 mm", "V", fmt="0.0000")
    s.row("g_tilt", "Tilt angle", "=ATAN(g_AB/g_AC)", "rad", "atan(AB/AC)", "V", fmt="0.00000")
    s.row("g_tilt_deg", "Tilt angle", "=DEGREES(g_tilt)", "deg", "NOT atan(250/1200)=11.77 (ignores hole offsets)", "V", fmt="0.000")
    s.row("g_cos", "cos(tilt)", "=COS(g_tilt)", "-", "", fmt="0.000000"); s.row("g_sin", "sin(tilt)", "=SIN(g_tilt)", "-", "", fmt="0.000000")
    s.section("Positions along base member (x from A)")
    s.row("g_J1", "J-bolt 1", "=J_off-base_end_A", "mm", "175-27.5", "V", fmt="0.00"); s.row("g_J2", "J-bolt 2", "=g_J1+J_pair", "mm", "", "V", fmt="0.00")
    s.row("g_J3", "J-bolt 3", "=g_J2+J_mid", "mm", "", "V", fmt="0.00"); s.row("g_J4", "J-bolt 4", "=g_J3+J_pair", "mm", "", "V", fmt="0.00")
    s.row("g_Jchk", "Check: drawing symmetric 175+150+550+150+175 = base length", "=2*J_off+2*J_pair+J_mid-base_len", "mm", "must be 0", "V", fmt="0.00")
    s.row("g_a1", "Overhang A to J1", "=g_J1", "mm", "", fmt="0.00"); s.row("g_c2", "Overhang J4 to C", "=g_AC-g_J4", "mm", "", fmt="0.00")
    s.row("g_L1", "Span J1-J2", "=J_pair", "mm", "", fmt="0.00"); s.row("g_L2", "Span J2-J3", "=J_mid", "mm", "", fmt="0.00"); s.row("g_L3", "Span J3-J4", "=J_pair", "mm", "", fmt="0.00")
    s.row("g_xb1", "Block 1 centre", "=(g_J1+g_J2)/2", "mm", "", fmt="0.00"); s.row("g_xb2", "Block 2 centre", "=(g_J3+g_J4)/2", "mm", "c/c = 700 as drawn", fmt="0.00")
    s.row("g_xpr", "Right toe of block 2 (overturning pivot, uplift)", "=g_xb2+block_w/2", "mm", "", fmt="0.00"); s.row("g_xpl", "Left toe of block 1 (pivot, downward wind)", "=g_xb1-block_w/2", "mm", "", fmt="0.00")
    s.section("Heights (y from roof surface) and module load points")
    s.row("g_yA", "Bolt line above roof = block height + gauge", "=block_h+bolt_h", "mm", "", "I", fmt="0.00"); s.row("g_yB", "Node B height", "=g_yA+g_AB", "mm", "", fmt="0.00")
    s.row("g_s1", "Slot 1 distance from B along member", "=slot_end-incl_end_B", "mm", "67-27.47", "V", fmt="0.00")
    s.row("g_s2c", "Slot 2 distance from C along member", "=slot_end-incl_end_C", "mm", "67-28.92", "V", fmt="0.00")
    s.row("g_s2", "Slot 2 distance from B along member", "=g_BC-g_s2c", "mm", "", fmt="0.00")
    s.row("g_slot_cc", "Slot c/c (computed)", "=g_s2-g_s1", "mm", "", fmt="0.00"); s.row("g_slot_chk", "Check vs drawn 1088", "=g_slot_cc-slot_cc_dwg", "mm", "0.01 rounding", "V", fmt="0.000")
    s.row("g_S1x", "S1 x", "=g_s1*g_cos", "mm", "", fmt="0.00"); s.row("g_S1y", "S1 y", "=g_yB-g_s1*g_sin", "mm", "", fmt="0.00")
    s.row("g_S2x", "S2 x", "=g_s2*g_cos", "mm", "", fmt="0.00"); s.row("g_S2y", "S2 y", "=g_yB-g_s2*g_sin", "mm", "", fmt="0.00")
    s.section("Module contact zone on the rafter (module rests DIRECTLY on the rafter - no purlins)")
    s.row("g_sc", "Module centre along rafter from B (= mid of module bolts)", "=(g_s1+g_s2)/2", "mm", "module centred on its 4 bolts", "I", fmt="0.00")
    s.row("g_Lm", "Module contact length along rafter = module width", "=mod_W", "mm", "module lies parallel to the rafter", "V", fmt="0.00")
    s.row("g_sa", "Contact zone starts (from B)", "=g_sc-g_Lm/2", "mm", "", "I", fmt="0.00"); s.row("g_sb", "Contact zone ends (from B)", "=g_sc+g_Lm/2", "mm", "", "I", fmt="0.00")
    s.row("g_zone_ok", "Zone lies within rafter physical length?", '=IF(AND(g_sa>=-incl_end_B,g_sb<=g_BC+incl_end_C),"PASS","FAIL")', "", "-27.47 .. B-C + 28.92", fmt="@")
    s.row("g_mod_ovh", "Module overhang beyond each rafter (carried by the module itself)", "=(mod_L-frame_sp)/2", "mm", "(2279 - 1400)/2", "I", fmt="0.0")
    s.row("g_sM", "Node M position (mid of module bolts)", "=g_sc", "mm", "", fmt="0.00")
    s.row("g_Pax", "Pa = zone start: x", "=g_sa*g_cos", "mm", "STAAD node 11", fmt="0.000"); s.row("g_Pay", "Pa: y", "=g_yB-g_sa*g_sin", "mm", "", fmt="0.000")
    s.row("g_Pbx", "Pb = zone end: x", "=g_sb*g_cos", "mm", "STAAD node 12", fmt="0.000"); s.row("g_Pby", "Pb: y", "=g_yB-g_sb*g_sin", "mm", "", fmt="0.000")
    s.row("g_Mx", "M: x", "=g_sM*g_cos", "mm", "STAAD node 9", fmt="0.000"); s.row("g_My", "M: y", "=g_yB-g_sM*g_sin", "mm", "", fmt="0.000")
    s.row("g_xQ", "Wind resultant point x (module mid-plane, between slots)", "=(g_S1x+g_S2x)/2+e_mod*g_sin", "mm", "normal offset e_mod", "I", fmt="0.00")
    s.row("g_yQ", "Wind resultant point y", "=(g_S1y+g_S2y)/2+e_mod*g_cos", "mm", "", "I", fmt="0.00")
    s.section("Base-beam constants (three-moment equation, constant EI)")
    s.row("g_a11", "a11 = 2(L1+L2)", "=2*(g_L1+g_L2)", "mm", "", fmt="0.0"); s.row("g_a12", "a12 = L2", "=g_L2", "mm", "", fmt="0.0")
    s.row("g_a21", "a21 = L2", "=g_L2", "mm", "", fmt="0.0"); s.row("g_a22", "a22 = 2(L2+L3)", "=2*(g_L2+g_L3)", "mm", "", fmt="0.0")
    s.row("g_det", "det = a11*a22 - a12*a21", "=g_a11*g_a22-g_a12*g_a21", "mm2", "", fmt="0")
    s.row("g_Ieff", "I_eff (from Section)", "=sec_Ieff", "mm4", "", fmt="#,##0")
    s.finish(); return s


def sh_wind(bk):
    s = Sh(bk, "Wind", tab="A9D08E")
    s.banner("4  WIND LOAD  -  IS 875 (Part 3)", "Vz = Vb k1 k2 k3 k4 ; pz = 0.6 Vz^2 ; pd = Kd Ka Kc pz ; F = Cp pd A   (net Cp, Table 7 mono-slope free roof)")
    s.std_header(); s.section("Design wind speed")
    s.row("w_z", "Height of panel top above ground", "=z_bldg+(g_yB+e_mod+mod_t/2)/1000", "m", "roof level + panel top", "I", fmt="0.00")
    s.row("w_k2", "k2 terrain/height factor (interpolated, Table 2)",
          "=INDEX(K2_tab,MIN(MATCH(MIN(MAX(w_z,10),20),K2_h,1),2),terrain-1)+(MIN(MAX(w_z,10),20)-INDEX(K2_h,MIN(MATCH(MIN(MAX(w_z,10),20),K2_h,1),2)))/(INDEX(K2_h,MIN(MATCH(MIN(MAX(w_z,10),20),K2_h,1),2)+1)-INDEX(K2_h,MIN(MATCH(MIN(MAX(w_z,10),20),K2_h,1),2)))*(INDEX(K2_tab,MIN(MATCH(MIN(MAX(w_z,10),20),K2_h,1),2)+1,terrain-1)-INDEX(K2_tab,MIN(MATCH(MIN(MAX(w_z,10),20),K2_h,1),2),terrain-1))",
          "-", "IS 875-3 cl 6.3.2, Table 2 (Cat 2 or 3)", "I", fmt="0.0000")
    s.row("w_Vz", "Design wind speed Vz", "=Vb*k1_risk*w_k2*k3_topo*k4_imp", "m/s", "IS 875-3 cl 6.3", "V", fmt="0.00")
    s.row("w_pz", "Wind pressure pz = 0.6 Vz^2", "=0.6*w_Vz^2/1000", "kN/m2", "IS 875-3 cl 7.2", "V", fmt="0.0000")
    s.row("w_hf", "Height<10 m reduction factor", "=IF(w_z<10,0.8,1)", "-", "house rule; not applicable at roof level", "I", fmt="0.00")
    s.row("w_pd", "Design pressure pd = Kd Ka Kc pz (>= 0.7 pz)", "=MAX(Kd_dir*Ka_area*Kc_comb*w_pz*w_hf,0.7*w_pz)", "kN/m2", "IS 875-3 cl 7.2.1", "V", fmt="0.0000")
    s.section("Pressure coefficients - Table 7, interpolated at tilt")
    cp = lambda col: (f"=INDEX({col},MATCH(g_tilt_deg,T7_ang,1))+(g_tilt_deg-INDEX(T7_ang,MATCH(g_tilt_deg,T7_ang,1)))/(INDEX(T7_ang,MATCH(g_tilt_deg,T7_ang,1)+1)-INDEX(T7_ang,MATCH(g_tilt_deg,T7_ang,1)))*(INDEX({col},MATCH(g_tilt_deg,T7_ang,1)+1)-INDEX({col},MATCH(g_tilt_deg,T7_ang,1)))")
    s.row("w_cp_dn", "Cp max (downward pressure)", cp("T7_dn"), "-", "IS 875-3 Table 7 (house-verified values)", "V", fmt="0.0000")
    s.row("w_cp_up", "Cp min (uplift suction)", cp("T7_up"), "-", "IS 875-3 Table 7", "V", fmt="0.0000")
    s.section("Forces (normal to module)")
    s.row("w_Amod", "Module area", "=mod_L*mod_W/1E6", "m2", "", fmt="0.0000")
    s.row("w_Nup", "Uplift force per module", "=ABS(w_cp_up)*w_pd*w_Amod*1000", "N", "Cp pd A", fmt="#,##0.0")
    s.row("w_Ndn", "Downward force per module", "=w_cp_dn*w_pd*w_Amod*1000", "N", "", fmt="#,##0.0")
    s.row("w_Fn_u", "Uplift per module bolt (÷4)", "=w_Nup/4", "N", "4 bolts, equal share", "I", fmt="#,##0.0")
    s.row("w_Fn_d", "Downward per module bolt (÷4)", "=w_Ndn/4", "N", "", "I", fmt="#,##0.0")
    s.finish(); return s


def sh_loads(bk):
    s = Sh(bk, "Loads", tab="A9D08E")
    s.banner("5  DEAD & SEISMIC LOADS", "Loads per FRAME (2 frames per module). Member self-weights lumped as nodal loads (same in STAAD).")
    s.std_header(); s.section("Dead load - IS 875 (Part 1)")
    s.row("l_ws", "Steel self-weight per mm of ISA 50x50x5", "=sec_A*1E-6*gam_s", "N/mm", "A * gamma_s (1 kN/m = 1 N/mm)", "V", fmt="0.00000")
    s.row("l_Wm", "Module weight", "=mod_kg*gacc", "N", "", "I", fmt="0.0")
    s.row("l_Wbase", "Base member weight", "=l_ws*base_len", "N", "", fmt="0.0"); s.row("l_Wv", "Vertical member weight", "=l_ws*vert_len", "N", "", fmt="0.0")
    s.row("l_Winc", "Inclined member weight", "=l_ws*incl_len", "N", "", fmt="0.0")
    s.row("l_stubA", "Base stub weight beyond A", "=l_ws*base_end_A", "N", "lumped at A", fmt="0.00"); s.row("l_stubC", "Base stub weight beyond C", "=l_ws*base_end_C", "N", "lumped at C", fmt="0.00")
    s.row("l_slotdl", "Dead load per slot = Wm/4 + Winc/2", "=l_Wm/4+l_Winc/2", "N", "module 4 bolts; incl. member split to 2 slots", fmt="0.00")
    s.section("R1  Module dead load as UDL on the rafter - tributary derivation (client comment: no purlins, module bears directly on rafters)")
    s.row("l_pm", "Module weight per unit area = Wm / (L x W)", "=l_Wm/(mod_L*mod_W)", "N/mm2", "uniform over the module", fmt="0.000000")
    s.row("l_pm_kN", "   same, in kN/m2", "=l_pm*1000", "kN/m2", "", fmt="0.0000")
    s.row("l_trib", "Tributary width per rafter = L/2", "=mod_L/2", "mm", "2 rafters at 1400 c/c, symmetric overhangs (g_mod_ovh each side) -> each rafter takes half the module", "I", fmt="0.0")
    s.row("l_udl_m", "Module UDL on one rafter = pm x tributary width", "=l_pm*l_trib", "N/mm", "numerically = kN/m; per mm of rafter length, vertical", "I", fmt="0.00000")
    s.row("l_udl_chk", "Check: UDL x contact length - Wm/2  (must be 0)", "=l_udl_m*g_Lm-l_Wm/2", "N", "load conserved", fmt="0.0000")
    s.row("l_udl_r", "Rafter self-weight UDL = Winc / B-C  (stubs spread)", "=l_Winc/g_BC", "N/mm", "weight conserved", fmt="0.00000")
    s.row("l_qu", "Wind uplift as UDL over contact length (wind_mode = 1 only)", "=(w_Nup/2)/g_Lm", "N/mm", "normal to module; = N per frame / contact length", fmt="0.00000")
    s.row("l_qd", "Wind downward as UDL over contact length (wind_mode = 1 only)", "=(w_Ndn/2)/g_Lm", "N/mm", "", fmt="0.00000")
    s.section("Seismic - IS 1893 (Part 1):2016 (horizontal only)")
    s.row("l_Ah", "Ah = (Z/2) I (Sa/g)(1+z/h)/Rp", "=Zf/2*I_imp*SaG*(1+zh)/Rp", "-", "component at roof level; clause text not retrievable offline", "I", fmt="0.0000",
          note="Sensitivity: Rp=1 gives Ah=0.25")
    s.finish(); return s


LCS = ["DL", "WLU", "WLD", "EQX"]
LC_TITLE = {"DL": "DL  dead", "WLU": "WL uplift", "WLD": "WL downward", "EQX": "EQ +x"}
# (key, label, unit, fmt, formula-or-list, basis)
def _clm(sx): return f"MAX(0,MIN({sx},g_sb)-g_sa)"
def _clr(sx): return f"MAX(0,MIN({sx},g_BC))"
def _Mf(sx, pts):
    """closed-form moment (closed-form sign: = -sagging) at distance sx from B; pts = ('Fn*MAX(0,sx-g_s1)', ...) """
    gm = f"IF({sx}>g_sa,{_clm(sx)}*({sx}-(g_sa+MIN({sx},g_sb))/2),0)"; gr = f"{_clr(sx)}*({sx}-MIN({sx},g_BC)/2)"
    return "=-({VB}*g_cos*" + sx + pts + "+{qnm}*" + gm + "+{qnr}*" + gr + ")"
_SECS = [("0", "0", 0, 0, "at B"), ("a", "g_sa", 0, 0, "start of module contact"), ("1m", "g_s1", 0, 0, "just before module bolt 1"), ("1p", "g_s1", 1, 0, "just after module bolt 1"),
         ("2m", "g_s2", 1, 0, "just before module bolt 2"), ("2p", "g_s2", 1, 1, "just after module bolt 2"), ("b", "g_sb", 1, 1, "end of module contact"), ("L", "g_BC", 1, 1, "at C")]
_sec_rows = []
for nm, sx, i1, i2, lab in _SECS:
    _sec_rows.append(("N_" + nm, f"Axial in rafter, {lab} (tension +)", "N", "#,##0.00", "={VB}*g_sin-{Ft}*" + str(i1 + i2) + "-{qtm}*" + _clm(sx) + "-{qtr}*" + _clr(sx), "piecewise linear"))
for nm, sx, i1, i2, lab in _SECS:
    _sec_rows.append(("V_" + nm, f"Shear in rafter, {lab}", "N", "#,##0.00", "=-({VB}*g_cos+{Fn}*" + str(i1 + i2) + "+{qnm}*" + _clm(sx) + "+{qnr}*" + _clr(sx) + ")", "piecewise linear"))

AN_ROWS = [
 ("_h", "Applied loads per frame - module bolts, module UDL zone, rafter UDL, direct loads at A and C", None, None, None, None),
 ("Fx_s", "Point load per module bolt, Fx (x right +)", "N", "#,##0.00", ["=0", "=IF(wind_mode=0,w_Fn_u*g_sin,0)", "=IF(wind_mode=0,-w_Fn_d*g_sin,0)", "=0"], "wind_mode 0: wind through the 4 module bolts"),
 ("Fy_s", "Point load per module bolt, Fy (y up +)", "N", "#,##0.00", ["=0", "=IF(wind_mode=0,w_Fn_u*g_cos,0)", "=IF(wind_mode=0,-w_Fn_d*g_cos,0)", "=0"], "R1: module DEAD load is NOT a point load any more"),
 ("qmx", "Module UDL on rafter over contact length, x-component", "N/mm", "0.00000", ["=0", "=IF(wind_mode=1,l_qu*g_sin,0)", "=IF(wind_mode=1,-l_qd*g_sin,0)", "=l_Ah*l_udl_m"], "per mm of rafter length, global x"),
 ("qmy", "Module UDL on rafter over contact length, y-component", "N/mm", "0.00000", ["=-l_udl_m", "=IF(wind_mode=1,l_qu*g_cos,0)", "=IF(wind_mode=1,-l_qd*g_cos,0)", "=0"], "DL: module weight x tributary width / contact length"),
 ("qrx", "Rafter self-weight / seismic UDL over full B-C, x", "N/mm", "0.00000", ["=0", "=0", "=0", "=l_Ah*l_udl_r"], ""),
 ("qry", "Rafter self-weight UDL over full B-C, y", "N/mm", "0.00000", ["=-l_udl_r", "=0", "=0", "=0"], ""),
 ("FxA", "Direct horizontal load at A", "N", "#,##0.00", ["=0", "=0", "=0", "=l_Ah*(l_Wv+l_stubA+0.5*l_ws*g_AC)"], "EQ on vertical+base masses"),
 ("FxC", "Direct horizontal load at C", "N", "#,##0.00", ["=0", "=0", "=0", "=l_Ah*(l_stubC+0.5*l_ws*g_AC)"], ""),
 ("dAy", "Direct downward load at A (vert. member + stub)", "N", "#,##0.00", ["=l_Wv+l_stubA", "=0", "=0", "=0"], ""),
 ("dCy", "Direct downward load at C (stub)", "N", "#,##0.00", ["=l_stubC", "=0", "=0", "=0"], ""),
 ("wb", "UDL on base member (down +)", "N/mm", "0.00000", ["=l_ws", "=0", "=0", "=0"], "self-weight"),
 ("Fnb", "Module-bolt force per bolt, normal to rafter (up/out +)", "N", "#,##0.00", ["=-(l_Wm/4)*g_cos", "=w_Fn_u", "=-w_Fn_d", "=l_Ah*(l_Wm/4)*g_sin"], "connection load path: 4 M8 bolts carry the module"),
 ("Ftb", "Module-bolt force per bolt, along rafter (B->C +)", "N", "#,##0.00", ["=(l_Wm/4)*g_sin", "=0", "=0", "=l_Ah*(l_Wm/4)*g_cos"], "used for M8 bolt shear"),
 ("_h", "Step 1 - rafter B-C (pin at C; vertical member = 2-force member). Load items: 2 module-bolt points + module UDL + rafter UDL", None, None, None, None),
 ("msum_p", "Moment about C of module-bolt point loads", "N.mm", "#,##0", "=(g_S1x-g_AC)*{Fy_s}-(g_S1y-g_yA)*{Fx_s}+(g_S2x-g_AC)*{Fy_s}-(g_S2y-g_yA)*{Fx_s}", "M_C = sum[(x-xC)Fy - (y-yC)Fx]"),
 ("msum_m", "Moment about C of module UDL resultant (at module centre)", "N.mm", "#,##0", "=(g_sc*g_cos-g_AC)*{qmy}*g_Lm-(g_yB-g_sc*g_sin-g_yA)*{qmx}*g_Lm", "resultant q x contact length"),
 ("msum_r", "Moment about C of rafter UDL resultant (at mid B-C)", "N.mm", "#,##0", "=(g_BC/2*g_cos-g_AC)*{qry}*g_BC-(g_yB-g_BC/2*g_sin-g_yA)*{qrx}*g_BC", ""),
 ("VB", "Vertical force on rafter at B (up +)", "N", "#,##0.00", "=-({msum_p}+{msum_m}+{msum_r})/(0-g_AC)", "moment equilibrium about C"),
 ("Cx", "Force on rafter at C, x", "N", "#,##0.00", "=-(2*{Fx_s}+{qmx}*g_Lm+{qrx}*g_BC)", "sum Fx = 0"),
 ("Cy", "Force on rafter at C, y", "N", "#,##0.00", "=-(2*{Fy_s}+{qmy}*g_Lm+{qry}*g_BC+{VB})", "sum Fy = 0"),
 ("NAB", "Axial force in vertical member (tension +)", "N", "#,##0.00", "=-{VB}", "joint B"),
 ("Fn", "Point load per bolt: component normal to rafter", "N", "#,##0.00", "={Fx_s}*g_sin+{Fy_s}*g_cos", "n=(sin,cos)"),
 ("Ft", "Point load per bolt: component along rafter (B->C)", "N", "#,##0.00", "={Fx_s}*g_cos-{Fy_s}*g_sin", "d=(cos,-sin)"),
 ("qnm", "Module UDL, normal component", "N/mm", "0.00000", "={qmx}*g_sin+{qmy}*g_cos", ""),
 ("qtm", "Module UDL, tangential component", "N/mm", "0.00000", "={qmx}*g_cos-{qmy}*g_sin", ""),
 ("qnr", "Rafter UDL, normal component", "N/mm", "0.00000", "={qrx}*g_sin+{qry}*g_cos", ""),
 ("qtr", "Rafter UDL, tangential component", "N/mm", "0.00000", "={qrx}*g_cos-{qry}*g_sin", ""),
 ("qn", "Total distributed normal load (deflection)", "N/mm", "0.00000", "={qnm}+{qnr}", ""),
] + _sec_rows + [
 ("Minc1", "Moment at module bolt 1 (closed-form sign = -sagging)", "N.mm", "#,##0", _Mf("g_s1", "+{Fn}*MAX(0,g_s1-g_s1)+{Fn}*MAX(0,g_s1-g_s2)"), "Macaulay sum from B"),
 ("Minc2", "Moment at module bolt 2", "N.mm", "#,##0", _Mf("g_s2", "+{Fn}*MAX(0,g_s2-g_s1)+{Fn}*MAX(0,g_s2-g_s2)"), ""),
 ("MincM", "Moment at node M (mid of module bolts)", "N.mm", "#,##0", _Mf("g_sM", "+{Fn}*MAX(0,g_sM-g_s1)+{Fn}*MAX(0,g_sM-g_s2)"), "for STAAD comparison"),
 ("MincL", "Moment at C (must be 0: pin)", "N.mm", "#,##0.0000", _Mf("g_BC", "+{Fn}*MAX(0,g_BC-g_s1)+{Fn}*MAX(0,g_BC-g_s2)"), "equilibrium check"),
 ("_h", "Step 2 - base member on 4 J-bolt supports (continuous beam, three-moment equation)", None, None, None, None),
 ("PA", "Downward load on base at A", "N", "#,##0.00", "={dAy}-{NAB}", "vertical member pulls A up if in tension"),
 ("PC", "Downward load on base at C", "N", "#,##0.00", "={dCy}+{Cy}", ""),
 ("FxCt", "Horizontal load on base at C", "N", "#,##0.00", "={FxC}-{Cx}", ""),
 ("RH1", "Horizontal reaction at J1 (restraint in x)", "N", "#,##0.00", "=-({FxA}+{FxCt})", "all horizontal to J1 (same in STAAD)"),
 ("NbA", "Axial in base A-J1 (tension +)", "N", "#,##0.00", "=-{FxA}", ""),
 ("NbC", "Axial in base J1-C (tension +)", "N", "#,##0.00", "={FxCt}", ""),
 ("M1", "Support moment at J1 (sagging +)", "N.mm", "#,##0", "=-({PA}*g_a1+{wb}*g_a1^2/2)", "overhang statics"),
 ("M4", "Support moment at J4", "N.mm", "#,##0", "=-({PC}*g_c2+{wb}*g_c2^2/2)", ""),
 ("b1", "RHS eq. at J2", "N.mm2", "#,##0", "=-{wb}*(g_L1^3+g_L2^3)/4-{M1}*g_L1", "Clapeyron"),
 ("b2", "RHS eq. at J3", "N.mm2", "#,##0", "=-{wb}*(g_L2^3+g_L3^3)/4-{M4}*g_L3", ""),
 ("M2", "Support moment at J2", "N.mm", "#,##0", "=({b1}*g_a22-g_a12*{b2})/g_det", "2x2 solve"),
 ("M3", "Support moment at J3", "N.mm", "#,##0", "=(g_a11*{b2}-g_a21*{b1})/g_det", ""),
 ("V1m", "Shear just left of J1", "N", "#,##0.00", "=-({PA}+{wb}*g_a1)", ""),
 ("V1p", "Shear just right of J1", "N", "#,##0.00", "=({M2}-{M1})/g_L1+{wb}*g_L1/2", ""),
 ("R1", "Reaction J1 (up +)", "N", "#,##0.00", "={V1p}-{V1m}", ""),
 ("V2m", "Shear left of J2", "N", "#,##0.00", "={V1p}-{wb}*g_L1", ""),
 ("V2p", "Shear right of J2", "N", "#,##0.00", "=({M3}-{M2})/g_L2+{wb}*g_L2/2", ""),
 ("R2", "Reaction J2", "N", "#,##0.00", "={V2p}-{V2m}", ""),
 ("V3m", "Shear left of J3", "N", "#,##0.00", "={V2p}-{wb}*g_L2", ""),
 ("V3p", "Shear right of J3", "N", "#,##0.00", "=({M4}-{M3})/g_L3+{wb}*g_L3/2", ""),
 ("R3", "Reaction J3", "N", "#,##0.00", "={V3p}-{V3m}", ""),
 ("V4m", "Shear left of J4", "N", "#,##0.00", "={V3p}-{wb}*g_L3", ""),
 ("V4p", "Shear right of J4", "N", "#,##0.00", "={PC}+{wb}*g_c2", ""),
 ("R4", "Reaction J4", "N", "#,##0.00", "={V4p}-{V4m}", ""),
 ("Mm1", "Mid-span moment J1-J2", "N.mm", "#,##0", "={M1}+{V1p}*g_L1/2-{wb}*(g_L1/2)^2/2", ""),
 ("Mm2", "Mid-span moment J2-J3", "N.mm", "#,##0", "={M2}+{V2p}*g_L2/2-{wb}*(g_L2/2)^2/2", ""),
 ("Mm3", "Mid-span moment J3-J4", "N.mm", "#,##0", "={M3}+{V3p}*g_L3/2-{wb}*(g_L3/2)^2/2", ""),
 ("_h", "Step 3 - tip deflections of base overhangs (down +), slope-deflection", None, None, None, None),
 ("th1", "Slope at J1 (dy/dx, y down)", "rad", "0.000000E+00", "=({M1}*g_L1/3+{M2}*g_L1/6+{wb}*g_L1^3/24)/(Es*g_Ieff)", "EI y'' = -M"),
 ("th4", "Slope at J4", "rad", "0.000000E+00", "=-({M3}*g_L3/6+{M4}*g_L3/3+{wb}*g_L3^3/24)/(Es*g_Ieff)", ""),
 ("dA", "Deflection at A", "mm", "0.00000", "=-{th1}*g_a1+({PA}*g_a1^3/3+{wb}*g_a1^4/8)/(Es*g_Ieff)", ""),
 ("dC", "Deflection at C", "mm", "0.00000", "={th4}*g_c2+({PC}*g_c2^3/3+{wb}*g_c2^4/8)/(Es*g_Ieff)", ""),
 ("_h", "Equilibrium self-checks (must be 0)", None, None, None, None),
 ("eqV", "sum(R) - sum(loads) on base", "N", "0.0000", "=({R1}+{R2}+{R3}+{R4})-({PA}+{PC}+{wb}*g_AC)", "vertical equilibrium"),
 ("eqN", "Rafter end axial at C  -  (Cx cos - Cy sin)", "N", "0.0000", "={N_L}-({Cx}*g_cos-{Cy}*g_sin)", "independent identity"),
 ("eqM", "Rafter moment at C (pin)", "N.mm", "0.0000", "={MincL}", "must be 0"),
]


def sh_analysis(bk):
    bk.reg = {"Analysis": {}, "Combos": {}}
    ws = bk.wb.create_sheet("Analysis"); ws.sheet_properties.tabColor = "F4B084"; ws.sheet_view.showGridLines = False
    for i, w in enumerate((5, 56, 9, 15, 15, 15, 15, 8, 40), 1): ws.column_dimensions[CL(i)].width = w
    ws.cell(1, 1, "6  FRAME ANALYSIS  -  closed-form statics per load case (one frame)").font = Font(bold=True, size=14, color="FFFFFF")
    for c in range(1, 10): ws.cell(1, c).fill = PatternFill("solid", fgColor=NAVY)
    ws.cell(2, 1, "Same model as STAAD (pinned single-bolt joints, base member continuous on 4 J-bolt supports). Verified against an independent matrix solver to 1e-11.").font = Font(italic=True, size=9)
    r = 4
    for i, h in enumerate(["#", "Quantity", "Key"] + [LC_TITLE[l] for l in LCS] + ["Unit", "Basis"], 1):
        c = ws.cell(r, i, h); c.font = Font(bold=True, color="FFFFFF", size=9); c.fill = PatternFill("solid", fgColor="44546A"); c.alignment = Alignment(horizontal="center", wrap_text=True)
    r += 1; n = 0
    for key, label, unit, fmt, fml, basis in AN_ROWS:
        if key == "_h":
            for c in range(1, 10): ws.cell(r, c).fill = PatternFill("solid", fgColor=LBLUE)
            ws.cell(r, 2, label).font = Font(bold=True, color=NAVY); r += 1; continue
        bk.reg["Analysis"][key] = r; n += 1
        ws.cell(r, 1, n).font = Font(size=8, color="7F7F7F"); ws.cell(r, 2, label); ws.cell(r, 3, key).font = Font(size=8, italic=True, color="7F7F7F")
        for j, lc in enumerate(LCS):
            col = CL(4 + j)
            f = fml[j] if isinstance(fml, list) else fml
            f = re.sub(r"\{(\w+)\}", lambda m: f"{col}{bk.reg['Analysis'][m.group(1)]}", f)
            c = ws.cell(r, 4 + j, f); c.number_format = fmt; c.border = BORDER
        ws.cell(r, 8, unit).font = Font(size=9); ws.cell(r, 9, basis).font = Font(size=9, italic=True, color="595959")
        r += 1
    ws.freeze_panes = "D5"; bk.an_ws = ws
    return ws


COMBO_LIST = [("C1", "1.5DL + 1.5WL(down)", (1.5, 0, 1.5, 0), "U"), ("C2", "0.9DL + 1.5WL(up)", (0.9, 1.5, 0, 0), "U"),
              ("C3", "1.5DL + 1.5EQ(+x)", (1.5, 0, 0, 1.5), "U"), ("C4", "1.5DL - 1.5EQ(+x)", (1.5, 0, 0, -1.5), "U"),
              ("C5", "0.9DL + 1.5EQ(+x)", (0.9, 0, 0, 1.5), "U"), ("C6", "0.9DL - 1.5EQ(+x)", (0.9, 0, 0, -1.5), "U"),
              ("S1", "DL + WL(down)  [service]", (1, 0, 1, 0), "S"), ("S2", "DL + WL(up)  [service]", (1, 1, 0, 0), "S")]
CB_KEYS = (["VB", "Cx", "Cy", "NAB", "Fn", "Ft", "qnm", "qnr", "qn"] + ["N_" + k for k in ("0", "a", "1m", "1p", "2m", "2p", "b", "L")] +
           ["V_" + k for k in ("0", "a", "1m", "1p", "2m", "2p", "b", "L")] +
           ["Minc1", "Minc2", "MincM", "NbA", "NbC", "RH1", "M1", "M2", "M3", "M4", "Mm1", "Mm2", "Mm3", "V1m", "V1p", "V2m", "V2p", "V3m", "V3p", "V4m", "V4p",
            "R1", "R2", "R3", "R4", "dA", "dC", "Fnb", "Ftb"])
CB_DERIVED = [("Rc", "Resultant at joint C = SQRT(Cx^2+Cy^2)", "N", "=SQRT({Cx}^2+{Cy}^2)"), ("Fnbpos", "Module bolt tension per bolt = MAX(Fnb,0)", "N", "=MAX({Fnb},0)"),
              ("Ftbabs", "Module bolt shear per bolt = ABS(Ftb)", "N", "=ABS({Ftb})"), ("Tb1", "Block 1 net uplift = MAX(0,-(R1+R2))", "N", "=MAX(0,-({R1}+{R2}))"),
              ("Tb2", "Block 2 net uplift = MAX(0,-(R3+R4))", "N", "=MAX(0,-({R3}+{R4}))"), ("Tj", "J-bolt max tension = MAX(0,-MIN(R1..R4))", "N", "=MAX(0,-MIN({R1},{R2},{R3},{R4}))"),
              ("sstar", "Rafter: section of zero shear between module bolts (clamped to S1..S2)", "mm", "=MIN(MAX((-({VB}*g_cos+{Fn})+{qnm}*g_sa)/({qnm}+{qnr}),g_s1),g_s2)"),
              ("Mstar", "Rafter: moment at zero-shear section s*", "N.mm", "=-({VB}*g_cos*{sstar}+{Fn}*({sstar}-g_s1)+{qnm}*({sstar}-g_sa)^2/2+{qnr}*{sstar}^2/2)"),
              ("Minc_abs", "Rafter: governing |M| = max(|M(S1)|, |M(S2)|, |M(s*)|)", "N.mm", "=MAX(ABS({Minc1}),ABS({Minc2}),ABS({Mstar}))")]


def sh_combos(bk):
    ws = bk.wb.create_sheet("Combos"); ws.sheet_properties.tabColor = "F4B084"; ws.sheet_view.showGridLines = False
    for i, w in enumerate((5, 50, 9) + (12,)*8 + (13, 13, 13, 8), 1): ws.column_dimensions[CL(i)].width = w
    ws.cell(1, 1, "7  LOAD COMBINATIONS (IS 800:2007 Table 4, limit state) AND ENVELOPES").font = Font(bold=True, size=14, color="FFFFFF")
    for c in range(1, 16): ws.cell(1, c).fill = PatternFill("solid", fgColor=NAVY)
    ws.cell(2, 1, "U = strength combinations C1-C6 (factored). S = service combinations (unfactored, deflection). 0.9DL when dead load is stabilising (Table 4 note).").font = Font(italic=True, size=9)
    r = 4
    hdr = ["#", "Quantity", "Key"] + [c[0] for c in COMBO_LIST] + ["max U", "min U", "abs max U", "Unit"]
    for i, h in enumerate(hdr, 1):
        c = ws.cell(r, i, h); c.font = Font(bold=True, color="FFFFFF", size=9); c.fill = PatternFill("solid", fgColor="44546A"); c.alignment = Alignment(horizontal="center")
    r += 1
    ws.cell(r, 2, "Combination").font = Font(bold=True)
    for j, (cid, desc, fac, kind) in enumerate(COMBO_LIST):
        c = ws.cell(r, 4 + j, desc); c.alignment = Alignment(wrap_text=True, horizontal="center", vertical="top"); c.font = Font(size=8)
    ws.row_dimensions[r].height = 36; r += 1
    frow = {}
    for i, lc in enumerate(LCS):
        ws.cell(r, 2, f"Factor on {LC_TITLE[lc]}"); ws.cell(r, 3, lc).font = Font(size=8, italic=True)
        for j, (cid, desc, fac, kind) in enumerate(COMBO_LIST):
            c = ws.cell(r, 4 + j, fac[i]); c.fill = PatternFill("solid", fgColor=YEL); c.font = Font(color="0000FF", bold=True); c.number_format = "0.0"; c.border = BORDER
        frow[lc] = r; r += 1
    bk.reg["Combos"]["_factors"] = frow; n = 0
    for key in CB_KEYS:
        n += 1; ar = bk.reg["Analysis"][key]; bk.reg["Combos"][key] = r
        ws.cell(r, 1, n).font = Font(size=8, color="7F7F7F"); ws.cell(r, 2, [x for x in AN_ROWS if x[0] == key][0][1]); ws.cell(r, 3, key).font = Font(size=8, italic=True)
        fmt = [x for x in AN_ROWS if x[0] == key][0][3]
        for j in range(len(COMBO_LIST)):
            col = CL(4 + j)
            f = "=" + "+".join(f"{col}${frow[lc]}*Analysis!${CL(4+k)}${ar}" for k, lc in enumerate(LCS))
            ws.cell(r, 4 + j, f).number_format = fmt
        r += 1
    for key, label, unit, fml in CB_DERIVED:
        n += 1; bk.reg["Combos"][key] = r
        ws.cell(r, 1, n).font = Font(size=8, color="7F7F7F"); ws.cell(r, 2, label); ws.cell(r, 3, key).font = Font(size=8, italic=True)
        for j in range(len(COMBO_LIST)):
            col = CL(4 + j)
            f = re.sub(r"\{(\w+)\}", lambda m: f"{col}{bk.reg['Combos'][m.group(1)]}", fml)
            ws.cell(r, 4 + j, f).number_format = "#,##0.00"
        r += 1
    last = r - 1
    for rr in range(frow["DL"] + 4, last + 1):
        ws.cell(rr, 12, f"=MAX(D{rr}:I{rr})").number_format = "#,##0.00"; ws.cell(rr, 13, f"=MIN(D{rr}:I{rr})").number_format = "#,##0.00"
        ws.cell(rr, 14, f"=MAX(L{rr},-M{rr})").number_format = "#,##0.00"
        unit = [x for x in AN_ROWS if x[0] == ws.cell(rr, 3).value]; ws.cell(rr, 15, unit[0][2] if unit else {"sstar": "mm", "Mstar": "N.mm", "Minc_abs": "N.mm"}.get(ws.cell(rr, 3).value, "N"))
        for cc in range(4, 15): ws.cell(rr, cc).border = BORDER
    ws.freeze_panes = "D6"; bk.cb_ws = ws


def CB(bk, key, col):
    """absolute reference into Combos: col in 'L','M','N' (envelope) or 'D'..'K' (combo)"""
    return f"Combos!${col}${bk.reg['Combos'][key]}"


def CBR(bk, k1, k2, c1="D", c2="I"):
    return f"Combos!${c1}${bk.reg['Combos'][k1]}:${c2}${bk.reg['Combos'][k2]}"


def ck(s, key, label, dem, cap, basis, unit="N", fmt="#,##0.0", mode="ratio"):
    """demand / capacity / UR / status rows. mode 'ratio': UR=dem/cap; mode 'ur': dem is already a UR (cap=1)."""
    s.row(key + "_d", label + " - demand", dem, unit, basis, fmt=fmt)
    s.row(key + "_c", label + " - capacity", cap, unit, "", fmt=fmt)
    s.row(key + "_ur", label + " - utilisation", f"={key}_d/{key}_c" if cap != 1 else f"={key}_d", "-", "", fmt="0.000")
    s.row(key + "_ok", "   status", f'=IF({key}_ur<=1,"PASS","FAIL")', "", "", fmt="@")


def sh_members(bk):
    s = Sh(bk, "Members", tab="F4B084")
    s.banner("8  MEMBER CHECKS  -  IS 800:2007 limit state (hot-rolled ISA 50x50x5, E250)",
             "Forces from Combos sheet (envelope of strength combinations C1-C6). Bending: elastic, in-plane, unsymmetric-bending modulus (Section sheet). No LTB reduction: spans <= 550 mm.")
    s.std_header(); s.section("Tension capacity - cl 6.2 (yielding) and cl 6.3.3 (tearing of net section, single bolt in connected leg)")
    s.row("m_Tdg", "Tdg = Ag fy / gamma_m0", "=sec_A*fy/gamma_m0", "N", "IS 800 cl 6.2", "V", fmt="#,##0")
    s.row("m_Anc", "Anc = (b - t/2 - d0) t  (net connected leg)", "=(sec_b-sec_t/2-d0_14)*sec_t", "mm2", "cl 6.3.3", "V", fmt="0.0")
    s.row("m_Ago", "Ago = (b - t/2) t  (outstanding leg)", "=(sec_b-sec_t/2)*sec_t", "mm2", "cl 6.3.3", "V", fmt="0.0")
    s.row("m_beta", "beta = 1.4 - 0.076 (w/t)(fy/fu)(bs/Lc), 0.7 <= beta <= fu gm0/(fy gm1)",
          "=MAX(0.7,MIN(1.4-0.076*(sec_b/sec_t)*(fy/fu)*((2*sec_b-sec_t)/edge_min),fu*gamma_m0/(fy*gamma_m1)))", "-", "cl 6.3.3; Lc=end dist. (single bolt) -> lower bound 0.7", "I", fmt="0.000")
    s.row("m_Tdn", "Tdn = 0.9 Anc fu/gm1 + beta Ago fy/gm0", "=0.9*m_Anc*fu/gamma_m1+m_beta*m_Ago*fy/gamma_m0", "N", "cl 6.3.3", "V", fmt="#,##0")
    s.row("m_Td", "Td = min(Tdg, Tdn)", "=MIN(m_Tdg,m_Tdn)", "N", "", fmt="#,##0")
    s.section("Compression capacity - cl 7.1.2 with equivalent slenderness for single angle struts, cl 7.5.1.2 / Table 12 (single bolt, hinged)")
    s.row("m_lamc", "pi sqrt(E/fy)", "=PI()*SQRT(Es/fy)", "-", "cl 7.1.2", "V", fmt="0.00")
    s.row("m_lphi", "lambda_phi = (b1+b2)/(2t) / (pi sqrt(E/fy))", "=((sec_b+sec_b)/(2*sec_t))/m_lamc", "-", "cl 7.5.1.2", "V", fmt="0.0000")
    s.row("m_k1", "k1 (Table 12, single bolt, hinged)", 1.25, "-", "Table 12 (search-confirmed)", "V", fmt="0.00", inp=True)
    s.row("m_k2", "k2", 0.50, "-", "Table 12", "V", fmt="0.00", inp=True); s.row("m_k3", "k3", 60, "-", "Table 12", "V", fmt="0.0", inp=True)
    s.row("m_alpha", "Imperfection factor, buckling class c", 0.49, "-", "Table 7 / Table 10 (angles: class c)", "V", fmt="0.00", inp=True)
    for sfx, lab, L in [("v", "Vertical A-B (L = bolt c/c)", "g_AB"), ("i", "Inclined B-C (L = bolt c/c)", "g_BC"), ("b", "Base (L = clear span between J-bolt pairs)", "J_mid")]:
        s.row(f"m_KL_{sfx}", f"{lab}: effective length KL (K=1)", f"={L}", "mm", "pinned, single bolt", "I", fmt="0.0")
        s.row(f"m_lvv_{sfx}", "   lambda_vv = (KL/rvv)/(pi sqrt(E/fy))", f"=(m_KL_{sfx}/sec_rvv)/m_lamc", "-", "", fmt="0.0000")
        s.row(f"m_le_{sfx}", "   lambda_e = sqrt(k1 + k2 lvv^2 + k3 lphi^2)", f"=SQRT(m_k1+m_k2*m_lvv_{sfx}^2+m_k3*m_lphi^2)", "-", "cl 7.5.1.2", fmt="0.0000")
        s.row(f"m_phi_{sfx}", "   phi = 0.5[1+alpha(le-0.2)+le^2]", f"=0.5*(1+m_alpha*(m_le_{sfx}-0.2)+m_le_{sfx}^2)", "-", "cl 7.1.2.1", fmt="0.0000")
        s.row(f"m_fcd_{sfx}", "   fcd = (fy/gm0)/(phi+sqrt(phi^2-le^2))", f"=(fy/gamma_m0)/(m_phi_{sfx}+SQRT(m_phi_{sfx}^2-m_le_{sfx}^2))", "MPa", "", fmt="0.00")
        s.row(f"m_Pd_{sfx}", "   Pd = Ag fcd", f"=sec_A*m_fcd_{sfx}", "N", "cl 7.1.2", fmt="#,##0")
    s.section("Bending and shear capacity - cl 8.2.1.2, 8.4")
    s.row("m_Mdg", "Md gross = Z_eff fy/gm0 (mid-span sections)", "=sec_Zg*fy/gamma_m0", "N.mm", "cl 8.2.1.2 elastic (beta_b = Ze/Zp)", "V", fmt="#,##0")
    s.row("m_Mdn", "Md net of Ø18 J-bolt hole (support sections)", "=sec_Zn*fy/gamma_m0", "N.mm", "", "I", fmt="#,##0")
    s.row("m_Vd", "Vd = Av fy/(sqrt3 gm0), Av = b t", "=sec_b*sec_t*fy/(SQRT(3)*gamma_m0)", "N", "cl 8.4.1", "V", fmt="#,##0")
    s.section("Demands (envelope of strength combinations) and checks")
    a = lambda k: CB(bk, k, "N"); mx = lambda k: CB(bk, k, "L"); mn = lambda k: CB(bk, k, "M")
    s.row("m_vT", "Vertical member: max tension", f"=MAX(0,{mx('NAB')})", "N", "Combos", fmt="#,##0.0"); s.row("m_vC", "Vertical member: max compression", f"=MAX(0,-{mn('NAB')})", "N", "", fmt="#,##0.0")
    s.row("m_iT", "Rafter: max tension (8 sections)", f"=MAX(0,MAX({CBR(bk,'N_0','N_L')}))", "N", "Combos", fmt="#,##0.0"); s.row("m_iC", "Rafter: max compression", f"=MAX(0,-MIN({CBR(bk,'N_0','N_L')}))", "N", "", fmt="#,##0.0")
    s.row("m_iM", "Rafter: max |M| (module-bolt sections and zero-shear section)", f"={CB(bk,'Minc_abs','L')}", "N.mm", "R1: UDL moment included", fmt="#,##0"); s.row("m_iV", "Rafter: max |V|", f"={absmax(CBR(bk,'V_0','V_L'))}", "N", "", fmt="#,##0.0")
    s.row("m_bT", "Base: max axial tension", f"=MAX(0,MAX({CBR(bk,'NbA','NbC')}))", "N", "", fmt="#,##0.0"); s.row("m_bC", "Base: max axial compression", f"=MAX(0,-MIN({CBR(bk,'NbA','NbC')}))", "N", "", fmt="#,##0.0")
    s.row("m_bMs", "Base: max |M| at J-bolt sections", f"={absmax(CBR(bk,'M1','M4'))}", "N.mm", "", fmt="#,##0"); s.row("m_bMm", "Base: max |M| mid-span", f"={absmax(CBR(bk,'Mm1','Mm3'))}", "N.mm", "", fmt="#,##0")
    s.row("m_bV", "Base: max |V|", f"={absmax(CBR(bk,'V1m','V4p'))}", "N", "", fmt="#,##0.0")
    ck(s, "mk_vT", "Vertical member tension", "=m_vT", "=m_Td", "cl 6.2/6.3")
    ck(s, "mk_vC", "Vertical member compression", "=m_vC", "=m_Pd_v", "cl 7.1.2, 7.5.1.2")
    ck(s, "mk_iT", "Inclined N+M (tension) cl 9.3.1", "=m_iT/m_Td+m_iM/m_Mdg", 1, "cl 9.3.1 linear interaction", unit="-", fmt="0.000")
    ck(s, "mk_iC", "Inclined N+M (compression) cl 9.3.2", "=m_iC/m_Pd_i+m_iM/m_Mdg", 1, "cl 9.3.2 (simplified, conservative)", unit="-", fmt="0.000")
    ck(s, "mk_iV", "Inclined shear", "=m_iV", "=m_Vd", "cl 8.4")
    ck(s, "mk_bS", "Base N+M at J-bolt sections (net of Ø18 hole)", "=MAX(m_bT/m_Td,m_bC/m_Pd_b)+m_bMs/m_Mdn", 1, "cl 9.3", unit="-", fmt="0.000")
    ck(s, "mk_bM", "Base N+M at mid-span", "=MAX(m_bT/m_Td,m_bC/m_Pd_b)+m_bMm/m_Mdg", 1, "cl 9.3", unit="-", fmt="0.000")
    ck(s, "mk_bV", "Base shear", "=m_bV", "=m_Vd", "cl 8.4")
    s.finish(); return s


def sh_connections(bk):
    s = Sh(bk, "Connections", tab="F4B084")
    s.banner("9  CONNECTIONS  -  bolts per hardware BOM, IS 800:2007 cl 10.3 / 10.2",
             "Single bolt per joint in single shear, threads in shear plane (n_n=1). Bearing reduced x0.7 for holes larger than standard (cl 10.3.4). Prying neglected (shear joints).")
    s.std_header(); s.section("Bolt data (IS 1367 / ISO 898-1 tensile-stress area An, shank area Asb)")
    for nm, (d, An, Asb) in BOLTS.items():
        s.row(f"bolt_{nm}_d", f"{nm}  nominal dia", d, "mm", "", "V", fmt="0", inp=True)
        s.row(f"bolt_{nm}_An", f"{nm}  tensile stress area An", An, "mm2", "ISO 898-1", "V", fmt="0.0", inp=True)
        s.row(f"bolt_{nm}_Asb", f"{nm}  shank area Asb", Asb, "mm2", "", "V", fmt="0.00", inp=True)
    joints = [("A", "M10", "M10 HDG 8.8  base-vertical (joint A)", "fub88", "fyb88", "d0_14", f"={CB(bk,'VB','N')}", "=0"),
              ("B", "M10", "M10 HDG 8.8  vertical-inclined (joint B)", "fub88", "fyb88", "d0_14", f"={CB(bk,'VB','N')}", "=0"),
              ("C", "M12", "M12 HDG 8.8  base-inclined (joint C)", "fub88", "fyb88", "d0_14", f"={CB(bk,'Rc','L')}", "=0"),
              ("M", "M8", "M8 SS-304 (A2-70)  module-inclined (slot 9x14)", "fub_ss", "fyb_ss", "d0_M8", f"={CB(bk,'Ftbabs','L')}", f"={CB(bk,'Fnbpos','L')}")]
    for j, nm, lab, fub, fyb, d0, V, T in joints:
        s.section(lab)
        s.row(f"c{j}_kb", "kb = min(e/(3 d0), fub/fu, 1.0)  (single bolt, no pitch)", f"=MIN(edge_min/(3*{d0}),{fub}/fu,1)", "-", "cl 10.3.4", "V", fmt="0.000", note="e = 22.5 mm (smaller edge/end distance)")
        s.row(f"c{j}_Vdsb", "Vdsb = fub/sqrt3 * An / gmb", f"={fub}/SQRT(3)*bolt_{nm}_An/gamma_mb", "N", "cl 10.3.3", "V", fmt="#,##0")
        s.row(f"c{j}_Vdpb", "Vdpb = 2.5 kb d t fu / gmb x k_over", f"=2.5*c{j}_kb*bolt_{nm}_d*sec_t*fu/gamma_mb*k_over", "N", "cl 10.3.4; ply t = 5 mm", "V", fmt="#,##0")
        s.row(f"c{j}_Tdb", "Tdb = min(0.9 fub An, fyb Asb gm1/gm0)/gmb", f"=MIN(0.9*{fub}*bolt_{nm}_An,{fyb}*bolt_{nm}_Asb*gamma_m1/gamma_m0)/gamma_mb", "N", "cl 10.3.5", "V", fmt="#,##0")
        s.row(f"c{j}_V", "Design shear (envelope)", V, "N", "Combos", fmt="#,##0.0"); s.row(f"c{j}_T", "Design tension (envelope)", T, "N", "Combos", fmt="#,##0.0")
        ck(s, f"ck_{j}", f"Bolt {nm} joint {j}  (shear / tension / combined, max)",
           f"=MAX(c{j}_V/MIN(c{j}_Vdsb,c{j}_Vdpb),c{j}_T/c{j}_Tdb,(c{j}_V/MIN(c{j}_Vdsb,c{j}_Vdpb))^2+(c{j}_T/c{j}_Tdb)^2)", 1, "cl 10.3.6 combined", unit="-", fmt="0.000")
    s.section("End / edge distances - cl 10.2.4.2: >= 1.5 d0 (rolled / machine-flame-cut edges)")
    holes = [("Base Ø14 @A  (end 27.5, edge 22.5)", "d0_14", "MIN(base_end_A,edge_min)"), ("Base Ø14 @C  (end 25, edge 22.5)", "d0_14", "MIN(base_end_C,edge_min)"),
             ("Base Ø18 J-bolt holes  (edge 22.5)", "d0_J", "edge_min"), ("Vertical Ø14  (end 22.5)", "d0_14", "MIN(vert_end,edge_min)"),
             ("Inclined Ø14 @B  (end 27.47)", "d0_14", "MIN(incl_end_B,edge_min)"), ("Inclined Ø14 @C  (end 28.92)", "d0_14", "MIN(incl_end_C,edge_min)"),
             ("Inclined slot 9x14  (edge 22.5)", "d0_M8", "edge_min")]
    for i, (lab, d0, e) in enumerate(holes):
        s.row(f"ed{i}_min", lab + " - required 1.5 d0", f"=1.5*{d0}", "mm", "cl 10.2.4.2", "V", fmt="0.0")
        s.row(f"ed{i}_act", "   provided (minimum of end / edge)", f"={e}", "mm", "", "V", fmt="0.0")
        s.row(f"ed{i}_ok", "   status", f'=IF(ed{i}_act>=ed{i}_min,"PASS","FAIL")', "", "", fmt="@",
              note="DRAWING NON-CONFORMANCE: 22.5 < 27.0" if i == 2 else "")
    s.finish(); return s


def sh_ballast(bk):
    s = Sh(bk, "Ballast", tab="C00000")
    s.banner("10  BALLAST STABILITY  -  uplift, sliding (horizontal movement), overturning",
             "Per FRAME (2 frames + 4 blocks per table). IS 800 Table 4: 0.9 DL when stabilising, 1.5 WL / 1.5 EQ. Friction mu only; no roof anchorage. J-bolts tie frame to block.")
    s.std_header(); s.section("Weights per frame")
    s.row("b_gamc", "Unit weight of concrete", "=gam_c*1E-6", "N/mm3", "IS 875-1", "V", fmt="0.000E+00")
    s.row("b_Wb1", "Weight of ONE block = gamma_c * w * h * L (provided)", "=b_gamc*block_w*block_h*block_L", "N", "block_L is an input (Inputs sheet)", "I", fmt="#,##0.0")
    s.row("b_massb", "   = mass of one block", "=b_Wb1/gacc", "kg", "", fmt="0.0")
    s.row("b_Wmh", "Half module (dead)", "=l_Wm/2", "N", "", fmt="0.0"); s.row("b_Wfr", "Frame steel (base+vertical+inclined)", "=l_Wbase+l_Wv+l_Winc", "N", "", fmt="0.0")
    s.row("b_Wfs", "Non-ballast dead load per frame", "=b_Wmh+b_Wfr", "N", "", fmt="0.0"); s.row("b_Wtot", "Total dead load per frame incl. 2 blocks", "=b_Wfs+2*b_Wb1", "N", "", fmt="0.0")
    s.section("Wind resultant per frame (sum of 2 slot loads, unfactored)")
    ar = bk.reg["Analysis"]
    res_ = lambda col, k1, kq1, kq2: f"=2*Analysis!${col}${ar[k1]}+Analysis!${col}${ar[kq1]}*g_Lm+Analysis!${col}${ar[kq2]}*g_BC"
    s.row("b_Fux", "Uplift case: Fx (module bolts + UDL)", res_("E", "Fx_s", "qmx", "qrx"), "N", "", fmt="0.0"); s.row("b_Fuy", "Uplift case: Fy (up)", res_("E", "Fy_s", "qmy", "qry"), "N", "", fmt="0.0")
    s.row("b_Fdx", "Downward case: Fx", res_("F", "Fx_s", "qmx", "qrx"), "N", "", fmt="0.0"); s.row("b_Fdy", "Downward case: Fy", res_("F", "Fy_s", "qmy", "qry"), "N", "", fmt="0.0")
    s.row("b_Mfs", "Restoring moment of non-ballast DL about right toe", "=b_Wmh*(g_xpr-g_xQ)+b_Wfr*(g_xpr-g_AC/2)", "N.mm", "", fmt="#,##0")
    s.row("b_Mot", "Overturning moment, uplift case (factored 1.5) about right toe", "=ll_fac*(b_Fuy*(g_xpr-g_xQ)+b_Fux*g_yQ)", "N.mm", "vertical uplift lever + horizontal x height", fmt="#,##0")
    s.section("REQUIRED block weight (each criterion solved for Wb; largest governs)")
    s.row("b_Wb_up", "Uplift:  0.9(Wfs+2Wb) >= 1.5 Fuy", "=(ll_fac*b_Fuy/dl_stab-b_Wfs)/2", "N", "IS 800 Table 4", fmt="#,##0.0")
    s.row("b_Wb_sl", "Sliding: mu[0.9(Wfs+2Wb) - 1.5 Fuy] >= 1.5 Fux", "=((ll_fac*b_Fuy+ll_fac*b_Fux/mu_f)/dl_stab-b_Wfs)/2", "N", "friction on roof", fmt="#,##0.0")
    s.row("b_Wb_ot", "Overturning about right toe", "=(b_Mot/dl_stab-b_Mfs)/((g_xpr-g_xb1)+(g_xpr-g_xb2))", "N", "", fmt="#,##0.0")
    s.row("b_Wb_bk", "Per-block net uplift (J-bolt reactions, Combos)", f"=MAX({CB(bk,'Tb1','L')},{CB(bk,'Tb2','L')})/dl_stab", "N", "0.9 Wb >= T_block", fmt="#,##0.0")
    s.row("b_Wb_req", "Required weight per block", "=MAX(0,b_Wb_up,b_Wb_sl,b_Wb_ot,b_Wb_bk)", "N", "", fmt="#,##0.0")
    s.row("b_L_req", "Required block length (300 w x 250 h)", "=b_Wb_req/(b_gamc*block_w*block_h)", "mm", "", fmt="0.0")
    s.row("b_L_rnd", "Required block length, rounded up to 50 mm", "=ROUNDUP(b_L_req/50,0)*50", "mm", "", fmt="0")
    s.row("b_gov", "Governing criterion", '=IF(b_Wb_req=b_Wb_sl,"Sliding (friction)",IF(b_Wb_req=b_Wb_ot,"Overturning",IF(b_Wb_req=b_Wb_bk,"Per-block uplift","Uplift")))', "", "", fmt="@")
    s.section("CHECKS with PROVIDED block (Inputs: block_L)")
    ck(s, "bk_up", "Global uplift (factored)", "=ll_fac*b_Fuy", "=dl_stab*b_Wtot", "0.9 DL >= 1.5 WL")
    ck(s, "bk_sl", "Sliding - uplift case (horizontal movement)", "=ll_fac*b_Fux", "=mu_f*MAX(0,dl_stab*b_Wtot-ll_fac*b_Fuy)", "mu N, N = 0.9DL - 1.5 Fuy")
    ck(s, "bk_ot", "Overturning - uplift case", "=b_Mot", "=dl_stab*(b_Mfs+b_Wb1*((g_xpr-g_xb1)+(g_xpr-g_xb2)))", "about right toe of block 2", unit="N.mm", fmt="#,##0")
    ck(s, "bk_bl", "Per-block uplift from J-bolt reactions", f"=MAX({CB(bk,'Tb1','L')},{CB(bk,'Tb2','L')})", "=dl_stab*b_Wb1", "frame continuity moment included")
    ck(s, "bk_sd", "Sliding - downward wind", "=ll_fac*ABS(b_Fdx)", "=mu_f*(1.5*b_Wtot+ll_fac*ABS(b_Fdy))", "1.5DL + 1.5WL")
    ck(s, "bk_od", "Overturning - downward wind (left toe)", "=MAX(0,ll_fac*(ABS(b_Fdx)*g_yQ-ABS(b_Fdy)*(g_xQ-g_xpl)))",
       "=1.5*(b_Wmh*(g_xQ-g_xpl)+b_Wfr*(g_AC/2-g_xpl)+b_Wb1*((g_xb1-g_xpl)+(g_xb2-g_xpl)))", "", unit="N.mm", fmt="#,##0")
    ck(s, "bk_se", "Sliding - seismic", "=ll_fac*l_Ah*b_Wtot", "=mu_f*dl_stab*b_Wtot", "IS 1893 horizontal; no vertical EQ")
    ck(s, "bk_oe", "Overturning - seismic", "=ll_fac*l_Ah*(b_Wmh*g_yQ+b_Wfr*(g_yA+g_yB)/2+2*b_Wb1*block_h/2)", "=dl_stab*(b_Mfs+b_Wb1*((g_xpr-g_xb1)+(g_xpr-g_xb2)))", "", unit="N.mm", fmt="#,##0")
    s.section("Information for the building structural engineer")
    s.row("b_roof", "Average ballast + array dead load on roof footprint", "=2*b_Wtot/1000/((base_len/1000)*(mod_L/1000))", "kN/m2", "per module footprint 1.2 x 2.279 m", "I", fmt="0.00", note="CONFIRM roof slab capacity")
    s.row("b_blkmass", "Number of blocks in project (82 tables x 4)", "=82*4", "nos", "BOM: 82 tables, 8 J-bolts/table", "V", fmt="0")
    s.row("b_concvol", "Concrete volume for all blocks", "=b_blkmass*block_w*block_h*block_L/1E9", "m3", "", fmt="0.0")
    s.finish(); return s


def sh_anchor(bk):
    s = Sh(bk, "Anchorage", tab="C00000")
    s.banner("11  J-BOLT ANCHORAGE  -  M16 (as drawn) and M10 (alternate)",
             "IS 800 cl 10.3 (bolt steel) + IS 456 cl 26.2 (bond + standard hook). Concrete-cone breakout is not covered by any IS -> NOT checked (declared).")
    s.std_header(); s.section("Demands per J-bolt (envelope, strength combinations)")
    s.row("a_T", "Max factored tension in any J-bolt", f"={CB(bk,'Tj','L')}", "N", "frame-continuity reactions J1..J4", fmt="#,##0.0")
    s.row("a_V", "Shear per J-bolt = max |H| / 4 (equal share)", f"={CB(bk,'RH1','N')}/4", "N", "all 4 bolts of a rigid frame", "I", fmt="#,##0.0")
    s.row("a_tau", "Design bond stress tau_bd (plain bar, tension)", "=VLOOKUP(fck,TAU_tab,2,FALSE)", "MPa", "IS 456 cl 26.2.1.1", "V", fmt="0.00")
    s.row("a_Lsmin", "Practical minimum straight embedment", 100, "mm", "engineering practice (not IS)", "I", fmt="0", inp=True)
    s.row("a_plate", "Plate washer PLT 50x50x5 thickness", 5, "mm", "Drawing sh.2", "I", fmt="0.0", inp=True)
    for nm, tw, tsp, tn, th in [("M16", 3.0, 4.0, 14.8, 4.0), ("M10", 2.5, 2.5, 8.4, 3.0)]:
        s.section(f"{nm} J-bolt  (HDG 8.8)")
        s.row(f"a_{nm}_tw", "Plain washer thickness (x4 per BOM)", tw, "mm", "IS 2016", "I", fmt="0.0", inp=True)
        s.row(f"a_{nm}_tsp", "Spring washer thickness", tsp, "mm", "IS 3063", "I", fmt="0.0", inp=True)
        s.row(f"a_{nm}_tn", "Nut height", tn, "mm", "IS 1364", "I", fmt="0.0", inp=True)
        s.row(f"a_{nm}_th", "Thread beyond nut (2 pitches)", th, "mm", "", "I", fmt="0.0", inp=True)
        s.row(f"a_{nm}_Tdb", "Tdb = min(0.9 fub An, fyb Asb gm1/gm0)/gmb", f"=MIN(0.9*fub88*bolt_{nm}_An,fyb88*bolt_{nm}_Asb*gamma_m1/gamma_m0)/gamma_mb", "N", "cl 10.3.5", "V", fmt="#,##0")
        s.row(f"a_{nm}_Vdsb", "Vdsb = fub/sqrt3 An / gmb", f"=fub88/SQRT(3)*bolt_{nm}_An/gamma_mb", "N", "cl 10.3.3", "V", fmt="#,##0")
        s.row(f"a_{nm}_kb", "kb for bearing on base leg (hole Ø18)", f"=MIN(edge_min/(3*d0_J),fub88/fu,1)", "-", "cl 10.3.4", "V", fmt="0.000")
        s.row(f"a_{nm}_Vdpb", "Vdpb x k_over (hole larger than standard)", f"=2.5*a_{nm}_kb*bolt_{nm}_d*sec_t*fu/gamma_mb*k_over", "N", "", "V", fmt="#,##0")
        ck(s, f"ak_{nm}_T", f"{nm} bolt tension", "=a_T", f"=a_{nm}_Tdb", "cl 10.3.5")
        ck(s, f"ak_{nm}_C", f"{nm} combined shear+tension", f"=(a_V/MIN(a_{nm}_Vdsb,a_{nm}_Vdpb))^2+(a_T/a_{nm}_Tdb)^2", 1, "cl 10.3.6", unit="-", fmt="0.000")
        s.row(f"a_{nm}_hook", "Anchorage value of standard hook = 16 phi", f"=16*bolt_{nm}_d", "mm", "IS 456 cl 26.2.2.1", "V", fmt="0")
        s.row(f"a_{nm}_Lsreq", "Straight embedment required = max(0, T/(tau pi phi) - hook)", f"=MAX(0,a_T/(a_tau*PI()*bolt_{nm}_d)-a_{nm}_hook)", "mm", "IS 456 cl 26.2.1: Ld = phi sigma/(4 tau)", "V", fmt="0.0")
        s.row(f"a_{nm}_Lsrec", "Straight embedment adopted = max(required, practical min)", f"=MAX(a_{nm}_Lsreq,a_Lsmin)", "mm", "", fmt="0")
        ck(s, f"ak_{nm}_B", f"{nm} bond + hook pull-out", "=a_T", f"=a_tau*PI()*bolt_{nm}_d*(a_{nm}_Lsrec+a_{nm}_hook)", "IS 456 cl 26.2.1 / 26.2.2.1")
        s.row(f"a_{nm}_Lproj", "Projection above block (leg+plate+4 washers+spring+nut+thread)", f"=sec_t+a_plate+4*a_{nm}_tw+a_{nm}_tsp+a_{nm}_tn+a_{nm}_th", "mm", "", "I", fmt="0.0")
        s.row(f"a_{nm}_Ltot", f"REQUIRED {nm} J-BOLT LENGTH (shank, to start of hook)", f"=ROUNDUP((a_{nm}_Lproj+a_{nm}_Lsrec)/10,0)*10", "mm", "projection + embedment, rounded to 10 mm", fmt="0")
        s.row(f"a_{nm}_fit", "Fit in block: embedment + 3 phi bend + 25 mm cover <= block height", f'=IF(a_{nm}_Lsrec+3*bolt_{nm}_d+25<=block_h,"PASS","FAIL")', "", "", fmt="@")
    s.row("a_BOM", "BOM J-bolt length (M16)", 150, "mm", "Hardware BOM item 5", "V", fmt="0", inp=True)
    s.row("a_BOMok", "BOM length >= required M16 length?", '=IF(a_BOM>=a_M16_Ltot,"PASS","FAIL")', "", "", fmt="@")
    s.section("Not covered by any IS (declared)")
    s.row("a_note", "Concrete cone breakout / side-blowout of J-bolts in a 300x250 block", "not checked", "", "No IS provision; ballast weight (Ballast sheet) resists uplift by mass", "I", fmt="@")
    s.finish(); return s


def sh_deflection(bk):
    s = Sh(bk, "Deflection", tab="F4B084")
    s.banner("12  DEFLECTION  -  IS 800:2007 cl 5.6.1, Table 6 (service loads DL + WL, unfactored)",
             "Limit L/180 (brittle glass cladding) on the inclined rail; base overhangs limited to 2 x overhang / 180 (cantilever, assumed). R1: module UDL included.")
    s.std_header()
    s.row("d_EI", "EI (in-plane, free sideways)", "=Es*g_Ieff", "N.mm2", "I_eff from Section", fmt="0.000E+00")
    s.row("d_a1", "Load 1 distance to nearest support", "=MIN(g_s1,g_BC-g_s1)", "mm", "", fmt="0.00"); s.row("d_a2", "Load 2 distance to nearest support", "=MIN(g_s2,g_BC-g_s2)", "mm", "", fmt="0.00")
    for cid, col in (("S1", "J"), ("S2", "K")):
        s.row(f"d_inc_{cid}", f"Inclined member mid-span deflection, {cid}", f"=ABS({CB(bk,'Fn',col)}*(d_a1*(3*g_BC^2-4*d_a1^2)+d_a2*(3*g_BC^2-4*d_a2^2))/(48*d_EI)+{CB(bk,'qn',col)}*5*g_BC^4/(384*d_EI))", "mm", "points: P a (3L^2-4a^2)/(48EI); UDL: 5 q L^4/(384EI) over full span (conservative)", fmt="0.0000")
        s.row(f"d_A_{cid}", f"Base tip deflection at A, {cid}", f"=ABS({CB(bk,'dA',col)})", "mm", "Analysis step 3", fmt="0.0000")
        s.row(f"d_C_{cid}", f"Base tip deflection at C, {cid}", f"=ABS({CB(bk,'dC',col)})", "mm", "", fmt="0.0000")
    ck(s, "dk_inc", "Inclined member (limit L/180)", "=MAX(d_inc_S1,d_inc_S2)", "=g_BC/defl_div", "Table 6 purlins/rails, brittle cladding", unit="mm", fmt="0.0000")
    ck(s, "dk_A", "Base overhang A (limit 2a/180)", "=MAX(d_A_S1,d_A_S2)", "=2*g_a1/defl_div", "Table 6 cantilever (assumed)", unit="mm", fmt="0.0000")
    ck(s, "dk_C", "Base overhang C (limit 2c/180)", "=MAX(d_C_S1,d_C_S2)", "=2*g_c2/defl_div", "", unit="mm", fmt="0.0000")
    s.finish(); return s


SUMMARY = [  # (key, label, clause, unit_divisor_hint)
 ("Members", None, None), ("mk_vT", "Vertical member - tension", "IS 800 cl 6.2, 6.3"), ("mk_vC", "Vertical member - compression (single-bolt angle strut)", "IS 800 cl 7.1.2, 7.5.1.2, Table 12"),
 ("mk_iT", "Inclined member - tension + bending", "IS 800 cl 9.3.1"), ("mk_iC", "Inclined member - compression + bending", "IS 800 cl 9.3.2"), ("mk_iV", "Inclined member - shear", "IS 800 cl 8.4"),
 ("mk_bS", "Base member - axial + bending at J-bolt sections", "IS 800 cl 9.3, 8.2"), ("mk_bM", "Base member - axial + bending at mid-span", "IS 800 cl 9.3, 8.2"), ("mk_bV", "Base member - shear", "IS 800 cl 8.4"),
 ("Connections", None, None), ("ck_A", "M10 bolt, base-vertical (joint A)", "IS 800 cl 10.3.3-10.3.6"), ("ck_B", "M10 bolt, vertical-inclined (joint B)", "IS 800 cl 10.3.3-10.3.6"),
 ("ck_C", "M12 bolt, base-inclined (joint C)", "IS 800 cl 10.3.3-10.3.6"), ("ck_M", "M8 SS bolt, module-inclined", "IS 800 cl 10.3.3-10.3.6"),
 ("Ballast stability (per frame)", None, None), ("bk_up", "Global uplift", "IS 800 Table 4 (0.9DL + 1.5WL)"), ("bk_sl", "Sliding / horizontal movement - wind uplift case", "IS 800 Table 4; friction mu"),
 ("bk_ot", "Overturning - wind uplift case", "IS 800 Table 4"), ("bk_bl", "Per-block uplift (J-bolt reactions)", "IS 800 Table 4"), ("bk_sd", "Sliding - downward wind", "IS 800 Table 4"),
 ("bk_od", "Overturning - downward wind", "IS 800 Table 4"), ("bk_se", "Sliding - seismic", "IS 1893-1:2016; IS 800 Table 4"), ("bk_oe", "Overturning - seismic", "IS 1893-1:2016; IS 800 Table 4"),
 ("J-bolt anchorage", None, None), ("ak_M16_T", "M16 J-bolt tension", "IS 800 cl 10.3.5"), ("ak_M16_C", "M16 J-bolt shear+tension", "IS 800 cl 10.3.6"), ("ak_M16_B", "M16 bond + hook pull-out", "IS 456 cl 26.2.1, 26.2.2.1"),
 ("ak_M10_T", "M10 J-bolt tension", "IS 800 cl 10.3.5"), ("ak_M10_C", "M10 J-bolt shear+tension", "IS 800 cl 10.3.6"), ("ak_M10_B", "M10 bond + hook pull-out", "IS 456 cl 26.2.1, 26.2.2.1"),
 ("Serviceability", None, None), ("dk_inc", "Inclined member deflection", "IS 800 cl 5.6.1, Table 6"), ("dk_A", "Base overhang A deflection", "IS 800 Table 6 (assumed)"), ("dk_C", "Base overhang C deflection", "IS 800 Table 6 (assumed)"),
]


def sh_summary(bk):
    ws = bk.wb.create_sheet("Summary"); ws.sheet_properties.tabColor = "00B050"; ws.sheet_view.showGridLines = False
    for i, w in enumerate((5, 58, 34, 15, 15, 8, 11, 10), 1): ws.column_dimensions[CL(i)].width = w
    ws.cell(1, 1, "0  DESIGN SUMMARY  -  45 kWp ballast-type rooftop MMS, CDSCO Hyderabad").font = Font(bold=True, size=14, color="FFFFFF")
    for c in range(1, 9): ws.cell(1, c).fill = PatternFill("solid", fgColor=NAVY)
    ws.cell(2, 1, "All cells are live formulas linked to the calculation sheets. Units: N, mm unless stated. PASS = utilisation <= 1.0").font = Font(italic=True, size=9)
    r = 4
    def kv(label, f, fmt="0.00", unit=""):
        nonlocal r
        ws.cell(r, 2, label); c = ws.cell(r, 4, f); c.number_format = fmt; c.font = Font(bold=True); ws.cell(r, 5, unit); r += 1
    ws.cell(r, 2, "KEY RESULTS").font = Font(bold=True, color=NAVY); r += 1
    kv("Tilt angle", "=g_tilt_deg", "0.000", "deg"); kv("Design wind pressure pd", "=w_pd", "0.000", "kN/m2"); kv("Uplift force per module (normal)", "=w_Nup/1000", "0.000", "kN")
    kv("Downward force per module (normal)", "=w_Ndn/1000", "0.000", "kN"); kv("Governing ballast criterion", "=b_gov", "@"); kv("REQUIRED ballast block length (300 x 250 x L)", "=b_L_rnd", "0", "mm")
    kv("PROVIDED ballast block length", "=block_L", "0", "mm"); kv("Weight of one block", "=b_massb", "0.0", "kg"); kv("Average roof load (ballast + array)", "=b_roof", "0.00", "kN/m2")
    kv("Max J-bolt tension (factored)", "=a_T/1000", "0.000", "kN"); kv(f"REQUIRED M10 J-bolt length", "=a_M10_Ltot", "0", "mm"); kv("REQUIRED M16 J-bolt length (BOM = 150)", "=a_M16_Ltot", "0", "mm")
    r += 1
    hdr = ["#", "Check", "Clause", "Demand", "Capacity", "Unit", "Utilisation", "Status"]
    for i, h in enumerate(hdr, 1):
        c = ws.cell(r, i, h); c.font = Font(bold=True, color="FFFFFF", size=9); c.fill = PatternFill("solid", fgColor="44546A"); c.alignment = Alignment(horizontal="center")
    r += 1; n = 0; urs = []; oks = []; first = r
    for key, label, clause in SUMMARY:
        if label is None:
            for c in range(1, 9): ws.cell(r, c).fill = PatternFill("solid", fgColor=LBLUE)
            ws.cell(r, 2, key).font = Font(bold=True, color=NAVY); r += 1; continue
        n += 1
        ws.cell(r, 1, n).font = Font(size=8, color="7F7F7F"); ws.cell(r, 2, label); ws.cell(r, 3, clause).font = Font(size=9)
        ws.cell(r, 4, f"={key}_d").number_format = "#,##0.0##"; ws.cell(r, 5, f"={key}_c").number_format = "#,##0.0##"
        ws.cell(r, 6, "N" if not key.startswith(("dk", "bk_ot", "bk_od", "bk_oe")) else ("mm" if key.startswith("dk") else "N.mm")).font = Font(size=9)
        if key in ("mk_iT", "mk_iC", "mk_bS", "mk_bM", "ck_A", "ck_B", "ck_C", "ck_M", "ak_M16_C", "ak_M10_C"): ws.cell(r, 6, "ratio")
        ws.cell(r, 7, f"={key}_ur").number_format = "0.000"; ws.cell(r, 8, f"={key}_ok").alignment = Alignment(horizontal="center")
        for c in range(4, 9): ws.cell(r, c).border = BORDER
        urs.append(f"G{r}"); oks.append(f"H{r}"); r += 1
    last = r - 1; bk.sum_rng = (first, last)
    r += 1
    ws.cell(r, 2, "Maximum utilisation (all checks)").font = Font(bold=True); ws.cell(r, 7, f"=MAX(G{first}:G{last})").number_format = "0.000"; ws.cell(r, 7).font = Font(bold=True); r += 1
    ws.cell(r, 2, "Number of FAILED checks").font = Font(bold=True); ws.cell(r, 7, f'=COUNTIF(H{first}:H{last},"FAIL")'); ws.cell(r, 7).font = Font(bold=True); fcell = f"G{r}"; r += 1
    ws.cell(r, 2, "Edge/end-distance checks failed (Connections sheet)").font = Font(bold=True)
    ws.cell(r, 7, "=" + "+".join(f'IF(ed{i}_ok="FAIL",1,0)' for i in range(7))); ws.cell(r, 7).font = Font(bold=True); ecell = f"G{r}"; r += 1
    ws.cell(r, 2, "OVERALL").font = Font(bold=True, size=12)
    c = ws.cell(r, 7, f'=IF({fcell}+{ecell}=0,"PASS","REVIEW")'); c.font = Font(bold=True, size=12)
    ws.cell(r, 8, "see Notes O1 (Ø18 hole edge distance)").font = Font(size=8, italic=True)
    red, grn = PatternFill("solid", fgColor=RED), PatternFill("solid", fgColor=GRN)
    ws.conditional_formatting.add(f"A1:H{r+2}", CellIsRule(operator="equal", formula=['"PASS"'], fill=grn, font=Font(color="006100", bold=True)))
    ws.conditional_formatting.add(f"A1:H{r+2}", CellIsRule(operator="equal", formula=['"FAIL"'], fill=red, font=Font(color="9C0006", bold=True)))
    ws.conditional_formatting.add(f"A1:H{r+2}", CellIsRule(operator="equal", formula=['"REVIEW"'], fill=PatternFill("solid", fgColor="FFEB9C"), font=Font(color="9C5700", bold=True)))
    ws.freeze_panes = "A4"


def sh_staad_map(bk):
    s = Sh(bk, "STAAD_Map", tab="7030A0")
    s.banner("13  STAAD MODEL MAP  -  nodes, members, loads, and Excel-vs-STAAD comparison", "Model file: staad/CDSCO_45kW_frame.std.  Paste STAAD results into the yellow cells: differences are computed automatically (tolerance 1 %).")
    s.std_header(); s.section("Nodes (m).  y measured from roof surface.  STAAD: UNIT METER KN for JOINT COORDINATES")
    nodes = [("A", "0", "g_yA"), ("J1", "g_J1", "g_yA"), ("J2", "g_J2", "g_yA"), ("J3", "g_J3", "g_yA"), ("J4", "g_J4", "g_yA"), ("C", "g_AC", "g_yA"),
             ("B", "0", "g_yB"), ("S1", "g_S1x", "g_S1y"), ("M", "g_Mx", "g_My"), ("S2", "g_S2x", "g_S2y"), ("Pa", "g_Pax", "g_Pay"), ("Pb", "g_Pbx", "g_Pby")]
    for i, (n, x, y) in enumerate(nodes, 1):
        s.row(f"sn_{n}x", f"Node {i} = {n}   X", f"=({x})/1000", "m", "", fmt="0.00000"); s.row(f"sn_{n}y", f"            {n}   Y", f"=({y})/1000", "m", "", fmt="0.00000")
    s.section("Members, properties, releases, supports (as in the .std file)")
    for t in ["Base: members 1-5 = A-J1, J1-J2, J2-J3, J3-J4, J4-C   beam, PRISMATIC AX=sec_A IZ=I_eff IY=I_eff (constant EI)",
              "Vertical: member 6 = A-B   MEMBER TRUSS (axial only: pinned single-bolt joints)",
              "Rafter: members 7-12 = B-Pa, Pa-S1, S1-M, M-S2, S2-Pb, Pb-C; member 12: END release MZ at C (pin). Pa-Pb = module contact zone",
              "Supports: J1 = FX FY FZ MX MY fixed (MZ free);  J2, J3, J4 = FY FZ MX MY fixed",
              "Load cases: 1 DL, 2 WL uplift, 3 WL down, 4 EQ +X. R1: module weight = UNI GY on members 8-11 (UDL over contact zone); rafter self-weight UNI on 7-12; base UDL on 1-5. Combos 11-18 = C1-C6, S1, S2",
              "STAAD printed in NEWTON/MMS: reaction FY is UP-positive (same sign as Excel R); axial: STAAD prints +ve = compression, so compare ABS."]:
        s.ws.cell(s.r, 2, t).font = Font(size=9); s.r += 1
    s.section("COMPARISON  Excel (closed form)  vs  STAAD  (paste STAAD values in yellow; units N / mm)")
    s.header(["#", "Quantity", "", "Excel", "STAAD", "Diff %", "Status", "STAAD output to read"])
    items = [("Reaction FY at J1, C1", CB(bk, "R1", "D")), ("Reaction FY at J2, C1", CB(bk, "R2", "D")), ("Reaction FY at J3, C1", CB(bk, "R3", "D")), ("Reaction FY at J4, C1", CB(bk, "R4", "D")),
             ("Reaction FY at J1, C2", CB(bk, "R1", "E")), ("Reaction FY at J2, C2", CB(bk, "R2", "E")), ("Reaction FY at J3, C2", CB(bk, "R3", "E")), ("Reaction FY at J4, C2", CB(bk, "R4", "E")),
             ("Reaction FX at J1, C2", CB(bk, "RH1", "E")), ("Axial force member A-B, C1 (abs)", f"ABS({CB(bk,'NAB','D')})"), ("Axial force member A-B, C2 (abs)", f"ABS({CB(bk,'NAB','E')})"),
             ("Vertical displacement node A, S2 (abs, mm)", f"ABS({CB(bk,'dA','K')})"), ("Vertical displacement node C, S2 (abs, mm)", f"ABS({CB(bk,'dC','K')})"),
             ("Rafter moment at node M, C1 (abs, N.mm)", f"ABS({CB(bk,'MincM','D')})"), ("Rafter moment at node M, C2 (abs, N.mm)", f"ABS({CB(bk,'MincM','E')})")]
    cmp0 = s.r
    for i, (lab, ref) in enumerate(items, 1):
        r = s.r; ws = s.ws
        ws.cell(r, 1, i).font = Font(size=8, color="7F7F7F"); ws.cell(r, 2, lab)
        ws.cell(r, 4, "=" + ref).number_format = "#,##0.000"
        c = ws.cell(r, 5, None); c.fill = PatternFill("solid", fgColor=YEL); c.number_format = "#,##0.000"; c.border = BORDER
        absf = "ABS(E{r})" if "abs" in lab else "E{r}"; d = "ABS(D{r})" if "abs" in lab else "D{r}"
        ws.cell(r, 6, f'=IF(ISNUMBER(E{r}),IF(ABS(D{r})<1,ABS({absf.format(r=r)}-{d.format(r=r)}),({absf.format(r=r)}-{d.format(r=r)})/ABS({d.format(r=r)})*100),"")').number_format = "0.000"
        ws.cell(r, 7, f'=IF(ISNUMBER(F{r}),IF(ABS(F{r})<=1,"PASS","FAIL"),"")')
        ws.cell(r, 8, "Reactions / Node Displacements tables" if "Reaction" in lab or "displ" in lab else ("Beam End Forces, member 9 (S1-M), end M, Mz" if "moment" in lab else "Beam End Forces, member 6 (A-B)")).font = Font(size=8, italic=True)
        s.r += 1
    s.finish(); return s


REGISTER = [
 ("Basic wind speed Vb, Hyderabad = 44 m/s", "IS 875-3 Annex A", "Verified (2 search sources: IITK-GSDMA W02, infralens)", "Primary code text not opened (egress blocked)"),
 ("Kd = 0.9 (frames), Ka = 1.0 (<=10 m2), Kc combination", "IS 875-3:2015 cl 7.2.1, 7.2.2, 7.3.3.13", "Verified (search)", "Kc=0.9 applies to combined wall+roof+internal pressures; net Cp used here so Kc=1.0 (house practice)"),
 ("k1 = 0.91 (25-yr life)", "IS 875-3 Table 1 (house value, issued ground-mount jobs)", "Assumption", "k1 = 1.0 (50-yr, occupied building) raises pd by 21 % -> see Notes sensitivity"),
 ("k2 Cat 2: 1.00 @10 m, 1.05 @15 m, 1.07 @20 m; Cat 3: 0.91, 0.97, 1.01", "IS 875-3 Table 2", "10 m/Cat 2 verified (house); remaining values RECALLED", "The search result only echoed the query -> not independent confirmation"),
 ("Cp (mono-slope free roof, phi=0): 10 deg +0.5/-0.9; 15 deg +0.7/-1.1", "IS 875-3 Table 7", "Verified (house: checked against table image in an issued design document)", "Linear interpolation at 10.115 deg"),
 ("Load combinations 1.5(DL+WL); 0.9DL + 1.5WL", "IS 800:2007 Table 4", "Verified (search)", ""),
 ("gamma_m0 = 1.10, gamma_m1 = 1.25, gamma_mb = 1.25", "IS 800:2007 Table 5", "Recalled", "Standard values"),
 ("Table 12: single bolt, hinged: k1=1.25, k2=0.50, k3=60", "IS 800:2007 cl 7.5.1.2", "Verified (search)", ""),
 ("Bearing reduction 0.7 for oversize / short-slot holes", "IS 800:2007 cl 10.3.4", "Verified (search)", "Applied conservatively to M10/M12 in Ø14 holes and M8 in 9x14 slot"),
 ("Min edge/end distance 1.5 d0 (rolled / machine-flame-cut)", "IS 800:2007 cl 10.2.4.2", "Recalled", "Ø18 J-bolt hole FAILS (22.5 < 27)"),
 ("tau_bd (M20, plain bar, tension) = 1.2 N/mm2; hook = 16 phi", "IS 456:2000 cl 26.2.1.1, 26.2.2.1", "Verified (multiple search sources)", ""),
 ("Zone II, Z = 0.10 (Hyderabad); Sa/g = 2.5", "IS 1893 (Part 1):2016 Table 3, cl 6.4.2", "Recalled", "Zone/Z to be confirmed by client basis"),
 ("Component seismic coefficient Ah = (Z/2) I (Sa/g)(1+z/h)/Rp, Rp = 2.5", "IS 1893-1:2016 (component provisions; ASCE-type form)", "ASSUMPTION - clause text not retrievable offline", "Rp = 1 gives Ah = 0.25: seismic sliding UR rises to 1.04 (FAIL) -> confirm Rp"),
 ("Friction coefficient mu = 0.4", "SEAOC PV2 (search: conservative value unless test-justified)", "Verified source / assumed surface", "Roof finish unknown"),
 ("Module 550 Wp, 2279 x 1134 x 35 mm, 29.1 kg; holes 1400 x ~1090 mm", "Manufacturer datasheets (search)", "Single-source weight; hole pitch consistent with drawing (slots 1088 c/c)", "Replace with actual module"),
 ("ISA 50x50x5: A=480.3 mm2, Ixx=Iyy=10.96 cm4, Iuu=17.38, Ivv=4.55", "Computed (exact polygon, r1=7, r2=3.5); IS 808 catalogue A=4.80, I=11.0, Iuu=17.5, Ivv=4.5", "Verified by two methods",
  "REJECTED search snippet (Cxx 1.24 cm, Iuu 10.2, Ivv 2.66): Iuu+Ivv must equal Ixx+Iyy = 21.9 cm4"),
 ("Concrete 24 kN/m3, steel 78.5 kN/m3", "IS 875-1 Table 1", "Recalled", ""),
 ("Bolt stress areas M8 36.6, M10 58, M12 84.3, M16 157 mm2; 8.8: fub 800, fyb 640", "ISO 898-1 / IS 1367", "Recalled", "SS A2-70 (700/450) is an ASSUMPTION - BOM gives no class"),
 ("Module dead load = UDL w = Wm/(2 W) on each rafter over the contact length W", "Client comment R1 (no purlins); statics: 2 rafters, symmetric overhangs", "Design requirement - load-conserving derivation (check row l_udl_chk = 0)", "Contact length = module width (module parallel to rafter) is an inference"),
 ("Module wind: bolt points (wind_mode 0) vs UDL (wind_mode 1)", "Load path via 4 M8 bolts; bounding alternative provided", "Design choice, both results reported", "wind_mode 1 raises rafter UR from 0.12 to 0.41"),
 ("Primary sources NOT opened", "law.resource.org, iitk.ac.in, docs.bentley.com, easy-calc.com, eng-tips.com", "Blocked by environment egress policy", "Cross-check every clause number against licensed code copies before issue"),
]


def sh_register(bk):
    ws = bk.wb.create_sheet("Register"); ws.sheet_properties.tabColor = "7F7F7F"; ws.sheet_view.showGridLines = False
    for i, w in enumerate((5, 66, 52, 44, 60), 1): ws.column_dimensions[CL(i)].width = w
    ws.cell(1, 1, "14  VERIFICATION REGISTER  -  source and status of every code value").font = Font(bold=True, size=14, color="FFFFFF")
    for c in range(1, 6): ws.cell(1, c).fill = PatternFill("solid", fgColor=NAVY)
    for i, h in enumerate(["#", "Value / provision used", "Source / clause", "Status", "Comment"], 1):
        c = ws.cell(3, i, h); c.font = Font(bold=True, color="FFFFFF", size=9); c.fill = PatternFill("solid", fgColor="44546A")
    for n, (a, b, c_, d) in enumerate(REGISTER, 1):
        r = 3 + n
        for j, v in enumerate((n, a, b, c_, d), 1):
            x = ws.cell(r, j, v); x.alignment = Alignment(wrap_text=True, vertical="top"); x.border = BORDER
        st = ws.cell(r, 4)
        if st.value.startswith(("Verified", "10 m", "Single")): st.fill = PatternFill("solid", fgColor=GRN)
        elif "REJECT" in d or "Blocked" in st.value or "ASSUMPTION" in st.value: st.fill = PatternFill("solid", fgColor=RED)
        else: st.fill = PatternFill("solid", fgColor="FFEB9C")


NOTES = [
 ("OBSERVATIONS ON THE ISSUED DRAWING / BOM (for the drawing owner)", None),
 ("O1", "J-bolt holes Ø18 in a 50 mm leg: smaller edge distance 22.5 mm < 1.5 d0 = 27 mm (IS 800 cl 10.2.4.2). Cannot be cured by moving the hole (max possible minimum edge distance in a 50 mm leg = 25 mm). Options: M12 J-bolt in Ø14 hole (1.5 d0 = 21 mm OK), or M10 J-bolt in Ø12 hole (18 mm OK) - which also supports the M10 alternative checked in this workbook."),
 ("O2", "M10 bolts (BOM 2, 3) in Ø14 holes = 4 mm clearance (standard 1-2 mm). Bearing reduced x0.7 (cl 10.3.4). Recommend Ø11/Ø12 holes."),
 ("O3", "Ballast block LENGTH (across the frame) is not on the drawing. Design result: governing criterion is SLIDING; required length is on the Summary sheet for 300 w x 250 h blocks (mu = 0.4). Drawing should state it."),
 ("O4", "Base member is continuous over the two J-bolts of each block; overhang loads create a couple on the bolt pair (J1 uplift is ~4x the average share). The J-bolt design uses the continuous-beam reactions, not the average."),
 ("O5", "BOM 'Total Qty' column shows ####### (narrow column). Totals = 82 x qty/table: 164, 164, 164, 328, 656."),
 ("O6", "Drawing note says 'dimensions in meters' but all values are mm."),
 ("O7", "Out-of-plane (east-west) stability of each frame relies on the module acting as a link between the 2 frames and on the J-bolt pairs; no out-of-plane load is in the model. Wind direction parallel to the ridge gives small horizontal load; recommended to confirm with client's module clamp details."),
 ("ASSUMPTIONS (inferences, each a single input cell on the Inputs sheet)", None),
 ("A1", "1 table = 1 module (45 kWp / 82 = 549 Wp) carried on 2 frames at 1400 mm (module hole pitch); 4 blocks and 8 J-bolts per table (matches BOM)."),
 ("A2", "Module 550 Wp, 2279 x 1134 x 35, 29.1 kg. Wind load shared equally by the 4 module bolts."),
 ("A3", "Terrain category 2 (conservative; Cat 3 = dense urban lowers pd by ~16 %), roof level 12 m, k1 = 0.91 (25-yr). k1 = 1.0 would raise pd by 21 %."),
 ("A4", "Net pressure coefficient (Table 7, solidity 0) applied as a uniform pressure over the module; no roof edge/corner zoning, no shielding by adjacent rows (conservative for interior rows)."),
 ("A5", "Friction coefficient 0.4 between block and roof; roof finish not known. No roof anchorage assumed."),
 ("A6", "Members E250 (fy 250, fu 410). Holes at bolt gauge 27.5 from heel; frame bolt line 27.5 above block top; eccentricities between bolt line and member centroid neglected."),
 ("A7", "Single bolt per lap joint = moment-free; angle loaded through one leg (cl 7.5.1.2, single bolt, hinged). No LTB reduction (spans <= 550 mm)."),
 ("A8", "Seismic: Zone II, I = 1.0, Sa/g = 2.5, Ah per assumed component formula (Rp = 2.5). Seismic sliding is sensitive to Rp - see Register."),
 ("A10", "R1 load path: the module rests directly on the two rafters (no purlins). Module dead load is a UDL over the contact length (= module width 1134 mm) of each rafter, w = Wm/(2 W) = module weight per area x tributary width (L/2 = 1139.5 mm). The 439.5 mm module overhang beyond each rafter is carried by the module. Rafter self-weight is a UDL (stubs spread). Module WIND is transferred through the 4 M8 bolts (wind_mode 0); wind_mode 1 applies it as a UDL as well (bounding case) - both satisfy all checks."),
 ("A9", "J-bolt: plain-bar bond (tau_bd 1.2, M20) + standard hook 16 phi; practical minimum embedment 100 mm; concrete cone breakout not checked (no IS provision)."),
 ("NOT INCLUDED", None),
 ("N1", "Roof slab / beam capacity under ballast (average load on Summary) - building structural engineer to confirm."),
 ("N2", "Module clamping capacity and module frame checks (module manufacturer)."),
 ("N3", "Corrosion allowance / HDG thickness, thermal effects, construction loads, snow (Hyderabad: nil)."),
 ("N4", "STAAD XtraReport PDF: must be produced from STAAD.Pro itself (see staad/REPORT_STEPS.md). Not generated here."),
]


def sh_notes(bk):
    ws = bk.wb.create_sheet("Notes"); ws.sheet_properties.tabColor = "7F7F7F"; ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 14; ws.column_dimensions["B"].width = 150
    ws.cell(1, 1, "15  NOTES  -  observations, assumptions, exclusions").font = Font(bold=True, size=14, color="FFFFFF")
    for c in range(1, 3): ws.cell(1, c).fill = PatternFill("solid", fgColor=NAVY)
    r = 3
    for k, t in NOTES:
        if t is None:
            for c in range(1, 3): ws.cell(r, c).fill = PatternFill("solid", fgColor=LBLUE)
            ws.cell(r, 1, k).font = Font(bold=True, color=NAVY)
        else:
            ws.cell(r, 1, k).font = Font(bold=True); x = ws.cell(r, 2, t); x.alignment = Alignment(wrap_text=True, vertical="top")
            ws.row_dimensions[r].height = 15 * (1 + len(t)//150)
        r += 1
    r += 1
    for c in range(1, 3): ws.cell(r, c).fill = PatternFill("solid", fgColor=LBLUE)
    ws.cell(r, 1, "SENSITIVITY (STATIC table generated from the Python engine at build time; the live workbook recalculates when Inputs change)").font = Font(bold=True, color=NAVY); r += 1
    import sensitivity
    ws.cell(r, 2, "scenario  |  pd kN/m2  |  required block length mm (raw / rounded 50)  |  governs  |  max utilisation at 650 mm  |  seismic sliding UR").font = Font(bold=True, size=9); r += 1
    for lab, pd_, lr, lrr, gov, mur, eq in sensitivity.run():
        ws.cell(r, 2, "%-42s |  %.3f  |  %4.0f / %4d  |  %-10s |  %.2f  |  %.2f" % (lab, pd_, lr, lrr, gov, mur, eq)).font = Font(name="Consolas", size=9); r += 1
    ws.cell(r, 2, "Seismic sliding UR is independent of block weight (mu*0.9 vs 1.5*Ah): at Rp = 1.0 it exceeds 1.0 for any block size -> confirm the IS 1893 component basis.").font = Font(italic=True, size=9)


def sh_index(bk):
    ws = bk.wb.create_sheet("Index", 0); ws.sheet_properties.tabColor = "00B050"; ws.sheet_view.showGridLines = False
    ws.column_dimensions["A"].width = 4; ws.column_dimensions["B"].width = 26; ws.column_dimensions["C"].width = 100
    ws.cell(1, 1, "CDSCO HYDERABAD - 45 kWp BALLAST-TYPE ROOFTOP MMS  |  DESIGN CALCULATION (IS 800:2007 LSD)").font = Font(bold=True, size=14, color="FFFFFF")
    for c in range(1, 4): ws.cell(1, c).fill = PatternFill("solid", fgColor=NAVY)
    info = [("Client / EPC", "M/s Sai Babuji Projects Pvt Ltd"), ("Design & Engg", "M/s JSP Solar Energy"), ("Drawing", "AL-001 R0 (10.09.2026, For Information)"),
            ("Structure", "ISA 50x50x5 frame, 10.115 deg tilt, ballast blocks + J-bolts, 82 tables"), ("Codes", "IS 875 (Pt 1,3), IS 800:2007 LSD, IS 456:2000 (anchorage), IS 1893 (Pt 1):2016"),
            ("Revision", "R1 - module dead load as UDL on rafters per client comment (see sheet Revision; R0 superseded)")]
    for i, (a, b) in enumerate(info):
        ws.cell(3 + i, 2, a).font = Font(bold=True); ws.cell(3 + i, 3, b)
    r = 10
    ws.cell(r, 2, "Sheet").font = Font(bold=True, color=NAVY); ws.cell(r, 3, "Content (calculation flows top to bottom)").font = Font(bold=True, color=NAVY); r += 1
    for nm, d in [("Summary", "All checks, utilisation, PASS/FAIL, key results"), ("Revision", "R1: client comment, response, R0 -> R1 comparison"), ("Inputs", "All inputs (yellow) + code tables - CHANGE ONLY HERE"), ("Section", "ISA 50x50x5 properties, unsymmetric-bending modulus"),
                  ("Geometry", "Bolt-centre frame, positions, constants"), ("Wind", "IS 875-3: Vz, pz, pd, Cp, forces"), ("Loads", "Dead and seismic loads"), ("Analysis", "Closed-form frame statics per load case (= STAAD model)"),
                  ("Combos", "IS 800 Table 4 combinations and envelopes"), ("Members", "IS 800 member checks"), ("Connections", "Bolt checks per BOM + edge distances"), ("Ballast", "Uplift / sliding / overturning, required block size"),
                  ("Anchorage", "J-bolt M16 and M10: bolt steel, bond + hook, required length"), ("Deflection", "Serviceability"), ("STAAD_Map", "Node/member map and Excel vs STAAD comparison"),
                  ("Register", "Source and verification status of every code value"), ("Notes", "Observations on drawing, assumptions, exclusions")]:
        c = ws.cell(r, 2, nm); c.hyperlink = f"#'{nm}'!A1"; c.font = Font(color="0563C1", underline="single"); ws.cell(r, 3, d); r += 1
    r += 1
    ws.cell(r, 2, "Colour code").font = Font(bold=True)
    for txt, col in (("Input (editable)", YEL), ("PASS", GRN), ("FAIL", RED)):
        r += 1; ws.cell(r, 2, txt).fill = PatternFill("solid", fgColor=col)
    r += 2
    ws.cell(r, 2, "Overall status").font = Font(bold=True, size=12)
    f0, f1 = bk.sum_rng
    ws.cell(r, 3, f'="Maximum utilisation "&TEXT(MAX(Summary!G{f0}:G{f1}),"0.000")&"   |   failed checks: "&COUNTIF(Summary!H{f0}:H{f1},"FAIL")&"   |   overall: "&Summary!G{f1+5}').font = Font(bold=True)


def sh_revision(bk):
    import json
    R0 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "R0_results.json")))
    ws = bk.wb.create_sheet("Revision"); ws.sheet_properties.tabColor = "00B050"; ws.sheet_view.showGridLines = False
    for i, w in enumerate((5, 58, 30, 24, 12, 52), 1): ws.column_dimensions[CL(i)].width = w
    ws.cell(1, 1, "REVISION R1  -  module dead load applied as UDL on the rafters (client comment)").font = Font(bold=True, size=14, color="FFFFFF")
    for c in range(1, 7): ws.cell(1, c).fill = PatternFill("solid", fgColor=NAVY)
    r = 3
    def block(title, lines):
        nonlocal r
        for c in range(1, 7): ws.cell(r, c).fill = PatternFill("solid", fgColor=LBLUE)
        ws.cell(r, 2, title).font = Font(bold=True, color=NAVY); r += 1
        for t in lines:
            x = ws.cell(r, 2, t); x.alignment = Alignment(wrap_text=True, vertical="top"); ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
            ws.row_dimensions[r].height = 15 * (1 + len(t)//140); r += 1
        r += 1
    block("Client comment", ["Since no purlins are provided in the proposed MMS arrangement and the PV modules are directly supported by the rafters, the module self-weight shall not be considered as concentrated/point loads at the joints. Revise the STAAD model by applying the module dead load as an appropriate UDL on the supporting rafters based on the actual module dimensions, support arrangement and tributary length. Revise the structural analysis/design and load calculations accordingly."])
    block("Response", ["1. Module dead load is now a UDL on each rafter over the module contact length: w = (Wm / (L x W)) x (L/2) = Wm / (2 W). Module 2279 x 1134 mm, 29.1 kg -> 0.1105 kN/m2; tributary width per rafter = 1139.5 mm (2 rafters at 1400 c/c, 439.5 mm overhang each side carried by the module); contact length along the rafter = 1134 mm (centred on the 4 module bolts, inside the rafter's physical length). w = 0.1259 kN/m (see sheet Loads, rows l_pm .. l_udl_chk).",
                       "2. Rafter self-weight is also a UDL (previously lumped at the bolts). Seismic mass of module and rafter follows the same UDL.",
                       "3. STAAD: two extra nodes (Pa, Pb) mark the contact zone; UNI GY loads on members 8-11 (module) and 7-12 (rafter). Statics, member checks, connection, deflection and the module-bolt demand rows were revised; analysis rows now carry the UDL zones with an exact zero-shear peak moment.",
                       "4. Module WIND: transferred to the rafter through the 4 M8 module bolts (point loads at the bolts, wind_mode 0 - unchanged from R0). The bounding alternative with wind also applied as a UDL (wind_mode 1) is available at one input cell and reported in the report; both satisfy every check.",
                       "5. Ballast, J-bolt and base-member results are unchanged because the resultant and its line of action are unchanged: only the rafter itself is affected."])
    for i, h in enumerate(["", "Quantity", "R0 (point loads at module bolts)", "R1 (UDL, live from this workbook)", "R1 / R0", "Comment"], 1):
        c = ws.cell(r, i, h); c.font = Font(bold=True, color="FFFFFF", size=9); c.fill = PatternFill("solid", fgColor="44546A"); c.alignment = Alignment(wrap_text=True, horizontal="center")
    r += 1
    rows = [("Module dead load on rafter (N/mm)", "2 x Wm/4 point loads", "=l_udl_m", None, "0.00000", "UDL over 1134 mm"),
            ("Rafter max |M|, strength combinations (N.m)", R0["env"]["inc_M"]/1e3, "=m_iM/1000", "r", "0.00", "governs rafter bending; combo C1"),
            ("Rafter N+M utilisation (tension) cl 9.3.1", R0["member_ur"]["Inclined  N+M (T)  cl 9.3.1"], "=mk_iT_ur", "r", "0.000", "PASS"),
            ("Rafter N+M utilisation (compression)", R0["member_ur"]["Inclined  N+M (C)  cl 9.3.1"], "=mk_iC_ur", "r", "0.000", "PASS"),
            ("Rafter shear utilisation", R0["member_ur"]["Inclined  shear cl 8.4"], "=mk_iV_ur", "r", "0.000", ""),
            ("Rafter deflection, service (mm)", max(v["inc"] for v in R0["defl"].values()), "=MAX(d_inc_S1,d_inc_S2)", "r", "0.000", "limit L/180 = 6.48 mm"),
            ("M8 module-bolt utilisation", R0["bolt_ur"]["M8 module (SS A2-70)"], "=ck_M_ur", "r", "0.0000", "bolt load path unchanged"),
            ("Max J-bolt tension, factored (N)", R0["anchor"]["M16"]["T"], "=a_T", "r", "#,##0.0", ""),
            ("Reaction J1, combination C2 (N)", R0["C2"]["R1"], "=" + CB(bk, "R1", "E"), "r", "#,##0.0", ""),
            ("Reaction J4, combination C2 (N)", R0["C2"]["R4"], "=" + CB(bk, "R4", "E"), "r", "#,##0.0", ""),
            ("Required block length, 300x250 section (mm)", R0["L_req"], "=b_L_req", "r", "0.0", "sliding governs - unchanged"),
            ("Sliding utilisation, provided 650 mm", R0["bal_ur"]["slide"], "=bk_sl_ur", "r", "0.0000", ""),
            ("Overturning utilisation", R0["bal_ur"]["overt"], "=bk_ot_ur", "r", "0.0000", "")]
    for lab, v0, f1, rr, fmt, cm in rows:
        ws.cell(r, 2, lab); a = ws.cell(r, 3, v0); a.number_format = fmt; a.font = Font(color="7F7F7F"); b = ws.cell(r, 4, f1); b.number_format = fmt; b.font = Font(bold=True)
        if rr: ws.cell(r, 5, f"=D{r}/C{r}").number_format = "0.00"
        ws.cell(r, 6, cm).font = Font(size=9, italic=True)
        for cc in range(2, 6): ws.cell(r, cc).border = BORDER
        r += 1
    r += 1; ws.cell(r, 2, "R0 values are static (from the issued R0 calculation, git tag R0); R1 values are live formulas.").font = Font(italic=True, size=9)


def build(out="../excel/CDSCO_45kW_Ballast_MMS_Design_Calc.xlsx"):
    bk = Book()
    sh_inputs(bk); sh_section(bk); sh_geometry(bk); sh_wind(bk); sh_loads(bk)
    sh_analysis(bk); sh_combos(bk)
    sh_members(bk); sh_connections(bk); sh_ballast(bk); sh_anchor(bk); sh_deflection(bk)
    sh_staad_map(bk); sh_register(bk); sh_notes(bk)
    sh_revision(bk); bk.wb.move_sheet("Revision", offset=-(len(bk.wb.sheetnames) - 1))
    sh_summary(bk); bk.wb.move_sheet("Summary", offset=-(len(bk.wb.sheetnames) - 1))
    sh_index(bk)
    bk.wb.properties.title = "CDSCO 45kWp Ballast MMS - Design Calculation"; bk.wb.properties.creator = "JSP Solar Energy (draft)"
    bk.wb.save(out); return bk


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../excel/CDSCO_45kW_Ballast_MMS_Design_Calc.xlsx"
    import os; os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    build(out); print("wrote", out)
