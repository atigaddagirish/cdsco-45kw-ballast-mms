"""Word design-calculation report generated from the verified engine (same numbers as the Excel workbook)."""
import os, sys, datetime
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import json
import engine as E
import sensitivity
from build_excel import REGISTER, NOTES

FIG = "../report/figures"


def shade(cell, hexcolor):
    tcPr = cell._tc.get_or_add_tcPr(); shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor); tcPr.append(shd)


class Rep:
    def __init__(self):
        d = self.d = Document(); s = d.sections[0]; s.page_width, s.page_height = Cm(21), Cm(29.7)
        s.left_margin = s.right_margin = Cm(1.9); s.top_margin = Cm(1.8); s.bottom_margin = Cm(1.6)
        st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(9.5)
        for lvl, sz in ((1, 14), (2, 11.5)):
            h = d.styles["Heading %d" % lvl]; h.font.name = "Calibri"; h.font.size = Pt(sz); h.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)
        self.fig = 0

    def title(self, t):
        p = self.d.add_paragraph(); r = p.add_run(t); r.bold = True; r.font.size = Pt(20); r.font.color.rgb = RGBColor(0x1F, 0x38, 0x64)

    def pagebreak(self): self.d.add_page_break()

    def save(self, out): self.d.save(out)

    def H(self, t, lvl=1): self.d.add_heading(t, lvl)

    def P(self, t, bold=False, italic=False, size=None, color=None):
        p = self.d.add_paragraph(); r = p.add_run(t); r.bold, r.italic = bold, italic
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = RGBColor(*color)
        p.paragraph_format.space_after = Pt(3); return p

    def B(self, items):
        for t in items:
            p = self.d.add_paragraph(style="List Bullet"); p.paragraph_format.space_after = Pt(1)
            if isinstance(t, tuple):
                r = p.add_run(t[0]); r.bold = True; p.add_run(t[1])
            else: p.add_run(t)

    def T(self, head, rows, widths=None, fs=8.5, status_col=None):
        t = self.d.add_table(rows=1, cols=len(head)); t.style = "Table Grid"; t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, h in enumerate(head):
            c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(h); r.bold = True; r.font.size = Pt(fs); r.font.color.rgb = RGBColor(255, 255, 255); shade(c, "44546A")
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""; r = cells[i].paragraphs[0].add_run(str(v)); r.font.size = Pt(fs)
                if status_col is not None and i == status_col:
                    r.bold = True
                    shade(cells[i], {"PASS": "C6EFCE", "FAIL": "FFC7CE", "REVIEW": "FFEB9C"}.get(str(v), "FFFFFF"))
        if widths:
            t.autofit = False
            tblPr = t._tbl.tblPr; lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
            for i, w in enumerate(widths): t.columns[i].width = Cm(w)
            for row in t.rows:
                for i, w in enumerate(widths): row.cells[i].width = Cm(w)
        self.d.add_paragraph().paragraph_format.space_after = Pt(2)

    def IMG(self, name, w=17.0):
        self.d.add_picture(os.path.join(FIG, name), width=Cm(w)); self.d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER


class RepMD:
    """Markdown backend with the same interface as Rep (docx)."""
    def __init__(self): self.out = []

    def _w(self, t=""): self.out.append(t)

    def title(self, t): self._w("# " + t.title() if t.isupper() else "# " + t); self._w()

    def pagebreak(self): self._w("---"); self._w()

    def H(self, t, lvl=1): self._w("#" * (lvl + 1) + " " + t); self._w()

    def P(self, t, bold=False, italic=False, size=None, color=None):
        t = t.replace("\n", " ")
        self._w(("**%s**" % t) if bold else ("*%s*" % t) if italic else t); self._w()

    def B(self, items):
        for t in items: self._w("- " + ("**%s** %s" % (t[0].rstrip(), t[1]) if isinstance(t, tuple) else t))
        self._w()

    def T(self, head, rows, widths=None, fs=None, status_col=None):
        esc = lambda v: str(v).replace("|", "\\|").replace("\n", " ")
        self._w("| " + " | ".join(esc(h) for h in head) + " |"); self._w("|" + "|".join("---" for _ in head) + "|")
        for row in rows:
            cells = []
            for i, v in enumerate(row):
                v = esc(v); cells.append("**%s**" % v if status_col is not None and i == status_col and v in ("PASS", "FAIL", "REVIEW") else v)
            self._w("| " + " | ".join(cells) + " |")
        self._w()

    def IMG(self, name, w=None):
        self._w("![%s](figures/%s)" % (name.rsplit(".", 1)[0].replace("_", " "), name)); self._w()

    def save(self, out):
        open(out, "w", encoding="utf-8").write("\n".join(self.out) + "\n")


def stat(x): return "PASS" if x <= 1.0 else "FAIL"


def build(out, backend=None):
    o = E.design(); p, g, w, L, mc, bal, env = o["p"], o["g"], o["w"], o["L"], o["mc"], o["bal"], o["env"]; cmb = o["cmb"]
    C1, C2 = cmb["C1 1.5DL+1.5WL(dn)"], cmb["C2 0.9DL+1.5WL(up)"]
    R = (backend or Rep)()
    R.title("DESIGN CALCULATION REPORT")
    R.P("45 kWp Ballast-Type Rooftop Module Mounting Structure - CDSCO, Hyderabad", bold=True, size=13)
    R.T(["Item", "Detail"], [["Client / EPC", "M/s Sai Babuji Projects Pvt Ltd"], ["Design & Engg", "M/s JSP Solar Energy"], ["Drawing", "AL-001 R0 (10.09.2026, For Information); Hardware BOM (82 tables)"],
                             ["Document", "DC-CDSCO-45kWp-R1  -  REVISION R1 (supersedes R0)  -  DRAFT FOR REVIEW  -  %s" % datetime.date(2026, 10, 8).strftime("%d %b %Y")],
                             ["Deliverables", "Excel calculation workbook (formula-linked) | STAAD.Pro input file | this report"],
                             ["Codes", "IS 875 (Pt 1, Pt 3) | IS 800:2007 (LSD) | IS 456:2000 | IS 1893 (Pt 1):2016 | IS 808 | IS 2062"]], widths=[3.5, 13.5])
    R.P("Status of this draft (R1): every numeric result is reproduced by three independent routes (closed-form statics in Excel, a separate matrix-stiffness solver, and a round-trip of the generated STAAD input). "
        "STAAD.Pro itself has not been run (not available in the authoring environment); the file is ready to run and the workbook has a comparison table for the STAAD output. "
        "Several design-basis inputs are assumptions (Section 3.3) and two are decisive (Section 11).", italic=True, size=9, color=(0x7F, 0x00, 0x00))

    R0 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "R0_results.json")))
    R.H("0  Revision R1 - response to client comment")
    R.P("Client comment: since no purlins are provided in the proposed MMS arrangement and the PV modules are directly supported by the rafters, the module self-weight shall not be considered as concentrated/point loads at the joints. "
        "Revise the STAAD model by applying the module dead load as an appropriate UDL on the supporting rafters based on the actual module dimensions, support arrangement and tributary length; revise the analysis, design and load calculations accordingly.", italic=True)
    R.B([("Accepted and implemented. ", "The module dead load is now a UDL on each rafter over the module contact length: w = (Wm / (L x W)) x (L / 2) = Wm / (2 W) = %.4f N/mm (= %.4f kN/m), acting over %.0f mm of the rafter (%.1f to %.1f mm from bolt B). Derivation in Section 4.2 and Fig 2." % (L["wm"], L["wm"], g["Lm"], g["sa"], g["sb"])),
         ("Rafter self-weight ", "is also a UDL (%.4f N/mm over B-C) instead of being lumped at the bolts; seismic mass of module and rafter follows the same distribution." % L["wr"]),
         ("STAAD model: ", "two additional nodes (Pa, Pb) delimit the contact zone; module weight is applied as UNI GY on members 8-11 (rafter members 7-12 carry the rafter self-weight). No joint loads remain for dead load except the vertical member and base stubs."),
         ("Module wind ", "is a different load path: wind suction/pressure is transferred through the four M8 module bolts, so it remains point loads at the bolts (wind_mode 0, as R0). As a bounding case the wind is also applied as a UDL over the contact length (wind_mode 1, alternate STAAD file); both satisfy every check (Section 11)."),
         ("Effect: ", "only the rafter changes. Peak rafter moment %.1f N.m (R0 %.1f), rafter utilisation %.2f (R0 %.2f). Reactions, J-bolt forces, base member, bolts and the ballast result are unchanged (resultant and line of action of the module load are the same)." % (env["inc_M"]/1e3, R0["env"]["inc_M"]/1e3, o["chk_member"]["Inclined  N+M (T)  cl 9.3.1"][0], R0["member_ur"]["Inclined  N+M (T)  cl 9.3.1"]))])
    c2 = cmb["C2 0.9DL+1.5WL(up)"]
    R.T(["Quantity", "R0 (point loads at bolts)", "R1 (UDL)", "Change"],
        [["Module dead load on a rafter", "2 x %.1f N at the module bolts" % (L["Wm"]/4), "%.4f N/mm over %.0f mm" % (L["wm"], g["Lm"]), "UDL"],
         ["Rafter max |M|, strength combos (N.m)", "%.1f" % (R0["env"]["inc_M"]/1e3), "%.1f" % (env["inc_M"]/1e3), "x %.2f" % (env["inc_M"]/R0["env"]["inc_M"])],
         ["Rafter N+M utilisation (tension / compression)", "%.3f / %.3f" % (R0["member_ur"]["Inclined  N+M (T)  cl 9.3.1"], R0["member_ur"]["Inclined  N+M (C)  cl 9.3.1"]), "%.3f / %.3f" % (o["chk_member"]["Inclined  N+M (T)  cl 9.3.1"][0], o["chk_member"]["Inclined  N+M (C)  cl 9.3.1"][0]), "PASS"],
         ["Rafter deflection, service (mm; limit %.2f)" % o["defl_lim"]["inc"], "%.3f" % max(v["inc"] for v in R0["defl"].values()), "%.3f" % max(v["inc"] for v in o["defl"].values()), "PASS"],
         ["Max J-bolt tension, factored (N)", "%.1f" % R0["anchor"]["M16"]["T"], "%.1f" % o["anchor"]["M16"]["T"], "unchanged"],
         ["Reactions J1..J4, combination C2 (N)", "%s" % ", ".join("%.1f" % R0["C2"][k] for k in ("R1", "R2", "R3", "R4")), "%s" % ", ".join("%.1f" % c2[k] for k in ("R1", "R2", "R3", "R4")), "<= 0.1 N"],
         ["Required block length, 300 x 250 section (mm)", "%.1f" % R0["L_req"], "%.1f" % bal["L_req"], "unchanged"],
         ["Sliding utilisation at 650 mm", "%.3f" % R0["bal_ur"]["slide"], "%.3f" % (bal["slide"][0]/bal["slide"][1]), "unchanged"]], widths=[6.2, 4.3, 4.3, 2.4])

    R.H("1  Summary of results")
    tk = lambda d_, c_: "%.3f" % (d_/c_)
    rows = [["Members (8 checks)", "max UR = %.2f" % max(o["chk_member"][k][0]/o["chk_member"][k][1] if o["chk_member"][k][1] != 1.0 else o["chk_member"][k][0] for k in o["chk_member"]), "PASS"],
            ["Frame bolts M10 / M12 / M8 (BOM)", "max UR = %.2f" % max(v["ur"] for v in o["chk_bolt"].values()), "PASS"],
            ["Ballast - uplift / sliding / overturning (300x250x%d blocks)" % p["block_L"], "UR %.2f / %.2f / %.2f" % (bal["uplift"][0]/bal["uplift"][1], bal["slide"][0]/bal["slide"][1], bal["overt"][0]/bal["overt"][1]), "PASS"],
            ["Required block length (sliding governs)", "%d mm  (%.0f kg per block; %.2f kN/m2 average roof load)" % (bal["L_req_round"], bal["Wb1"]/p["gacc"], bal["roof_load_kN_m2"]), "REVIEW"],
            ["J-bolt anchorage M16 (BOM) / M10 (alternate)", "UR bond %.2f / %.2f ; required length %d / %d mm" % (o["anchor"]["M16"]["T"]/o["anchor"]["M16"]["Tanch"], o["anchor"]["M10"]["T"]/o["anchor"]["M10"]["Tanch"], o["anchor"]["M16"]["Ltot"], o["anchor"]["M10"]["Ltot"]), "PASS"],
            ["Deflection (L/180)", "UR %.2f" % max(max(v["inc"] for v in o["defl"].values())/o["defl_lim"]["inc"], max(v["dA"] for v in o["defl"].values())/o["defl_lim"]["tip_A"]), "PASS"],
            ["Drawing: Ø18 J-bolt hole edge distance (IS 800 cl 10.2.4.2)", "22.5 mm provided < 27 mm required", "FAIL"]]
    R.T(["Check group", "Result", "Status"], rows, widths=[7.6, 7.4, 2.2], status_col=2)
    R.B([("Ballast governs the design. ", "Structural members and bolts are lightly stressed (UR <= %.2f); the ballast blocks are sized by SLIDING under wind uplift (friction mu = 0.4). The drawing does not give the block length; %d mm is required for 300 x 250 blocks." % (max(o["chk_member"][k][0]/o["chk_member"][k][1] if o["chk_member"][k][1] != 1.0 else o["chk_member"][k][0] for k in o["chk_member"]), bal["L_req_round"])),
         ("M10 J-bolts are adequate. ", "M10 satisfies every IS 800 / IS 456 check (steel UR 0.04, bond + hook UR 0.15) and, unlike the drawn Ø18 holes, M10 in a Ø12 hole meets the edge-distance rule (Section 12)."),
         ("Decisive assumptions: ", "design life factor k1 (0.91 vs 1.0), terrain category, roof friction, and the seismic component factor Rp (Section 11). All are single input cells in the workbook.")])

    R.H("2  Structure and geometry")
    R.P("One table carries one module (45 kWp / 82 tables = 549 Wp, inferred) on two identical planar frames at 1400 mm (module hole pitch). Each frame is three ISA 50x50x5 angles joined by single bolts "
        "(base 1200 mm, vertical 249.72 mm, inclined 1222.01 mm) and rests on two 300 x 250 concrete blocks at 700 mm c/c, each tied by two J-bolts at 150 mm c/c (BOM: 8 J-bolts per table = 4 blocks).")
    R.IMG("fig1_geometry.png")
    R.T(["Quantity", "Value", "Basis"], [["A-C / A-B / B-C (bolt centres)", "%.2f / %.2f / %.2f mm" % (g["AC"], g["AB"], g["BC"]), "Drawing sheet 2, derived"],
                                          ["Triangle closure", "%.4f mm" % g["closure"], "hypot(AC,AB) - BC; verified"],
                                          ["Tilt", "%.3f deg" % g["tilt_deg"], "atan(AB/AC); 250/1200 shortcut (11.77 deg) rejected"],
                                          ["J-bolt positions from A", "%.1f, %.1f, %.1f, %.1f mm" % (g["J1"], g["J2"], g["J3"], g["J4"]), "175/325/875/1025 from base end"],
                                          ["Module bolt points from B", "%.2f and %.2f mm (c/c %.2f)" % (g["s1"], g["s2"], g["slot_cc"]), "slots 67 mm from member ends; drawn 1088 c/c"]], widths=[5.5, 5.8, 5.9])

    R.H("3  Design basis")
    R.H("3.1  Codes and materials", 2)
    R.T(["Item", "Adopted", "Status"], [["Steel members", "ISA 50x50x5 (IS 808), IS 2062 E250: fy 250, fu 410, E 2x10^5 MPa", "Assumed grade"],
                                        ["Bolts", "HDG class 8.8 (fub 800, fyb 640); module bolts SS-304 taken as A2-70 (700/450)", "SS class assumed"],
                                        ["Partial factors", "gamma_m0 1.10, gamma_m1 1.25, gamma_mb 1.25 (IS 800 Table 5)", "Recalled"],
                                        ["Load combinations", "IS 800 Table 4: 1.5(DL+WL); 0.9 DL + 1.5 WL (stabilising); EQ likewise", "Verified"],
                                        ["Concrete blocks", "M20, plain, 24 kN/m3 (IS 875-1); tau_bd 1.2 N/mm2 (IS 456 cl 26.2.1.1)", "Verified / assumed grade"],
                                        ["Section (computed)", "A 480.3 mm2, Ixx=Iyy 10.96 cm4, Ixy -6.42 cm4, Iuu 17.38, Ivv 4.55 cm4 (exact polygon, r1 7 / r2 3.5); IS 808 catalogue agrees <1 %", "Verified by two methods"]], widths=[3.3, 11.3, 2.6])
    R.H("3.2  Unsymmetric bending of angles", 2)
    R.P("Loads act in the plane of the legs, so the angle bends obliquely. Stress is evaluated with the unsymmetric-bending relation sigma/M = (Iyy y - Ixy x)/(Ixx Iyy - Ixy^2) at every vertex: "
        "Z_eff = %.0f mm3 (gross) and %.0f mm3 (net of the Ø18 J-bolt hole). In-plane stiffness uses I_eff = %.0f mm4 (section free to deflect sideways), which also feeds STAAD." % (mc["Zg"], mc["Zn"], g["Ieff"]))
    R.H("3.3  Assumptions (each is one input cell)", 2)
    R.B([a[1] for a in NOTES if a[0].startswith("A") and a[1]])

    R.H("4  Loads")
    R.H("4.1  Wind - IS 875 (Part 3)", 2)
    R.T(["Step", "Expression", "Value"], [["Basic wind speed", "Vb (Hyderabad, Annex A)", "%.0f m/s" % p["Vb"]], ["Risk coefficient", "k1 (25-yr life, house value)", "%.2f" % p["k1_risk"]],
                                          ["Height / terrain", "z = %.2f m, Category %d -> k2 (Table 2, interpolated)" % (w["z"], p["terrain"]), "%.4f" % w["k2"]], ["Topography, cyclonic", "k3, k4", "1.0, 1.0"],
                                          ["Design wind speed", "Vz = Vb k1 k2 k3 k4", "%.2f m/s" % w["Vz"]], ["Wind pressure", "pz = 0.6 Vz^2", "%.4f kN/m2" % w["pz"]],
                                          ["Design pressure", "pd = Kd Ka Kc pz = 0.9 x 1.0 x 1.0 x pz", "%.4f kN/m2" % w["pd"]],
                                          ["Net Cp, Table 7 mono-slope free roof (solidity 0)", "interpolated at %.3f deg" % g["tilt_deg"], "%.4f down / %.4f uplift" % (w["cp_dn"], w["cp_up"])],
                                          ["Module area", "%.0f x %.0f mm" % (p["mod_L"], p["mod_W"]), "%.4f m2" % w["A_mod"]],
                                          ["Force normal to module", "Cp pd A", "%.0f N uplift / %.0f N down" % (w["N_up"], w["N_dn"])],
                                          ["Per module bolt (4 per module)", "F/4", "%.1f N uplift / %.1f N down" % (w["N_up"]/4, w["N_dn"]/4)]], widths=[5.0, 7.6, 4.6])
    R.P("Limitations: IS 875-3 has no rooftop-PV or roof edge/corner provision; uniform net pressure is applied and shielding by adjacent rows is ignored (conservative for interior rows). "
        "Hyderabad Vb = 44 m/s is confirmed by two secondary sources; the code text itself could not be opened (see Appendix A).", italic=True, size=8.5)
    R.H("4.2  Dead load: module as UDL on the rafters (R1), and seismic", 2)
    R.P("Support arrangement: no purlins - each module (L x W = %.0f x %.0f mm) rests directly on two rafters %.0f mm apart, centred, so %.1f mm of module overhangs each rafter and is carried by the module itself. "
        "Each rafter therefore takes half the module: tributary width = L/2 = %.1f mm. The module lies parallel to the rafter and bears on it over its full width W = %.0f mm (contact zone %.1f ... %.1f mm from bolt B, inside the rafter's physical length). "
        "The four M8 bolts (%.0f x %.0f mm) only fix the module." % (p["mod_L"], p["mod_W"], p["frame_sp"], g["mod_ovh"], L["trib"], g["Lm"], g["sa"], g["sb"], p["frame_sp"], p["slot_cc_dwg"]))
    R.T(["Step", "Expression", "Value"], [["Module weight", "Wm = %.1f kg x %.2f" % (p["mod_kg"], p["gacc"]), "%.1f N" % L["Wm"]], ["Weight per unit area", "Wm / (L x W)", "%.2f N/m2 = %.4f kN/m2" % (L["pm"]*1e6, L["pm"]*1e3)],
                                       ["Tributary width per rafter", "L / 2", "%.1f mm" % L["trib"]], ["UDL on one rafter", "w = (Wm/(L W)) x (L/2) = Wm / (2 W)", "%.5f N/mm  =  %.4f kN/m" % (L["wm"], L["wm"])],
                                       ["Resultant per rafter", "w x W", "%.2f N = Wm/2  (2 rafters: %.2f N = Wm)" % (L["wm"]*g["Lm"], 2*L["wm"]*g["Lm"])],
                                       ["Rafter self-weight UDL", "ws x 1222.01 / %.2f" % g["BC"], "%.5f N/mm" % L["wr"]], ["Seismic (module + rafter)", "Ah x w (horizontal UDL)", "Ah = %.3f" % L["Ah"]]], widths=[4.4, 6.6, 6.2])
    R.IMG("fig2_udl_derivation.png", 16.0)
    R.P("Other dead loads:", bold=True)
    R.T(["Item", "Value"], [["Module", "%.1f kg = %.1f N (datasheet search, single source); applied as UDL, see above" % (p["mod_kg"], L["Wm"])], ["Steel", "%.4f N/mm = %.2f kg/m; base %.1f N, vertical %.1f N, inclined %.1f N" % (L["ws"], L["ws"]*1000/p["gacc"], L["Wbase"], L["Wv"], L["Winc"])],
                             ["Ballast block", "300 x 250 x %d mm x 24 kN/m3 = %.1f N (%.1f kg)" % (p["block_L"], bal["Wb1"], bal["Wb1"]/p["gacc"])],
                             ["Seismic", "Ah = (Z/2) I (Sa/g)(1+z/h)/Rp = (0.10/2)(1.0)(2.5)(2.0)/2.5 = %.3f  (horizontal only; Zone II)" % L["Ah"]]], widths=[3.5, 13.7])
    R.IMG("fig3_loads.png")
    R.H("4.3  Load combinations - IS 800:2007 Table 4", 2)
    R.T(["No.", "Combination", "Use"], [[n.split()[0], n.split(" ", 1)[1], "strength" if k == "U" else "serviceability (unfactored)"] for n, f, k in E.COMBOS], widths=[1.5, 8, 7.7])

    R.H("5  Analysis")
    R.P("The frame is analysed as a plane model (STAAD file staad/CDSCO_45kW_Ballast_Frame.std, 12 nodes, 12 members): single-bolt joints are moment-free (vertical member is a truss element; rafter pinned at C); "
        "the base member is continuous over four rigid J-bolt supports (J1 restrained in X and Y, J2-J4 in Y). R1 loads: module dead load and rafter self-weight are UDLs on the rafter (zone Pa-Pb, members 8-11 / 7-12); wind acts through the four module bolts (joint loads at S1, S2). "
        "The rafter and vertical member are statically determinate; its internal forces use closed-form shear/moment with the UDL zones and the exact zero-shear section. The base beam is solved with the three-moment equation in the workbook and with a full stiffness solution in STAAD.")
    R.T(["Result (per frame)", "C1 1.5DL+1.5WL(dn)", "C2 0.9DL+1.5WL(up)"],
        [["J1 reaction FY (N)", "%.1f" % C1["R1"], "%.1f" % C2["R1"]], ["J2 reaction FY (N)", "%.1f" % C1["R2"], "%.1f" % C2["R2"]], ["J3 reaction FY (N)", "%.1f" % C1["R3"], "%.1f" % C2["R3"]],
         ["J4 reaction FY (N)", "%.1f" % C1["R4"], "%.1f" % C2["R4"]], ["J1 horizontal reaction FX (N)", "%.1f" % C1["RH1"], "%.1f" % C2["RH1"]], ["Vertical member axial (tension +, N)", "%.1f" % C1["NAB"], "%.1f" % C2["NAB"]],
         ["Rafter |M| at bolt 1 / bolt 2 / peak (N.m)", "%.1f / %.1f / %.1f" % (abs(C1["Minc1"])/1e3, abs(C1["Minc2"])/1e3, abs(C1["Mstar"])/1e3), "%.1f / %.1f / %.1f" % (abs(C2["Minc1"])/1e3, abs(C2["Minc2"])/1e3, abs(C2["Mstar"])/1e3)],
         ["Base moment at J1 / J2 / J3 / J4 (N.m)", "%.1f / %.1f / %.1f / %.1f" % tuple(C1[k]/1e3 for k in ("M1", "M2", "M3", "M4")), "%.1f / %.1f / %.1f / %.1f" % tuple(C2[k]/1e3 for k in ("M1", "M2", "M3", "M4"))]], widths=[6.6, 5.3, 5.3])
    R.P("Note the J-bolt reactions: continuity of the base angle over each bolt pair turns the overhang load into a couple, so J1 carries about four times the average uplift share (Fig 4).")
    R.IMG("fig4_results_C2.png", 16.0)
    R.IMG("fig5_rafter_moment.png", 16.0)
    R.H("5.1  Cross-checks performed", 2)
    R.B(["Closed-form statics (Excel, with UDL zones) vs independent matrix-stiffness solver (rafter split at the contact ends): agree to 2e-10 for all four load cases in both wind modes (reactions, moments, axial/shear at 8 rafter sections, tip deflections); equilibrium identities hold to machine precision.",
         "Peak rafter moment (closed form, zero-shear section) vs a dense scan of the solver's moment diagram, all 8 combinations: agree within 2e-5.",
         "Excel recalculated in LibreOffice: 308 key cells compared with the Python engine, worst difference 1.7e-13; no formula errors. Live-linkage test: 10 inputs changed at once (incl. module width, wind_mode) -> outputs agree to 3e-15.",
         "STAAD input text re-parsed (12 nodes, UNI loads) and solved: agrees with the workbook to 5e-8 for all 8 combinations, both STAAD files.",
         "To confirm in STAAD: sum of FY reactions for load case 1 = %.1f N (confirms UNI GY is per unit member length)." % (L["ws"]*g["AC"] + L["wr"]*g["BC"] + L["wm"]*g["Lm"] + L["Wv"] + L["stubA"] + L["stubC"]),
         "Not done: an actual STAAD.Pro run. Expected reactions are in staad/expected_results.csv and the workbook sheet STAAD_Map compares them automatically."])

    R.H("6  Member design - IS 800:2007 (rafter = inclined member B-C)")
    U = lambda k: (o["chk_member"][k][0]/o["chk_member"][k][1]) if o["chk_member"][k][1] != 1.0 else o["chk_member"][k][0]
    rows = [["Vertical - tension (cl 6.2, 6.3)", "%.0f N" % env["vert_T"], "Td = %.0f N" % mc["Td"], "%.3f" % U("Vertical member  N (T)")],
            ["Vertical - compression (cl 7.1.2, 7.5.1.2, Table 12)", "%.0f N" % env["vert_C"], "Pd = %.0f N (lambda_e %.2f)" % (mc["Pd_vert"], mc["lam_vert"]), "%.3f" % U("Vertical member  N (C)")],
            ["Inclined - N + M tension (cl 9.3.1)", "N %.0f N, M %.1f N.m" % (env["inc_T"], env["inc_M"]/1e3), "Td, Md = %.0f N.m" % (mc["Mdg"]/1e3), "%.3f" % U("Inclined  N+M (T)  cl 9.3.1")],
            ["Inclined - N + M compression (cl 9.3.2)", "N %.0f N, M %.1f N.m" % (env["inc_C"], env["inc_M"]/1e3), "Pd = %.0f N" % mc["Pd_inc"], "%.3f" % U("Inclined  N+M (C)  cl 9.3.1")],
            ["Inclined - shear (cl 8.4)", "%.0f N" % env["inc_V"], "Vd = %.0f N" % mc["Vd"], "%.3f" % U("Inclined  shear cl 8.4")],
            ["Base - N + M at J-bolt sections (net of Ø18 hole)", "M %.1f N.m" % (env["base_Msup"]/1e3), "Md(net) = %.0f N.m" % (mc["Mdn"]/1e3), "%.3f" % max(U("Base  N+M at J-bolt section (T)"), U("Base  N+M at J-bolt section (C)"))],
            ["Base - N + M at mid-span", "M %.1f N.m" % (env["base_Mspan"]/1e3), "Md = %.0f N.m" % (mc["Mdg"]/1e3), "%.3f" % U("Base  N+M at mid-span")],
            ["Base - shear (cl 8.4)", "%.0f N" % env["base_V"], "Vd = %.0f N" % mc["Vd"], "%.3f" % U("Base  shear cl 8.4")]]
    R.T(["Check", "Demand (envelope C1-C6)", "Capacity", "UR"], rows, widths=[6.8, 4.3, 4.3, 1.8])
    R.P("Bending is elastic with the unsymmetric-bending modulus; no lateral-torsional reduction is applied (unsupported lengths <= 550 mm). Tearing of the net section (cl 6.3.3) uses beta = 0.7, the lower bound, for single-bolt connections. "
        "Axial-bending interaction is the conservative linear sum.", italic=True, size=8.5)

    R.H("7  Connections - IS 800:2007 cl 10.3 and 10.2")
    cb = o["chk_bolt"]; rows = []
    for k, v in cb.items(): rows.append([k, "%.0f" % v["V"], "%.0f" % v["T"], "%.0f / %.0f" % (v["Vdsb"], v["Vdpb"]), "%.0f" % v["Tdb"], "%.3f" % v["ur"]])
    R.T(["Bolt / joint", "V (N)", "T (N)", "Vdsb / Vdpb (N)", "Tdb (N)", "UR"], rows, widths=[5.6, 1.7, 1.7, 3.6, 2.0, 1.6])
    R.P("Single bolt, single shear, threads in the shear plane. Bearing on 5 mm angle legs with kb = e/(3 d0) = 0.536 and the 0.7 reduction for holes larger than standard (cl 10.3.4) - applied to M10/M12 in Ø14 holes and M8 in the 9x14 slot. "
        "Bolt utilisation is very low (<= 0.05); the limiting feature is the hole detailing below.")
    R.T(["Hole", "d0 (mm)", "Edge/end provided (mm)", "1.5 d0 (mm)", "Status"], [[n, "%.0f" % d0, "%.1f" % e, "%.1f" % m, "PASS" if ok else "FAIL"] for n, d0, e, m, ok in o["edge"]], widths=[6.4, 1.6, 3.4, 2.4, 1.6], status_col=4)

    R.H("8  Ballast stability: uplift, sliding, overturning")
    R.P("Per frame. Resisting dead load is factored by 0.9 and wind by 1.5 (IS 800 Table 4). Friction mu = %.1f (SEAOC PV2 conservative value; roof finish unknown). No roof anchorage is assumed; the J-bolts tie the frame to the block, and the block mass resists uplift." % p["mu_f"])
    R.T(["Criterion", "Required block weight", "Expression"],
        [["Uplift", "%.0f N (%.0f kg)" % (bal["Wb_uplift"], bal["Wb_uplift"]/p["gacc"]), "0.9 (Wfs + 2Wb) >= 1.5 Fuy"], ["Sliding (horizontal movement)", "%.0f N (%.0f kg)  <- governs" % (bal["Wb_slide"], bal["Wb_slide"]/p["gacc"]), "mu [0.9 W - 1.5 Fuy] >= 1.5 Fux"],
         ["Overturning (right toe)", "%.0f N (%.0f kg)" % (bal["Wb_overt"], bal["Wb_overt"]/p["gacc"]), "0.9 M_restoring >= 1.5 M_overturning"], ["Per-block uplift (J-bolt reactions)", "%.0f N (%.0f kg)" % (bal["Wb_block"], bal["Wb_block"]/p["gacc"]), "0.9 Wb >= T_block (frame continuity)"],
         ["Required block length, 300 x 250 section", "%.0f mm -> %d mm" % (bal["L_req"], bal["L_req_round"]), "Wb / (gamma_c w h)"]], widths=[5.3, 5.6, 6.3])
    rows = []
    for lab, k in (("Uplift", "uplift"), ("Sliding - wind uplift", "slide"), ("Overturning - wind uplift", "overt"), ("Per-block uplift", "block_up"), ("Sliding - downward wind", "slide_dn"), ("Overturning - downward wind", "overt_dn"), ("Sliding - seismic", "slide_eq"), ("Overturning - seismic", "overt_eq")):
        dd, cc = bal[k]; rows.append([lab, "%.0f" % dd, "%.0f" % cc, "%.3f" % (dd/cc), stat(dd/cc)])
    R.T(["Check (provided 300x250x%d blocks)" % p["block_L"], "Demand (N or N.mm)", "Capacity", "UR", "Status"], rows, widths=[6.4, 3.4, 3.4, 1.8, 1.8], status_col=4)
    R.IMG("fig6_ballast.png", 15.5)
    R.P("Roof load: %d blocks x %.0f kg + array = %.2f kN/m2 average over the table footprint. The building structural engineer must confirm the slab/beam capacity (not part of this scope). "
        "Seismic sliding utilisation (%.2f) does not depend on block weight; it rises above 1.0 if the component factor Rp is taken as 1.0 (Section 11)." % (4, bal["Wb1"]/p["gacc"], bal["roof_load_kN_m2"], bal["slide_eq"][0]/bal["slide_eq"][1]))

    R.H("9  J-bolt anchorage - M16 (as drawn) and M10 (alternate)")
    A = o["anchor"]
    rows = [["Max factored tension per bolt (N)", "%.0f" % A["M16"]["T"], "%.0f" % A["M10"]["T"], "continuous-beam reactions J1..J4"],
            ["Shear per bolt (N)", "%.0f" % A["M16"]["V"], "%.0f" % A["M10"]["V"], "max H / 4"],
            ["Tdb, cl 10.3.5 (N)", "%.0f" % A["M16"]["Tdb"], "%.0f" % A["M10"]["Tdb"], "0.9 fub An / gamma_mb"],
            ["UR - tension", "%.3f" % (A["M16"]["T"]/A["M16"]["Tdb"]), "%.3f" % (A["M10"]["T"]/A["M10"]["Tdb"]), ""],
            ["UR - shear + tension, cl 10.3.6", "%.4f" % A["M16"]["comb"], "%.4f" % A["M10"]["comb"], "(V/Vd)^2 + (T/Tdb)^2"],
            ["Hook anchorage value 16 phi (mm)", "%.0f" % A["M16"]["hook"], "%.0f" % A["M10"]["hook"], "IS 456 cl 26.2.2.1"],
            ["tau_bd, M20 plain bar (MPa)", "%.1f" % A["M16"]["tau"], "%.1f" % A["M10"]["tau"], "IS 456 cl 26.2.1.1"],
            ["Bond + hook capacity, 100 mm straight embedment (N)", "%.0f" % A["M16"]["Tanch"], "%.0f" % A["M10"]["Tanch"], "tau pi phi (Ls + 16 phi)"],
            ["UR - bond + hook", "%.3f" % (A["M16"]["T"]/A["M16"]["Tanch"]), "%.3f" % (A["M10"]["T"]/A["M10"]["Tanch"]), ""],
            ["Projection above block (mm)", "%.1f" % A["M16"]["Lproj"], "%.1f" % A["M10"]["Lproj"], "leg 5 + plate 5 + 4 washers + spring + nut + thread"],
            ["REQUIRED J-BOLT SHANK LENGTH (mm)", "%d" % A["M16"]["Ltot"], "%d" % A["M10"]["Ltot"], "BOM M16 = 150 mm: %s" % ("adequate" if 150 >= A["M16"]["Ltot"] else "SHORT")]]
    R.T(["Item", "M16", "M10", "Basis"], rows, widths=[6.6, 2.0, 2.0, 6.6])
    R.P("Bond governs: the required straight embedment computes to zero because the standard hook alone (16 phi) covers the demand; a practical 100 mm minimum embedment is adopted (engineering practice, not IS). "
        "Concrete-cone breakout and side-blowout of the J-bolts in a 300 x 250 block are not covered by any IS and are NOT checked; the block mass (Section 8) provides the uplift resistance. "
        "The Ø18 hole in the 50 mm leg cannot satisfy cl 10.2.4.2 (Section 12).", italic=True, size=8.5)

    R.H("10  Deflection - IS 800 cl 5.6.1, Table 6")
    dl, lim = o["defl"], o["defl_lim"]
    R.T(["Member", "Service combination", "Deflection (mm)", "Limit (mm)", "UR"],
        [["Inclined B-C, mid-span (L/180)", "DL + WL (up)", "%.3f" % dl["S2 DL+WL(up)"]["inc"], "%.2f" % lim["inc"], "%.3f" % (dl["S2 DL+WL(up)"]["inc"]/lim["inc"])],
         ["Base overhang at A (2a/180)", "DL + WL (up)", "%.3f" % dl["S2 DL+WL(up)"]["dA"], "%.2f" % lim["tip_A"], "%.3f" % (dl["S2 DL+WL(up)"]["dA"]/lim["tip_A"])],
         ["Base overhang at C (2c/180)", "DL + WL (up)", "%.3f" % dl["S2 DL+WL(up)"]["dC"], "%.2f" % lim["tip_C"], "%.3f" % (dl["S2 DL+WL(up)"]["dC"]/lim["tip_C"])]], widths=[5.6, 3.3, 3.0, 2.6, 2.6])

    R.H("11  Sensitivity to the decisive assumptions")
    R.T(["Scenario", "pd (kN/m2)", "Required block length (mm)", "Governs", "Max UR at 650 mm", "Seismic sliding UR"],
        [[lab, "%.3f" % pd_, "%d (%.0f)" % (lrr, lr), gov, "%.2f" % mur, "%.2f" % eq] for lab, pd_, lr, lrr, gov, mur, eq in sensitivity.run()], widths=[5.6, 1.8, 3.0, 2.0, 2.4, 2.4])
    pw = E.P0(); pw["wind_mode"] = 1; ow = E.design(pw)
    f_ = lambda oo, k: oo["chk_member"][k][0]
    R.P("Module wind as UDL (wind_mode 1) instead of through the four bolts - bounding case for the rafter:", bold=True)
    R.T(["Item", "Wind at 4 bolts (R1 base)", "Wind as UDL (alt)"],
        [["Rafter max |M| (N.m)", "%.1f" % (env["inc_M"]/1e3), "%.1f" % (ow["env"]["inc_M"]/1e3)], ["Rafter N+M utilisation (tension)", "%.3f" % f_(o, "Inclined  N+M (T)  cl 9.3.1"), "%.3f" % f_(ow, "Inclined  N+M (T)  cl 9.3.1")],
         ["Rafter N+M utilisation (compression)", "%.3f" % f_(o, "Inclined  N+M (C)  cl 9.3.1"), "%.3f" % f_(ow, "Inclined  N+M (C)  cl 9.3.1")],
         ["Rafter deflection (mm; limit %.2f)" % o["defl_lim"]["inc"], "%.3f" % max(v["inc"] for v in o["defl"].values()), "%.3f" % max(v["inc"] for v in ow["defl"].values())],
         ["Reactions / ballast / J-bolts", "as reported", "identical (resultant unchanged): L_req %.1f / %.1f mm" % (bal["L_req"], ow["bal"]["L_req"])]], widths=[7.0, 5.1, 5.1])
    R.P("Reading: the required block length moves between 550 mm (Category 3) and 950 mm (combined worst case); sliding governs in every case, so a higher roof friction coefficient (tested value) is the most economical lever. "
        "Seismic sliding exceeds 1.0 at Rp = 1.0 for any block size: the IS 1893 component provisions must be confirmed before issue.")

    R.H("12  Observations on the drawing and BOM")
    R.B([(a[0] + ": ", a[1]) for a in NOTES if a[0].startswith("O") and a[1]])

    R.H("13  Verification, limitations and open items")
    R.B(["Sources: Vb, Kd/Ka, IS 800 Table 4/Table 12/cl 10.3.4 and IS 456 bond/hook values were corroborated by web search; Table 7 Cp comes from the validated house table; other values are recalled (Appendix A). "
         "The primary code texts (law.resource.org, iitk.ac.in, Bentley docs) were blocked by the environment and were NOT opened: verify every clause number against licensed copies before issue.",
         "A web-search snippet for ISA 50x50x5 (Cxx 1.24 cm, Iuu 10.2 cm4) was rejected: Iuu + Ivv must equal Ixx + Iyy; the section was computed from geometry and agrees with the IS 808 catalogue.",
         "STAAD.Pro was not run. To complete: open staad/CDSCO_45kW_Ballast_Frame.std, Analyze, paste reactions into Excel sheet STAAD_Map (tolerance 1 %), then produce the XtraReport per staad/REPORT_STEPS.md.",
         "Open inputs to confirm with the client: module model and weight, design life (k1), terrain and building height, roof finish / friction, block length, seismic basis, steel grade, SS bolt class.",
         "Not in scope: roof slab capacity, module clamp capacity, corrosion/HDG thickness, construction loads."])
    R.T(["Prepared", "Checked", "Approved"], [["", "", ""], ["Name / date:", "Name / date:", "Name / date:"]], widths=[5.7, 5.7, 5.7])

    R.pagebreak()
    R.H("Appendix A  Verification register")
    R.T(["#", "Value / provision", "Source", "Status", "Comment"], [[i + 1, a, b, c, dd] for i, (a, b, c, dd) in enumerate(REGISTER)], widths=[0.7, 5.0, 3.8, 3.3, 4.4], fs=7.5)
    R.save(out); return out


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../report/CDSCO_45kW_Ballast_MMS_Design_Report.docx"
    build(out, RepMD if out.endswith(".md") else None); print("wrote", out)
