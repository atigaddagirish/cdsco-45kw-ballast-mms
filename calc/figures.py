"""Engineering figures for the design report (matplotlib). All geometry and values come from engine.py."""
import os, math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, FancyArrowPatch, Arc
import engine as E

STEEL, WIND, WEIGHT, ROOF, MOD = "#1F4E79", "#C00000", "#2E7D32", "#7F7F7F", "#5B9BD5"
OUT = "../report/figures"


def band(ax, p1, p2, w, **kw):
    """polygon band of width w about segment p1-p2"""
    (x1, y1), (x2, y2) = p1, p2; L = math.hypot(x2 - x1, y2 - y1); nx, ny = -(y2 - y1)/L*w/2, (x2 - x1)/L*w/2
    ax.add_patch(Polygon([(x1 + nx, y1 + ny), (x2 + nx, y2 + ny), (x2 - nx, y2 - ny), (x1 - nx, y1 - ny)], closed=True, **kw))


def arrow(ax, p, q, color, lw=1.6, **kw):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=9, color=color, lw=lw, **kw))


def dim(ax, p, q, txt, off=(0, 0), color="k", fs=7):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="<->", mutation_scale=6, color=color, lw=0.7, shrinkA=0, shrinkB=0))
    ax.text((p[0] + q[0])/2 + off[0], (p[1] + q[1])/2 + off[1], txt, ha="center", va="center", fontsize=fs, color=color,
            bbox=dict(fc="white", ec="none", pad=0.6, alpha=0.85))


def pts(o):
    g = o["g"]; yA, yB = g["yA"], g["yB"]
    return dict(A=(0, yA), B=(0, yB), C=(g["AC"], yA), S1=g["S1"], S2=g["S2"], J=[(g[k], yA) for k in ("J1", "J2", "J3", "J4")])


def fig_geometry(o, path):
    p, g = o["p"], dict(o["g"]); g["xb1"], g["xb2"] = o["bal"]["xb1"], o["bal"]["xb2"]; P = pts(o); d = (g["cos"], -g["sin"]); n = (g["sin"], g["cos"])
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.add_patch(Rectangle((-150, -25), 1500, 25, fc="#D9D9D9", ec=ROOF, hatch="////", lw=0.5)); ax.text(1300, -12, "ROOF SLAB", fontsize=6, ha="right", va="center")
    for xc in (g["xb1"], g["xb2"]):
        ax.add_patch(Rectangle((xc - p["block_w"]/2, 0), p["block_w"], p["block_h"], fc="#EDEDED", ec="k", lw=1))
    ax.text(g["xb1"], 125, "BLOCK\n300 x 250 x L\n(L = %d mm)" % p["block_L"], ha="center", fontsize=6.5)
    ax.text(g["xb2"], 125, "BLOCK\n300 x 250 x L\n(L = %d mm)" % p["block_L"], ha="center", fontsize=6.5)
    # J bolts
    for (x, y) in P["J"]:
        ax.plot([x, x], [p["block_h"] + 45, p["block_h"] - 105], color="k", lw=1.6)
        hook_dir = 1 if x < (g["xb1"] if x < 500 else g["xb2"]) else -1
        ax.plot([x, x + hook_dir*32], [p["block_h"] - 105, p["block_h"] - 105], color="k", lw=1.6)
    # base (vertical leg face), vertical member, inclined
    ax.add_patch(Rectangle((-p["base_end_A"], p["block_h"]), p["base_len"], 50, fc="#9DC3E6", ec=STEEL, lw=1.2))
    ax.add_patch(Rectangle((-25, p["block_h"] + 5), 50, p["vert_len"] + 40, fc="#BDD7EE", ec=STEEL, lw=1.2))
    A1 = (P["B"][0] - p["incl_end_B"]*d[0], P["B"][1] - p["incl_end_B"]*d[1]); A2 = (P["C"][0] + p["incl_end_C"]*d[0], P["C"][1] + p["incl_end_C"]*d[1])
    band(ax, A1, A2, 50, fc="#BDD7EE", ec=STEEL, lw=1.2)
    mid = ((P["S1"][0] + P["S2"][0])/2, (P["S1"][1] + P["S2"][1])/2); half = p["mod_W"]/2
    m1 = (mid[0] - half*d[0] + 25*n[0], mid[1] - half*d[1] + 25*n[1]); m2 = (mid[0] + half*d[0] + 25*n[0], mid[1] + half*d[1] + 25*n[1])
    band(ax, m1, m2, p["mod_t"], fc=MOD, ec="#1F3864", lw=0.8, alpha=0.85)
    for nm, q in (("A", P["A"]), ("B", P["B"]), ("C", P["C"]), ("S1", P["S1"]), ("S2", P["S2"])):
        ax.plot(*q, "o", color="#C55A11", ms=4); ax.text(q[0] + 12, q[1] + 18, nm, fontsize=7, color="#C55A11", fontweight="bold")
    for i, (x, y) in enumerate(P["J"], 1): ax.text(x + 14, 228, "J%d" % i, fontsize=6.5, ha="left", color="k", bbox=dict(fc="#EDEDED", ec="none", pad=0.5))
    # dimensions
    dim(ax, (0, -55), (g["AC"], -55), "A-C = %.1f" % g["AC"])
    dim(ax, (g["xb1"], -90), (g["xb2"], -90), "blocks c/c 700")
    dim(ax, (-110, P["A"][1]), (-110, P["B"][1]), "A-B = %.2f" % g["AB"], off=(-28, 0))
    dim(ax, (-200, 0), (-200, p["block_h"]), "250", off=(-20, 0))
    dim(ax, (g["xb1"] - 150, 290 - 100), (g["xb1"] + 150, 290 - 100), "300", off=(0, 18))
    bc_mid = ((P["B"][0] + P["C"][0])/2, (P["B"][1] + P["C"][1])/2)
    ax.text(bc_mid[0] + 40, bc_mid[1] + 105, "B-C = %.2f  (module bolts 1088 c/c)" % g["BC"], rotation=-g["tilt_deg"], fontsize=7, ha="center")
    ax.add_patch(Arc((g["AC"], g["yA"]), 360, 360, theta1=180 - g["tilt_deg"], theta2=180, lw=0.8)); ax.text(g["AC"] - 270, g["yA"] + 30, "%.3f°" % g["tilt_deg"], fontsize=8, fontweight="bold")
    ax.text(330, 700, "ISA 50x50x5 (all members)\nBase 1200 | Vertical 249.72 | Inclined 1222.01\nJ-bolts: 2 per block @150 c/c\nPinned single-bolt joints A, B, C", fontsize=7.5, va="top")
    ax.set_xlim(-300, 1400); ax.set_ylim(-120, 720); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Fig 1  Frame elevation (one of two frames per table) - dimensions in mm, bolt-centre geometry from drawing AL-001 R0", fontsize=9, loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def frame_lines(ax, o, lw=2.0):
    P = pts(o)
    ax.plot([-27.5, P["C"][0] + 25], [P["A"][1]]*2, color=STEEL, lw=lw)
    ax.plot([P["A"][0], P["B"][0]], [P["A"][1], P["B"][1]], color=STEEL, lw=lw)
    ax.plot([P["B"][0], P["C"][0]], [P["B"][1], P["C"][1]], color=STEEL, lw=lw)
    for (x, y) in P["J"]: ax.plot(x, y, "s", color="k", ms=4)
    for nm in ("A", "B", "C"): ax.plot(*P[nm], "o", color="#C55A11", ms=4)
    return P


def fig_loads(o, path):
    g, L, w, p = o["g"], o["L"], o["w"], o["p"]; fig, axs = plt.subplots(1, 3, figsize=(13, 4.2))
    specs = [("DL", "DEAD LOAD (per frame)  -  R1: module = UDL", WEIGHT), ("WLU", "WIND UPLIFT  Cp = %.3f" % w["cp_up"], WIND), ("WLD", "WIND DOWNWARD  Cp = +%.3f" % w["cp_dn"], WIND)]
    for ax, (lc, ttl, col) in zip(axs, specs):
        P = frame_lines(ax, o); d = L["lc"][lc]; s_, c_ = g["sin"], g["cos"]
        pt = lambda sp: (sp*c_, g["yB"] - sp*s_)
        # distributed loads: arrows spread over the zone, scaled 1 N/mm -> K mm
        for key, (a0, b0), K in (("qm", (g["sa"], g["sb"]), 0.0), ("qr", (0.0, g["BC"]), 0.0)):
            qx, qy = d[key]; mag = math.hypot(qx, qy)
            if mag < 1e-9: continue
            K = (110.0/0.1259) if lc == "DL" else (110.0/0.938)
            if key == "qr": K *= 2.5
            ns = 16 if key == "qm" else 9
            for sp in np.linspace(a0, b0, ns):
                q = pt(sp); head = q if qy < 0 else (q[0] + qx*K, q[1] + qy*K); tail = (q[0] - qx*K, q[1] - qy*K) if qy < 0 else q
                arrow(ax, tail, head, col if key == "qm" else "#7F7F7F", lw=0.9 if key == "qm" else 0.7)
            top = (pt((a0 + b0)/2)[0] + (qx*K if qy > 0 else -qx*K), pt((a0 + b0)/2)[1] + (qy*K if qy > 0 else -qy*K))
            if key == "qm": ax.text(top[0] + 20, top[1] + 30, "%s UDL %.4f N/mm\n(= %.4f kN/m) over %.0f mm" % ("module" if lc == "DL" else "wind (normal)", mag, mag, g["Lm"]), fontsize=7, color=col)
        fx, fy = d["slots"][0]; mag = math.hypot(fx, fy)
        if mag > 1e-9:
            kk = 230/531.0
            for s2 in ("S1", "S2"):
                q = P[s2]; tail = (q[0] - fx*kk, q[1] - fy*kk) if fy < 0 else q; head = q if fy < 0 else (q[0] + fx*kk, q[1] + fy*kk)
                arrow(ax, tail, head, col, lw=2.0); ax.text((tail[0] + head[0])/2 + 25, (tail[1] + head[1])/2 + 10, "%.1f N" % mag, fontsize=7, color=col)
        if lc == "DL":
            ax.text(600, 40, "rafter self-weight UDL %.4f N/mm (grey); base UDL %.4f N/mm;\nvertical member + stubs lumped at A, C" % (L["wr"], d["wb"]), fontsize=6.5, ha="center")
        else:
            ax.text(600, 40, "%s\npd = %.3f kN/m2, A = %.3f m2" % ("through the 4 module bolts (alternate, wind_mode 0)" if p["wind_mode"] == 0 else "UDL over the module contact zone (wind_mode 1)", w["pd"], w["A_mod"]), fontsize=6.5, ha="center")
        ax.set_title(ttl, fontsize=8.5); ax.set_xlim(-150, 1300); ax.set_ylim(-60, 950); ax.set_aspect("equal"); ax.axis("off")
    fig.suptitle("Fig 3  Load cases applied to one frame; IS 875 Pt 3 wind, IS 875 Pt 1 dead load", fontsize=9, x=0.01, ha="left")
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def fig_results(o, path):
    g, p = o["g"], o["p"]; c = o["cmb"]["C2 0.9DL+1.5WL(up)"]; w_ = 0.9*o["L"]["ws"]
    fig = plt.figure(figsize=(12, 8.6)); gs = fig.add_gridspec(2, 1, height_ratios=[1.35, 1])
    ax = fig.add_subplot(gs[0]); P = frame_lines(ax, o, lw=1.8)
    for i, (R, (x, y)) in enumerate(zip((c["R1"], c["R2"], c["R3"], c["R4"]), P["J"]), 1):
        L_ = 35 + abs(R)*0.05; y0 = y - 40; up = R > 0
        arrow(ax, (x, y0 - L_) if up else (x, y0), (x, y0) if up else (x, y0 - L_), "#7030A0", lw=1.8)
        left = i in (1, 3)
        ax.text(x + (-10 if left else 10), y0 - L_ - 12, "R%d = %+.0f N\n%s" % (i, R, "bearing" if up else "J-bolt tension"), fontsize=7, ha="right" if left else "left", va="top", color="#7030A0")
    ax.text(10, P["B"][1] + 30, "A-B axial = %+.0f N (tension +)" % c["NAB"], fontsize=8, color=STEEL)
    ax.text(600, 600, "Rafter B-C:  |M|max = %.1f N.m (zero-shear section s* = %.0f mm),  |V|max = %.0f N" % (max(abs(c["Minc1"]), abs(c["Minc2"]), abs(c["Mstar"]))/1e3, c["sstar"], max(abs(c[k]) for k in ("V_0", "V_a", "V_1m", "V_1p", "V_2m", "V_2p", "V_b", "V_L"))), fontsize=8, color=STEEL, ha="center")
    ax.text(600, -300, "Horizontal reaction at J1 = %.0f N   |   Base N+M at J-bolt section UR = %.2f" % (c["RH1"], o["chk_member"]["Base  N+M at J-bolt section (T)"][0]), fontsize=8, ha="center")
    ax.set_xlim(-150, 1300); ax.set_ylim(-340, 680); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Fig 4  Governing strength combination C2 = 0.9 DL + 1.5 WL (uplift): reactions and forces, per frame (N, N.m)", fontsize=9, loc="left")
    ax2 = fig.add_subplot(gs[1])
    xs = []; ms = []
    sup = [g["J1"], g["J2"], g["J3"], g["J4"]]; Ms = [c["M1"], c["M2"], c["M3"], c["M4"]]
    PA, PC = c["PA"], c["PC"]
    x = np.linspace(0, g["a1"], 40); xs += list(x); ms += [-(PA*xx + w_*xx**2/2) for xx in x]
    for i, (Mi, Vp, L_) in enumerate(((c["M1"], c["V1p"], p["J_pair"]), (c["M2"], c["V2p"], p["J_mid"]), (c["M3"], c["V3p"], p["J_pair"]))):
        x = np.linspace(0, L_, 80); xs += list(sup[i] + x); ms += [Mi + Vp*xx - w_*xx**2/2 for xx in x]
    x = np.linspace(0, g["c2"], 40); xs += list(g["J4"] + x); ms += [-(PC*(g["c2"] - xx) + w_*(g["c2"] - xx)**2/2) for xx in x]
    ms = np.array(ms)/1e3
    ax2.fill_between(xs, 0, ms, color="#F4B183", alpha=0.6); ax2.plot(xs, ms, color="#C55A11", lw=1.2); ax2.axhline(0, color="k", lw=0.6)
    for xj, Mj in zip(sup, Ms): ax2.annotate("%.1f" % (Mj/1e3), (xj, Mj/1e3), fontsize=7, ha="center", va="bottom" if Mj > 0 else "top")
    for xj in sup: ax2.axvline(xj, color="#999999", lw=0.5, ls=":")
    ax2.set_xlabel("x along base (mm); dotted = J-bolt supports J1..J4", fontsize=8); ax2.set_ylabel("M (N.m), sagging +", fontsize=8); ax2.tick_params(labelsize=7)
    ax2.set_title("Base member bending moment.  Capacity Md(net of Ø18 hole) = %.0f N.m at J-bolt sections" % (o["mc"]["Mdn"]/1e3), fontsize=8, loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def fig_ballast(o, path):
    g, p, b, L = o["g"], o["p"], o["bal"], o["L"]; f, d9 = p["ll_fac"], p["dl_stab"]
    fig, ax = plt.subplots(figsize=(11, 5.6))
    ax.add_patch(Rectangle((-150, -25), 1500, 25, fc="#D9D9D9", ec=ROOF, hatch="////", lw=0.5))
    for xc in (b["xb1"], b["xb2"]): ax.add_patch(Rectangle((xc - p["block_w"]/2, 0), p["block_w"], p["block_h"], fc="#EDEDED", ec="k", lw=1))
    P = frame_lines(ax, o, lw=1.6); Q = (b["xQ"], b["yQ"]); Fx, Fy = b["Fu"]
    sc = 220/max(abs(Fy), 1)
    arrow(ax, (Q[0] - Fx*sc*0, Q[1]), (Q[0] + Fx*sc, Q[1] + Fy*sc), WIND, lw=2.4)
    ax.text(Q[0] + 40, Q[1] + Fy*sc - 30, "WL uplift (unfactored)\nFy = %.0f N up, Fx = %.0f N\nfactored x1.5: %.0f / %.0f N" % (Fy, Fx, f*Fy, f*Fx), fontsize=7, color=WIND, va="top")
    Wb1 = b["Wb1"]; k = 140/2500.0
    for xc in (b["xb1"], b["xb2"]): arrow(ax, (xc, 125 + Wb1*k), (xc, 125), WEIGHT, lw=2.0); ax.text(xc + 10, 130 + Wb1*k, "0.9 Wb = %.0f N" % (d9*Wb1), fontsize=7, color=WEIGHT)
    ax.plot(b["xp_r"], 0, "^", color="k", ms=9); ax.text(b["xp_r"] + 15, -45, "pivot (right toe)", fontsize=7)
    dim(ax, (b["xQ"], -75), (b["xp_r"], -75), "lever arm %.0f mm" % (b["xp_r"] - b["xQ"]))
    U = b; txt = ["Per frame, block %.0f x %.0f x %.0f mm = %.1f kg each" % (p["block_w"], p["block_h"], p["block_L"], Wb1/p["gacc"]),
                  "Uplift      : %.0f N  <= %.0f N   UR %.2f" % (b["uplift"][0], b["uplift"][1], b["uplift"][0]/b["uplift"][1]),
                  "Sliding     : %.0f N  <= %.0f N   UR %.2f   (mu = %.1f)  <- GOVERNS" % (b["slide"][0], b["slide"][1], b["slide"][0]/b["slide"][1], p["mu_f"]),
                  "Overturning : %.0f N.m <= %.0f N.m  UR %.2f" % (b["overt"][0]/1e3, b["overt"][1]/1e3, b["overt"][0]/b["overt"][1]),
                  "Required block length %d mm (provided %d mm)" % (b["L_req_round"], p["block_L"])]
    ax.text(-140, 880, "\n".join(txt), fontsize=8, va="top", family="monospace")
    ax.set_xlim(-200, 1350); ax.set_ylim(-130, 900); ax.set_aspect("equal"); ax.axis("off")
    ax.set_title("Fig 6  Ballast stability, wind-uplift case (IS 800 Table 4: 0.9 DL + 1.5 WL), per frame", fontsize=9, loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def fig_udl(o, path):
    """Tributary derivation of the module dead-load UDL on the rafter (client comment R1)."""
    p, g, L = o["p"], o["g"], o["L"]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(11, 8.6), gridspec_kw=dict(height_ratios=[1.15, 1]))
    # ---- plan view (x across frames, y along slope)
    ML, MW, fs, ov, tw = p["mod_L"], p["mod_W"], p["frame_sp"], g["mod_ovh"], L["trib"]
    x1, x2 = ov, ov + fs
    a1.add_patch(Rectangle((0, 0), ML, MW, fc="#DEEBF7", ec="#1F3864", lw=1.4))
    a1.add_patch(Rectangle((0, 0), tw, MW, fc="#F8CBAD", ec="none", alpha=0.55)); a1.add_patch(Rectangle((tw, 0), ML - tw, MW, fc="#C6E0B4", ec="none", alpha=0.55))
    for xr in (x1, x2):
        a1.add_patch(Rectangle((xr - 25, -0.5*(p["incl_len"] - MW)), 50, p["incl_len"], fc="#9DC3E6", ec=STEEL, lw=1.2))
        for yb in (g["sa"] - 0 + 0, ): pass
        for yy in (MW/2 - p["slot_cc_dwg"]/2, MW/2 + p["slot_cc_dwg"]/2): a1.plot(xr, yy, "o", color="#C00000", ms=5)
    a1.text(tw/2, MW*0.5, "tributary of rafter 1\n%.1f mm" % tw, ha="center", va="center", fontsize=9); a1.text(tw + (ML - tw)/2, MW*0.5, "tributary of rafter 2\n%.1f mm" % (ML - tw), ha="center", va="center", fontsize=9)
    dim(a1, (0, -190), (ML, -190), "module L = %.0f" % ML); dim(a1, (x1, -90), (x2, -90), "rafters %.0f c/c" % fs)
    dim(a1, (0, MW + 90), (x1, MW + 90), "overhang %.1f" % ov); dim(a1, (x2, MW + 90), (ML, MW + 90), "%.1f" % ov)
    dim(a1, (-120, 0), (-120, MW), "W = %.0f" % MW, off=(-45, 0))
    a1.text(x1 + 40, MW/2 + p["slot_cc_dwg"]/2 + 30, "M8 bolts\n1400 x 1088", fontsize=7, color="#C00000")
    a1.set_xlim(-300, ML + 120); a1.set_ylim(-330, MW + 220); a1.set_aspect("equal"); a1.axis("off")
    a1.set_title("Fig 2a  PLAN: module on two rafters (no purlins). Support arrangement and tributary width (mm)", fontsize=9, loc="left")
    # ---- rafter elevation (schematic, horizontal)
    LB = g["BC"]; a2.plot([0, LB], [0, 0], color=STEEL, lw=5, solid_capstyle="butt"); a2.plot([-p["incl_end_B"], 0], [0, 0], color=STEEL, lw=5, alpha=0.5); a2.plot([LB, LB + p["incl_end_C"]], [0, 0], color=STEEL, lw=5, alpha=0.5)
    a2.add_patch(Rectangle((g["sa"], 14), g["Lm"], 22, fc="#9DC3E6", ec="#1F3864", lw=1))
    for sp in np.linspace(g["sa"], g["sb"], 40): arrow(a2, (sp, 175), (sp, 40), WEIGHT, lw=0.8)
    a2.plot([g["sa"], g["sb"]], [175, 175], color=WEIGHT, lw=1.4)
    for nm, sp in (("B", 0.0), ("C", LB)): a2.plot(sp, -3, "^", color="#C55A11", ms=11); a2.text(sp, -62, "pin %s" % nm, ha="center", fontsize=8, color="#C55A11")
    for nm, sp in (("bolt 1", g["s1"]), ("bolt 2", g["s2"])): a2.plot(sp, 25, "o", color="#C00000", ms=6); a2.text(sp, -118, nm + " (M8)", ha="center", fontsize=7.5, color="#C00000"); a2.plot([sp, sp], [20, -105], color="#C00000", lw=0.5, ls=":")
    dim(a2, (g["sa"], 240), (g["sb"], 240), "contact length = module width = %.0f mm  (%.1f ... %.1f from B)" % (g["Lm"], g["sa"], g["sb"]))
    a2.text(LB/2, 205, "w = %.4f N/mm  (= %.4f kN/m, vertical, per mm of rafter length)" % (L["wm"], L["wm"]), ha="center", fontsize=9, color=WEIGHT, fontweight="bold")
    a2.text(LB/2, -175, "w = ( Wm / (L x W) ) x ( L / 2 )  =  ( %.1f N / (%.0f x %.0f mm) ) x %.1f mm  =  Wm / (2 W)\nresultant w x W = %.1f N = Wm / 2 per rafter  (check: 2 rafters carry %.1f N = Wm)" % (L["Wm"], ML, MW, tw, L["wm"]*g["Lm"], L["Wm"]),
            ha="center", va="top", fontsize=8.5, family="monospace")
    a2.set_xlim(-120, LB + 150); a2.set_ylim(-330, 290); a2.set_aspect("equal"); a2.axis("off")
    a2.set_title("Fig 2b  ELEVATION of one rafter (along slope): module dead load as UDL over the contact length", fontsize=9, loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def fig_rafter(o, path):
    """Rafter bending moment, governing strength combination C1 (UDL module + wind at bolts)."""
    import json, solver2d
    g, p = o["g"], o["p"]; Uc = [t for t in E.COMBOS if t[2] == "U"]
    n, fac, _k = max(Uc, key=lambda t: max(abs(o["cmb"][t[0]][k]) for k in ("Minc1", "Minc2", "Mstar"))); c = o["cmb"][n]
    R0 = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "R0_results.json")))
    comb = dict(slots=[(0.0, 0.0)]*2, qm=(0.0, 0.0), qr=(0.0, 0.0), FxA=0.0, FxC=0.0, dAy=0.0, dCy=0.0, wb=0.0)
    for k, fa in fac.items():
        d = o["L"]["lc"][k]; comb["slots"] = [(comb["slots"][i][0] + fa*d["slots"][i][0], comb["slots"][i][1] + fa*d["slots"][i][1]) for i in (0, 1)]
        comb["qm"] = (comb["qm"][0] + fa*d["qm"][0], comb["qm"][1] + fa*d["qm"][1]); comb["qr"] = (comb["qr"][0] + fa*d["qr"][0], comb["qr"][1] + fa*d["qr"][1])
        for kk in ("FxA", "FxC", "dAy", "dCy", "wb"): comb[kk] += fa*d[kk]
    f, nodal, udl = E.build_model(p, g, comb); m = f.solve(nodal, udl)
    xs, ms = [], []; s0 = 0.0
    for nm in ["B-Pa", "Pa-S1", "S1-M", "M-S2", "S2-Pb", "Pb-C"]:
        el = m["elems"][nm]; qy = udl.get(nm, (0.0, 0.0))[1]
        for x in np.linspace(0, el["L"], 60): xs.append(s0 + x); ms.append((el["M1"] + el["fl"][1]*x + qy*x*x/2)/1e3)
        s0 += el["L"]
    fig, ax = plt.subplots(figsize=(11, 4.2)); ax.fill_between(xs, 0, ms, color="#F4B183", alpha=0.6); ax.plot(xs, ms, color="#C55A11", lw=1.4); ax.axhline(0, color="k", lw=0.6)
    ax.axvspan(g["sa"], g["sb"], color="#DEEBF7", alpha=0.5, zorder=0); ax.text(g["sa"] + 10, ax.get_ylim()[1]*0.12, "module contact zone (UDL)", fontsize=7.5, color="#1F3864")
    pk = max(ms, key=abs); xp = xs[ms.index(pk)]
    ax.annotate("R1 peak %.1f N.m at s = %.0f mm\n(closed form %.1f N.m)" % (abs(pk), xp, max(abs(c["Minc1"]), abs(c["Minc2"]), abs(c["Mstar"]))/1e3), (xp, pk), (xp + 120, pk*0.55), fontsize=8, arrowprops=dict(arrowstyle="->", lw=0.8))
    sg = 1 if pk > 0 else -1; ax.axhline(sg*R0["env"]["inc_M"]/1e3, color="#7F7F7F", ls="--", lw=1); ax.text(g["BC"]*0.02, sg*R0["env"]["inc_M"]/1e3 + sg*abs(pk)*0.03, "R0 peak (module as bolt point loads) %.1f N.m" % (R0["env"]["inc_M"]/1e3), fontsize=7.5, color="#595959", va="bottom" if sg > 0 else "top")
    for sp, lb in ((g["s1"], "bolt 1"), (g["s2"], "bolt 2")): ax.axvline(sp, color="#C00000", lw=0.6, ls=":"); ax.text(sp, min(ms)*1.0, lb, fontsize=7, color="#C00000", ha="center", va="bottom")
    ax.set_xlabel("distance along rafter from B (mm)", fontsize=8); ax.set_ylabel("M (N.m), sagging +", fontsize=8); ax.tick_params(labelsize=7)
    ax.set_title("Fig 5  Rafter bending moment, governing combination %s, per frame.  Capacity Md = %.0f N.m" % (n, o["mc"]["Mdg"]/1e3), fontsize=9, loc="left")
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


def make_all():
    os.makedirs(OUT, exist_ok=True); o = E.design()
    for fn, nm in ((fig_geometry, "fig1_geometry.png"), (fig_loads, "fig3_loads.png"), (fig_results, "fig4_results_C2.png"), (fig_ballast, "fig6_ballast.png"), (fig_udl, "fig2_udl_derivation.png"), (fig_rafter, "fig5_rafter_moment.png")):
        fn(o, os.path.join(OUT, nm)); print("wrote", nm)


if __name__ == "__main__":
    make_all()
