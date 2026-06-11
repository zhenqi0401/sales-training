import unittest
from pydantic import ValidationError

from app.schemas.video import VideoCreate


class VideoCreateSchemaTest(unittest.TestCase):
    def test_requires_category_id(self):
        with self.assertRaises(ValidationError):
            VideoCreate.model_validate(
                {
                    "title": "Product demo",
                    "file_url": "/uploads/videos/demo.mp4",
                }
            )

    def test_accepts_category_id(self):
        video = VideoCreate.model_validate(
            {
                "title": "Product demo",
                "category_id": 8,
                "file_url": "/uploads/videos/demo.mp4",
            }
        )

        self.assertEqual(video.category_id, 8)


if __name__ == "__main__":
    unittest.main()
