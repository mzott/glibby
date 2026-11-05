#!/usr/bin/env python3
"""Run every file in examples/ through the glibby CLI and check the outcome matches its name.

  valid_*  / stress_*  -> converts successfully
  prompt_*             -> stops and asks about atomic numbers
  error_*              -> rejected with an error message

Usage: python tests/check_examples.py
"""
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CLI = ROOT / "skill" / "glibby" / "scripts" / "glibby_cli.py"


def outcome(xyz, tmp):
    r = subprocess.run(
        [sys.executable, str(CLI), "convert", "--input", str(xyz),
         "--glb-output", str(tmp / "out.glb"), "--output", str(tmp / "out.json")],
        capture_output=True, text=True)
    if r.returncode == 0:
        return "valid", ""
    msg = r.stderr.strip().splitlines()[-1] if r.stderr.strip() else ""
    return ("prompt" if "--atomic-numbers-to-symbols" in msg else "error"), msg


def main():
    failures = 0
    with tempfile.TemporaryDirectory() as d:
        tmp = pathlib.Path(d)
        for xyz in sorted((ROOT / "examples").glob("*.xyz")):
            prefix = xyz.name.split("_", 1)[0]
            expected = "valid" if prefix == "stress" else prefix
            got, msg = outcome(xyz, tmp)
            ok = got == expected
            failures += not ok
            print(f"{'PASS' if ok else 'FAIL'}  {xyz.name:<50} {got:<7} {msg[:70]}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
