"""Gate checkpoints are only reused for the exact inputs that produced them."""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gate_ckpt import Checkpoints, fingerprint, sha256_bytes


class TestFingerprint(unittest.TestCase):
    def test_changes_when_any_input_changes(self):
        base = fingerprint(compiler="aaa", source="src")
        self.assertNotEqual(base, fingerprint(compiler="aab", source="src"))
        self.assertNotEqual(base, fingerprint(compiler="aaa", source="srd"))

    def test_input_names_matter(self):
        self.assertNotEqual(fingerprint(a="x", b="y"), fingerprint(a="y", b="x"))

    def test_order_of_arguments_does_not_matter(self):
        self.assertEqual(fingerprint(a="x", b="y"), fingerprint(b="y", a="x"))


class TestCheckpoints(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_round_trip_under_same_key(self):
        ck = Checkpoints(self.dir, "gatee", "k1")
        ck.save("ast", {"x": [1, 2]})
        self.assertEqual(Checkpoints(self.dir, "gatee", "k1").load("ast"),
                         {"x": [1, 2]})

    def test_different_key_discards(self):
        Checkpoints(self.dir, "gatee", "old-compiler").save("ast", [1])
        ck = Checkpoints(self.dir, "gatee", "new-compiler")
        self.assertIsNone(ck.load("ast"))
        self.assertFalse(ck.path("ast").exists())

    def test_legacy_unkeyed_checkpoint_is_stale(self):
        path = self.dir / ".ckpt.gatee.emit.json"
        path.write_text(json.dumps({"ok": 1, "value": "{\"constants\"..."}))
        ck = Checkpoints(self.dir, "gatee", "k1")
        self.assertEqual(ck.purge_stale(), [path.name])
        self.assertFalse(path.exists())

    def test_corrupt_checkpoint_is_discarded(self):
        ck = Checkpoints(self.dir, "gated", "k1")
        ck.path("doc").write_text("{not json")
        self.assertIsNone(ck.load("doc"))
        self.assertFalse(ck.path("doc").exists())

    def test_purge_keeps_matching_and_other_prefixes(self):
        Checkpoints(self.dir, "gated", "k1").save("ast", 1)
        Checkpoints(self.dir, "gated", "k0").save("doc", 2)
        Checkpoints(self.dir, "gatee", "zz").save("ast", 3)
        removed = Checkpoints(self.dir, "gated", "k1").purge_stale()
        self.assertEqual(removed, [".ckpt.gated.doc.json"])
        self.assertTrue((self.dir / ".ckpt.gated.ast.json").exists())
        self.assertTrue((self.dir / ".ckpt.gatee.ast.json").exists())

    def test_falsy_values_survive(self):
        ck = Checkpoints(self.dir, "s2", "k")
        ck.save("verify", 0)
        self.assertEqual(ck.load("verify"), 0)

    def test_sha256_bytes(self):
        self.assertEqual(
            sha256_bytes(b""),
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")


if __name__ == "__main__":
    unittest.main()
