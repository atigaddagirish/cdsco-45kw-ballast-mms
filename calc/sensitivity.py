"""Sensitivity of the governing results to the assumed inputs (engine, block_L fixed at provided 650 mm unless stated)."""
import engine as E

SCEN = [("Base case (as issued)", {}),
        ("k1 = 1.00 (50-yr life)", {"k1_risk": 1.0}),
        ("Terrain Cat 3 (dense urban)", {"terrain": 3}),
        ("Roof level 15 m (taller building)", {"z_bldg": 15.0}),
        ("mu = 0.5 (rougher roof finish)", {"mu_f": 0.5}),
        ("mu = 0.3 (smooth / membrane)", {"mu_f": 0.3}),
        ("Module 27.5 kg (lighter)", {"mod_kg": 27.5}),
        ("Seismic Rp = 1.0 (no reduction)", {"Rp": 1.0}),
        ("Worst: k1=1.0 + roof 15 m + mu=0.3", {"k1_risk": 1.0, "z_bldg": 15.0, "mu_f": 0.3})]


def run():
    rows = []
    for lab, ch in SCEN:
        p = E.P0(); p.update(ch); o = E.design(p); b = o["bal"]
        ur = {k: b[k][0]/b[k][1] for k in ("uplift", "slide", "overt", "slide_eq")}
        gov = max(("Uplift", b["Wb_uplift"]), ("Sliding", b["Wb_slide"]), ("Overturning", b["Wb_overt"]), ("Per-block uplift", b["Wb_block"]), key=lambda t: t[1])[0]
        rows.append((lab, o["w"]["pd"], b["L_req"], b["L_req_round"], gov, max(ur.values()), ur["slide_eq"]))
    return rows


if __name__ == "__main__":
    print("%-40s %7s %9s %8s %-16s %8s %8s" % ("scenario", "pd", "L_req", "L_rnd", "governs", "maxUR@650", "EQ slide"))
    for r in run(): print("%-40s %7.3f %9.0f %8d %-16s %8.3f %8.3f" % r)
