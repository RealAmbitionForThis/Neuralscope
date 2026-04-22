"""RunPod REST API wrapper.

Uses https://rest.runpod.io/v1 directly via httpx rather than the Python
SDK, because the REST API is more complete and is documented by an
OpenAPI spec (fetchable from /v1/openapi.json). GPU types and pricing
are discovered at runtime, not hardcoded.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import httpx

logger = logging.getLogger(__name__)


RUNPOD_BASE_URL = "https://rest.runpod.io/v1"
DEFAULT_IMAGE = "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"


class RunPodError(Exception):
    pass


class RunPodService:
    def __init__(self, api_key: str) -> None:
        if not api_key:
            raise RunPodError("RunPod API key is required.")
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=RUNPOD_BASE_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def list_gpus(self) -> list[dict]:
        return await self._request("GET", "/gpus")

    async def list_pods(self) -> list[dict]:
        data = await self._request("GET", "/pods")
        return data if isinstance(data, list) else data.get("pods", [])

    async def get_pod(self, pod_id: str) -> dict:
        return await self._request("GET", f"/pods/{pod_id}")

    async def create_pod(
        self,
        name: str = "neuralscope",
        gpu_type_ids: Optional[list[str]] = None,
        gpu_count: int = 1,
        image: str = DEFAULT_IMAGE,
        container_disk_gb: int = 50,
        volume_gb: int = 100,
        env: Optional[dict[str, str]] = None,
        ports: str = "3000/http,8000/http",
    ) -> dict:
        payload: dict[str, Any] = {
            "name": name,
            "imageName": image,
            "gpuTypeIds": gpu_type_ids or ["NVIDIA A100 80GB PCIe"],
            "gpuCount": gpu_count,
            "containerDiskInGb": container_disk_gb,
            "volumeInGb": volume_gb,
            "ports": ports,
            "env": env or {},
        }
        return await self._request("POST", "/pods", json=payload)

    async def stop_pod(self, pod_id: str) -> dict:
        return await self._request("POST", f"/pods/{pod_id}/stop")

    async def start_pod(self, pod_id: str) -> dict:
        return await self._request("POST", f"/pods/{pod_id}/start")

    async def terminate_pod(self, pod_id: str) -> dict:
        return await self._request("DELETE", f"/pods/{pod_id}")

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            response = await self._client.request(method, path, **kwargs)
        except httpx.HTTPError as exc:
            raise RunPodError(f"RunPod request failed: {exc}") from exc

        if response.status_code >= 400:
            raise RunPodError(
                f"RunPod {method} {path} returned {response.status_code}: "
                f"{response.text[:500]}"
            )
        if not response.content:
            return {}
        try:
            return response.json()
        except ValueError:
            return response.text


def build_proxy_url(pod_id: str, port: int) -> str:
    """RunPod's documented HTTP proxy URL format."""
    return f"https://{pod_id}-{port}.proxy.runpod.net"
