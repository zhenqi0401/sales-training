import unittest

from pydantic import ValidationError

from app.schemas.question import AIQuestionGenerate


class AIQuestionGenerateSchemaTest(unittest.TestCase):
    def test_accepts_user_requirements(self):
        payload = AIQuestionGenerate.model_validate(
            {
                "video_id": 10,
                "count": 1,
                "difficulty_level": "L2",
                "question_type_ratios": {"single": 100},
                "user_requirements": "重点考察门店实战话术",
            }
        )

        self.assertEqual(payload.user_requirements, "重点考察门店实战话术")

    def test_rejects_removed_transcript_field(self):
        with self.assertRaises(ValidationError):
            AIQuestionGenerate.model_validate(
                {
                    "video_id": 10,
                    "count": 1,
                    "difficulty_level": "L2",
                    "question_type_ratios": {"single": 100},
                    "transcript": "不再支持人工字幕/转写",
                }
            )


if __name__ == "__main__":
    unittest.main()
