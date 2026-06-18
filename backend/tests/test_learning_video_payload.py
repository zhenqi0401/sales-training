"""学员端 video_payload 应把 OSS 地址转成可播放的签名 URL。"""

import unittest
from unittest.mock import patch

from app.api.v1 import learning
from app.models.video import Video


class VideoPayloadPlayableUrlTest(unittest.TestCase):
    def test_oss_file_url_is_converted_to_playable_url(self):
        oss_url = "https://my-bucket.oss-cn-hangzhou.aliyuncs.com/videos/202606/abc.mp4"
        video = Video(id=1, title="x", file_url=oss_url, category_id=1, status="published")

        with patch.object(
            learning.oss_storage, "to_playable_url", return_value="https://signed"
        ) as conv:
            payload = learning.video_payload(video)

        conv.assert_called_once_with(oss_url)
        self.assertEqual(payload["url"], "https://signed")

    def test_local_file_url_passes_through(self):
        video = Video(
            id=2, title="x", file_url="/uploads/videos/abc.mp4", category_id=1, status="published"
        )

        # 真实 to_playable_url：本地路径原样返回，不签名
        payload = learning.video_payload(video)
        self.assertEqual(payload["url"], "/uploads/videos/abc.mp4")

    def test_empty_file_url_stays_empty(self):
        video = Video(id=3, title="x", file_url="", category_id=1, status="published")
        payload = learning.video_payload(video)
        self.assertEqual(payload["url"], "")


if __name__ == "__main__":
    unittest.main()
