"""Generates the STAAD.Pro input file (.std) from the same engine used for the Excel workbook."""
import os, sys
import engine as E
from inputs import SEC

NODES = ["A", "J1", "J2", "J3", "J4", "C", "B", "S1", "M", "S2"]
MEMBERS = [("A", "J1"), ("J1", "J2"), ("J2", "J3"), ("J3", "J4"), ("J4", "C"), ("A", "B"), ("B", "S1"), ("S1", "M"), ("M", "S2"), ("S2", "C")]
BASE, VERT, INCL = [1, 2, 3, 4, 5], [6], [7, 8, 9, 10]
COMBO_NO = {"C1": 11, "C2": 12, "C3": 13, "C4": 14, "C5": 15, "C6": 16, "S1": 17, "S2": 18}
LC_NO = {"DL": 1, "WLU": 2, "WLD": 3, "EQX": 4}


def coords(g):
    yA, yB = g["yA"], g["yB"]
    return {"A": (0, yA), "J1": (g["J1"], yA), "J2": (g["J2"], yA), "J3": (g["J3"], yA), "J4": (g["J4"], yA), "C": (g["AC"], yA),
            "B": (0, yB), "S1": g["S1"], "S2": g["S2"], "M": ((g["S1"][0] + g["S2"][0])/2, (g["S1"][1] + g["S2"][1])/2)}


def generate(p=None):
    o = E.design(p); p, g, L = o["p"], o["g"], o["L"]; c = coords(g); idx = {n: i + 1 for i, n in enumerate(NODES)}
    t = []; w = t.append
    w("STAAD SPACE")
    w("START JOB INFORMATION")
    w("ENGINEER DATE 30-SEP-26")
    w("JOB CLIENT M/S SAI BABUJI PROJECTS PVT LTD")
    w("JOB NAME ENG TBD  (JSP SOLAR ENERGY)")
    w("JOB NO MMS 45KWP BALLAST 10.1 DEG CDSCO HYD")
    w("JOB REV R0")
    w("JOB PART FRAME ISA50X50X5 IS800 LSD AL-001 R0")
    w("END JOB INFORMATION")
    w("INPUT WIDTH 79")
    w("* Plane frame, global X-Y. X along base (A = high end), Y up from roof.")
    w("* Pinned bolt joints; base beam continuous on 4 J-bolt supports.")
    w("* ONE frame (table = 2 frames); loads per frame. See Excel STAAD_Map.")
    w("UNIT METER KN")
    w("JOINT COORDINATES")
    for n in NODES: w("%d %.9f %.9f 0.0;" % (idx[n], c[n][0]/1000, c[n][1]/1000))
    w("MEMBER INCIDENCES")
    for i, (a, b) in enumerate(MEMBERS, 1): w("%d %d %d;" % (i, idx[a], idx[b]))
    w("UNIT MMS NEWTON")
    # in-plane EI uses I_eff (angle free to deflect sideways); J = sum(l t^3)/3
    J = (SEC["b"] + SEC["b"] - SEC["t"])*SEC["t"]**3/3
    w("MEMBER PROPERTY")
    w("1 TO 5 7 TO 10 PRIS AX %.2f IX %.1f IY %.2f IZ %.2f" % (SEC["A"], J, g["Ieff"], g["Ieff"]))
    w("6 PRIS AX %.2f" % SEC["A"])
    w("CONSTANTS")
    w("E %.1f ALL" % p["Es"])
    w("POISSON 0.3 ALL")
    w("DENSITY 7.85E-05 ALL")
    w("MEMBER TRUSS")
    w("6")
    w("MEMBER RELEASE")
    w("10 END MZ")
    w("SUPPORTS")
    w("%d FIXED BUT MZ" % idx["J1"])
    w("%d %d %d FIXED BUT FX MZ" % (idx["J2"], idx["J3"], idx["J4"]))
    lcs = L["lc"]
    titles = {"DL": "DL", "WLU": "WL UP (IS875 T7 CP MIN)", "WLD": "WL DOWN (IS875 T7 CP MAX)", "EQX": "EQ +X AH=%.3f" % L["Ah"]}
    for lc in ("DL", "WLU", "WLD", "EQX"):
        d = lcs[lc]; w("LOAD %d LOADTYPE None  TITLE %s" % (LC_NO[lc], titles[lc]))
        if d["wb"]:
            w("MEMBER LOAD"); w("1 TO 5 UNI GY %.9f" % -d["wb"])
        jl = []
        fx, fy = d["slots"][0]
        if abs(fx) > 1e-12 or abs(fy) > 1e-12:
            jl.append("%d %d FX %.6f FY %.6f" % (idx["S1"], idx["S2"], fx, fy))
        if d["FxA"] or d["dAy"]: jl.append("%d FX %.6f FY %.6f" % (idx["A"], d["FxA"], -d["dAy"]))
        if d["FxC"] or d["dCy"]: jl.append("%d FX %.6f FY %.6f" % (idx["C"], d["FxC"], -d["dCy"]))
        if jl: w("JOINT LOAD"); [w(x) for x in jl]
    for name, fac, kind in E.COMBOS:
        no = COMBO_NO[name.split()[0]]
        w("LOAD COMB %d %s" % (no, name.replace("(+x)", "").replace("(", " ").replace(")", "")))
        w(" ".join("%d %.2f" % (LC_NO[k], f) for k, f in fac.items()))
    w("PERFORM ANALYSIS PRINT ALL")
    w("LOAD LIST 11 TO 18")
    w("PRINT MEMBER FORCES ALL")
    w("PRINT SUPPORT REACTION ALL")
    w("PRINT JOINT DISPLACEMENTS ALL")
    w("FINISH")
    return "\n".join(t) + "\n", o


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "../staad/CDSCO_45kW_Ballast_Frame.std"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    txt, o = generate(); open(out, "w", newline="\r\n").write(txt)
    print("wrote", out, "| lines", txt.count("\n"), "| max line len", max(len(l) for l in txt.splitlines()))
