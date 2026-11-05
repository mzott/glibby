#!/usr/bin/env python3
"""
glibby_cli.py — Pure-Python CLI for converting single-frame or multi-frame .xyz
molecular files into PowerPoint-compatible 3D .glb models (static or bone-skinned animated)
with ChimeraX SEQROW ball-stick-endcap styling and customizable color palettes.
"""

import argparse
import json
import math
import os
import struct
import sys

BOND_RADIUS = 0.16
COORD_BOND_RADIUS = 0.125

def srgb_to_linear(c):
    """Convert 0-255 sRGB channel to 0.0-1.0 linear RGB for glTF 2.0 baseColorFactor."""
    v = max(0.0, min(255.0, float(c))) / 255.0
    if v <= 0.04045:
        return v / 12.92
    return ((v + 0.055) / 1.055) ** 2.4

def rgba_from_rgb255(r, g, b):
    return (srgb_to_linear(r), srgb_to_linear(g), srgb_to_linear(b), 1.0)

# Base element definitions: symbol -> (covalent_radius, sphere_radius, zott_rgb255, chimerax_rgb255)
ELEMENT_SPECS = {
    'H':  (0.31, BOND_RADIUS, (248, 248, 248), (248, 248, 248)),
    'B':  (0.84, 0.34,        (255, 181, 181), (255, 181, 181)),
    'C':  (0.76, 0.34,        (143, 143, 143), (143, 143, 143)),
    'N':  (0.71, 0.34,        (0, 68, 134),    (31, 71, 235)),
    'O':  (0.66, 0.34,        (240, 25, 25),   (240, 25, 25)),
    'F':  (0.57, 0.32,        (144, 224, 80),  (144, 224, 80)),
    'Si': (1.11, 0.42,        (240, 200, 160), (240, 200, 160)),
    'P':  (1.07, 0.40,        (255, 128, 0),   (255, 128, 0)),
    'S':  (1.05, 0.40,        (255, 200, 50),  (255, 200, 50)),
    'Cl': (1.02, 0.38,        (31, 240, 31),   (31, 240, 31)),
    'Br': (1.20, 0.42,        (166, 41, 41),   (166, 41, 41)),
    'I':  (1.39, 0.45,        (148, 0, 148),   (148, 0, 148)),
    'Fe': (1.32, 0.48,        (153, 119, 0),   (224, 107, 36)),
    'Co': (1.26, 0.48,        (240, 144, 160), (240, 144, 160)),
    'Ni': (1.24, 0.48,        (80, 208, 80),   (80, 208, 80)),
    'Cu': (1.32, 0.48,        (200, 128, 51),  (200, 128, 51)),
    'Zn': (1.22, 0.48,        (125, 128, 176), (125, 128, 176)),
    'Ru': (1.46, 0.50,        (36, 143, 143),  (36, 143, 143)),
    'Pd': (1.39, 0.50,        (0, 105, 133),   (0, 105, 133)),
    'Pt': (1.36, 0.50,        (208, 208, 224), (208, 208, 224)),
    'Mo': (1.54, 0.50,        (84, 181, 181),  (84, 181, 181)),
    'Mn': (1.39, 0.48,        (156, 122, 199), (156, 122, 199)),
    'Cr': (1.39, 0.48,        (138, 153, 199), (138, 153, 199)),
    'CoordBond': (0.0, 0.0,   (135, 175, 235), (143, 176, 245)),
}
DEFAULT_SPEC = (1.20, 0.38, (204, 51, 204), (204, 51, 204))
METALS = {'Fe', 'Co', 'Ni', 'Cu', 'Zn', 'Ru', 'Rh', 'Pd', 'Ir', 'Pt', 'Mo', 'W', 'Mn', 'Cr', 'V', 'Ti', 'Sc', 'Au', 'Ag', 'Mg', 'Ca', 'Al'}

def get_palette_elements(palette_name='zott', color_overrides=None):
    """Returns dict: el -> (linear_rgba, r_cov, r_sphere, rgb255)."""
    overrides = {}
    if color_overrides:
        for item in color_overrides:
            if '=' not in item:
                raise ValueError(f"Invalid --color format '{item}'. Expected EL=R,G,B (e.g. N=0,68,134).")
            el_key, rgb_str = item.split('=', 1)
            el_key = el_key.strip()
            parts = [int(x.strip()) for x in rgb_str.split(',')]
            if len(parts) != 3 or any(p < 0 or p > 255 for p in parts):
                raise ValueError(f"Invalid RGB values in '{item}'. Must be three integers 0..255.")
            overrides[el_key] = tuple(parts)

    result = {}
    all_keys = set(ELEMENT_SPECS.keys()) | set(overrides.keys())
    for k in all_keys:
        rcov, rsphere, zott_rgb, chimerax_rgb = ELEMENT_SPECS.get(k, DEFAULT_SPEC)
        rgb255 = zott_rgb if palette_name == 'zott' else chimerax_rgb
        if k in overrides:
            rgb255 = overrides[k]
        result[k] = (rgba_from_rgb255(*rgb255), rcov, rsphere, rgb255)
    return result

PERIODIC = ['H','He','Li','Be','B','C','N','O','F','Ne','Na','Mg','Al','Si','P','S','Cl','Ar','K','Ca','Sc','Ti','V','Cr','Mn','Fe','Co','Ni','Cu','Zn','Ga','Ge','As','Se','Br','Kr','Rb','Sr','Y','Zr','Nb','Mo','Tc','Ru','Rh','Pd','Ag','Cd','In','Sn','Sb','Te','I','Xe','Cs','Ba','La','Ce','Pr','Nd','Pm','Sm','Eu','Gd','Tb','Dy','Ho','Er','Tm','Yb','Lu','Hf','Ta','W','Re','Os','Ir','Pt','Au','Hg','Tl','Pb','Bi','Po','At','Rn','Fr','Ra','Ac','Th','Pa','U','Np','Pu','Am','Cm','Bk','Cf','Es','Fm','Md','No','Lr','Rf','Db','Sg','Bh','Hs','Mt','Ds','Rg','Cn','Nh','Fl','Mc','Lv','Ts','Og']


class AtomicNumberError(ValueError):
    """Raised when an .xyz file uses atomic numbers and conversion was not requested."""


def normalize_element(raw, line_no, convert_atomic_numbers=False):
    """Normalize element case ('fe', 'FE' -> 'Fe'); convert atomic numbers only on request."""
    if raw.isdigit():
        z = int(raw)
        if not 1 <= z <= len(PERIODIC):
            raise ValueError(f"Line {line_no}: {raw!r} is not a valid atomic number.")
        if not convert_atomic_numbers:
            raise AtomicNumberError(
                f"Line {line_no}: element is given as atomic number {raw!r}. If this file uses atomic "
                f"numbers instead of element symbols, re-run with --atomic-numbers-to-symbols.")
        return PERIODIC[z - 1]
    if not (raw.isalpha() and 1 <= len(raw) <= 3):
        raise ValueError(f"Line {line_no}: {raw!r} is not an element symbol.")
    return raw[0].upper() + raw[1:].lower()


def parse_coord(token, line_no):
    try:
        v = float(token.replace('d', 'e').replace('D', 'e'))
    except ValueError:
        raise ValueError(f"Line {line_no}: coordinate {token!r} is not a number.") from None
    if not math.isfinite(v):
        raise ValueError(f"Line {line_no}: coordinate {token!r} is not a finite number.")
    return v


def parse_xyz(filepath, convert_atomic_numbers=False):
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Input XYZ file not found: {filepath}")
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        lines = [line.strip() for line in f.readlines()]
    
    # Filter trailing blank lines while keeping structure
    while lines and not lines[-1]:
        lines.pop()

    frames = []
    idx = 0
    while idx < len(lines):
        if not lines[idx]:
            idx += 1
            continue
        try:
            n_atoms = int(lines[idx])
        except ValueError as e:
            raise ValueError(f"Expected atom count integer at line {idx+1} of {filepath}, got: {lines[idx]!r}") from e
        if idx + 1 + n_atoms >= len(lines):
            raise ValueError(f"Truncated XYZ frame starting at line {idx+1} in {filepath}.")
        comment = lines[idx + 1]
        atoms = []
        for i in range(n_atoms):
            parts = lines[idx + 2 + i].split()
            if len(parts) < 4:
                raise ValueError(f"Malformed atom line at {idx + 3 + i}: {lines[idx + 2 + i]!r}")
            line_no = idx + 3 + i
            el = normalize_element(parts[0], line_no, convert_atomic_numbers)
            x, y, z = (parse_coord(t, line_no) for t in parts[1:4])
            atoms.append((el, (x, y, z)))
        if frames and len(atoms) != len(frames[0][1]):
            raise ValueError(f"Inconsistent atom count across frames: frame 0 has {len(frames[0][1])}, frame {len(frames)} has {len(atoms)}.")
        if frames:
            for k, ((el_new, _), (el_ref, _)) in enumerate(zip(atoms, frames[0][1])):
                if el_new != el_ref:
                    raise ValueError(f"Atom order differs across frames: atom {k+1} is {el_new} in frame {len(frames)} but {el_ref} in frame 0.")
        frames.append((comment, atoms))
        idx += 2 + n_atoms
    if not frames:
        raise ValueError(f"No valid XYZ frames found in {filepath}.")
    return frames

def vec_sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def vec_len(v):
    return math.sqrt(v[0]*v[0] + v[1]*v[1] + v[2]*v[2])

def quat_from_y_axis(diff):
    d = vec_len(diff)
    if d < 1e-8:
        return (0.0, 0.0, 0.0, 1.0)
    dx, dy, dz = diff[0]/d, diff[1]/d, diff[2]/d
    if dy < -0.999999:
        return (1.0, 0.0, 0.0, 0.0)
    w = 1.0 + dy
    qx, qy, qz = dz, 0.0, -dx
    norm = math.sqrt(qx*qx + qy*qy + qz*qz + w*w)
    return (qx/norm, qy/norm, qz/norm, w/norm)

def analyze_bonds(frames, elem_map, dynamic_mode='include', add_bonds=None, remove_bonds=None):
    """
    Analyzes all pairwise distances across frames.
    Returns (bonds, static_bonds_info, dynamic_bonds_info)
    where each item in bonds is (i, j, dmin, dmax, cutoff, is_dynamic, is_coord).
    """
    n_atoms = len(frames[0][1])
    elements = [a[0] for a in frames[0][1]]

    add_set = set()
    if add_bonds:
        for pair in add_bonds:
            a, b = [int(x) - 1 for x in pair.split('-')]
            add_set.add((min(a, b), max(a, b)))

    rem_set = set()
    if remove_bonds:
        for pair in remove_bonds:
            a, b = [int(x) - 1 for x in pair.split('-')]
            rem_set.add((min(a, b), max(a, b)))

    bonds = []
    static_info = []
    dynamic_info = []

    for i in range(n_atoms):
        for j in range(i + 1, n_atoms):
            if (i, j) in rem_set:
                continue
            el_i, el_j = elements[i], elements[j]
            rcov_i = elem_map.get(el_i, (None, DEFAULT_SPEC[0]))[1]
            rcov_j = elem_map.get(el_j, (None, DEFAULT_SPEC[0]))[1]
            is_coord = (el_i in METALS or el_j in METALS)

            cutoff = (rcov_i + rcov_j) * 1.22
            if is_coord:
                # Coordinate metals to N, O, P, S, halides, etc., avoid spurious M-C or M-H unless close
                other = el_j if el_i in METALS else el_i
                if other == 'H':
                    cutoff = 1.75
                elif other == 'C':
                    cutoff = 2.15
                else:
                    cutoff = 2.40
            elif el_i == 'H' and el_j == 'H':
                cutoff = 0.95
            elif 'H' in (el_i, el_j):
                cutoff = 1.30

            dists = [vec_len(vec_sub(atoms[j][1], atoms[i][1])) for _, atoms in frames]
            dmin, dmax = min(dists), max(dists)
            d0 = dists[0]

            forced = (i, j) in add_set
            if dmin <= cutoff or forced:
                # A bond is dynamic if it stretches across the cutoff or changes length by > 0.35 A
                is_dyn = (dmax > cutoff and dmin <= cutoff) or ((dmax - dmin) > 0.35)
                info_entry = {
                    "atoms_1based": [i + 1, j + 1],
                    "labels": f"{el_i}{i+1}-{el_j}{j+1}",
                    "d_min_A": round(dmin, 3),
                    "d_max_A": round(dmax, 3),
                    "d_frame0_A": round(d0, 3),
                    "cutoff_A": round(cutoff, 3),
                    "type": "coordination" if is_coord else "covalent"
                }
                if is_dyn:
                    dynamic_info.append(info_entry)
                else:
                    static_info.append(info_entry)

                if dynamic_mode == 'exclude' and is_dyn and not forced and d0 > cutoff:
                    continue
                bonds.append((i, j, dmin, dmax, cutoff, is_dyn, is_coord))

    return bonds, static_info, dynamic_info

def generate_uv_sphere(radius, rings=16, sectors=24):
    """Outward CCW-wound UV sphere."""
    positions = []
    normals = []
    indices = []
    for r in range(rings + 1):
        theta = r * math.pi / rings
        sin_t = math.sin(theta)
        cos_t = math.cos(theta)
        for s in range(sectors + 1):
            phi = s * 2 * math.pi / sectors
            nx = sin_t * math.cos(phi)
            ny = cos_t
            nz = sin_t * math.sin(phi)
            normals.append((nx, ny, nz))
            positions.append((nx * radius, ny * radius, nz * radius))
    
    for r in range(rings):
        for s in range(sectors):
            first = r * (sectors + 1) + s
            second = first + sectors + 1
            indices.extend([first, first + 1, second])
            indices.extend([second, first + 1, second + 1])
    return positions, normals, indices

def generate_cylinder(radius, y_min=0.0, y_max=1.0, sectors=20):
    """Outward CCW-wound cylinder along +Y."""
    positions = []
    normals = []
    indices = []
    for y in (y_min, y_max):
        for s in range(sectors + 1):
            phi = s * 2 * math.pi / sectors
            nx = math.cos(phi)
            nz = math.sin(phi)
            normals.append((nx, 0.0, nz))
            positions.append((nx * radius, y, nz * radius))
    
    for s in range(sectors):
        first = s
        second = s + (sectors + 1)
        indices.extend([first, second, first + 1])
        indices.extend([second, second + 1, first + 1])
    return positions, normals, indices

MAX_VERTS_PER_PRIMITIVE = 65535  # keeps every primitive addressable with 16-bit indices (widest compatibility)


def split_geometry(g, max_verts=MAX_VERTS_PER_PRIMITIVE):
    """Split one material's geometry into chunks of at most max_verts vertices.

    Spheres and cylinders are appended as contiguous vertex blocks whose triangles only
    reference their own block, so a chunk can always start at the lowest vertex any
    remaining triangle uses. Returns a list of dicts with the same keys as g and
    indices rebased to each chunk.
    """
    n = len(g["pos"])
    if n <= max_verts:
        return [g]
    ind = g["ind"]
    tris = [ind[t:t + 3] for t in range(0, len(ind), 3)]
    suffix_min = [0] * len(tris)
    m = n
    for t in range(len(tris) - 1, -1, -1):
        m = min(m, min(tris[t]))
        suffix_min[t] = m
    chunks, start_tri, v0 = [], 0, suffix_min[0]

    def emit(t_end, v0):
        v1 = max(max(tr) for tr in tris[start_tri:t_end]) + 1
        chunks.append({
            "pos": g["pos"][v0:v1], "norm": g["norm"][v0:v1],
            "joints": g["joints"][v0:v1], "weights": g["weights"][v0:v1],
            "ind": [i - v0 for tr in tris[start_tri:t_end] for i in tr],
        })

    for t, tr in enumerate(tris):
        if max(tr) - v0 >= max_verts:
            emit(t, v0)
            start_tri, v0 = t, suffix_min[t]
    emit(len(tris), v0)
    return chunks


MAX_BONES_PER_SKIN = 200  # PowerPoint fails above ~255 bones per skinned mesh (235 ok, 259 fails)


def quat_rotate(q, v):
    x, y, z, w = q
    vx, vy, vz = v
    tx, ty, tz = 2 * (y * vz - z * vy), 2 * (z * vx - x * vz), 2 * (x * vy - y * vx)
    return (vx + w * tx + (y * tz - z * ty), vy + w * ty + (z * tx - x * tz), vz + w * tz + (x * ty - y * tx))


def bake_point(node, p):
    """Apply a bone node's scale, rotation and translation to a vertex position."""
    s, t = node["scale"], node["translation"]
    r = quat_rotate(node["rotation"], (p[0] * s[0], p[1] * s[1], p[2] * s[2]))
    return (r[0] + t[0], r[1] + t[1], r[2] + t[2])


def bake_normal(node, n):
    """Transform a normal by a bone node (inverse-transpose of scale, then rotation)."""
    s = node["scale"]
    r = quat_rotate(node["rotation"], tuple(n[k] / max(s[k], 1e-9) for k in range(3)))
    length = math.sqrt(r[0] ** 2 + r[1] ** 2 + r[2] ** 2) or 1.0
    return (r[0] / length, r[1] / length, r[2] / length)


def subset_by_joint(g, lo, hi):
    """Triangles whose bone is in [lo, hi), with vertices re-indexed and joints rebased to lo."""
    out = {"pos": [], "norm": [], "joints": [], "weights": [], "ind": []}
    vmap = {}
    ind = g["ind"]
    for t in range(0, len(ind), 3):
        tri = ind[t:t + 3]
        if not lo <= g["joints"][tri[0]][0] < hi:
            continue
        for v in tri:
            if v not in vmap:
                vmap[v] = len(out["pos"])
                out["pos"].append(g["pos"][v])
                out["norm"].append(g["norm"][v])
                j = g["joints"][v]
                out["joints"].append((j[0] - lo, 0, 0, 0))
                out["weights"].append(g["weights"][v])
            out["ind"].append(vmap[v])
    return out


def build_glb(xyz_path, glb_path, palette='zott', color_overrides=None, fps=12.0, loop_mode='auto',
              dynamic_bonds='include', add_bonds=None, remove_bonds=None, convert_atomic_numbers=False):
    raw_frames = parse_xyz(xyz_path, convert_atomic_numbers)
    elem_map = get_palette_elements(palette, color_overrides)
    bonds, static_info, dynamic_info = analyze_bonds(
        raw_frames, elem_map, dynamic_mode=dynamic_bonds, add_bonds=add_bonds, remove_bonds=remove_bonds
    )

    # Determine frame sequence based on loop_mode and frame count
    n_raw = len(raw_frames)
    is_stationary = (n_raw == 1)

    if is_stationary:
        frames = raw_frames
        effective_loop = 'stationary'
    else:
        if loop_mode == 'auto':
            # Check RMSD between frame 0 and frame -1
            n_atoms_check = len(raw_frames[0][1])
            rmsd_sq = sum(
                vec_len(vec_sub(raw_frames[0][1][k][1], raw_frames[-1][1][k][1])) ** 2
                for k in range(n_atoms_check)
            ) / n_atoms_check
            if math.sqrt(rmsd_sq) < 0.05:
                effective_loop = 'cycle'
            else:
                effective_loop = 'ping-pong'
        else:
            effective_loop = loop_mode

        if effective_loop == 'ping-pong' and n_raw > 2:
            frames = raw_frames + raw_frames[-2:0:-1]
        else:
            frames = raw_frames

    n_frames = len(frames)
    n_atoms = len(frames[0][1])
    elements = [a[0] for a in frames[0][1]]
    n_bonds = len(bonds)
    n_joints = n_atoms + n_bonds

    # Center coordinates around frame 0 centroid
    cx = sum(a[1][0] for a in frames[0][1]) / n_atoms
    cy = sum(a[1][1] for a in frames[0][1]) / n_atoms
    cz = sum(a[1][2] for a in frames[0][1]) / n_atoms

    centered_frames = []
    for comment, atoms in frames:
        c_atoms = [(el, (x - cx, y - cy, z - cz)) for el, (x, y, z) in atoms]
        centered_frames.append(c_atoms)

    mat_keys = sorted(list(set(elements))) + ['CoordBond']
    elem_geom = {
        k: {"pos": [], "norm": [], "joints": [], "weights": [], "ind": []}
        for k in mat_keys
    }

    # Generate unit meshes in bone-local origin space (rigged to joints)
    for a_idx in range(n_atoms):
        el = elements[a_idx]
        _, _, rad, _ = elem_map.get(el, get_palette_elements(palette)['C'])
        s_pos, s_norm, s_ind = generate_uv_sphere(rad, rings=16, sectors=24)
        g = elem_geom[el]
        base_v = len(g["pos"])
        g["pos"].extend(s_pos)
        g["norm"].extend(s_norm)
        g["joints"].extend([(a_idx, 0, 0, 0)] * len(s_pos))
        g["weights"].extend([(1.0, 0.0, 0.0, 0.0)] * len(s_pos))
        g["ind"].extend([base_v + idx for idx in s_ind])

    cyl_bot_pos, cyl_bot_norm, cyl_bot_ind = generate_cylinder(radius=BOND_RADIUS, y_min=0.0, y_max=0.5, sectors=20)
    cyl_top_pos, cyl_top_norm, cyl_top_ind = generate_cylinder(radius=BOND_RADIUS, y_min=0.5, y_max=1.0, sectors=20)
    coord_cyl_pos, coord_cyl_norm, coord_cyl_ind = generate_cylinder(radius=COORD_BOND_RADIUS, y_min=0.0, y_max=1.0, sectors=20)

    for b_idx, (i, j, dmin, dmax, cutoff, is_dyn, is_coord) in enumerate(bonds):
        joint_idx = n_atoms + b_idx
        el_i = elements[i]
        el_j = elements[j]

        if is_coord:
            gc = elem_geom['CoordBond']
            base_vc = len(gc["pos"])
            gc["pos"].extend(coord_cyl_pos)
            gc["norm"].extend(coord_cyl_norm)
            gc["joints"].extend([(joint_idx, 0, 0, 0)] * len(coord_cyl_pos))
            gc["weights"].extend([(1.0, 0.0, 0.0, 0.0)] * len(coord_cyl_pos))
            gc["ind"].extend([base_vc + idx for idx in coord_cyl_ind])
        else:
            gi = elem_geom[el_i]
            base_vi = len(gi["pos"])
            gi["pos"].extend(cyl_bot_pos)
            gi["norm"].extend(cyl_bot_norm)
            gi["joints"].extend([(joint_idx, 0, 0, 0)] * len(cyl_bot_pos))
            gi["weights"].extend([(1.0, 0.0, 0.0, 0.0)] * len(cyl_bot_pos))
            gi["ind"].extend([base_vi + idx for idx in cyl_bot_ind])

            gj = elem_geom[el_j]
            base_vj = len(gj["pos"])
            gj["pos"].extend(cyl_top_pos)
            gj["norm"].extend(cyl_top_norm)
            gj["joints"].extend([(joint_idx, 0, 0, 0)] * len(cyl_top_pos))
            gj["weights"].extend([(1.0, 0.0, 0.0, 0.0)] * len(cyl_top_pos))
            gj["ind"].extend([base_vj + idx for idx in cyl_top_ind])

    bin_data = bytearray()
    buffer_views = []
    accessors = []

    def align4(ba):
        while len(ba) % 4 != 0:
            ba.append(0)

    def add_accessor(data_bytes, component_type, count, acc_type, target=None, min_val=None, max_val=None):
        align4(bin_data)
        offset = len(bin_data)
        bin_data.extend(data_bytes)
        bv = {
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(data_bytes)
        }
        if target is not None:
            bv["target"] = target
        bv_idx = len(buffer_views)
        buffer_views.append(bv)

        acc = {
            "bufferView": bv_idx,
            "byteOffset": 0,
            "componentType": component_type,
            "count": count,
            "type": acc_type
        }
        if min_val is not None:
            acc["min"] = min_val
        if max_val is not None:
            acc["max"] = max_val
        acc_idx = len(accessors)
        accessors.append(acc)
        return acc_idx

    def pack_vec3_list(v_list):
        b = bytearray()
        min_v = [float('inf')] * 3
        max_v = [float('-inf')] * 3
        for x, y, z in v_list:
            b.extend(struct.pack('<3f', x, y, z))
            if x < min_v[0]: min_v[0] = x
            if y < min_v[1]: min_v[1] = y
            if z < min_v[2]: min_v[2] = z
            if x > max_v[0]: max_v[0] = x
            if y > max_v[1]: max_v[1] = y
            if z > max_v[2]: max_v[2] = z
        return b, min_v, max_v

    def pack_vec4_float_list(v_list):
        b = bytearray()
        for x, y, z, w in v_list:
            b.extend(struct.pack('<4f', x, y, z, w))
        return b

    def pack_vec4_ushort_list(v_list):
        b = bytearray()
        for x, y, z, w in v_list:
            b.extend(struct.pack('<4H', x, y, z, w))
        return b

    def pack_indices(idx_list):
        # Always 16-bit: split_geometry keeps every primitive at <= 65,535 vertices.
        return struct.pack(f'<{len(idx_list)}H', *idx_list), 5123

    materials = []
    mat_geoms = []
    used_colors_rgb255 = {}

    for k in mat_keys:
        g = elem_geom[k]
        if not g["pos"]:
            continue
        rgba, _, _, rgb255 = elem_map.get(k, get_palette_elements(palette)['C'])
        used_colors_rgb255[k] = list(rgb255)
        mat_idx = len(materials)
        materials.append({
            "name": f"Mat_{k}",
            "alphaMode": "OPAQUE",
            "doubleSided": True,
            "pbrMetallicRoughness": {
                "baseColorFactor": list(rgba),
                "metallicFactor": 0.05,
                "roughnessFactor": 0.40
            }
        })
        mat_geoms.append((mat_idx, g))

    def add_primitives(prims, g, mat_idx, skinned):
        # Large materials are split so every primitive fits 16-bit indices.
        for g in split_geometry(g):
            pos_b, min_v, max_v = pack_vec3_list(g["pos"])
            norm_b, _, _ = pack_vec3_list(g["norm"])
            ind_b, ind_type = pack_indices(g["ind"])
            attributes = {
                "POSITION": add_accessor(pos_b, 5126, len(g["pos"]), "VEC3", target=34962, min_val=min_v, max_val=max_v),
                "NORMAL": add_accessor(norm_b, 5126, len(g["norm"]), "VEC3", target=34962),
            }
            if skinned:
                attributes["JOINTS_0"] = add_accessor(pack_vec4_ushort_list(g["joints"]), 5123, len(g["joints"]), "VEC4", target=34962)
                attributes["WEIGHTS_0"] = add_accessor(pack_vec4_float_list(g["weights"]), 5126, len(g["weights"]), "VEC4", target=34962)
            prims.append({
                "attributes": attributes,
                "indices": add_accessor(ind_b, ind_type, len(g["ind"]), "SCALAR", target=34963),
                "material": mat_idx
            })

    ident_mat4 = [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0
    ]

    joint_node_indices = list(range(3, 3 + n_joints))

    nodes = [
        {"name": "RootNode", "children": [1, 2]},
        {"name": "MoleculeMesh_1"},
        {"name": "Armature", "children": joint_node_indices}
    ]

    samplers = []
    channels = []

    if not is_stationary:
        times = [f / fps for f in range(n_frames)]
        time_b = bytearray()
        for t in times:
            time_b.extend(struct.pack('<f', t))
        time_acc = add_accessor(time_b, 5126, n_frames, "SCALAR", min_val=[times[0]], max_val=[times[-1]])

    for a_idx in range(n_atoms):
        el = elements[a_idx]
        node_idx = len(nodes)
        trans_list = [centered_frames[f][a_idx][1] for f in range(n_frames)]
        nodes.append({
            "name": f"Bone_Atom_{a_idx+1}_{el}",
            "translation": list(trans_list[0]),
            "rotation": [0.0, 0.0, 0.0, 1.0],
            "scale": [1.0, 1.0, 1.0]
        })

        if not is_stationary:
            trans_b, _, _ = pack_vec3_list(trans_list)
            trans_acc = add_accessor(trans_b, 5126, n_frames, "VEC3")
            sampler_idx = len(samplers)
            samplers.append({
                "input": time_acc,
                "interpolation": "LINEAR",
                "output": trans_acc
            })
            channels.append({
                "sampler": sampler_idx,
                "target": {"node": node_idx, "path": "translation"}
            })

    for b_idx, (i, j, dmin, dmax, cutoff, is_dyn, is_coord) in enumerate(bonds):
        el_i = elements[i]
        el_j = elements[j]
        node_idx = len(nodes)

        trans_list = []
        rot_list = []
        scale_list = []

        for f in range(n_frames):
            pi = centered_frames[f][i][1]
            pj = centered_frames[f][j][1]
            diff = vec_sub(pj, pi)
            dist = vec_len(diff)
            quat = quat_from_y_axis(diff)

            thickness = 1.0
            if is_dyn:
                # Taper dynamic bonds smoothly between equilibrium and cleavage
                full_dist = min(cutoff * 0.94, dmin * 1.16)
                break_dist = max(cutoff * 1.25, full_dist + 0.55)
                if dist <= full_dist:
                    thickness = 1.0
                elif dist >= break_dist:
                    thickness = 0.001
                else:
                    thickness = max(0.001, 1.0 - (dist - full_dist) / (break_dist - full_dist))

            trans_list.append(pi)
            rot_list.append(quat)
            scale_list.append((thickness, dist, thickness))

        nodes.append({
            "name": f"Bone_Bond_{i+1}_{j+1}",
            "translation": list(trans_list[0]),
            "rotation": list(rot_list[0]),
            "scale": list(scale_list[0])
        })

        if not is_stationary:
            t_b, _, _ = pack_vec3_list(trans_list)
            r_b = pack_vec4_float_list(rot_list)
            s_b, _, _ = pack_vec3_list(scale_list)

            t_acc = add_accessor(t_b, 5126, n_frames, "VEC3")
            r_acc = add_accessor(r_b, 5126, n_frames, "VEC4")
            s_acc = add_accessor(s_b, 5126, n_frames, "VEC3")

            s_t = len(samplers)
            samplers.append({"input": time_acc, "interpolation": "LINEAR", "output": t_acc})
            channels.append({"sampler": s_t, "target": {"node": node_idx, "path": "translation"}})

            s_r = len(samplers)
            samplers.append({"input": time_acc, "interpolation": "LINEAR", "output": r_acc})
            channels.append({"sampler": s_r, "target": {"node": node_idx, "path": "rotation"}})

            s_s = len(samplers)
            samplers.append({"input": time_acc, "interpolation": "LINEAR", "output": s_acc})
            channels.append({"sampler": s_s, "target": {"node": node_idx, "path": "scale"}})

    meshes, skins = [], []
    if is_stationary:
        # A single frame needs no bones: bake each bone's transform into the vertices.
        # This also avoids PowerPoint's bone limit for large static molecules.
        bone_nodes = nodes[3:3 + n_joints]
        prims = []
        for mat_idx, g in mat_geoms:
            baked = dict(g)
            baked["pos"] = [bake_point(bone_nodes[j[0]], p) for p, j in zip(g["pos"], g["joints"])]
            baked["norm"] = [bake_normal(bone_nodes[j[0]], n) for n, j in zip(g["norm"], g["joints"])]
            add_primitives(prims, baked, mat_idx, skinned=False)
        meshes.append({"name": "MoleculeMesh", "primitives": prims})
        nodes = [{"name": "RootNode", "children": [1]}, {"name": "MoleculeMesh", "mesh": 0}]
    else:
        # PowerPoint fails to import a skin with more than ~255 bones, so large molecules
        # are split into several skinned meshes, each driven by at most MAX_BONES_PER_SKIN bones.
        for lo in range(0, n_joints, MAX_BONES_PER_SKIN):
            hi = min(lo + MAX_BONES_PER_SKIN, n_joints)
            prims = []
            for mat_idx, g in mat_geoms:
                sub = subset_by_joint(g, lo, hi)
                if sub["ind"]:
                    add_primitives(prims, sub, mat_idx, skinned=True)
            ibm_b = bytearray()
            for _ in range(hi - lo):
                ibm_b.extend(struct.pack('<16f', *ident_mat4))
            part = len(meshes) + 1
            meshes.append({"name": f"MoleculeSkinnedMesh_{part}", "primitives": prims})
            skins.append({
                "name": f"ArmatureSkin_{part}",
                "inverseBindMatrices": add_accessor(ibm_b, 5126, hi - lo, "MAT4"),
                "skeleton": 2,
                "joints": joint_node_indices[lo:hi]
            })
            mesh_node = {"name": f"MoleculeMesh_{part}", "mesh": len(meshes) - 1, "skin": len(skins) - 1}
            if part == 1:
                nodes[1] = mesh_node
            else:
                nodes[0]["children"].append(len(nodes))
                nodes.append(mesh_node)

    align4(bin_data)

    gltf = {
        "asset": {
            "version": "2.0",
            "generator": "glibby CLI (PowerPoint 3D Molecular GLB Generator)"
        },
        "scene": 0,
        "scenes": [{"name": "Scene", "nodes": [0]}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "buffers": [{"byteLength": len(bin_data)}],
        "bufferViews": buffer_views,
        "accessors": accessors
    }

    if skins:
        gltf["skins"] = skins
    if not is_stationary:
        gltf["animations"] = [{
            "name": "Reaction_Trajectory",
            "samplers": samplers,
            "channels": channels
        }]

    json_bytes = json.dumps(gltf, separators=(',', ':')).encode('utf-8')
    while len(json_bytes) % 4 != 0:
        json_bytes += b' '

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_data)
    os.makedirs(os.path.dirname(os.path.abspath(glb_path)), exist_ok=True)
    with open(glb_path, 'wb') as f:
        f.write(struct.pack('<4sII', b'glTF', 2, total_len))
        f.write(struct.pack('<I4s', len(json_bytes), b'JSON'))
        f.write(json_bytes)
        f.write(struct.pack('<I4s', len(bin_data), b'BIN\x00'))
        f.write(bin_data)

    return {
        "input_xyz": os.path.abspath(xyz_path),
        "output_glb": os.path.abspath(glb_path),
        "glb_size_kb": round(total_len / 1024.0, 1),
        "is_stationary": is_stationary,
        "input_frames": n_raw,
        "exported_frames": n_frames,
        "loop_mode": effective_loop,
        "fps": fps if not is_stationary else 0.0,
        "atom_count": n_atoms,
        "bond_count": n_bonds,
        "palette": palette,
        "colors_rgb255": used_colors_rgb255,
        "dynamic_bonds": dynamic_info
    }

def write_output(data, output_file):
    try:
        os.makedirs(os.path.dirname(os.path.abspath(output_file)), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        print(f"Success! Data written to: {output_file}")
    except (OSError, TypeError) as e:
        print(f"Error writing to file {output_file}: {e}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="glibby CLI: Convert single-frame or multi-frame .xyz files to PowerPoint-ready 3D .glb models."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Subcommand: inspect ---
    p_inspect = subparsers.add_parser(
        "inspect",
        help="Inspect an .xyz file (frames, elements, static & dynamic bonds) before conversion."
    )
    p_inspect.add_argument("--input", required=True, help="Input .xyz file path")
    p_inspect.add_argument("--output", required=True, help="Output JSON report file path")
    p_inspect.add_argument("--atomic-numbers-to-symbols", action="store_true",
                           help="Convert atomic numbers in the element column (e.g. 26) to symbols (Fe). Only use after the user confirms.")

    # --- Subcommand: convert ---
    p_convert = subparsers.add_parser(
        "convert",
        help="Convert an .xyz file into a PowerPoint-ready 3D .glb model."
    )
    p_convert.add_argument("--input", required=True, help="Input .xyz file path")
    p_convert.add_argument("--glb-output", required=True, help="Output .glb file path")
    p_convert.add_argument("--output", required=True, help="Output JSON conversion manifest path")
    p_convert.add_argument(
        "--palette",
        choices=["zott", "chimerax"],
        default="zott",
        help="Color palette preset: 'zott' (default: N=0,68,134; Fe=153,119,0; C=143,143,143) or 'chimerax'."
    )
    p_convert.add_argument(
        "--color",
        action="append",
        default=[],
        help="Custom sRGB color override in EL=R,G,B format (e.g. --color N=0,68,134 --color Fe=153,119,0)."
    )
    p_convert.add_argument("--fps", type=float, default=12.0, help="Frames per second for animated trajectories")
    p_convert.add_argument(
        "--loop-mode",
        choices=["auto", "cycle", "ping-pong"],
        default="auto",
        help="Loop mode for multi-frame trajectories ('auto', 'cycle', or 'ping-pong')."
    )
    p_convert.add_argument(
        "--dynamic-bonds",
        choices=["include", "exclude"],
        default="include",
        help="Whether to include dynamic bonds that form/break across the trajectory."
    )
    p_convert.add_argument(
        "--add-bond",
        action="append",
        default=[],
        help="Explicitly add bond between 1-based atom indices I-J (e.g. --add-bond 44-47)."
    )
    p_convert.add_argument("--atomic-numbers-to-symbols", action="store_true",
                           help="Convert atomic numbers in the element column (e.g. 26) to symbols (Fe). Only use after the user confirms.")
    p_convert.add_argument(
        "--remove-bond",
        action="append",
        default=[],
        help="Explicitly remove bond between 1-based atom indices I-J (e.g. --remove-bond 44-47)."
    )

    args = parser.parse_args()

    try:
        if args.command == "inspect":
            frames = parse_xyz(args.input, args.atomic_numbers_to_symbols)
            elem_map = get_palette_elements("zott")
            bonds, static_info, dynamic_info = analyze_bonds(frames, elem_map)
            elements = [a[0] for a in frames[0][1]]
            el_counts = {}
            for el in elements:
                el_counts[el] = el_counts.get(el, 0) + 1
            report = {
                "input_xyz": os.path.abspath(args.input),
                "frame_count": len(frames),
                "is_stationary": len(frames) == 1,
                "atom_count": len(elements),
                "element_counts": el_counts,
                "static_bond_count": len(static_info),
                "dynamic_bond_count": len(dynamic_info),
                "dynamic_bonds": dynamic_info,
                "static_bonds": static_info
            }
            write_output(report, args.output)

        elif args.command == "convert":
            manifest = build_glb(
                xyz_path=args.input,
                glb_path=args.glb_output,
                palette=args.palette,
                color_overrides=args.color,
                fps=args.fps,
                loop_mode=args.loop_mode,
                dynamic_bonds=args.dynamic_bonds,
                add_bonds=args.add_bond,
                remove_bonds=args.remove_bond,
                convert_atomic_numbers=args.atomic_numbers_to_symbols
            )
            write_output(manifest, args.output)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
