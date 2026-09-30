"""ISA equal-angle properties by exact polygon integration (root r1, toe r2 fillets). Units mm.
Independent cross-check of the IS 808 catalogue values used in the workbook."""
import numpy as np


def outline(b=50.0, t=5.0, r1=7.0, r2=3.5, n=400):
    """CCW outline; heel at (0,0); horizontal leg along +x, vertical leg along +y."""
    P = [(0, 0), (b, 0), (b, t - r2)]
    a = np.linspace(0, np.pi/2, n)
    P += [(b - r2 + r2*np.cos(u), t - r2 + r2*np.sin(u)) for u in a]          # toe of horizontal leg
    P += [(t + r1, t)]
    a = np.linspace(-np.pi/2, -np.pi, n)
    P += [(t + r1 + r1*np.cos(u), t + r1 + r1*np.sin(u)) for u in a]          # root fillet
    P += [(t, b - r2)]
    a = np.linspace(0, np.pi/2, n)
    P += [(t - r2 + r2*np.cos(u), b - r2 + r2*np.sin(u)) for u in a]          # toe of vertical leg
    P += [(0, b)]
    return np.array(P)


def polyprops(P):
    x, y = P[:, 0], P[:, 1]
    x1, y1 = np.roll(x, -1), np.roll(y, -1)
    c = x*y1 - x1*y
    A = c.sum()/2
    cx = ((x + x1)*c).sum()/(6*A)
    cy = ((y + y1)*c).sum()/(6*A)
    Ixx = ((y*y + y*y1 + y1*y1)*c).sum()/12 - A*cy*cy
    Iyy = ((x*x + x*x1 + x1*x1)*c).sum()/12 - A*cx*cx
    Ixy = ((x*y1 + 2*x*y + 2*x1*y1 + x1*y)*c).sum()/24 - A*cx*cy
    return dict(A=A, cx=cx, cy=cy, Ixx=Ixx, Iyy=Iyy, Ixy=Ixy)


def principal(p):
    Ixx, Iyy, Ixy = p["Ixx"], p["Iyy"], p["Ixy"]
    avg, R = (Ixx + Iyy)/2, np.hypot((Ixx - Iyy)/2, Ixy)
    return avg + R, avg - R          # Iuu (max), Ivv (min)


if __name__ == "__main__":
    P = outline()
    p = polyprops(P)
    Iu, Iv = principal(p)
    print("A=%.1f mm2  cx=cy=%.2f mm  Ixx=%.0f Iyy=%.0f Ixy=%.0f mm4" % (p["A"], p["cx"], p["Ixx"], p["Iyy"], p["Ixy"]))
    print("Iuu=%.0f Ivv=%.0f  ruu=%.2f rvv=%.2f mm  mass=%.3f kg/m" % (Iu, Iv, (Iu/p["A"])**.5, (Iv/p["A"])**.5, p["A"]*1e-6*7850))
    # sharp-corner check (no fillets) - should be A=475
    Q = polyprops(outline(r1=1e-9, r2=1e-9, n=2))
    print("sharp-corner: A=%.1f cx=%.2f Ixx=%.0f" % (Q["A"], Q["cx"], Q["Ixx"]))
