#!/usr/bin/env python3
"""Compare three authored candidates using the unchanged cursor verifier.

Host requirements: Python 3.10+, Git, and Docker running Linux containers.
No model calls or third-party host Python packages are used.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid


ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "envs" / "cursor-pagination"
IMAGE = "swe-rl-cursor-pagination:walkthrough"
EXPECTED = {
    "seeded": [True] * 6 + [False, False, False],
    "partial": [True] * 7 + [False, False],
    "reference": [True] * 9,
}


def command(args: list[str], *, cwd: Path | None = None, timeout: int = 120):
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True,
        encoding="utf-8", errors="replace", timeout=timeout,
    )


def checked(args: list[str], *, cwd: Path | None = None) -> str:
    result = command(args, cwd=cwd)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result.stdout.strip()


def validate_transcript(output: str, returncode: int, case: str) -> list[bool]:
    """Do not mistake a Docker/setup error for a correctly rejected candidate."""
    expected_result = "PASS" if case == "reference" else "FAIL"
    expected_code = 0 if case == "reference" else 1
    if returncode != expected_code or not output.rstrip().endswith(
        f"RESULT: {expected_result}"
    ):
        raise RuntimeError(f"{case}: unexpected exit code or final verifier result")
    if re.search(r"^\s*FATAL:", output, re.MULTILINE):
        raise RuntimeError(f"{case}: verifier setup/integrity failure")
    sections = list(re.finditer(r"^=== \[(\d+)\] .+$", output, re.MULTILINE))
    if [int(match[1]) for match in sections] != list(range(1, 10)):
        raise RuntimeError(f"{case}: expected all nine verifier gates")
    statuses = []
    for index, match in enumerate(sections):
        end = sections[index + 1].start() if index + 1 < len(sections) else len(output)
        body = output[match.end():end]
        failed = bool(re.search(r"^\s*FAIL:", body, re.MULTILINE))
        passed = bool(re.search(r"^\s*ok:", body, re.MULTILINE))
        if not failed and not passed:
            raise RuntimeError(f"{case}: missing result for gate {index + 1}")
        statuses.append(passed and not failed)
    if statuses != EXPECTED[case]:
        raise RuntimeError(f"{case}: unexpected gate outcomes {statuses}")
    return statuses


def verify(candidate: Path, output_dir: Path, case: str, image_id: str) -> dict:
    name = f"swe-walkthrough-{uuid.uuid4().hex}"
    args = [
        "docker", "run", "--name", name, "--rm", "--network", "none",
        "--read-only", "--tmpfs", "/tmp:rw,exec,nosuid,size=256m",
        "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
        "--memory", "1g", "--pids-limit", "256",
        "--mount", f"type=bind,source={candidate},target=/work/repo,readonly",
        "--mount", f"type=bind,source={ENV / 'heldout'},target=/verify/heldout,readonly",
        "--mount", f"type=bind,source={ENV / 'verify.sh'},target=/verify/verify.sh,readonly",
        image_id, "bash", "/verify/verify.sh",
    ]
    try:
        result = command(args, timeout=300)
    except subprocess.TimeoutExpired:
        command(["docker", "rm", "--force", name], timeout=30)
        raise RuntimeError(f"{case}: verification timed out") from None
    transcript = result.stdout + result.stderr
    (output_dir / f"{case}.log").write_text(transcript, encoding="utf-8")
    statuses = validate_transcript(transcript, result.returncode, case)
    return {
        "case": case, "exit_code": result.returncode,
        "gate_passed": statuses, "result": "PASS" if result.returncode == 0 else "FAIL",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="New directory for candidates and logs")
    args = parser.parse_args()
    for executable in ("git", "docker"):
        if shutil.which(executable) is None:
            parser.error(f"{executable} must be installed and on PATH")
    if checked(["docker", "info", "--format", "{{.OSType}}"]) != "linux":
        parser.error("Docker must be running Linux containers")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = (args.output_dir or ROOT / "artifacts" / f"walkthrough-{stamp}").resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    print(f"Artifacts: {output_dir}", flush=True)
    print("Building the pinned cursor-pagination image...", flush=True)
    build = command(["docker", "build", "--tag", IMAGE, str(ENV)], timeout=600)
    (output_dir / "build.log").write_text(build.stdout + build.stderr, encoding="utf-8")
    if build.returncode:
        raise RuntimeError(f"Docker build failed; see {output_dir / 'build.log'}")
    image_id = checked(["docker", "image", "inspect", IMAGE, "--format", "{{.Id}}"])
    source_files = sorted(path for path in ENV.rglob("*") if path.is_file()
                          and "__pycache__" not in path.parts)
    source_files += [Path(__file__).resolve(), ROOT / "examples" / "partial-pagination.patch"]
    metadata = {
        "kind": "authored-candidate-verification-walkthrough",
        "environment": "cursor-pagination",
        "created_at_utc": stamp,
        "source_commit": checked(["git", "rev-parse", "HEAD"], cwd=ROOT),
        "working_tree_dirty": bool(checked(["git", "status", "--porcelain"], cwd=ROOT)),
        "image_id": image_id,
        "host_python": sys.version.split()[0],
        "input_sha256": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in source_files},
        "results": [],
    }
    metadata_path = output_dir / "metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    for case in EXPECTED:
        candidate = output_dir / "candidates" / case
        shutil.copytree(ENV / "repo", candidate, ignore=shutil.ignore_patterns(
            "__pycache__", "*.pyc", ".pytest_cache", ".git"))
        # A nested repository keeps git apply relative to this disposable copy,
        # including when output_dir is inside the caller's existing checkout.
        checked(["git", "init", "--quiet", str(candidate)])
        patch = {
            "partial": ROOT / "examples" / "partial-pagination.patch",
            "reference": ENV / "golden" / "fix.patch",
        }.get(case)
        if patch is not None:
            checked(["git", "apply", "--whitespace=nowarn", str(patch)], cwd=candidate)
        print(f"Verifying {case} candidate...", flush=True)
        metadata["results"].append(verify(candidate, output_dir, case, image_id))
        metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print("\nCandidate   Visible  Held-out  Combined  Overall")
    for result in metadata["results"]:
        suite_results = ["PASS" if passed else "FAIL" for passed in result["gate_passed"][6:]]
        print(f"{result['case']:<11} {suite_results[0]:<8} {suite_results[1]:<9} "
              f"{suite_results[2]:<9} {result['result']}")
    print("\nWalkthrough verified. Authored examples; no model was run.")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
