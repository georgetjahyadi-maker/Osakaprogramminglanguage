# Performance Baseline (v1.1.1)

Recorded at the end of Phase 0, before any optimisation work. Phase 3
(v1.4) measures against these numbers; its targets are **at least 1 million
simple VM instructions per second** on the native VM and a **full native
bootstrap under 5 minutes**.

Machine: x86_64, Intel Xeon @ 2.10 GHz, 4 vCPUs, Linux, Python 3.13,
`native/osakavm` built with the default `make build` flags (`-O2`).
Numbers vary between machines; compare runs on the same machine.

## Bootstrap: native VM compiles the compiler

`python3 run_gate_e.py`: the checked-in stage2 compiler, running on
`native/osakavm` with no Python at run time, compiles the full selfhost
bundle. The run passed: `SHA256(stage2'') == SHA256(stage2)` =
`07c2b0f18db27e7faac2b7fd82e8b131434ee9193625d5fc481897f07dc2d690`.

| Phase | Time |
| --- | --- |
| parse bundle source | 3519 s (58 m 39 s) |
| compile bundle AST | 20 s |
| verify compiled doc | 39 s |
| emit stage2'' SBC text | 273 s (4 m 33 s) |
| **total (wall clock)** | **3852 s (64 m 12 s)** |

Parsing is 91% of the bootstrap. That is the first place to look in
Phase 3. (The repo's earlier record of ~42 minutes was taken on a different
machine.)

## VM throughput

`python3 bench/vm_throughput.py --repeats 5`: median of 5 runs, start-up
subtracted. Instructions per iteration are counted from the compiled loop
body (plus the called function's body for `call_loop`).

| Workload | Native VM (instr/s) | Python VM (instr/s) |
| --- | ---: | ---: |
| `arith_loop` (add + increment) | 457,555 | 1,226,796 |
| `call_loop` (function call per iteration) | 442,158 | 1,292,037 |
| `list_loop` (`push` per iteration) | 445,551 | 1,106,163 |

The native VM is about **2.7× slower than the Python VM**. It is C
transpiled from the Osaka VM (`selfhost/vm.saka`), so every instruction
pays for the Osaka-level data structures (map lookups for variables,
boxed values). The Phase 3 work on slot-indexed locals and hot-path
profiling targets exactly this.

Note: `call_loop` must write `i = Americaya(step(i));` because function
results come back as grain. That is the Phase 1 "Americaya tax"; the
benchmark will drop the `Americaya` once arguments and results keep their
kind.

## Reproducing

```bash
make build
python3 bench/vm_throughput.py --json bench/results/throughput.json
python3 run_gate_e.py            # about an hour; resumable
```

`bench/results/` is not tracked; the JSON there records the toolchain
hashes and git revision the numbers came from.
