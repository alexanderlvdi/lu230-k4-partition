#!/usr/bin/env python3
"""check_cut.py — standalone cut/balance checker for hMETIS hypergraphs and k-way partitions.

Written independently from the benchmark's problem statement (it does not use the
leaderboard's own evaluator code).

Statement implemented:
  * Partition: one block id per vertex, id in [0, k); exactly num_vertices ids.
  * Cut: a hyperedge is cut when its vertices span >= 2 distinct blocks;
    the cut is the number of cut hyperedges (all edge weights are 1 in an
    unweighted file).
  * Balance (BOTH bounds, eps in percent = UBfactor):
        (100/k - eps)% * W  <=  block weight  <=  (100/k + eps)% * W
    checked in exact integer arithmetic: 100*k*w >= (100 - eps*k)*W and
    100*k*w <= (100 + eps*k)*W, with eps*k as an exact Fraction.

File-format facts are asserted from the file itself, never assumed:
  * header = two ints a, b [flag]. The body must have exactly one of a or b
    lines (that one is #hyperedges) and the .part must have the other many
    entries (that one is #vertices); if both or neither fit, refuse.
  * flag == 0 (no weights) is required; otherwise refuse (fail closed).
  * every vertex id on an edge line must lie in [1, num_vertices].

Usage:
  check_cut.py <hgr> <part> <k> <eps> [<expected_cut>] [--broken]
  --broken also builds three deliberately broken variants of <part>
    (out-of-range id, truncated, unassigned -1) and requires each to be REJECTED.

Exit code 0 only if every stated check passes.
"""
import hashlib
import sys
import tempfile
from fractions import Fraction
from pathlib import Path


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_part(path: str, k: int, num_vertices: int, allow_unassigned: bool = False):
    """Read .part; return list of ints or raise SystemExit on any violation."""
    toks = Path(path).read_text().split()
    if len(toks) != num_vertices:
        sys.exit(f"REJECT: part has {len(toks)} ids, expected {num_vertices}")
    part = []
    for i, t in enumerate(toks):
        try:
            v = int(t)
        except ValueError:
            sys.exit(f"REJECT: part entry {i} not an integer: {t!r}")
        if v == -1 and not allow_unassigned:
            sys.exit(f"REJECT: vertex {i} unassigned (-1)")
        if not (0 <= v < k):
            sys.exit(f"REJECT: vertex {i} -> block {v} outside [0,{k})")
        part.append(v)
    return part


def check(hgr: str, part_path: str, k: int, eps: Fraction, expected=None,
          require_balance: bool = True):
    # --- hypergraph header + body ---
    with open(hgr) as f:
        header = f.readline().split()
        if len(header) not in (2, 3):
            sys.exit(f"REJECT: header has {len(header)} fields: {header!r}")
        a, b = int(header[0]), int(header[1])
        flag = int(header[2]) if len(header) == 3 else 0
        body = f.readlines()
    n_body = len(body)
    fits_a = n_body == a          # a = #hyperedges
    fits_b = n_body == b          # b = #hyperedges
    print(f"header a={a} b={b} flag={flag} body_lines={n_body}")
    print(f"reading a=#hyperedges: {fits_a}; reading b=#hyperedges: {fits_b}")
    if fits_a == fits_b:
        sys.exit("REJECT: header ambiguous (both or neither reading fits)")
    num_hyperedges, num_vertices = (a, b) if fits_a else (b, a)
    if flag != 0:
        sys.exit(f"REJECT: flag={flag} (this checker is fail-closed on weighted files)")
    print(f"num_hyperedges={num_hyperedges} num_vertices={num_vertices}")

    # --- partition validity ---
    part = load_part(part_path, k, num_vertices)

    # --- balance: both bounds, exact arithmetic, unit vertex weights ---
    W = num_vertices  # flag == 0 -> every vertex weight is 1
    eps_k = eps * k
    lo_num, hi_num = (100 - eps_k) * W, (100 + eps_k) * W  # w >= lo_num/100k etc.
    block_w = [0] * k
    for v in part:
        block_w[v] += 1
    den = 100 * k
    min_ok = all(w * den >= lo_num for w in block_w)
    max_ok = all(w * den <= hi_num for w in block_w)
    balance_ok = min_ok and max_ok
    print(f"total_weight={W} bounds=[{float(lo_num)/den:.3f}, {float(hi_num)/den:.3f}]")
    print(f"block_weights={block_w}")
    print(f"block_fractions={[round(w / W, 6) for w in block_w]}")
    print(f"balance_ok={balance_ok} (min_bound_ok={min_ok} max_bound_ok={max_ok})")
    if require_balance and not balance_ok:
        sys.exit("REJECT: balance violated")

    # --- cut: hyperedges spanning >= 2 blocks ---
    cut = 0
    for i in range(num_hyperedges):
        toks = body[i].split()
        if not toks:
            sys.exit(f"REJECT: empty hyperedge line {i + 2}")
        n = int(toks[0])
        if len(toks) - 1 != n:
            sys.exit(f"REJECT: hyperedge line {i + 2}: declares {n} pins, "
                     f"has {len(toks) - 1}")
        seen = set()
        for t in toks[1:]:
            v = int(t)
            if not (1 <= v <= num_vertices):
                sys.exit(f"REJECT: hyperedge line {i + 2} refs vertex {v} "
                         f"outside [1,{num_vertices}]")
            seen.add(part[v - 1])
            if len(seen) > 1:
                break
        if len(seen) > 1:
            cut += 1
    print(f"cut={cut}")

    if expected is not None:
        match = cut == expected
        print(f"expected_cut={expected} match={match}")
        if not match:
            sys.exit(f"REJECT: cut {cut} != expected {expected}")
    print(f"sha256 hgr={sha256(hgr)}")
    print(f"sha256 part={sha256(part_path)}")
    print(f"VERDICT: PASS cut={cut} k={k} eps={eps}")
    return cut


def broken_tests(hgr: str, part_path: str, k: int, eps: Fraction):
    """Three deliberately broken variants must each be REJECTED."""
    lines = Path(part_path).read_text().split()
    variants = {
        "out_of_range": lines[:100] + [str(k)] + lines[101:],   # id == k
        "truncated": lines[:-1],                                 # wrong count
        "unassigned": ["-1"] + lines[1:],                        # -1 id
    }
    with tempfile.TemporaryDirectory(dir=str(Path(__file__).parent)) as td:
        for name, toks in variants.items():
            p = Path(td) / f"{name}.part"
            p.write_text("\n".join(toks) + "\n")
            try:
                # validate id/count rules without balance (these variants may
                # also break balance; any rejection counts, but we want the
                # *id/count* rule to fire, so allow_unassigned stays False and
                # we call load_part directly)
                num_vertices = None
                with open(hgr) as f:
                    h = f.readline().split()
                    a, b = int(h[0]), int(h[1])
                    n_body = sum(1 for _ in f)
                num_vertices = b if n_body == a else a
                load_part(str(p), k, num_vertices)
                print(f"BROKEN {name}: ACCEPTED -> GATE BROKEN")
                sys.exit(1)
            except SystemExit as e:
                if e.code in (None, 0):
                    print(f"BROKEN {name}: ACCEPTED -> GATE BROKEN")
                    sys.exit(1)
                print(f"BROKEN {name}: rejected ({e})")
    print("BROKEN-TESTS: all three rejected (ok)")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) < 4:
        sys.exit(__doc__)
    hgr, part_path = args[0], args[1]
    k = int(args[2])
    eps = Fraction(args[3])
    expected = int(args[4]) if len(args) > 4 else None
    if "--broken" in flags:
        broken_tests(hgr, part_path, k, eps)
    check(hgr, part_path, k, eps, expected)


if __name__ == "__main__":
    main()
