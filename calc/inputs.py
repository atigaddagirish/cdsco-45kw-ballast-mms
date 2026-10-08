"""Single source of truth for design inputs.
Used by engine.py (independent Python check) AND build_excel.py (Inputs sheet), so the two can never disagree.
status: V = verified fact (drawing / BOM / cross-checked) ; I = inference or assumption (flagged in report)
"""
from collections import OrderedDict as OD

# name: (value, unit, description, source, status)
INPUTS = OD([
 # ---- geometry, drawing AL-001 R0 -------------------------------------------------------
 ("base_len",   (1200.0, "mm", "Base member length (ISA 50x50x5)", "Drawing AL-001 sh.2", "V")),
 ("base_end_A", (27.5,   "mm", "Base: end -> bolt to vertical member (A)", "Drawing AL-001 sh.2", "V")),
 ("base_end_C", (25.0,   "mm", "Base: end -> bolt to inclined member (C)", "Drawing AL-001 sh.2", "V")),
 ("vert_len",   (249.72, "mm", "Vertical member length", "Drawing AL-001 sh.2", "V")),
 ("vert_end",   (22.5,   "mm", "Vertical: end -> bolt (both ends)", "Drawing AL-001 sh.2", "V")),
 ("incl_len",   (1222.01,"mm", "Inclined member length", "Drawing AL-001 sh.2", "V")),
 ("incl_end_B", (27.47,  "mm", "Inclined: end -> bolt at vertical member (B)", "Drawing AL-001 sh.2", "V")),
 ("incl_end_C", (28.92,  "mm", "Inclined: end -> bolt at base member (C)", "Drawing AL-001 sh.2", "V")),
 ("slot_end",   (67.0,   "mm", "Inclined: end -> module slot (both ends)", "Drawing AL-001 sh.2", "V")),
 ("J_off",      (175.0,  "mm", "Base: end -> first J-bolt hole (both ends)", "Drawing AL-001 sh.2", "V")),
 ("J_pair",     (150.0,  "mm", "J-bolt spacing within one block", "Drawing AL-001 sh.1/2", "V")),
 ("J_mid",      (550.0,  "mm", "Clear spacing between J-bolt pairs (block to block)", "Drawing AL-001 sh.2", "V")),
 ("edge_min",   (22.5,   "mm", "Smaller edge distance of bolt holes (gauge 22.5/27.5)", "Drawing AL-001 sh.2", "V")),
 ("block_w",    (300.0,  "mm", "Ballast block width (along slope)", "Drawing AL-001 sh.1", "V")),
 ("block_h",    (250.0,  "mm", "Ballast block height", "Drawing AL-001 sh.1", "V")),
 ("block_L",    (650.0,  "mm", "Ballast block length across frame - PROVIDED (not on drawing)", "Design output, see Ballast sheet", "I")),
 ("J_gauge",   (27.5,   "mm", "Gauge of J-bolt hole from heel (horizontal leg)", "Drawing AL-001 sh.2 (27.5/22.5)", "V")),
 ("slot_cc_dwg",(1088.0, "mm", "Module slot c/c as drawn (cross-check)", "Drawing AL-001 sh.2", "V")),
 ("bolt_h",     (27.5,   "mm", "Height of frame bolt line above block top (gauge from heel)", "Standard gauge for 50 leg (assumed)", "I")),
 ("wind_mode", (0, "0/1", "Module wind transfer to rafter: 0 = at the 4 module bolts (point loads); 1 = UDL over module contact length", "Design choice (R1); alt run provided", "I")),
 ("e_mod",      (25.0,   "mm", "Module mid-plane offset from inclined-member bolt line", "t_leg + t_mod/2 (assumed)", "I")),
 # ---- module ------------------------------------------------------------------------
 ("mod_L",  (2279.0, "mm", "Module length", "550 Wp mono-PERC datasheets (search) ", "I")),
 ("mod_W",  (1134.0, "mm", "Module width", "550 Wp mono-PERC datasheets (search)", "I")),
 ("mod_t",  (35.0,   "mm", "Module frame thickness", "550 Wp mono-PERC datasheets (search)", "I")),
 ("mod_kg", (29.1,   "kg", "Module weight", "Indosol 550 Wp datasheet (search summary, single source)", "I")),
 ("frame_sp",(1400.0,"mm", "Frame-to-frame spacing = module hole pitch (long side)", "Datasheet hole pitch 1400; slot geometry matches", "I")),
 # ---- site / wind (IS 875 Pt 3) -------------------------------------------------------
 ("Vb",     (44.0, "m/s", "Basic wind speed, Hyderabad", "IS 875-3 Annex A (search-confirmed)", "V")),
 ("k1_risk",(0.91, "-",   "Risk coefficient, 25-yr life (house value from issued ground-mount jobs)", "Skill template; IS 875-3 Table 1", "I")),
 ("terrain",(2,    "cat", "Terrain category (2 conservative; 3 = dense urban)", "Assumed - conservative", "I")),
 ("k3_topo",(1.0,  "-",   "Topography factor", "IS 875-3 cl 6.3.3", "I")),
 ("k4_imp", (1.0,  "-",   "Cyclonic importance factor (non-cyclonic)", "IS 875-3 cl 6.3.4", "I")),
 ("Kd_dir", (0.9,  "-",   "Wind directionality factor", "IS 875-3 cl 7.2.1 (search-confirmed)", "V")),
 ("Ka_area",(1.0,  "-",   "Area averaging factor (A <= 10 m2)", "IS 875-3 cl 7.2.2 (search-confirmed)", "V")),
 ("Kc_comb",(1.0,  "-",   "Combination factor (net Cp used, so 1.0)", "House practice", "I")),
 ("z_bldg", (12.0, "m",   "Roof level above ground (3-storey bldg, assumed)", "Assumed", "I")),
 # ---- seismic (IS 1893 Pt 1:2016) -----------------------------------------------------
 ("Zf",   (0.10, "-", "Zone factor, Hyderabad = Zone II", "IS 1893-1:2016 Table 3 (recall)", "I")),
 ("I_imp",(1.0,  "-", "Importance factor", "Assumed", "I")),
 ("SaG",  (2.5,  "-", "Sa/g (rigid, T < 0.4 s)", "IS 1893-1:2016 cl 6.4.2 (recall)", "I")),
 ("Rp",   (2.5,  "-", "Component response reduction (ap=1)", "ASCE-type form; IS clause not retrievable offline", "I")),
 ("zh",   (1.0,  "-", "z/h of attachment (roof level)", "Roof-mounted", "V")),
 # ---- materials / partial factors (IS 800:2007) ---------------------------------------
 ("fy",   (250.0, "MPa", "Yield strength, IS 2062 E250, t<=20", "IS 2062 (assumed grade)", "I")),
 ("fu",   (410.0, "MPa", "Ultimate strength", "IS 2062 E250", "I")),
 ("Es",   (200000.0, "MPa", "Young's modulus", "IS 800 cl 2.2.4.1", "V")),
 ("gamma_m0",  (1.10, "-", "Partial factor, yielding", "IS 800 Table 5", "V")),
 ("gamma_m1",  (1.25, "-", "Partial factor, ultimate", "IS 800 Table 5", "V")),
 ("gamma_mb",  (1.25, "-", "Partial factor, bolts", "IS 800 Table 5", "V")),
 ("gam_s",(78.5, "kN/m3", "Unit weight of steel", "IS 875-1 Table 1", "V")),
 ("gacc", (9.81, "m/s2", "Gravity", "-", "V")),
 ("fub88",(800.0, "MPa", "Bolt class 8.8 fub", "IS 1367 / IS 800", "V")),
 ("fyb88",(640.0, "MPa", "Bolt class 8.8 fyb", "IS 1367 / IS 800", "V")),
 ("fub_ss",(700.0,"MPa", "SS-304 bolt, class A2-70 fub (BOM gives no class)", "ISO 3506-1 (assumed class)", "I")),
 ("fyb_ss",(450.0,"MPa", "SS-304 bolt, class A2-70 fyb", "ISO 3506-1 (assumed class)", "I")),
 ("k_over",(0.7,  "-", "Bearing reduction, oversize / short-slot holes", "IS 800 cl 10.3.4 (search-confirmed)", "V")),
 ("d0_14", (14.0, "mm", "Hole dia for M10/M12 bolts (drawing)", "Drawing AL-001 sh.2", "V")),
 ("d0_J",  (18.0, "mm", "Hole dia for J-bolts (drawing)", "Drawing AL-001 sh.2", "V")),
 ("d0_M8", (9.0,  "mm", "Slot width for M8 module bolts (9x14 slot)", "Drawing AL-001 sh.2", "V")),
 # ---- concrete / ballast ----------------------------------------------------------------
 ("gam_c", (24.0, "kN/m3", "Unit weight of plain concrete", "IS 875-1 Table 1", "V")),
 ("fck",   (20.0, "MPa", "Block concrete grade (M20)", "Assumed", "I")),
 ("mu_f",  (0.4,  "-", "Friction coeff. concrete block / roof surface", "SEAOC PV2 conservative value (search)", "I")),
 ("dl_stab",(0.9, "-", "DL factor when stabilising", "IS 800 Table 4 (search-confirmed)", "V")),
 ("ll_fac", (1.5, "-", "Wind/EQ load factor with stabilising DL", "IS 800 Table 4", "V")),
 ("defl_div",(180.0,"-", "Deflection limit = L/180 (brittle glass cladding)", "IS 800 Table 6 (recall)", "I")),
])

# IS 875 Pt 3 Table 7, mono-slope free roof, solidity 0: angle -> (max down Cp, min uplift Cp)
T7 = [(0, 0.2, -0.5), (5, 0.4, -0.7), (10, 0.5, -0.9), (15, 0.7, -1.1),
      (20, 0.8, -1.3), (25, 1.0, -1.6), (30, 1.2, -1.8)]
# IS 875 Pt 3 Table 2 k2: height -> {category: k2}
K2 = [(10, {2: 1.00, 3: 0.91}), (15, {2: 1.05, 3: 0.97}), (20, {2: 1.07, 3: 1.01})]
# IS 456 Table 26.2.1.1 design bond stress, plain bars in tension
TAUBD = {20: 1.2, 25: 1.4, 30: 1.5, 35: 1.7, 40: 1.9}
# Bolt data: name -> (d, An tensile stress area, Asb shank area)
BOLTS = OD([("M8", (8, 36.6, 50.27)), ("M10", (10, 58.0, 78.54)), ("M12", (12, 84.3, 113.1)), ("M16", (16, 157.0, 201.06))])
# ISA 50x50x5 (exact polygon integration, r1=7, r2=3.5) - section_isa.py
SEC = dict(A=480.3, cx=14.04, Ixx=109643.0, Iyy=109643.0, Ixy=-64173.0, Iuu=173816.0, Ivv=45469.0,
           b=50.0, t=5.0, r1=7.0, r2=3.5)
