import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.services import ai_service


def _async_return(value):
    async def _fake(*args, **kwargs):
        return value
    return _fake


class DoubaoQuestionGenerationTest(unittest.IsolatedAsyncioTestCase):
    async def test_generate_questions_from_transcript_parses_questions(self):
        captured = {}

        async def fake_responses(*, instructions, content, **kwargs):
            captured["instructions"] = instructions
            captured["content"] = content
            return (
                '{"questions":[{"content":"推荐镜片时首先应确认什么？","type":"single",'
                '"options":{"A":"顾客用眼场景","B":"直接报价","C":"库存","D":"包装"},'
                '"answer":"A","analysis":"[00:10] 先确认场景才能匹配产品价值。","tags":["镜片推荐"]}]}'
            )

        with patch.object(ai_service.settings, "ai_api_key", "test-key"), patch.object(
            ai_service, "_call_responses", fake_responses
        ):
            questions = await ai_service.generate_questions_from_transcript(
                transcript="[00:10] 先确认顾客的用眼场景。",
                video_title="镜片销售",
                count=1,
                difficulty_level="L2",
                question_type_ratios={"single": 100, "multiple": 0, "true_false": 0},
                category_id=2,
                video_id=8,
            )

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["content"], "推荐镜片时首先应确认什么？")
        self.assertEqual(questions[0]["answer"], "A")
        self.assertEqual(questions[0]["source"], "ai")
        self.assertEqual(questions[0]["category_id"], 2)
        # user prompt must carry the transcript with timestamps
        self.assertIn("transcript_with_timestamps", captured["content"][0]["text"])
        self.assertIn("[00:10]", captured["content"][0]["text"])

    async def test_generate_questions_transcribes_then_generates(self):
        async def fake_transcribe(video_path):
            return "[00:05] 顾客提出价格异议时要回到价值。"

        async def fake_responses(*, instructions, content, **kwargs):
            return (
                '{"questions":[{"content":"顾客提价格异议更合适的做法？","type":"single",'
                '"options":{"A":"回到需求和价值","B":"立即放弃","C":"只说最低价","D":"回避"},'
                '"answer":"A","analysis":"[00:05] 价格异议要结合价值。"}]}'
            )

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            ai_service.settings, "upload_dir", tmp_dir
        ), patch.object(ai_service.settings, "ai_api_key", "test-key"), patch.object(
            ai_service, "transcribe_video_audio", fake_transcribe
        ), patch.object(ai_service, "_call_responses", fake_responses):
            Path(tmp_dir, "demo.mp4").write_bytes(b"fake-video")
            questions = await ai_service.generate_questions(
                video_title="异议处理",
                video_file_url="/uploads/demo.mp4",
                count=1,
                difficulty_level="L2",
                question_type_ratios={"single": 100, "multiple": 0, "true_false": 0},
                category_id=2,
                video_id=8,
                user_requirements="偏向门店实战",
            )

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["content"], "顾客提价格异议更合适的做法？")
        self.assertEqual(questions[0]["source"], "ai")

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

    async def test_generate_questions_rejects_true_false_answer_outside_ab(self):
        async def fake_transcribe(video_path):
            return "[19:32] 视频提到镜片直径要求。"

        async def fake_responses(*, instructions, content, **kwargs):
            return (
                '{"questions":[{"content":"关于镜片直径要求的说法是否正确？","type":"true_false",'
                '"options":{"A":"正确","B":"错误"},"answer":"C","analysis":"[19:32] 视频提到。"}]}'
            )

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            ai_service.settings, "upload_dir", tmp_dir
        ), patch.object(ai_service.settings, "ai_api_key", "test-key"), patch.object(
            ai_service, "transcribe_video_audio", fake_transcribe
        ), patch.object(ai_service, "_call_responses", fake_responses):
            Path(tmp_dir, "demo.mp4").write_bytes(b"fake-video")
            with self.assertRaisesRegex(ai_service.AIQuestionGenerationError, "答案.*A/B"):
                await ai_service.generate_questions(
                    video_title="多焦RGP验配",
                    video_file_url="/uploads/demo.mp4",
                    count=1,
                    difficulty_level="L2",
                    question_type_ratios={"true_false": 100},
                )

    async def test_generate_questions_raises_when_llm_returns_no_questions(self):
        async def fake_transcribe(video_path):
            return "[00:01] 一些内容。"

        with tempfile.TemporaryDirectory() as tmp_dir, patch.object(
            ai_service.settings, "upload_dir", tmp_dir
        ), patch.object(ai_service.settings, "ai_api_key", "test-key"), patch.object(
            ai_service, "transcribe_video_audio", fake_transcribe
        ), patch.object(ai_service, "_call_responses", _async_return('{"questions":[]}')):
            Path(tmp_dir, "demo.mp4").write_bytes(b"fake-video")
            with self.assertRaisesRegex(ai_service.AIQuestionGenerationError, "未返回题目"):
                await ai_service.generate_questions(
                    video_title="镜片销售",
                    video_file_url="/uploads/demo.mp4",
                    count=1,
                    difficulty_level="L2",
                    question_type_ratios={"single": 100},
                )


class AsrTimestampFormattingTest(unittest.TestCase):
    def test_format_asr_timestamps_converts_seconds_to_mmss(self):
        raw = "0.0-3.2-大家好今天讲镜片销售\n65.5-70.0-第二句内容；"
        formatted = ai_service._format_asr_timestamps(raw)
        lines = formatted.splitlines()
        self.assertEqual(lines[0], "[00:00] 大家好今天讲镜片销售")
        self.assertEqual(lines[1], "[01:05] 第二句内容")

    def test_format_asr_timestamps_keeps_unmatched_lines(self):
        raw = "这是一段没有时间戳的文本"
        self.assertEqual(
            ai_service._format_asr_timestamps(raw), "这是一段没有时间戳的文本"
        )


class ResponseParsingTest(unittest.TestCase):
    def test_parse_questions_handles_trailing_comma_and_fence(self):
        content = (
            "```json\n"
            '{"questions":[{"content":"题1","type":"single",'
            '"options":{"A":"a","B":"b","C":"c","D":"d"},"answer":"A","analysis":"x",}]}\n'
            "```"
        )
        questions = ai_service.parse_questions_from_content(content)
        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["content"], "题1")

    def test_extract_output_text_handles_object_and_dict(self):
        class _Block:
            def __init__(self, text):
                self.text = text

        class _Item:
            def __init__(self, blocks):
                self.content = blocks

        class _Resp:
            output_text = None
            output = [_Item([_Block("hello "), _Block("world")])]

        self.assertEqual(ai_service._extract_output_text(_Resp()), "hello world")
        dict_resp = {"output": [{"content": [{"text": "from dict"}]}]}
        self.assertEqual(ai_service._extract_output_text(dict_resp), "from dict")


if __name__ == "__main__":
    unittest.main()
