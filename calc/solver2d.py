"""Minimal 2D frame direct-stiffness solver (beam + truss elements, end moment releases, UDL with axial+transverse parts).
Independent of the closed-form statics used in the Excel workbook -> used to cross-check it.
Units: N, mm.  Sign: x right, y up, rotation CCW positive."""
import numpy as np


class Frame2D:
    def __init__(self):
        self.nodes, self.elems, self.supports = {}, [], {}
        self.order = []

    def node(self, name, x, y):
        self.nodes[name] = (float(x), float(y)); self.order.append(name)

    def beam(self, name, n1, n2, EA, EI, rel1=False, rel2=False):
        self.elems.append(dict(name=name, n1=n1, n2=n2, kind="beam", EA=EA, EI=EI, rel1=rel1, rel2=rel2))

    def truss(self, name, n1, n2, EA):
        self.elems.append(dict(name=name, n1=n1, n2=n2, kind="truss", EA=EA, EI=0, rel1=False, rel2=False))

    def support(self, n, ux=True, uy=True, rz=False):
        self.supports[n] = (ux, uy, rz)

    # -- element matrices ------------------------------------------------------------
    def _geom(self, e):
        x1, y1 = self.nodes[e["n1"]]; x2, y2 = self.nodes[e["n2"]]
        L = np.hypot(x2 - x1, y2 - y1); c, s = (x2 - x1)/L, (y2 - y1)/L
        T = np.zeros((6, 6)); R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])
        T[:3, :3] = R; T[3:, 3:] = R
        return L, T

    def _klocal(self, e, L):
        EA, EI = e["EA"], e["EI"]; k = np.zeros((6, 6))
        a = EA/L; k[0, 0] = k[3, 3] = a; k[0, 3] = k[3, 0] = -a
        if e["kind"] == "beam":
            b = 12*EI/L**3; c = 6*EI/L**2; d = 4*EI/L; f = 2*EI/L
            k[1, 1] = k[4, 4] = b; k[1, 4] = k[4, 1] = -b
            k[1, 2] = k[2, 1] = c; k[1, 5] = k[5, 1] = c
            k[2, 4] = k[4, 2] = -c; k[4, 5] = k[5, 4] = -c
            k[2, 2] = k[5, 5] = d; k[2, 5] = k[5, 2] = f
        return k

    def _condense(self, k, f, rel):
        for r in rel:
            kr = k[:, r].copy(); krr = k[r, r]
            f = f - kr*f[r]/krr
            k = k - np.outer(kr, k[r, :])/krr
            k[r, :] = 0; k[:, r] = 0; f[r] = 0
        return k, f

    def local_udl(self, name, qx, qy):
        """global distributed load vector (N/mm of member length) -> (axial, transverse) local components"""
        e = [x for x in self.elems if x["name"] == name][0]
        x1, y1 = self.nodes[e["n1"]]; x2, y2 = self.nodes[e["n2"]]; L = np.hypot(x2 - x1, y2 - y1); c, s = (x2 - x1)/L, (y2 - y1)/L
        return (qx*c + qy*s, -qx*s + qy*c)

    def solve(self, nodal, udl=None):
        """nodal: {node:(Fx,Fy,M)} ; udl: {elem_name: q_local_y or (q_axial, q_transverse)} (N/mm) -> results dict"""
        udl = udl or {}; idx = {n: i for i, n in enumerate(self.order)}; N = 3*len(self.order)
        K = np.zeros((N, N)); F = np.zeros(N); store = {}
        for n, (fx, fy, m) in nodal.items():
            i = idx[n]; F[3*i:3*i+3] += [fx, fy, m]
        for e in self.elems:
            L, T = self._geom(e); k = self._klocal(e, L); f0 = np.zeros(6)
            q = udl.get(e["name"], 0.0)
            qa, qy = (q if isinstance(q, tuple) else (0.0, q))                    # local axial, local transverse (N/mm)
            if (qa or qy) and e["kind"] == "beam":
                f0 = np.array([qa*L/2, qy*L/2, qy*L**2/12, qa*L/2, qy*L/2, -qy*L**2/12])
            rel = ([2] if e["rel1"] else []) + ([5] if e["rel2"] else [])
            k, f0 = self._condense(k, f0, rel)
            kg = T.T @ k @ T; fg = T.T @ f0
            d = [3*idx[e["n1"]] + j for j in range(3)] + [3*idx[e["n2"]] + j for j in range(3)]
            K[np.ix_(d, d)] += kg; F[d] += fg
            store[e["name"]] = (k, f0, T, d, L, e)
        # truss-only nodes: rotation dof has no stiffness -> fix it
        fixed = set()
        for n, (ux, uy, rz) in self.supports.items():
            i = idx[n]
            if ux: fixed.add(3*i)
            if uy: fixed.add(3*i + 1)
            if rz: fixed.add(3*i + 2)
        for i in range(len(self.order)):
            if abs(K[3*i+2, 3*i+2]) < 1e-9: fixed.add(3*i + 2)
        free = [i for i in range(N) if i not in fixed]
        u = np.zeros(N)
        u[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
        R = K @ u - F
        out = dict(u={n: u[3*i:3*i+3] for n, i in idx.items()},
                   R={n: R[3*idx[n]:3*idx[n]+3] for n in self.supports}, elems={})
        for name, (k, f0, T, d, L, e) in store.items():
            fl = k @ (T @ u[d]) - f0               # local end forces on element
            # local axial tension = F_x at end 2 ; M sagging at end = -M1 (end1) / +M2 (end2) for CCW-positive end moments
            out["elems"][name] = dict(N=fl[3], V1=fl[1], V2=fl[4], M1=-fl[2], M2=fl[5], L=L, fl=fl)
        return out
