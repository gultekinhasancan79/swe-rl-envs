"""Failure classification for the reviewer helper, separate from benchmark tests."""

import importlib.util
from pathlib import Path
import unittest


spec = importlib.util.spec_from_file_location(
    "walkthrough", Path(__file__).resolve().parents[1] / "examples/verification_walkthrough.py")
walkthrough = importlib.util.module_from_spec(spec)
spec.loader.exec_module(walkthrough)


def transcript(states, result):
    return "\n".join(
        f"=== [{index}] Gate\n    {'ok' if passed else 'FAIL'}: outcome"
        for index, passed in enumerate(states, 1)
    ) + f"\nRESULT: {result}\n"


class WalkthroughClassificationTests(unittest.TestCase):
    def test_expected_candidate_behaviours(self):
        for case, states in walkthrough.EXPECTED.items():
            with self.subTest(case=case):
                code = 0 if case == "reference" else 1
                result = "PASS" if code == 0 else "FAIL"
                self.assertEqual(walkthrough.validate_transcript(
                    transcript(states, result), code, case), states)

    def test_docker_failure_is_not_a_rejected_candidate(self):
        with self.assertRaises(RuntimeError):
            walkthrough.validate_transcript("Cannot connect to Docker", 125, "seeded")

    def test_integrity_failure_is_not_expected_rejection(self):
        states = [True] * 6 + [False] * 3
        states[2] = False
        with self.assertRaises(RuntimeError):
            walkthrough.validate_transcript(transcript(states, "FAIL"), 1, "seeded")

    def test_partial_fix_must_pass_visible_tests(self):
        with self.assertRaises(RuntimeError):
            walkthrough.validate_transcript(
                transcript(walkthrough.EXPECTED["seeded"], "FAIL"), 1, "partial")

    def test_truncated_verifier_run_is_not_expected_rejection(self):
        with self.assertRaises(RuntimeError):
            walkthrough.validate_transcript(transcript([True] * 6, "FAIL"), 1, "seeded")

    def test_reference_must_pass_every_gate(self):
        with self.assertRaises(RuntimeError):
            walkthrough.validate_transcript(
                transcript(walkthrough.EXPECTED["partial"], "PASS"), 0, "reference")


if __name__ == "__main__":
    unittest.main()
