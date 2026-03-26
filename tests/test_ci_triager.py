import unittest

from agents.ci_triager.heuristics import classify_failure


class CITriagerTests(unittest.TestCase):
    def test_classify_failure_matches_missing_dependency(self) -> None:
        result = classify_failure('ModuleNotFoundError: No module named yaml')
        self.assertIn('Missing Python dependency', result['root_cause'])


if __name__ == '__main__':
    unittest.main()
