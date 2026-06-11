import unittest
from pathlib import Path

from app.core.config import BACKEND_DIR, PROJECT_ROOT, Settings


class SettingsEnvFileTest(unittest.TestCase):
    def test_settings_loads_env_files_from_project_root_and_backend_dir(self):
        env_files = Settings.model_config["env_file"]
        env_paths = [Path(item) for item in env_files]

        self.assertIn(PROJECT_ROOT / ".env", env_paths)
        self.assertIn(BACKEND_DIR / ".env", env_paths)

    def test_default_ai_provider_is_bailian(self):
        settings = Settings(_env_file=None)

        self.assertEqual(
            settings.ai_base_url,
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.assertEqual(settings.ai_model, "qwen3.5-omni-flash")
        self.assertEqual(settings.ai_video_max_inline_mb, 100)
        self.assertEqual(settings.ai_video_max_data_url_chars, 10_000_000)


if __name__ == "__main__":
    unittest.main()
