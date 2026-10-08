"""Independent Python implementation of the whole calculation chain (geometry -> IS 875 wind -> loads ->
closed-form frame statics -> IS 800 checks -> ballast / anchorage).  The Excel workbook replicates exactly this
chain with live formulas; build_excel.py output is recalculated in LibreOffice and compared against this file.
Units: N, mm, MPa unless stated."""
import math
from inputs import INPUTS, T7, K2, TAUBD, BOLTS, SEC

sin, cos, sqrt, hypot = math.sin, math.cos, math.sqrt, math.hypot


def P0():
    return {k: v[0] for k, v in INPUTS.items()}


def interp(x, pts):
    if x <= pts[0][0]: return pts[0][1:]
    for a, b in zip(pts, pts[1:]):
        if a[0] <= x <= b[0]:
            f = (x - a[0])/(b[0] - a[0])
            return tuple(a[i] + f*(b[i] - a[i]) for i in range(1, len(a)))
    return pts[-1][1:]


def geometry(p):
    g = {}
    g["AC"] = p["base_len"] - p["base_end_A"] - p["base_end_C"]
    g["AB"] = p["vert_len"] - 2*p["vert_end"]
    g["BCdwg"] = p["incl_len"] - p["incl_end_B"] - p["incl_end_C"]       # as drawn (2 decimals)
    g["BC"] = hypot(g["AC"], g["AB"])                                    # working length: triangle closes exactly
    g["tilt"] = math.atan2(g["AB"], g["AC"]); g["tilt_deg"] = math.degrees(g["tilt"])
    g["closure"] = g["BC"] - g["BCdwg"]
    g["cos"], g["sin"] = cos(g["tilt"]), sin(g["tilt"])
    g["J1"] = p["J_off"] - p["base_end_A"]; g["J2"] = g["J1"] + p["J_pair"]
    g["J3"] = g["J2"] + p["J_mid"]; g["J4"] = g["J3"] + p["J_pair"]
    g["a1"] = g["J1"]; g["c2"] = g["AC"] - g["J4"]
    g["yA"] = p["block_h"] + p["bolt_h"]; g["yB"] = g["yA"] + g["AB"]
    g["s1"] = p["slot_end"] - p["incl_end_B"]; g["s2c"] = p["slot_end"] - p["incl_end_C"]
    g["s2"] = g["BC"] - g["s2c"]; g["slot_cc"] = g["s2"] - g["s1"]
    d = (g["cos"], -g["sin"])
    g["S1"] = (0 + g["s1"]*d[0], g["yB"] + g["s1"]*d[1]); g["S2"] = (0 + g["s2"]*d[0], g["yB"] + g["s2"]*d[1])
    g["Ieff"] = (SEC["Ixx"]*SEC["Iyy"] - SEC["Ixy"]**2)/SEC["Iyy"]      # in-plane, free sideways
    # module contact zone on the rafter (module sits directly on the rafter, no purlin)
    g["sc"] = (g["s1"] + g["s2"])/2; g["Lm"] = p["mod_W"]
    g["sa"], g["sb"] = g["sc"] - g["Lm"]/2, g["sc"] + g["Lm"]/2
    g["sM"] = g["sc"]                                                     # node M (mid of slots)
    g["Pa"] = (g["sa"]*g["cos"], g["yB"] - g["sa"]*g["sin"]); g["Pb"] = (g["sb"]*g["cos"], g["yB"] - g["sb"]*g["sin"])
    g["M"] = (g["sM"]*g["cos"], g["yB"] - g["sM"]*g["sin"])
    g["mod_ovh"] = (p["mod_L"] - p["frame_sp"])/2                         # module overhang beyond each rafter
    g["zone_ok"] = (g["sa"] >= -p["incl_end_B"]) and (g["sb"] <= g["BC"] + p["incl_end_C"])
    return g


def wind(p, g):
    w = {}
    w["z"] = p["z_bldg"] + (g["yB"] + p["e_mod"] + p["mod_t"]/2)/1000.0
    cat = int(p["terrain"]); hs = [h for h, _ in K2]; ks = [d[cat] for _, d in K2]
    z = w["z"]
    if z <= hs[0]: k2 = ks[0]
    elif z >= hs[-1]: k2 = ks[-1]
    else:
        i = max(j for j in range(len(hs) - 1) if hs[j] <= z)
        k2 = ks[i] + (ks[i+1] - ks[i])*(z - hs[i])/(hs[i+1] - hs[i])
    w["k2"] = k2
    w["Vz"] = p["Vb"]*p["k1_risk"]*k2*p["k3_topo"]*p["k4_imp"]
    w["pz"] = 0.6*w["Vz"]**2/1000.0                                  # kN/m2
    pd = p["Kd_dir"]*p["Ka_area"]*p["Kc_comb"]*w["pz"]*(0.8 if z < 10 else 1.0)
    w["pd"] = max(pd, 0.7*w["pz"])
    w["cp_dn"], w["cp_up"] = interp(g["tilt_deg"], T7)
    w["A_mod"] = p["mod_L"]*p["mod_W"]/1e6                            # m2
    w["N_up"] = abs(w["cp_up"])*w["pd"]*w["A_mod"]*1000               # N normal force per module
    w["N_dn"] = w["cp_dn"]*w["pd"]*w["A_mod"]*1000
    return w


def loads(p, g, w):
    """Per-frame load cases. The module is carried DIRECTLY by the two rafters (no purlins): module dead load (and, in
    wind_mode 1, module wind) is a UDL over the module contact length of each rafter, not point loads at joints."""
    L = {}
    A = SEC["A"]; ws = A*1e-6*p["gam_s"]                               # N/mm
    L["ws"] = ws; L["Wm"] = p["mod_kg"]*p["gacc"]
    L["Wbase"], L["Wv"], L["Winc"] = ws*p["base_len"], ws*p["vert_len"], ws*p["incl_len"]
    L["stubA"], L["stubC"] = ws*p["base_end_A"], ws*p["base_end_C"]
    L["Ah"] = (p["Zf"]/2)*p["I_imp"]*p["SaG"]*(1 + p["zh"])/p["Rp"]
    # --- tributary UDL on one rafter (N per mm of rafter length, vertical) ---------------------------------------------
    L["pm"] = L["Wm"]/(p["mod_L"]*p["mod_W"])                          # module weight per unit area, N/mm2
    L["trib"] = p["mod_L"]/2.0                                         # 2 rafters, symmetric overhangs -> each takes half
    L["wm"] = L["pm"]*L["trib"]                                        # = Wm/(2 mod_W)
    L["wr"] = L["Winc"]/g["BC"]                                        # rafter self-weight spread over bolt c/c
    s, c = g["sin"], g["cos"]; mode = int(p["wind_mode"]); Z = (0.0, 0.0)
    Fn_u, Fn_d = w["N_up"]/4, w["N_dn"]/4                              # per module bolt
    q_u, q_d = (w["N_up"]/2)/p["mod_W"], (w["N_dn"]/2)/p["mod_W"]     # per mm of rafter if wind taken as UDL
    wl = lambda Fn, q, sg: (dict(slots=[(sg*Fn*s, sg*Fn*c)]*2, qm=Z) if mode == 0 else dict(slots=[Z, Z], qm=(sg*q*s, sg*q*c)))
    base = dict(qr=Z, FxA=0.0, FxC=0.0, dAy=0.0, dCy=0.0, wb=0.0)
    L["lc"] = {
        "DL":  dict(base, slots=[Z, Z], qm=(0.0, -L["wm"]), qr=(0.0, -L["wr"]), dAy=L["Wv"] + L["stubA"], dCy=L["stubC"], wb=ws,
                    bolt=(-(L["Wm"]/4)*c, (L["Wm"]/4)*s)),
        "WLU": dict(base, **wl(Fn_u, q_u, +1), bolt=(Fn_u, 0.0)),
        "WLD": dict(base, **wl(Fn_d, q_d, -1), bolt=(-Fn_d, 0.0)),
        "EQX": dict(base, slots=[Z, Z], qm=(L["Ah"]*L["wm"], 0.0), qr=(L["Ah"]*L["wr"], 0.0),
                    FxA=L["Ah"]*(L["Wv"] + L["stubA"] + 0.5*ws*g["AC"]), FxC=L["Ah"]*(L["stubC"] + 0.5*ws*g["AC"]),
                    bolt=(L["Ah"]*(L["Wm"]/4)*s, L["Ah"]*(L["Wm"]/4)*c)),
    }
    return L


def resultant(g, lc):
    """total force (Fx, Fy) applied to the rafter by a load case"""
    Fx = sum(f[0] for f in lc["slots"]) + lc["qm"][0]*g["Lm"] + lc["qr"][0]*g["BC"]
    Fy = sum(f[1] for f in lc["slots"]) + lc["qm"][1]*g["Lm"] + lc["qr"][1]*g["BC"]
    return Fx, Fy


def clen(sx, a, b): return max(0.0, min(sx, b) - a)


def closed_form(p, g, lc):
    """Closed-form statics of one frame for one load case. Returns dict (N, mm; tension +; R up +)."""
    xB, yB, xC, yC = 0.0, g["yB"], g["AC"], g["yA"]
    s, c, LB = g["sin"], g["cos"], g["BC"]; sa, sb, Lm, s1, s2 = g["sa"], g["sb"], g["Lm"], g["s1"], g["s2"]
    r = {}
    (qmx, qmy), (qrx, qry) = lc["qm"], lc["qr"]
    F1, F2 = lc["slots"]
    pt = lambda sp: (sp*c, yB - sp*s)                                  # point on the rafter axis
    items = [(g["S1"], F1), (g["S2"], F2), (pt(g["sc"]), (qmx*Lm, qmy*Lm)), (pt(LB/2), (qrx*LB, qry*LB))]
    msum = sum((q[0] - xC)*F[1] - (q[1] - yC)*F[0] for q, F in items)
    r["VB"] = -msum/(xB - xC)
    r["Cx"] = -sum(F[0] for _, F in items)
    r["Cy"] = -(sum(F[1] for _, F in items) + r["VB"])
    r["NAB"] = -r["VB"]
    Fd = lambda F: F[0]*c - F[1]*s                                     # along d = (c, -s)
    Fn = lambda F: F[0]*s + F[1]*c                                     # along n = (s, c)
    r["Fn1"], r["Fn2"], r["Ft1"], r["Ft2"] = Fn(F1), Fn(F2), Fd(F1), Fd(F2)
    r["qnm"], r["qtm"], r["qnr"], r["qtr"] = Fn((qmx, qmy)), Fd((qmx, qmy)), Fn((qrx, qry)), Fd((qrx, qry))
    r["qn"] = r["qnm"] + r["qnr"]
    VBc = r["VB"]*c
    secs = [("0", 0.0, 0, 0), ("a", sa, 0, 0), ("1m", s1, 0, 0), ("1p", s1, 1, 0), ("2m", s2, 1, 0), ("2p", s2, 1, 1), ("b", sb, 1, 1), ("L", LB, 1, 1)]
    for nm, sx, i1, i2 in secs:
        cm, cr = clen(sx, sa, sb), clen(sx, 0.0, LB)
        r["N_" + nm] = r["VB"]*s - (r["Ft1"]*i1 + r["Ft2"]*i2) - r["qtm"]*cm - r["qtr"]*cr
        r["V_" + nm] = -(VBc + r["Fn1"]*i1 + r["Fn2"]*i2 + r["qnm"]*cm + r["qnr"]*cr)
    def Mat(sx):
        gm = clen(sx, sa, sb)*(sx - (sa + min(sx, sb))/2.0) if sx > sa else 0.0
        gr = clen(sx, 0.0, LB)*(sx - min(sx, LB)/2.0)
        return -(VBc*sx + r["Fn1"]*max(0.0, sx - s1) + r["Fn2"]*max(0.0, sx - s2) + r["qnm"]*gm + r["qnr"]*gr)
    r["Minc1"], r["Minc2"], r["MincM"], r["MincL"] = Mat(s1), Mat(s2), Mat(g["sM"]), Mat(LB)
    # base beam
    PA = lc["dAy"] - r["NAB"]; PC = lc["dCy"] + r["Cy"]; w_ = lc["wb"]
    FxA_t = lc["FxA"]; FxC_t = lc["FxC"] - r["Cx"]
    r["PA"], r["PC"] = PA, PC
    r["RH1"] = -(FxA_t + FxC_t); r["Nbase_A"] = -FxA_t; r["Nbase_C"] = FxC_t
    a1, c2 = g["a1"], g["c2"]; L1, L2, L3 = p["J_pair"], p["J_mid"], p["J_pair"]
    M1 = -(PA*a1 + w_*a1**2/2); M4 = -(PC*c2 + w_*c2**2/2)
    a11, a12, a21, a22 = 2*(L1 + L2), L2, L2, 2*(L2 + L3)
    b1 = -w_*(L1**3 + L2**3)/4 - M1*L1; b2 = -w_*(L2**3 + L3**3)/4 - M4*L3
    det = a11*a22 - a12*a21
    M2 = (b1*a22 - a12*b2)/det; M3 = (a11*b2 - a21*b1)/det
    V1p = (M2 - M1)/L1 + w_*L1/2; V1m = -(PA + w_*a1); R1 = V1p - V1m
    V2m = V1p - w_*L1; V2p = (M3 - M2)/L2 + w_*L2/2; R2 = V2p - V2m
    V3m = V2p - w_*L2; V3p = (M4 - M3)/L3 + w_*L3/2; R3 = V3p - V3m
    V4m = V3p - w_*L3; V4p = PC + w_*c2; R4 = V4p - V4m
    r.update(M1=M1, M2=M2, M3=M3, M4=M4, R1=R1, R2=R2, R3=R3, R4=R4,
             Mm1=M1 + V1p*L1/2 - w_*(L1/2)**2/2, Mm2=M2 + V2p*L2/2 - w_*(L2/2)**2/2, Mm3=M3 + V3p*L3/2 - w_*(L3/2)**2/2,
             V1m=V1m, V1p=V1p, V2m=V2m, V2p=V2p, V3m=V3m, V3p=V3p, V4m=V4m, V4p=V4p,
             sumR=R1 + R2 + R3 + R4, sumP=PA + PC + w_*g["AC"])
    EI = p["Es"]*g["Ieff"]
    th1 = (M1*L1/3 + M2*L1/6 + w_*L1**3/24)/EI        # slope dy/dx (y down +), EI y'' = -M
    th4 = -(M3*L3/6 + M4*L3/3 + w_*L3**3/24)/EI
    r["dA"] = -th1*a1 + (PA*a1**3/3 + w_*a1**4/8)/EI
    r["dC"] = th4*c2 + (PC*c2**3/3 + w_*c2**4/8)/EI
    r["Fnb"], r["Ftb"] = lc["bolt"]
    return r


def build_model(p, g, lc, EI=None):
    """Same frame for the matrix solver (independent check). Rafter is split at the module contact ends Pa, Pb."""
    from solver2d import Frame2D
    EI = EI or p["Es"]*g["Ieff"]; EA = p["Es"]*SEC["A"]
    f = Frame2D(); yA = g["yA"]
    base = [("A", 0.0), ("J1", g["J1"]), ("J2", g["J2"]), ("J3", g["J3"]), ("J4", g["J4"]), ("C", g["AC"])]
    for n, x in base: f.node(n, x, yA)
    f.node("B", 0.0, g["yB"])
    inc = [("B", 0.0), ("Pa", g["sa"]), ("S1", g["s1"]), ("M", g["sM"]), ("S2", g["s2"]), ("Pb", g["sb"]), ("C", g["BC"])]
    for n, sp in inc[1:-1]: f.node(n, *{"Pa": g["Pa"], "S1": g["S1"], "M": g["M"], "S2": g["S2"], "Pb": g["Pb"]}[n])
    names = []
    for (n1, _), (n2, _) in zip(base, base[1:]):
        nm = n1 + "-" + n2; f.beam(nm, n1, n2, EA, EI); names.append(nm)
    f.truss("AB", "A", "B", EA)
    udl = {}
    for (n1, s_a), (n2, s_b) in zip(inc, inc[1:]):
        nm = n1 + "-" + n2; f.beam(nm, n1, n2, EA, EI, rel2=(n2 == "C"))
        qx, qy = lc["qr"]
        if s_a >= g["sa"] - 1e-9 and s_b <= g["sb"] + 1e-9: qx, qy = qx + lc["qm"][0], qy + lc["qm"][1]
        if qx or qy: udl[nm] = f.local_udl(nm, qx, qy)
    f.support("J1", True, True); [f.support(n, False, True) for n in ("J2", "J3", "J4")]
    nodal = {"S1": (lc["slots"][0][0], lc["slots"][0][1], 0), "S2": (lc["slots"][1][0], lc["slots"][1][1], 0),
             "A": (lc["FxA"], -lc["dAy"], 0), "C": (lc["FxC"], -lc["dCy"], 0)}
    for n in names: udl[n] = -lc["wb"]
    return f, nodal, udl


if __name__ == "__main__":
    import verify_udl; verify_udl.main()


# =====================================================================================================
#  Combinations, design checks, ballast and anchorage
# =====================================================================================================
COMBOS = [  # name, {lc: factor}, kind
    ("C1 1.5DL+1.5WL(dn)", {"DL": 1.5, "WLD": 1.5}, "U"),
    ("C2 0.9DL+1.5WL(up)", {"DL": 0.9, "WLU": 1.5}, "U"),
    ("C3 1.5DL+1.5EQ(+x)", {"DL": 1.5, "EQX": 1.5}, "U"),
    ("C4 1.5DL-1.5EQ(+x)", {"DL": 1.5, "EQX": -1.5}, "U"),
    ("C5 0.9DL+1.5EQ(+x)", {"DL": 0.9, "EQX": 1.5}, "U"),
    ("C6 0.9DL-1.5EQ(+x)", {"DL": 0.9, "EQX": -1.5}, "U"),
    ("S1 DL+WL(dn)", {"DL": 1.0, "WLD": 1.0}, "S"),
    ("S2 DL+WL(up)", {"DL": 1.0, "WLU": 1.0}, "S"),
]


def combine(res, factors):
    out = {}
    for k in res["DL"]:
        if isinstance(res["DL"][k], (int, float)):
            out[k] = sum(f*res[lc][k] for lc, f in factors.items())
    return out


def section_moduli(p):
    """Effective elastic modulus for in-plane bending of the angle (free sideways), gross and net of J-bolt hole."""
    b, t, cx = SEC["b"], SEC["t"], SEC["cx"]
    pts = [(0, 0), (b, 0), (b, t), (t, t), (t, b), (0, b)]
    Ixx, Iyy, Ixy = SEC["Ixx"], SEC["Iyy"], SEC["Ixy"]
    def zmin(Ixx, Iyy, Ixy):
        D = Ixx*Iyy - Ixy**2
        return 1.0/max(abs((Iyy*(y - cx) - Ixy*(x - cx))/D) for x, y in pts)
    Zg = zmin(Ixx, Iyy, Ixy)
    Ah_ = p["d0_J"]*t; xh, yh = p["J_gauge"] - cx, t/2 - cx            # J-bolt hole in horizontal leg at gauge 27.5
    Zn = zmin(Ixx - Ah_*yh**2, Iyy - Ah_*xh**2, Ixy - Ah_*xh*yh)
    return Zg, Zn


def member_caps(p, g):
    c = {}
    A, t, b = SEC["A"], SEC["t"], SEC["b"]; fy, fu, E = p["fy"], p["fu"], p["Es"]
    c["Tdg"] = A*fy/p["gamma_m0"]
    Anc = (b - t/2 - p["d0_14"])*t; Ago = (b - t/2)*t
    bs, Lc = b + b - t, p["edge_min"]
    beta = max(0.7, min(1.4 - 0.076*(b/t)*(fy/fu)*(bs/Lc), fu*p["gamma_m0"]/(fy*p["gamma_m1"])))
    c["beta"] = beta; c["Tdn"] = 0.9*Anc*fu/p["gamma_m1"] + beta*Ago*fy/p["gamma_m0"]; c["Td"] = min(c["Tdg"], c["Tdn"])
    Ivv = (SEC["Ixx"] + SEC["Iyy"])/2 - sqrt(((SEC["Ixx"] - SEC["Iyy"])/2)**2 + SEC["Ixy"]**2)
    rvv = sqrt(Ivv/A); lam_c = math.pi*sqrt(E/fy)
    k1, k2, k3 = 1.25, 0.50, 60.0                      # Table 12: single bolt, hinged
    lphi = ((b + b)/(2*t))/lam_c
    def pd_comp(L):
        lvv = (L/rvv)/lam_c; lam = sqrt(k1 + k2*lvv**2 + k3*lphi**2)
        ph = 0.5*(1 + 0.49*(lam - 0.2) + lam**2); fcd = (fy/p["gamma_m0"])/(ph + sqrt(ph**2 - lam**2))
        return A*fcd, lam, fcd
    c["rvv"] = rvv; c["Pd_vert"], c["lam_vert"], c["fcd_vert"] = pd_comp(g["AB"])
    c["Pd_inc"], c["lam_inc"], c["fcd_inc"] = pd_comp(g["BC"])
    c["Pd_base"], c["lam_base"], c["fcd_base"] = pd_comp(p["J_mid"])
    c["Zg"], c["Zn"] = section_moduli(p)
    c["Mdg"], c["Mdn"] = c["Zg"]*fy/p["gamma_m0"], c["Zn"]*fy/p["gamma_m0"]
    c["Vd"] = b*t*fy/(sqrt(3)*p["gamma_m0"])
    return c


def bolt_caps(p, name, fub, fyb, d0, t_ply=5.0, e=None, oversize=True):
    d, An, Asb = BOLTS[name]
    e = e or p["edge_min"]
    kb = min(e/(3*d0), fub/p["fu"], 1.0)
    Vdsb = fub/sqrt(3)*An/p["gamma_mb"]                                   # threads in shear plane, n_n=1
    Vdpb = 2.5*kb*d*t_ply*p["fu"]/p["gamma_mb"]*(p["k_over"] if oversize else 1.0)
    Tdb = min(0.9*fub*An, fyb*Asb*p["gamma_m1"]/p["gamma_m0"])/p["gamma_mb"]
    return dict(d=d, An=An, Asb=Asb, kb=kb, Vdsb=Vdsb, Vdpb=Vdpb, Vd=min(Vdsb, Vdpb), Tdb=Tdb)


def design(p=None, block_L=None):
    p = dict(p or P0())
    if block_L is not None: p["block_L"] = block_L
    g = geometry(p); w = wind(p, g); L = loads(p, g, w)
    res = {lc: closed_form(p, g, d) for lc, d in L["lc"].items()}
    cmb = {n: combine(res, f) for n, f, _ in COMBOS}
    for n, c_ in cmb.items():                                  # exact peak moment of the rafter, region S1-S2 (all UDL zones active)
        den = c_["qnm"] + c_["qnr"]
        sst = (-(c_["VB"]*g["cos"] + c_["Fn1"]) + c_["qnm"]*g["sa"])/den if abs(den) > 1e-12 else g["sM"]
        sst = min(max(sst, g["s1"]), g["s2"])
        c_["sstar"] = sst
        c_["Mstar"] = -(c_["VB"]*g["cos"]*sst + c_["Fn1"]*(sst - g["s1"]) + c_["qnm"]*(sst - g["sa"])**2/2 + c_["qnr"]*sst**2/2)
    U = [n for n, _, k in COMBOS if k == "U"]; S = [n for n, _, k in COMBOS if k == "S"]
    mc = member_caps(p, g); out = dict(p=p, g=g, w=w, L=L, res=res, cmb=cmb, mc=mc)
    # ---- member force envelopes (strength combos) ---------------------------------------------------
    env = {}
    def E_(keys, fn): return fn([cmb[n][k] for n in U for k in keys])
    env["vert_T"] = max(0, E_(["NAB"], max)); env["vert_C"] = max(0, -E_(["NAB"], min))
    env["inc_T"] = max(0, E_(["N_0", "N_a", "N_1m", "N_1p", "N_2m", "N_2p", "N_b", "N_L"], max)); env["inc_C"] = max(0, -E_(["N_0", "N_a", "N_1m", "N_1p", "N_2m", "N_2p", "N_b", "N_L"], min))
    env["inc_M"] = max(abs(v) for v in [cmb[n][k] for n in U for k in ("Minc1", "Minc2", "Mstar")])
    env["inc_V"] = max(abs(v) for v in [cmb[n][k] for n in U for k in ["V_0", "V_a", "V_1m", "V_1p", "V_2m", "V_2p", "V_b", "V_L"]])
    env["base_T"] = max(0, E_(["Nbase_A", "Nbase_C"], max)); env["base_C"] = max(0, -E_(["Nbase_A", "Nbase_C"], min))
    env["base_Msup"] = max(abs(cmb[n][k]) for n in U for k in ("M1", "M2", "M3", "M4"))
    env["base_Mspan"] = max(abs(cmb[n][k]) for n in U for k in ("Mm1", "Mm2", "Mm3"))
    env["base_V"] = max(abs(cmb[n][k]) for n in U for k in ("V1m", "V1p", "V2m", "V2p", "V3m", "V3p", "V4m", "V4p"))
    out["env"] = env
    # ---- member checks -------------------------------------------------------------------------------
    chk = {}
    chk["Vertical member  N (T)"] = (env["vert_T"], mc["Td"])
    chk["Vertical member  N (C)"] = (env["vert_C"], mc["Pd_vert"])
    chk["Inclined  N+M (T)  cl 9.3.1"] = (env["inc_T"]/mc["Td"] + env["inc_M"]/mc["Mdg"], 1.0)
    chk["Inclined  N+M (C)  cl 9.3.1"] = (env["inc_C"]/mc["Pd_inc"] + env["inc_M"]/mc["Mdg"], 1.0)
    chk["Inclined  shear cl 8.4"] = (env["inc_V"], mc["Vd"])
    chk["Base  N+M at J-bolt section (T)"] = (env["base_T"]/mc["Td"] + env["base_Msup"]/mc["Mdn"], 1.0)
    chk["Base  N+M at J-bolt section (C)"] = (env["base_C"]/mc["Pd_base"] + env["base_Msup"]/mc["Mdn"], 1.0)
    chk["Base  N+M at mid-span"] = (max(env["base_T"]/mc["Td"], env["base_C"]/mc["Pd_base"]) + env["base_Mspan"]/mc["Mdg"], 1.0)
    chk["Base  shear cl 8.4"] = (env["base_V"], mc["Vd"])
    out["chk_member"] = chk
    # ---- connection (frame) bolts ---------------------------------------------------------------------
    VB = max(abs(cmb[n]["VB"]) for n in U); RC = max(hypot(cmb[n]["Cx"], cmb[n]["Cy"]) for n in U)
    Fn_t = max(max(cmb[n]["Fnb"], 0.0) for n in U)                 # module-bolt tension per bolt (load path via the 4 M8 bolts)
    Ft_s = max(abs(cmb[n]["Ftb"]) for n in U)                      # module-bolt shear per bolt (along slope)
    bc = {}
    bc["M10 A base-vertical"] = bolt_caps(p, "M10", p["fub88"], p["fyb88"], p["d0_14"])
    bc["M10 B vertical-inclined"] = bolt_caps(p, "M10", p["fub88"], p["fyb88"], p["d0_14"])
    bc["M12 C base-inclined"] = bolt_caps(p, "M12", p["fub88"], p["fyb88"], p["d0_14"])
    bc["M8 module (SS A2-70)"] = bolt_caps(p, "M8", p["fub_ss"], p["fyb_ss"], p["d0_M8"])
    dem = {"M10 A base-vertical": (VB, 0), "M10 B vertical-inclined": (VB, 0), "M12 C base-inclined": (RC, 0),
           "M8 module (SS A2-70)": (Ft_s, Fn_t)}
    chk_b = {}
    for k, cap in bc.items():
        V, T = dem[k]; ur_v = V/cap["Vd"]; ur_t = T/cap["Tdb"]
        chk_b[k] = dict(V=V, T=T, Vd=cap["Vd"], Vdsb=cap["Vdsb"], Vdpb=cap["Vdpb"], Tdb=cap["Tdb"], kb=cap["kb"],
                        ur=max(ur_v, ur_t, (V/cap["Vd"])**2 + (T/cap["Tdb"])**2))
    out["bolts"] = bc; out["chk_bolt"] = chk_b; out["bolt_dem"] = dem
    # ---- edge / end distances (cl 10.2.4.2: >= 1.5 d0) -------------------------------------------------
    hole = [("Base Ø14 @A (end 27.5)", p["d0_14"], min(p["base_end_A"], p["edge_min"])),
            ("Base Ø14 @C (end 25)", p["d0_14"], min(p["base_end_C"], p["edge_min"])),
            ("Base Ø18 J-bolt (edge)", p["d0_J"], p["edge_min"]),
            ("Vertical Ø14 (end 22.5)", p["d0_14"], min(p["vert_end"], p["edge_min"])),
            ("Inclined Ø14 @B (end 27.47)", p["d0_14"], min(p["incl_end_B"], p["edge_min"])),
            ("Inclined Ø14 @C (end 28.92)", p["d0_14"], min(p["incl_end_C"], p["edge_min"])),
            ("Inclined slot 9x14 (edge)", p["d0_M8"], p["edge_min"])]
    out["edge"] = [(n, d0, e, 1.5*d0, e >= 1.5*d0) for n, d0, e in hole]
    # ---- ballast stability (per frame = half table) -------------------------------------------------------
    gam_c = p["gam_c"]*1e-6                                          # N/mm3
    Wb1 = gam_c*p["block_w"]*p["block_h"]*p["block_L"]
    xb1, xb2 = (g["J1"] + g["J2"])/2, (g["J3"] + g["J4"])/2
    xp_r, xp_l = xb2 + p["block_w"]/2, xb1 - p["block_w"]/2
    Wfr = L["Wbase"] + L["Wv"] + L["Winc"]; Wmh = L["Wm"]/2
    mx = (g["S1"][0] + g["S2"][0])/2; my = (g["S1"][1] + g["S2"][1])/2
    xQ, yQ = mx + p["e_mod"]*g["sin"], my + p["e_mod"]*g["cos"]
    up = res["WLU"]; dn = res["WLD"]
    Fu = resultant(g, L["lc"]["WLU"]); Fd = resultant(g, L["lc"]["WLD"])
    f = p["ll_fac"]; d9 = p["dl_stab"]; mu = p["mu_f"]
    Wfs = Wmh + Wfr                                                  # non-ballast dead load per frame
    bal = dict(Wb1=Wb1, xb1=xb1, xb2=xb2, xp_r=xp_r, xp_l=xp_l, xQ=xQ, yQ=yQ, Wfs=Wfs, Fu=Fu, Fd=Fd)
    # required block weight from each criterion (closed form, linear in Wb)
    Mfs = Wmh*(xp_r - xQ) + Wfr*(xp_r - g["AC"]/2)
    Mot = f*(Fu[1]*(xp_r - xQ) + Fu[0]*yQ)
    bal["Wb_uplift"] = (f*Fu[1]/d9 - Wfs)/2
    bal["Wb_slide"] = ((f*Fu[1] + f*Fu[0]/mu)/d9 - Wfs)/2
    bal["Wb_overt"] = ((Mot/d9) - Mfs)/((xp_r - xb1) + (xp_r - xb2))
    Tblk = max(max(0.0, -(cmb[n]["R1"] + cmb[n]["R2"])) for n in U), max(max(0.0, -(cmb[n]["R3"] + cmb[n]["R4"])) for n in U)
    bal["Tblk"] = Tblk; bal["Wb_block"] = max(Tblk)/d9
    bal["Wb_req"] = max(bal["Wb_uplift"], bal["Wb_slide"], bal["Wb_overt"], bal["Wb_block"], 0)
    bal["L_req"] = bal["Wb_req"]/(gam_c*p["block_w"]*p["block_h"])
    bal["L_req_round"] = math.ceil(bal["L_req"]/50.0)*50
    Wtot = Wfs + 2*Wb1
    bal["uplift"] = (f*Fu[1], d9*Wtot)                                 # demand, capacity
    bal["slide"] = (f*Fu[0], mu*max(0.0, d9*Wtot - f*Fu[1]))
    bal["overt"] = (Mot, d9*(Mfs + Wb1*((xp_r - xb1) + (xp_r - xb2))))
    bal["block_up"] = (max(Tblk), d9*Wb1)
    # downward wind: sliding & overturning about left toe
    Mot_d = f*(abs(Fd[0])*yQ - abs(Fd[1])*(xQ - xp_l))
    Mr_d = 1.5*(Wmh*(xQ - xp_l) + Wfr*(g["AC"]/2 - xp_l) + Wb1*((xb1 - xp_l) + (xb2 - xp_l)))
    bal["slide_dn"] = (f*abs(Fd[0]), mu*(1.5*Wtot + f*abs(Fd[1])))
    bal["overt_dn"] = (max(Mot_d, 0.0), Mr_d)
    # seismic
    yb = p["block_h"]/2; y_fr = (g["yA"] + g["yB"])/2
    bal["slide_eq"] = (f*L["Ah"]*Wtot, mu*d9*Wtot)
    Meq = f*L["Ah"]*(Wmh*yQ + Wfr*y_fr + 2*Wb1*yb)
    bal["overt_eq"] = (Meq, d9*(Mfs + Wb1*((xp_r - xb1) + (xp_r - xb2))))
    bal["roof_load_kN_m2"] = 2*Wtot/1000.0/((g["AC"] + 100)*p["frame_sp"]/1e6)/1.0 if False else (2*Wtot/1000.0)/((p["base_len"]/1000.0)*(p["mod_L"]/1000.0))
    out["bal"] = bal
    # ---- J-bolt anchorage ---------------------------------------------------------------------------------------
    tau = TAUBD[int(p["fck"])]
    Tj = max(max(0.0, -cmb[n][k]) for n in U for k in ("R1", "R2", "R3", "R4"))
    Vj = max(abs(cmb[n]["RH1"]) for n in U)/4.0
    anc = {}
    for nm, (d, An, Asb) in BOLTS.items():
        if nm not in ("M10", "M16"): continue
        cap = bolt_caps(p, nm, p["fub88"], p["fyb88"], p["d0_J"])
        t_w = {"M16": 3.0, "M10": 2.5}[nm]; t_sp = {"M16": 4.0, "M10": 2.5}[nm]
        t_nut = {"M16": 14.8, "M10": 8.4}[nm]; thr = {"M16": 4.0, "M10": 3.0}[nm]
        Lproj = 5 + 5 + 4*t_w + t_sp + t_nut + thr
        hook = 16*d
        Ls_req = max(0.0, Tj/(tau*math.pi*d) - hook)
        Ls_rec = max(Ls_req, 100.0)
        Tanch = tau*math.pi*d*(Ls_rec + hook)
        kbJ = min(p["edge_min"]/(3*p["d0_J"]), p["fub88"]/p["fu"], 1.0)
        Vdpb = 2.5*kbJ*d*SEC["t"]*p["fu"]/p["gamma_mb"]*p["k_over"]
        anc[nm] = dict(An=An, Tdb=cap["Tdb"], Vdsb=cap["Vdsb"], Vdpb=Vdpb, T=Tj, V=Vj, comb=(Vj/min(cap["Vdsb"], Vdpb))**2 + (Tj/cap["Tdb"])**2,
                       Lproj=Lproj, hook=hook, Ls_req=Ls_req, Ls_rec=Ls_rec, Tanch=Tanch,
                       Ltot=math.ceil((Lproj + Ls_rec)/10.0)*10, tau=tau)
    out["anchor"] = anc
    # ---- deflection (service) ---------------------------------------------------------------------------------------
    EI = p["Es"]*g["Ieff"]; Lb = g["BC"]
    dfl = {}
    for n in S:
        c = cmb[n]; tot = 0.0
        for Fn_i, s_i in ((c["Fn1"], g["s1"]), (c["Fn2"], g["s2"])):
            a = min(s_i, Lb - s_i); tot += Fn_i*a*(3*Lb**2 - 4*a**2)/(48*EI)
        tot += c["qn"]*5*Lb**4/(384*EI)                              # distributed normal load, taken over full span (conservative; module covers 97 %)
        dfl[n] = dict(inc=abs(tot), dA=abs(c["dA"]), dC=abs(c["dC"]))
    out["defl"] = dfl
    out["defl_lim"] = dict(inc=Lb/p["defl_div"], tip_A=2*g["a1"]/p["defl_div"], tip_C=2*g["c2"]/p["defl_div"])
    return out


if __name__ == "__main__" and False:
    pass
