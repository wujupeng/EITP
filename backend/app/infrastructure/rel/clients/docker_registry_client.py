"""Docker Registry 客户端 - 封装镜像查询。"""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.domain.rel.error_codes import RELErrorCode
from app.domain.rel.exceptions import RELError


@dataclass(frozen=True)
class ImageInfo:
    name: str
    tag: str
    digest: str | None
    is_locked: bool


class DockerRegistryClient:
    """Docker Registry API 客户端。"""

    def __init__(self, registry_url: str, username: str | None = None, password: str | None = None) -> None:
        self._registry_url = registry_url.rstrip("/")
        self._username = username
        self._password = password

    def _auth(self) -> httpx.BasicAuth | None:
        if self._username and self._password:
            return httpx.BasicAuth(self._username, self._password)
        return None

    async def get_image_digest(self, image_name: str, tag: str) -> str | None:
        async with httpx.AsyncClient(auth=self._auth()) as client:
            resp = await client.get(
                f"{self._registry_url}/v2/{image_name}/manifests/{tag}",
                headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
            )
            if resp.status_code == 404:
                return None
            if resp.status_code != 200:
                raise RELError(
                    RELErrorCode.IMAGE_PUSH_FAILED,
                    f"registry query failed: {resp.status_code}",
                )
            return resp.headers.get("Docker-Content-Digest")

    async def scan_compose_images(self, compose_file_path: str) -> list[ImageInfo]:
        import yaml
        from pathlib import Path
        content = Path(compose_file_path).read_text(encoding="utf-8")
        compose = yaml.safe_load(content)
        images: list[ImageInfo] = []
        for service_name, service_config in compose.get("services", {}).items():
            image_ref = service_config.get("image", "")
            if not image_ref:
                continue
            parts = image_ref.rsplit(":", 1)
            name = parts[0]
            tag = parts[1] if len(parts) > 1 else "latest"
            is_locked = ":" in image_ref and tag != "latest"
            digest = None
            if is_locked:
                digest = await self.get_image_digest(name, tag)
            images.append(ImageInfo(name=name, tag=tag, digest=digest, is_locked=is_locked))
        return images