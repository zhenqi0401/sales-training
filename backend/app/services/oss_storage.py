"""阿里云 OSS 对象存储封装。

仅负责"把本地文件传上去 / 下回来 / 删掉"以及 object key ↔ 公共 URL 的互转。
key 的命名（日期前缀等）由调用方决定，这层保持纯粹、易测。

所有 oss2 网络调用都集中在 ``_get_bucket`` 之后，方便测试时整体 mock。
"""

import tempfile
import uuid
from pathlib import Path

from app.core.config import settings


def is_enabled() -> bool:
    """是否启用 OSS 存储。"""
    return bool(settings.oss_enabled)


def _public_base() -> str:
    """公共访问前缀（不含末尾斜杠）。"""
    base = (settings.oss_public_base_url or "").strip()
    if base:
        return base.rstrip("/")
    return f"https://{settings.oss_bucket}.{settings.oss_endpoint}"


def build_public_url(object_key: str) -> str:
    """由 object key 拼出可直接播放的公共 URL。"""
    return f"{_public_base()}/{object_key.lstrip('/')}"


def is_oss_url(file_url: str) -> bool:
    """判断 file_url 是否为 OSS 绝对地址（区别于本地 /uploads/... 路径）。"""
    return file_url.startswith("http://") or file_url.startswith("https://")


def object_key_from_url(file_url: str) -> str:
    """从存库的 file_url 反解出 object key；传入裸 key 时原样返回。"""
    if not is_oss_url(file_url):
        return file_url.lstrip("/")
    base = _public_base()
    if file_url.startswith(base):
        return file_url[len(base):].lstrip("/")
    # 兜底：去掉协议和域名，取路径部分
    without_scheme = file_url.split("://", 1)[-1]
    path = without_scheme.split("/", 1)[1] if "/" in without_scheme else ""
    return path


def _https_endpoint() -> str:
    """确保 endpoint 带 https scheme，避免签出的 URL 是 http（被 https 页面拦为混合内容）。"""
    endpoint = (settings.oss_endpoint or "").strip()
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    return f"https://{endpoint}"


def _get_bucket():
    """构造 oss2.Bucket（延迟导入，避免未启用时强依赖 oss2）。"""
    import oss2

    auth = oss2.Auth(settings.oss_access_key_id, settings.oss_access_key_secret)
    return oss2.Bucket(auth, _https_endpoint(), settings.oss_bucket)


def upload_file(local_path: Path, object_key: str) -> str:
    """上传本地文件到 OSS，返回公共 URL。"""
    bucket = _get_bucket()
    bucket.put_object_from_file(object_key, str(local_path))
    return build_public_url(object_key)


def download_to_temp(file_url_or_key: str) -> Path:
    """把 OSS 对象下载到临时 .mp4 文件，返回本地路径（调用方负责删除）。"""
    key = object_key_from_url(file_url_or_key)
    suffix = Path(key).suffix or ".mp4"
    fd, tmp_name = tempfile.mkstemp(prefix="oss_", suffix=suffix)
    import os

    os.close(fd)
    temp_path = Path(tmp_name)
    bucket = _get_bucket()
    bucket.get_object_to_file(key, str(temp_path))
    return temp_path


# 学员端播放用的签名 URL 默认有效期（12 小时，覆盖一次完整观看 + 拖动）
DEFAULT_SIGN_EXPIRES = 12 * 3600


def sign_url(file_url_or_key: str, expires: int = 3600) -> str:
    """为私有桶对象生成带时效的签名 GET URL（纯本地计算，无网络请求）。"""
    key = object_key_from_url(file_url_or_key)
    bucket = _get_bucket()
    return bucket.sign_url("GET", key, expires, slash_safe=True)


def to_playable_url(file_url: str, expires: int = DEFAULT_SIGN_EXPIRES) -> str:
    """把存库的 file_url 转成客户端可直接播放的地址。

    OSS 地址 → 临时签名 URL；本地 /uploads 路径或空值 → 原样返回。
    """
    if not file_url:
        return file_url
    if is_oss_url(file_url):
        return sign_url(file_url, expires)
    return file_url


def delete_object(file_url_or_key: str) -> None:
    """删除 OSS 对象。"""
    key = object_key_from_url(file_url_or_key)
    bucket = _get_bucket()
    bucket.delete_object(key)


def build_object_key(prefix: str, ext: str) -> str:
    """生成带日期前缀的 object key：{prefix}/{YYYYMM}/{uuid}{ext}。"""
    from datetime import datetime, timezone

    month = datetime.now(timezone.utc).strftime("%Y%m")
    ext = ext if ext.startswith(".") else f".{ext}"
    return f"{prefix}/{month}/{uuid.uuid4().hex}{ext}"
