import unittest
from pathlib import Path

from app.core.config import BACKEND_DIR, PROJECT_ROOT, Settings


class SettingsEnvFileTest(unittest.TestCase):
    def test_settings_loads_env_files_from_project_root_and_backend_dir(self):
        env_files = Settings.model_config["env_file"]
        env_paths = [Path(item) for item in env_files]

        self.assertIn(PROJECT_ROOT / ".env", env_paths)
        self.assertIn(BACKEND_DIR / ".env", env_paths)

    def test_default_ai_provider_is_volcengine_doubao(self):
        settings = Settings(_env_file=None)

        self.assertEqual(
            settings.ai_base_url,
            "https://ark.cn-beijing.volces.com/api/v3",
        )
        self.assertEqual(settings.ai_model, "doubao-seed-2-0-mini-260428")
        self.assertEqual(settings.agent_model, "doubao-seed-2-0-mini-260428")
        self.assertEqual(settings.methodology_model, "doubao-seed-2-0-mini-260428")


if __name__ == "__main__":
    unittest.main()
