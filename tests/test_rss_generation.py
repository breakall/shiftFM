import tempfile
import unittest
from pathlib import Path

import server


class TestRssGeneration(unittest.TestCase):
    def test_generate_rss_from_recordings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            base_dir = Path(tmp_dir)
            recordings_dir = base_dir / "recordings"
            recordings_dir.mkdir(parents=True, exist_ok=True)
            rss_path = base_dir / "rss.xml"

            files = [
                "show_one_101.1_2024-01-01_1200.mp3",
                "news_99.5_2024-01-02_1200.mp3",
            ]
            for name in files:
                (recordings_dir / name).write_bytes(b"fake mp3 data")

            original_recordings = server.RECORDINGS_DIR
            original_rss = server.RSS_PATH
            try:
                server.RECORDINGS_DIR = recordings_dir
                server.RSS_PATH = rss_path
                server.generate_rss(
                    {
                        "base_url": "http://example.test",
                        "rss_title": "Test Feed",
                        "rss_description": "Test Description",
                    }
                )
            finally:
                server.RECORDINGS_DIR = original_recordings
                server.RSS_PATH = original_rss

            self.assertTrue(rss_path.exists())
            payload = rss_path.read_text(encoding="utf-8")
            self.assertIn(
                "http://example.test/recordings/show_one_101.1_2024-01-01_1200.mp3",
                payload,
            )
            self.assertIn(
                "http://example.test/recordings/news_99.5_2024-01-02_1200.mp3",
                payload,
            )
            self.assertIn("<title>show one 101.1 2024-01-01 1200</title>", payload)
            self.assertIn("<title>news 99.5 2024-01-02 1200</title>", payload)


if __name__ == "__main__":
    unittest.main()
