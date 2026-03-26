import unittest

from agents.git_summarizer.summarize import build_stats


class GitSummarizerTests(unittest.TestCase):
    def test_build_stats_counts_authors(self) -> None:
        commits = [
            {'author': 'alice', 'subject': 'feat', 'sha': '1', 'date': '2026-03-26'},
            {'author': 'bob', 'subject': 'fix', 'sha': '2', 'date': '2026-03-26'},
            {'author': 'alice', 'subject': 'docs', 'sha': '3', 'date': '2026-03-26'},
        ]
        stats = build_stats(commits)
        self.assertEqual(stats['commit_count'], 3)
        self.assertEqual(stats['author_count'], 2)
        self.assertEqual(stats['top_authors'][0], ('alice', 2))


if __name__ == '__main__':
    unittest.main()
