# LU230 (titan23), k = 4 — cut 5304

A 4-way partition of the **LU230** hypergraph from the titan23 suite with a cut of **5304** nets.
The best entry I could find on the [UCSD hypergraph partitioning leaderboard](https://vlsicad.ucsd.edu/partitioning)
for this cell is 5405 (FastPart, no KEP, ε = 1%), so this is about 1.9% lower.

| | |
|---|---|
| Instance | `titan23/LU230.hgr` from the ABKGroup `hgp-benchmarks` dataset (574,372 vertices, 669,477 nets) |
| Instance sha256 | `44ce3c88235357f1b3fc7fcf6a4583954bc76c9b1a196502ab4166ec537822d0` |
| Blocks (k) | 4 |
| Balance | satisfies both ε = 1% and ε = 2% (min and max block bounds) |
| Block weights | 145822 / 145822 / 143556 / 139172 |
| Cut | **5304** (nets spanning ≥ 2 blocks) |
| Partition file | `LU230_k4_cut5304.part` — one block id per line, sha256 in `SHA256SUMS` |

## Checking it

With the instance downloaded and its sha256 confirmed:

```
python3 check/check_cut.py LU230.hgr LU230_k4_cut5304.part 4 1 5304 --broken
```

It should print `cut=5304` with `balance_ok=True`. `--broken` also makes three deliberately broken copies of the
partition (bad id, truncated, unassigned vertex) and makes sure each one is rejected.

I also checked it with the leaderboard's own evaluator (ABKGroup source, commit `e2b18054`), which gives
`PASS cut=5304` at ε = 1 and ε = 2. Entries with smaller cuts on the page (5233, 5125, 4806) are posted at
looser balance (ε = 5, 10, 20); I downloaded and scored them, and all three break the ε = 1 and ε = 2 bounds,
so they aren't comparable to this cell.

## How it was found

Seeded multilevel refinement with Mt-KaHyPar (QUALITY / HIGHEST_QUALITY V-cycles) plus a few targeted
refinement strategies run as a small adaptive portfolio, starting from the previous best partitions.

## Credits

Alexander LaVerdi. The search runs and the independent checker were built with help from AI coding
assistants (Claude); every result here was re-checked from scratch with two separate checkers before posting.
Benchmark and evaluator: ABKGroup / UCSD VLSI CAD Lab.
