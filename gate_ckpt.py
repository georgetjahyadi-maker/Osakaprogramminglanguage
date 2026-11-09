"""Hash-keyed checkpoints for the bootstrap gate drivers.

A gate run is long (tens of minutes), so each pipeline phase saves its
result to bootstrap/.ckpt.<prefix>.<name>.json and a crashed run resumes
from there. A checkpoint is only valid for the exact compiler artifact and
inputs that produced it. If the checkpoint were reused after the compiler
or the selfhost sources changed, a gate could "pass" on stale results.

Every checkpoint therefore stores a key: the SHA-256 fingerprint of
everything that determines its value (compiler artifact, bundle source,
and for the native gate the VM binary). Loading with a different key
discards the file. Checkpoints written before keys existed have no key and
are discarded too.
"""

import hashlib
import json
from pathlib import Path


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_file(path):
    return sha256_bytes(Path(path).read_bytes())


def fingerprint(**parts):
    """Combine named input hashes into one key.

    Each value is a hex digest or a str/bytes payload (hashed here). Names
    are part of the key so that swapping two inputs changes it.
    """
    h = hashlib.sha256()
    for name in sorted(parts):
        value = parts[name]
        if isinstance(value, str):
            value = value.encode("utf-8")
        h.update(name.encode("utf-8") + b"\0")
        h.update(sha256_bytes(value).encode("ascii") + b"\0")
    return h.hexdigest()


class Checkpoints:
    """Checkpoint files bootstrap/.ckpt.<prefix>.<name>.json bound to a key."""

    def __init__(self, directory, prefix, key):
        self.directory = Path(directory)
        self.prefix = prefix
        self.key = key

    def path(self, name):
        return self.directory / f".ckpt.{self.prefix}.{name}.json"

    def _all(self):
        return sorted(self.directory.glob(f".ckpt.{self.prefix}.*.json"))

    def purge_stale(self):
        """Delete every checkpoint of this prefix not written under self.key.

        Returns the names of the removed files.
        """
        removed = []
        for path in self._all():
            if self._read(path) is None:
                removed.append(path.name)
        return removed

    def _read(self, path):
        """Return the stored value, or None (and delete the file) if the
        file is corrupt, from the old unkeyed format, or keyed differently."""
        try:
            envelope = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except Exception:
            path.unlink(missing_ok=True)
            return None
        if not (isinstance(envelope, dict)
                and envelope.get("ckpt_key") == self.key
                and "value" in envelope):
            path.unlink(missing_ok=True)
            return None
        return envelope

    def load(self, name):
        envelope = self._read(self.path(name))
        return None if envelope is None else envelope["value"]

    def save(self, name, value):
        path = self.path(name)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps({"ckpt_key": self.key, "value": value}),
                       encoding="utf-8")
        tmp.replace(path)

    def clear(self):
        for path in self._all():
            path.unlink(missing_ok=True)


STAGE0_FILES = ("lexer.py", "parser.py", "compiler.py", "bytecode.py",
                "sbc.py", "verifier.py", "vm.py", "runtime.py")


def git_revision(root):
    import subprocess
    try:
        rev = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                             text=True, check=True, cwd=str(root)).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain"],
                               capture_output=True, text=True,
                               cwd=str(root)).stdout.strip()
        return rev + ("+dirty" if dirty else "")
    except Exception:
        return "unknown"


def report_provenance(root, extra_files=()):
    """What produced a saved gate report: the git revision and the hashes of
    the Stage 0 toolchain (plus any extra files, e.g. the native VM)."""
    root = Path(root)
    files = {}
    for name in tuple(STAGE0_FILES) + tuple(extra_files):
        path = root / name
        files[name] = sha256_file(path) if path.is_file() else None
    return {"git_revision": git_revision(root),
            "toolchain_sha256": fingerprint(**{k: v or "missing"
                                               for k, v in files.items()}),
            "files_sha256": files}
