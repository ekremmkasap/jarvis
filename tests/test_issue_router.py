import unittest

from agents.issue_router.labels import infer_labels, infer_priority


class IssueRouterTests(unittest.TestCase):
    def test_issue_router_infers_labels_and_priority(self) -> None:
        config = {
            'default_labels': ['needs-triage'],
            'keyword_labels': {'crash': ['bug', 'priority:high']},
            'priority_keywords': {'high': ['crash'], 'medium': ['bug'], 'low': ['docs']},
        }
        labels = infer_labels('App crash on startup', 'Crash after login', config)
        priority = infer_priority('App crash on startup', 'Crash after login', config)
        self.assertIn('bug', labels)
        self.assertEqual(priority, 'high')


if __name__ == '__main__':
    unittest.main()
