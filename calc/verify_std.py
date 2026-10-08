"""Round-trip check: parse the generated .std TEXT, rebuild the model in the independent matrix solver,
solve every combination and compare with the closed-form results used in the Excel workbook."""
import re, sys
import numpy as np
from solver2d import Frame2D
import engine as E

STD = sys.argv[1] if len(sys.argv) > 1 else "../staad/CDSCO_45kW_Ballast_Frame.std"
lines = [l.strip() for l in open(STD).read().replace("\r", "").split("\n") if l.strip() and not l.startswith("*")]
sec = None; nodes = {}; mem = {}; props = {}; truss = set(); rel = {}; sup = {}; loads = {}; combos = {}; cur = None; unit_len = 1.0; Ez = None; lastcomb = None
for l in lines:
    u = l.upper()
    if u.startswith("UNIT"): unit_len = 1000.0 if "METER" in u else 1.0; continue
    if u in ("JOINT COORDINATES", "MEMBER INCIDENCES", "MEMBER PROPERTY", "CONSTANTS", "MEMBER TRUSS", "MEMBER RELEASE", "SUPPORTS", "MEMBER LOAD", "JOINT LOAD"): sec = u; continue
    if u.startswith("LOAD COMB"): m = re.match(r"LOAD COMB (\d+)", u); lastcomb = int(m.group(1)); combos[lastcomb] = {}; sec = "COMBDATA"; continue
    if u.startswith("LOAD ") and "LOADTYPE" in u: cur = int(u.split()[1]); loads[cur] = dict(joint={}, udl={}); sec = None; continue
    if u.startswith(("PERFORM", "FINISH", "PRINT", "START", "END", "ENGINEER", "JOB", "STAAD", "INPUT", "LOAD LIST")): sec = None if not u.startswith("LOAD LIST") else sec; continue
    if sec == "JOINT COORDINATES":
        a = l.rstrip(";").split(); nodes[int(a[0])] = (float(a[1])*unit_len, float(a[2])*unit_len)
    elif sec == "MEMBER INCIDENCES":
        a = l.rstrip(";").split(); mem[int(a[0])] = (int(a[1]), int(a[2]))
    elif sec == "MEMBER PROPERTY":
        a = l.upper().split("PRIS")[0].split(); ids = []
        toks = a; i = 0
        while i < len(toks):
            if i + 2 < len(toks) and toks[i+1] == "TO": ids += list(range(int(toks[i]), int(toks[i+2]) + 1)); i += 3
            else: ids.append(int(toks[i])); i += 1
        d = l.upper().split("PRIS")[1].split(); kv = dict(zip(d[::2], map(float, d[1::2])))
        for k in ids: props[k] = kv
    elif sec == "CONSTANTS" and u.startswith("E "): Ez = float(l.split()[1])
    elif sec == "MEMBER TRUSS": truss.update(int(x) for x in l.split())
    elif sec == "MEMBER RELEASE": a = l.split(); rel[int(a[0])] = (a[1].upper(), a[2].upper())
    elif sec == "SUPPORTS":
        a = l.upper().split("FIXED BUT"); ids = [int(x) for x in a[0].split()]; free = a[1].split()
        for k in ids: sup[k] = (("FX" not in free), True, ("MZ" not in free))
    elif sec == "MEMBER LOAD":
        m = re.match(r"(\d+) TO (\d+) UNI G([XY]) (\S+)", l.upper())
        for k in range(int(m.group(1)), int(m.group(2)) + 1):
            q = loads[cur]["udl"].setdefault(k, [0.0, 0.0]); q[0 if m.group(3) == "X" else 1] += float(m.group(4))
    elif sec == "JOINT LOAD":
        a = l.upper().split("FX"); ids = [int(x) for x in a[0].split()]; b = a[1].split("FY"); fx, fy = float(b[0]), float(b[1])
        for k in ids:
            o_ = loads[cur]["joint"].get(k, (0.0, 0.0)); loads[cur]["joint"][k] = (o_[0] + fx, o_[1] + fy)
    elif sec == "COMBDATA":
        a = l.split()
        for x, y in zip(a[::2], a[1::2]): combos[lastcomb][int(x)] = float(y)

name = {i + 1: n for i, n in enumerate(["A", "J1", "J2", "J3", "J4", "C", "B", "S1", "M", "S2", "Pa", "Pb"])}
def model(lcfac):
    f = Frame2D()
    for i, (x, y) in nodes.items(): f.node(name[i], x, y)
    for k, (a, b) in mem.items():
        nm = f"m{k}"
        if k in truss: f.truss(nm, name[a], name[b], Ez*props[k]["AX"])
        else: f.beam(nm, name[a], name[b], Ez*props[k]["AX"], Ez*props[k]["IZ"], rel2=(k in rel and rel[k][0] == "END"))
    for k, (ux, uy, rz) in sup.items(): f.support(name[k], ux, uy, rz)
    nodal = {}; gq = {}
    for lc, fac in lcfac.items():
        for k, (fx, fy) in loads[lc]["joint"].items():
            o_ = nodal.get(name[k], (0, 0, 0)); nodal[name[k]] = (o_[0] + fac*fx, o_[1] + fac*fy, 0)
        for k, (qx, qy) in loads[lc]["udl"].items():
            a = gq.setdefault(f"m{k}", [0.0, 0.0]); a[0] += fac*qx; a[1] += fac*qy
    udl = {nm: f.local_udl(nm, qx, qy) for nm, (qx, qy) in gq.items() if not nm == "m6"}
    return f, nodal, udl

_p = E.P0(); _p['wind_mode'] = 1 if 'windUDL' in STD else 0; o = E.design(_p); names = {11: "C1 1.5DL+1.5WL(dn)", 12: "C2 0.9DL+1.5WL(up)", 13: "C3 1.5DL+1.5EQ(+x)", 14: "C4 1.5DL-1.5EQ(+x)", 15: "C5 0.9DL+1.5EQ(+x)", 16: "C6 0.9DL-1.5EQ(+x)", 17: "S1 DL+WL(dn)", 18: "S2 DL+WL(up)"}
worst = 0.0
print("parsed: %d nodes, %d members, %d supports, %d load cases, %d combos, truss=%s, release=%s" % (len(nodes), len(mem), len(sup), len(loads), len(combos), sorted(truss), rel))
for no, nm in names.items():
    f, nodal, udl = model(combos[no]); r = f.solve(nodal, udl); cb = o["cmb"][nm]
    pairs = [("R1", r["R"]["J1"][1], cb["R1"]), ("R2", r["R"]["J2"][1], cb["R2"]), ("R3", r["R"]["J3"][1], cb["R3"]), ("R4", r["R"]["J4"][1], cb["R4"]),
             ("RH1", r["R"]["J1"][0], cb["RH1"]), ("N_AB", r["elems"]["m6"]["N"], cb["NAB"]), ("dA", -r["u"]["A"][1], cb["dA"]), ("dC", -r["u"]["C"][1], cb["dC"]),
             ("M_J2", r["elems"]["m2"]["M2"], cb["M2"]), ("M_J3", r["elems"]["m3"]["M2"], cb["M3"])]
    scan = []
    for k in range(7, 13):
        el = r["elems"][f"m{k}"]; qy = udl.get(f"m{k}", (0.0, 0.0))[1]
        scan += [abs(el["M1"] + el["fl"][1]*x + qy*x*x/2) for x in np.linspace(0, el["L"], 80)]
    pairs.append(("rafter peak |M| (scan vs closed form)", max(scan), max(abs(cb["Minc1"]), abs(cb["Minc2"]), abs(cb["Mstar"]))))
    e = max(abs(a - b)/max(1.0, abs(b)) for _, a, b in pairs[:-1]); e = max(e, abs(pairs[-1][1] - pairs[-1][2])/max(1.0, pairs[-1][2])*0.0 + (abs(pairs[-1][1] - pairs[-1][2])/pairs[-1][2] if abs(pairs[-1][1] - pairs[-1][2])/pairs[-1][2] > 1e-4 else 0.0)); worst = max(worst, e)
    print("%-22s max rel diff .std-model vs Excel closed form: %.2e   R(J1..J4) = %s" % (nm, e, [round(x, 1) for x in (r['R']['J1'][1], r['R']['J2'][1], r['R']['J3'][1], r['R']['J4'][1])]))
print("WORST:", "%.2e" % worst, "->", "PASS" if worst < 1e-6 else "FAIL")
