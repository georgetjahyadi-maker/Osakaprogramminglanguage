# Gate E Provenance: Compiler Bootstrap on the Native VM

The stage chain was executed by `native/osakavm` — the transpiled
`selfhost/vm.saka` (via `transpile_vm.py`) plus the C host runtime
(`native/rt.c`, `builtins.c`, `json.c`, `main.c`). No Python
interpreter is involved at run time. Each phase is checkpointed
under `bootstrap/.ckpt.gatee.*.json`.

Inputs (checkpoints are keyed to these; any change discards them):

- compiler (stage2) sha256: `07c2b0f18db27e7faac2b7fd82e8b131434ee9193625d5fc481897f07dc2d690`
- bundle source sha256: `094e498bc0795db7944dd3c63000dc52fd285d6f8d2a482e742a3f6d7309721a`
- native VM binary sha256: `e6cab32bb37299a27d10f4315dada6c4db777fd82d830f13097a7f188fc01b16`
- checkpoint key: `4625fe5b743d560c7c169ed99317a2de4e6475cb74845c537685db824e79129d`

| Stage | SHA256 | Chars |
| --- | --- | --- |
| stage2 (checked in) | `07c2b0f18db27e7faac2b7fd82e8b131434ee9193625d5fc481897f07dc2d690` | 1233542 |
| stage2'' (native VM) | `07c2b0f18db27e7faac2b7fd82e8b131434ee9193625d5fc481897f07dc2d690` | 1233542 |

**GATE E PASSED**: the native VM executed the full compiler pipeline (parse -> compile -> verify -> emit) and produced byte-identical output to the checked-in stage2 artifact (SHA256(stage2'') == SHA256(stage2)).

Note: generation N+1 was skipped as redundant, matching Gate D: Gate C proved the fixed point on the Python VM, and a byte-identical stage2'' makes the N+1 cycle a repeat of the identical computation.
