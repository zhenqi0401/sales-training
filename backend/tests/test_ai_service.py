import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services import ai_service


class BailianQuestionGenerationTest(unittest.IsolatedAsyncioTestCase):
    async def test_call_question_llm_posts_bailian_video_payload_and_parses_questions(self):
        captured_payload = {}

        def fake_post(payload, timeout_seconds):
            captured_payload.update(payload)
            return """
            data: {"choices":[{"delta":{"content":"{\\"questions\\":["}}]}
            data: {"choices":[{"delta":{"content":"{\\"content\\":\\"推荐镜片时首先应确认什么？\\",\\"type\\":\\"single\\",\\"options\\":{\\"A\\":\\"顾客用眼场景\\",\\"B\\":\\"直接报价\\",\\"C\\":\\"库存\\",\\"D\\":\\"包装\\"},\\"answer\\":\\"A\\",\\"analysis\\":\\"先确认场景才能匹配产品价值。\\",\\"tags\\":[\\"镜片推荐\\"]}"}}]}
            data: {"choices":[{"delta":{"content":"]}"}}]}
            data: [DONE]
            """

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            ai_service.settings, "upload_dir", tmp_dir
        ), patch.object(ai_service.settings, "ai_api_key", "test-key"), patch.object(
            ai_service.settings, "ai_model", "qwen3.5-omni-flash"
        ), patch.object(
            ai_service.settings, "ai_video_fps", 1
        ), patch.object(ai_service, "_post_chat_completion", fake_post):
            Path(tmp_dir, "demo.mp4").write_bytes(b"fake-video")
            result = await ai_service.call_question_llm(
                {
                    "count": 1,
                    "difficulty_level": "L2",
                    "question_types": ["single"],
                    "video": {"title": "镜片销售", "file_url": "/uploads/demo.mp4"},
                    "user_requirements": "重点考察需求确认",
                }
            )

        self.assertEqual(result[0]["content"], "推荐镜片时首先应确认什么？")
        self.assertEqual(captured_payload["model"], "qwen3.5-omni-flash")
        self.assertEqual(captured_payload["stream"], True)
        self.assertEqual(captured_payload["modalities"], ["text"])
        self.assertNotIn("enable_thinking", captured_payload)
        self.assertNotIn("thinking_budget", captured_payload)
        self.assertNotIn("response_format", captured_payload)
        self.assertEqual(captured_payload["messages"][0]["role"], "system")
        self.assertIn("JSON", captured_payload["messages"][0]["content"])
        user_content = captured_payload["messages"][1]["content"]
        self.assertIsInstance(user_content, list)
        self.assertEqual(user_content[0]["type"], "video_url")
        self.assertTrue(user_content[0]["video_url"]["url"].startswith("data:video/mp4;base64,"))
        self.assertEqual(user_content[0]["fps"], 1)
        self.assertEqual(set(user_content[0]["video_url"].keys()), {"url"})
        self.assertEqual(user_content[1]["type"], "text")
        self.assertIn("user_requirements", user_content[1]["text"])
        self.assertNotIn("transcript", user_content[1]["text"])

    async def test_call_question_llm_rejects_empty_model_content(self):
        def fake_post(payload, timeout_seconds):
            return {"choices": [{"message": {"content": ""}}]}

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            ai_service.settings, "upload_dir", tmp_dir
        ), patch.object(ai_service.settings, "ai_api_key", "test-key"), patch.object(
            ai_service, "_post_chat_completion", fake_post
        ):
            Path(tmp_dir, "demo.mp4").write_bytes(b"fake-video")
            with self.assertRaisesRegex(ai_service.AIQuestionGenerationError, "空响应"):
                await ai_service.call_question_llm(
                    {
                        "count": 1,
                        "question_types": ["single"],
                        "video": {"file_url": "/uploads/demo.mp4"},
                    }
                )

    async def test_generate_questions_uses_llm_instead_of_placeholder_questions(self):
        captured_prompt = {}

        async def fake_llm(prompt):
            captured_prompt.update(prompt)
            return [
                {
                    "content": "顾客提出价格异议时，销售顾问更合适的做法是什么？",
                    "type": "single",
                    "options": {"A": "回到需求和价值", "B": "立即放弃推荐", "C": "只说最低价", "D": "回避问题"},
                    "answer": "A",
                    "analysis": "价格异议需要结合需求、价值和证据回应。",
                }
            ]

        with patch.object(ai_service, "call_question_llm", fake_llm):
            questions = await ai_service.generate_questions(
                video_title="异议处理",
                video_file_url="/uploads/demo.mp4",
                count=1,
                difficulty_level="L2",
                question_type_ratios={"single": 100, "multiple": 0, "true_false": 0},
                category_id=2,
                video_id=8,
                user_requirements="希望偏向门店实战话术",
            )

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["content"], "顾客提出价格异议时，销售顾问更合适的做法是什么？")
        self.assertNotIn("占位", questions[0]["content"])
        self.assertEqual(questions[0]["source"], "ai")
        self.assertEqual(questions[0]["category_id"], 2)
        self.assertEqual(questions[0]["video_id"], 8)
        self.assertEqual(captured_prompt["video"]["file_url"], "/uploads/demo.mp4")
        self.assertEqual(captured_prompt["user_requirements"], "希望偏向门店实战话术")

    async def test_generate_questions_requires_video_file_url(self):
        with self.assertRaisesRegex(ai_service.AIQuestionGenerationError, "视频文件地址为空"):
            await ai_service.generate_questions(
                video_title="镜片销售",
                video_file_url="",
                count=1,
                difficulty_level="L2",
                question_type_ratios={"single": 100},
                user_requirements="生成实战题",
            )

    async def test_generate_questions_raises_when_llm_returns_no_questions(self):
        async def fake_llm(prompt):
            return []

        with patch.object(ai_service, "call_question_llm", fake_llm):
            with self.assertRaisesRegex(ai_service.AIQuestionGenerationError, "未返回题目"):
                await ai_service.generate_questions(
                    video_title="镜片销售",
                    video_file_url="/uploads/demo.mp4",
                    count=1,
                    difficulty_level="L2",
                    question_type_ratios={"single": 100},
                )

    async def test_generate_questions_rejects_true_false_answer_outside_ab(self):
        async def fake_llm(prompt):
            return [
                {
                    "content": "视频中关于镜片直径要求的说法是否正确？",
                    "type": "true_false",
                    "options": {"A": "正确", "B": "错误"},
                    "answer": "C",
                    "analysis": "19:32-19:36 视频提到镜片直径要求。",
                }
            ]

        with patch.object(ai_service, "call_question_llm", fake_llm):
            with self.assertRaisesRegex(ai_service.AIQuestionGenerationError, "答案.*A/B"):
                await ai_service.generate_questions(
                    video_title="多焦RGP验配",
                    video_file_url="/uploads/demo.mp4",
                    count=1,
                    difficulty_level="L2",
                    question_type_ratios={"true_false": 100},
                )

    def test_prompt_requires_ab_for_true_false_and_timestamped_option_analysis(self):
        payload = ai_service.build_chat_completion_payload(
            {
                "count": 3,
                "difficulty_level": "L2",
                "question_types": ["single", "multiple", "true_false"],
                "video": {"file_url": "https://example.com/demo.mp4"},
            }
        )

        system_prompt = payload["messages"][0]["content"]
        text_prompt = payload["messages"][1]["content"][1]["text"]

        self.assertIn("true_false 只能使用 A 或 B", system_prompt)
        self.assertIn("A=正确，B=错误", system_prompt)
        self.assertIn("每个选项", system_prompt)
        self.assertIn("时间段", system_prompt)
        self.assertIn("true_false_options", text_prompt)

    def test_resolve_video_input_uses_remote_url_directly(self):
        result = ai_service.build_video_url_payload("https://example.com/video.mp4")

        self.assertEqual(result, {"url": "https://example.com/video.mp4"})

    def test_resolve_video_input_encodes_local_upload_as_data_url(self):
        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(ai_service.settings, "upload_dir", tmp_dir):
            Path(tmp_dir, "clip.mp4").write_bytes(b"fake-video")

            result = ai_service.build_video_url_payload("/uploads/clip.mp4")

        self.assertTrue(result["url"].startswith("data:video/mp4;base64,"))

    def test_resolve_video_input_compresses_local_upload_when_data_url_exceeds_bailian_limit(self):
        with (
            tempfile.TemporaryDirectory() as tmp_dir,
            patch.object(ai_service.settings, "upload_dir", tmp_dir),
            patch.object(ai_service.settings, "ai_video_max_data_url_chars", 80, create=True),
            patch.object(
                ai_service,
                "build_compressed_video_data_url",
                return_value="data:video/mp4;base64,dGlueQ==",
                create=True,
            ) as compress,
        ):
            Path(tmp_dir, "clip.mp4").write_bytes(b"x" * 120)

            result = ai_service.build_video_url_payload("/uploads/clip.mp4")

        self.assertEqual(result, {"url": "data:video/mp4;base64,dGlueQ=="})
        compress.assert_called_once()

    def test_resolve_video_input_rejects_missing_local_upload(self):
        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(ai_service.settings, "upload_dir", tmp_dir):
            with self.assertRaisesRegex(ai_service.AIQuestionGenerationError, "视频文件不存在"):
                ai_service.build_video_url_payload("/uploads/missing.mp4")

    def test_compress_video_for_ai_uses_small_video_with_audio(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            source_path = Path(tmp_dir, "source.mp4")
            output_path = Path(tmp_dir, "ai.mp4")
            source_path.write_bytes(b"source")

            def fake_run(cmd, **kwargs):
                Path(cmd[-1]).write_bytes(b"compressed")
                return MagicMock(returncode=0, stdout="", stderr="")

            with (
                patch("app.services.ai_service.resolve_video_tool", return_value="ffmpeg"),
                patch.object(ai_service.settings, "ai_video_fps", 1),
                patch.object(ai_service.settings, "ai_video_compress_max_width", 640),
                patch.object(ai_service.settings, "ai_video_compress_crf", 35),
                patch.object(ai_service.settings, "ai_video_compress_audio_bitrate", "48k", create=True),
                patch("app.services.ai_service.subprocess.run", side_effect=fake_run) as run,
            ):
                ai_service.compress_video_for_ai(source_path, output_path)

            cmd = run.call_args.args[0]
            self.assertNotIn("-an", cmd)
            self.assertIn("0:a:0?", cmd)
            self.assertIn("-b:a", cmd)
            self.assertIn("48k", cmd)
            self.assertIn("-crf", cmd)
            self.assertIn("35", cmd)
            self.assertIn("-vf", cmd)
            self.assertIn("min(640,iw)", cmd[cmd.index("-vf") + 1])
            self.assertIn("fps=fps=1", cmd[cmd.index("-vf") + 1])
            self.assertEqual(output_path.read_bytes(), b"compressed")


if __name__ == "__main__":
    unittest.main()
