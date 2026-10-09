import json
import sys
import tempfile
import unittest
from contextlib import ExitStack, contextmanager
from pathlib import Path
from unittest.mock import patch

import numpy as np

ROOT = Path(r"D:\STUDY\darker\agent-pointcloud-registration")
TEST_TMP_ROOT = ROOT / "outputs" / "development_tests"
TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "src"))

import agent_runner
from agnnes_agent import AgnesDecisionAdapter, MAX_PROBES_PER_RUN


def diagnosis():
    return {"source_point_count": 10, "target_point_count": 10,
            "initial_transform_available": True, "base_scale": 0.1}


def final_decision():
    return {
        "observation_summary": "smoke", "information_sufficient": True,
        "requested_probe": "NONE", "probe_reason": None,
        "candidate_methods": [{"method": "LOCAL_ICP", "pros": "smoke", "risks": "smoke"}],
        "selected_method": "LOCAL_ICP", "parameter_policy": {"icp_max_corr_scale": 1.0},
        "reasoning_summary": "model-selected smoke method", "confidence": 0.5,
    }


def probe_decision(name):
    return {
        "observation_summary": "more evidence needed", "information_sufficient": False,
        "requested_probe": name, "probe_reason": "model requested this observation",
        "candidate_methods": [], "selected_method": None, "parameter_policy": {},
        "reasoning_summary": "model requested a probe", "confidence": 0.4,
    }


def assessment():
    return {
        "assessment": "smoke", "global_consistency_assessment": "smoke",
        "local_optimum_risk": "UNKNOWN", "evidence_conflicts": [], "decision": "ABORT",
        "reason": "stop smoke after one registration call", "next_method": None,
        "next_parameter_policy": None, "confidence": 0.5,
    }


@contextmanager
def stub_runtime():
    events = []
    with ExitStack() as stack:
        stack.enter_context(patch.object(agent_runner, "diagnose", lambda _s, _t: diagnosis()))
        stack.enter_context(patch.object(
            agent_runner, "run_local_icp",
            lambda *_a, **_k: events.append("registration") or {
                "transform": np.eye(4), "fitness": 0.9, "rmse": 0.01, "elapsed_s": 0.01,
            }))
        stack.enter_context(patch.object(
            agent_runner, "evaluate_agent_result",
            lambda _transform, _gt: events.append("evaluator") or {
                "success": True, "rot_err_deg": 0.0, "trans_err": 0.0,
                "rot_thr_deg": 5.0, "trans_thr": 0.05,
            }))
        stack.enter_context(patch.object(
            agent_runner, "save_evaluator_result",
            lambda value, path: Path(path).write_text(json.dumps(value), encoding="utf-8")))
        stack.enter_context(patch.object(
            agent_runner, "heuristic_decide",
            lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("heuristic used"))))
        stack.enter_context(patch.object(
            agent_runner, "heuristic_assess",
            lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("heuristic used"))))
        yield events


class E0StableLaunchTests(unittest.TestCase):
    def test_no_probe_variant_uses_real_callbacks_without_probe(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TMP_ROOT)) as td, stub_runtime() as events, patch.object(
                agent_runner, "dispatch_probe", side_effect=AssertionError("probe executed")):
            state = {"probes_already_run": [], "probe_observations": []}
            adapter = AgnesDecisionAdapter(
                lambda _p: json.dumps(final_decision()), lambda _p: json.dumps(assessment()),
                lambda: state["probes_already_run"], lambda: state["probe_observations"])
            result = agent_runner.run_agent_case(
                "source.ply", "target.ply", str(Path(td) / "run"), "gt.npy",
                agnes_decide_fn=adapter.decide, agnes_assess_fn=adapter.assess,
                variant="REAL_AGNES_NO_PROBE", probe_state=state)
            self.assertEqual(result["probe_count"], 0)
            self.assertEqual(events, ["registration", "evaluator"])

    def test_active_probe_observation_reaches_second_decision(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TMP_ROOT)) as td, stub_runtime() as events:
            state = {"probes_already_run": [], "probe_observations": []}
            prompts = []

            def raw_decision(prompt):
                prompts.append(json.loads(prompt))
                if len(prompts) == 1:
                    return json.dumps(probe_decision("PCA_ORIENTATION"))
                self.assertEqual(prompts[-1]["probes"]["already_executed"], ["PCA_ORIENTATION"])
                self.assertEqual(prompts[-1]["probes"]["observations"][0]["probe_name"],
                                 "PCA_ORIENTATION")
                return json.dumps(final_decision())

            def fake_probe(name, *_a, **_k):
                events.append(f"probe:{name}")
                return {"orientation_confidence": "LOW", "rotation_estimate_deg": None}

            adapter = AgnesDecisionAdapter(
                raw_decision, lambda _p: json.dumps(assessment()),
                lambda: state["probes_already_run"], lambda: state["probe_observations"])
            with patch.object(agent_runner, "dispatch_probe", fake_probe):
                result = agent_runner.run_agent_case(
                    "source.ply", "target.ply", str(Path(td) / "run"), "gt.npy",
                    agnes_decide_fn=adapter.decide, agnes_assess_fn=adapter.assess,
                    variant="REAL_AGNES_ACTIVE_PROBE", probe_state=state)
            self.assertEqual(result["probe_count"], 1)
            self.assertEqual(len(prompts), 2)
            self.assertEqual(events, ["probe:PCA_ORIENTATION", "registration", "evaluator"])
            self.assertTrue((Path(td) / "run" / "probe_01_PCA_ORIENTATION.json").is_file())

    def test_no_probe_variant_rejects_model_probe_request(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TMP_ROOT)) as td, stub_runtime(), patch.object(
                agent_runner, "dispatch_probe", side_effect=AssertionError("probe executed")):
            with self.assertRaisesRegex(RuntimeError, "disabled by REAL_AGNES_NO_PROBE"):
                agent_runner.run_agent_case(
                    "source.ply", "target.ply", str(Path(td) / "run"), "gt.npy",
                    agnes_decide_fn=lambda *_a: probe_decision("PCA_ORIENTATION"),
                    agnes_assess_fn=lambda *_a: assessment(),
                    variant="REAL_AGNES_NO_PROBE",
                    probe_state={"probes_already_run": [], "probe_observations": []})

    def test_probe_limit_fails_closed(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TMP_ROOT)) as td, stub_runtime() as events, patch.object(
                agent_runner, "dispatch_probe", lambda name, *_a, **_k: {"probe_name": name}):
            requests = iter(["PCA_ORIENTATION", "CHEAP_LOCAL_ICP", "PCA_ORIENTATION"])
            with self.assertRaisesRegex(RuntimeError, "probe quota exhausted"):
                agent_runner.run_agent_case(
                    "source.ply", "target.ply", str(Path(td) / "run"), "gt.npy",
                    agnes_decide_fn=lambda *_a: probe_decision(next(requests)),
                    agnes_assess_fn=lambda *_a: assessment(),
                    variant="REAL_AGNES_ACTIVE_PROBE",
                    probe_state={"probes_already_run": [], "probe_observations": []})
            self.assertEqual(MAX_PROBES_PER_RUN, 2)
            self.assertNotIn("evaluator", events)

    def test_gt_isolation_and_evaluator_order(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TMP_ROOT)) as td, stub_runtime() as events:
            captured = []
            state = {"probes_already_run": [], "probe_observations": []}

            def decide(prompt):
                captured.append(prompt)
                return json.dumps(final_decision())

            def assess(prompt):
                captured.append(prompt)
                self.assertNotIn("evaluator", events)
                return json.dumps(assessment())

            adapter = AgnesDecisionAdapter(
                decide, assess, lambda: state["probes_already_run"],
                lambda: state["probe_observations"])
            agent_runner.run_agent_case(
                "source.ply", "target.ply", str(Path(td) / "run"), "secret_gt.npy",
                agnes_decide_fn=adapter.decide, agnes_assess_fn=adapter.assess,
                variant="REAL_AGNES_NO_PROBE", probe_state=state)
            joined = "\n".join(captured).lower()
            self.assertNotIn("secret_gt.npy", joined)
            self.assertNotIn("gt_transform", joined)
            self.assertEqual(events[-1], "evaluator")

    def test_invalid_assessment_schema_reports_clear_error(self):
        with tempfile.TemporaryDirectory(dir=str(TEST_TMP_ROOT)) as td, stub_runtime():
            state = {"probes_already_run": [], "probe_observations": []}
            adapter = AgnesDecisionAdapter(
                lambda _p: json.dumps(final_decision()),
                lambda _p: json.dumps(probe_decision("CHEAP_LOCAL_ICP")),
                lambda: state["probes_already_run"], lambda: state["probe_observations"])
            with self.assertRaisesRegex(RuntimeError, "invalid Agnes Assessment schema"):
                agent_runner.run_agent_case(
                    "source.ply", "target.ply", str(Path(td) / "run"), "secret_gt.npy",
                    agnes_decide_fn=adapter.decide, agnes_assess_fn=adapter.assess,
                    variant="REAL_AGNES_ACTIVE_PROBE", probe_state=state)


if __name__ == "__main__":
    unittest.main()
