"""Cross-check of the R1 closed-form statics (UDL zones) against the independent matrix solver, both wind modes,
plus dense scan of the true peak moment of the rafter for every strength combination."""
import numpy as np
import engine as E


def rafter_scan(m, f, udl, names, npts=60):
    """sagging-positive local moment along the rafter elements -> array of (s_along_member, M_sag)"""
    out = []; s0 = 0.0
    for nm in names:
        el = m["elems"][nm]; Lq = el["L"]; qy = udl.get(nm, (0.0, 0.0))[1]
        for x in np.linspace(0, Lq, npts):
            out.append((s0 + x, el["M1"] + el["fl"][1]*x + qy*x*x/2))
        s0 += Lq
    return out


def main(verbose=True):
    worst = 0.0; bad = []
    for mode in (0, 1):
        p = E.P0(); p["wind_mode"] = mode; g = E.geometry(p); w = E.wind(p, g); L = E.loads(p, g, w)
        res = {}
        for name, lc in L["lc"].items():
            cf = E.closed_form(p, g, lc); res[name] = cf; f, nodal, udl = E.build_model(p, g, lc); m = f.solve(nodal, udl)
            names = ["B-Pa", "Pa-S1", "S1-M", "M-S2", "S2-Pb", "Pb-C"]
            chk = {"NAB": (cf["NAB"], m["elems"]["AB"]["N"]), "RH1": (cf["RH1"], m["R"]["J1"][0]),
                   "dA": (cf["dA"], -m["u"]["A"][1]), "dC": (cf["dC"], -m["u"]["C"][1]),
                   "M2": (cf["M2"], m["elems"]["J1-J2"]["M2"]), "M3": (cf["M3"], m["elems"]["J2-J3"]["M2"]), "M1": (cf["M1"], m["elems"]["A-J1"]["M2"]),
                   "N_L": (cf["N_L"], m["elems"]["Pb-C"]["N"]),
                   "Minc1(S1)": (cf["Minc1"], -m["elems"]["Pa-S1"]["M2"]), "Minc2(S2)": (cf["Minc2"], -m["elems"]["S2-Pb"]["M1"]),
                   "MincM(M)": (cf["MincM"], -m["elems"]["S1-M"]["M2"]), "MincL(C)": (cf["MincL"], 0.0)}
            for k in ("R1", "R2", "R3", "R4"): chk[k] = (cf[k], m["R"]["J" + k[1]][1])
            for k, (a, b) in chk.items():
                err = abs(a - b)/max(1.0, abs(a)); worst = max(worst, err)
                if err > 1e-9: bad.append((mode, name, k, a, b))
            # axial / shear at section points via the solver (before/after point loads: use elements ends)
            sec = {"N_a": ("B-Pa", "N"), "N_b": ("Pb-C", "N")}
            chk2 = {"N_a": (cf["N_a"], m["elems"]["B-Pa"]["N"]), "V_0": (cf["V_0"], -m["elems"]["B-Pa"]["fl"][1]), "V_L": (cf["V_L"], m["elems"]["Pb-C"]["fl"][4])}
            for k, (a, b) in chk2.items():
                err = abs(abs(a) - abs(b))/max(1.0, abs(a)); worst = max(worst, err)
                if err > 1e-9: bad.append((mode, name, k, a, b))
        if verbose: print("wind_mode %d: closed form vs matrix solver, 4 LC x 20 quantities -> worst rel. diff %.2e %s" % (mode, worst, "OK" if not [b for b in bad if b[0] == mode] else "MISMATCH " + str([b for b in bad if b[0] == mode][:4])))
        # ---- combined peak moment: closed form vs dense scan of the solver ------------------------------------------------
        o = E.design(dict(p)); pk_worst = 0.0
        for n, fac, kind in E.COMBOS:
            lcc = {}
            f = None
            # build combined load case by linear superposition of the primary load-case definitions
            comb = dict(slots=[(0.0, 0.0), (0.0, 0.0)], qm=(0.0, 0.0), qr=(0.0, 0.0), FxA=0.0, FxC=0.0, dAy=0.0, dCy=0.0, wb=0.0, bolt=(0, 0))
            for k, fa in fac.items():
                d = L["lc"][k]
                comb["slots"] = [(comb["slots"][i][0] + fa*d["slots"][i][0], comb["slots"][i][1] + fa*d["slots"][i][1]) for i in (0, 1)]
                comb["qm"] = (comb["qm"][0] + fa*d["qm"][0], comb["qm"][1] + fa*d["qm"][1]); comb["qr"] = (comb["qr"][0] + fa*d["qr"][0], comb["qr"][1] + fa*d["qr"][1])
                for kk in ("FxA", "FxC", "dAy", "dCy", "wb"): comb[kk] += fa*d[kk]
            f, nodal, udl = E.build_model(p, g, comb); m = f.solve(nodal, udl)
            scan = rafter_scan(m, f, udl, ["B-Pa", "Pa-S1", "S1-M", "M-S2", "S2-Pb", "Pb-C"])
            true_peak = max(abs(v) for _, v in scan)
            c_ = o["cmb"][n]; cf_peak = max(abs(c_["Minc1"]), abs(c_["Minc2"]), abs(c_["Mstar"]))
            e = abs(true_peak - cf_peak)/max(1.0, true_peak); pk_worst = max(pk_worst, e)
            if e > 2e-4: bad.append((mode, n, "peak M", cf_peak, true_peak))
        if verbose: print("wind_mode %d: rafter peak |M| (closed form s*, S1, S2) vs dense solver scan, 8 combos -> worst rel. diff %.2e" % (mode, pk_worst))
    print("RESULT:", "OK - closed form == matrix solver" if not bad else "MISMATCHES: %s" % bad[:6])
    return not bad


if __name__ == "__main__":
    main()
