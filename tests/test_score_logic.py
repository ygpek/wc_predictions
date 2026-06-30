import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "app.py"


def load_helpers():
    module = ast.parse(SOURCE.read_text(encoding="utf-8"))
    namespace = {}
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name in {"safe_int", "match_has_result", "get_result"}:
            exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace


class ScoreLogicTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.helpers = load_helpers()

    def test_extra_time_score_is_used_when_no_penalties(self):
        match = {"score": {"et": [1, 2], "ft": [0, 0]}}
        self.assertEqual(self.helpers["get_result"](match), (1, 2))

    def test_penalties_add_one_goal_to_winner(self):
        match = {"score": {"p": [2, 3], "et": [1, 1], "ft": [1, 1]}}
        self.assertEqual(self.helpers["get_result"](match), (1, 2))

    def test_match_has_result_detects_et_and_p_scores(self):
        self.assertTrue(self.helpers["match_has_result"]({"score": {"et": [1, 0]}}))
        self.assertTrue(self.helpers["match_has_result"]({"score": {"p": [2, 3]}}))
        self.assertFalse(self.helpers["match_has_result"]({"score": {}}))


if __name__ == "__main__":
    unittest.main()
