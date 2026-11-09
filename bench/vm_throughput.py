#!/usr/bin/env python3
"""VM throughput baseline: how many bytecode instructions per second each
backend executes on small, fixed workloads.

Each workload is a single `while` loop compiled by the Stage 0 compiler.
The instructions per iteration are counted from the compiled loop body (the
span from the loop's backward-jump target to the jump), plus the
instructions of any function the body calls, so

    instructions/sec = iterations * per_iteration / (time(N) - time(0))

Subtracting the N=0 run removes process start-up and document loading.

Usage:
    python3 bench/vm_throughput.py              # native + Python VM
    python3 bench/vm_throughput.py --native-only
    python3 bench/vm_throughput.py --json bench/results/throughput.json
"""

import argparse
import contextlib
import io
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from gate_ckpt import report_provenance  # noqa: E402
from tests.test_selfhost_vm import compile_document, run_on_python_vm  # noqa: E402

OSAKAVM = ROOT / "native" / "osakavm"

WORKLOADS = {
    # name: (source template with {n}, native N, python N)
    "arith_loop": ("""
truthaboutgrain total = 0;
truthaboutgrain i = 0;
while i < {n} {{
    total = total + i;
    i = i + 1;
}}
Say(total);
""", 300000, 30000),
    "call_loop": ("""
function step(x) {{
    return x + 1;
}}
truthaboutgrain i = 0;
while i < {n} {{
    // Function results come back as grain today, so the loop counter must
    // be vouched for again (the Phase 1 "Americaya tax").
    i = Americaya(step(i));
}}
Say(i);
""", 100000, 10000),
    "list_loop": ("""
truthaboutgrain xs = [];
truthaboutgrain i = 0;
while i < {n} {{
    push(xs, i);
    i = i + 1;
}}
Say(len(xs));
""", 100000, 10000),
}


def instructions_per_iteration(document):
    main = document["main"]
    back = [k for k, ins in enumerate(main)
            if ins["op"] == "JMP" and isinstance(ins["arg"], int)
            and ins["arg"] < k]
    if len(back) != 1:
        raise RuntimeError("workload must contain exactly one loop")
    end = back[0]
    start = main[end]["arg"]
    body = main[start:end + 1]
    count = len(body)
    for ins in body:
        if ins["op"] == "CALL_FUNC":
            name = ins["arg"][0]
            count += len(document["functions"][name]["code"])
    return count


def run_native(document):
    with tempfile.TemporaryDirectory() as tmp:
        doc = Path(tmp) / "bench.sbc"
        args = Path(tmp) / "args.json"
        doc.write_text(json.dumps(document, separators=(",", ":")) + "\n")
        args.write_text("[]")
        t0 = time.perf_counter()
        proc = subprocess.run([str(OSAKAVM), "run", str(doc), str(args)],
                              capture_output=True, text=True)
        elapsed = time.perf_counter() - t0
    if proc.returncode != 0:
        raise RuntimeError(f"osakavm failed: {proc.stderr[:300]}")
    return elapsed, json.loads(proc.stdout)["value"]["stdout"].strip()


def run_python(document):
    t0 = time.perf_counter()
    with contextlib.redirect_stdout(io.StringIO()):
        result = run_on_python_vm(document)
    elapsed = time.perf_counter() - t0
    if result["error"]:
        raise RuntimeError(f"python vm failed: {result['error']}")
    return elapsed, result["stdout"].strip()


def measure(runner, template, n, repeats):
    doc_n = compile_document(template.format(n=n))
    doc_0 = compile_document(template.format(n=0))
    per_iter = instructions_per_iteration(doc_n)
    timings, base = [], []
    for _ in range(repeats):
        base.append(runner(doc_0)[0])
        elapsed, out = runner(doc_n)
        timings.append(elapsed)
    loop_s = max(statistics.median(timings) - statistics.median(base), 1e-9)
    return {
        "iterations": n,
        "instructions_per_iteration": per_iter,
        "median_total_s": round(statistics.median(timings), 4),
        "median_startup_s": round(statistics.median(base), 4),
        "iterations_per_s": round(n / loop_s),
        "instructions_per_s": round(n * per_iter / loop_s),
        "output": out,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--native-only", action="store_true")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--json", type=Path)
    opts = ap.parse_args()

    if not OSAKAVM.is_file():
        raise SystemExit("native/osakavm not built; run `make build`")

    backends = [("native", run_native, 1)]
    if not opts.native_only:
        backends.append(("python_vm", run_python, 2))

    results = {}
    for name, (template, n_native, n_python) in WORKLOADS.items():
        for backend, runner, idx in backends:
            n = n_native if idx == 1 else n_python
            r = measure(runner, template, n, opts.repeats)
            results.setdefault(name, {})[backend] = r
            print(f"{name:11s} {backend:9s} {r['instructions_per_s']:>12,} instr/s"
                  f"  {r['iterations_per_s']:>10,} iter/s"
                  f"  ({r['instructions_per_iteration']} instr/iter,"
                  f" startup {r['median_startup_s']}s)", flush=True)

    report = {
        "generated_by": report_provenance(ROOT, ("native/osakavm",)),
        "machine": {"platform": platform.platform(),
                    "python": platform.python_version(),
                    "cpus": os.cpu_count()},
        "results": results,
    }
    if opts.json:
        opts.json.parent.mkdir(parents=True, exist_ok=True)
        opts.json.write_text(json.dumps(report, indent=1) + "\n")
        print(f"wrote {opts.json}")


if __name__ == "__main__":
    main()
