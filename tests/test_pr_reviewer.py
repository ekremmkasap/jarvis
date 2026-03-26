import unittest

from agents.pr_reviewer.parser import summarize_files


class PRReviewerTests(unittest.TestCase):
    def test_summarize_files_detects_high_risk_file(self) -> None:
        files = [
            {'filename': 'server/bridge.py', 'changes': 320, 'additions': 200, 'deletions': 120, 'status': 'modified'},
            {'filename': 'README.md', 'changes': 20, 'additions': 15, 'deletions': 5, 'status': 'modified'},
        ]
        summary = summarize_files(files)
        self.assertEqual(summary['total_files'], 2)
        self.assertEqual(len(summary['high_risk']), 1)
        self.assertEqual(summary['high_risk'][0]['filename'], 'server/bridge.py')


if __name__ == '__main__':
    unittest.main()
