"""Launch NeuralScope on RunPod with one command.

Uses the RunPod REST API directly via httpx. Does not depend on the
NeuralScope backend being running locally -- this is a standalone launcher.

Usage:
    python scripts/launch_runpod.py --api-key $RUNPOD_API_KEY
    python scripts/launch_runpod.py --api-key $RUNPOD_API_KEY --gpu-type "NVIDIA A100 80GB PCIe"
    python scripts/launch_runpod.py --api-key $RUNPOD_API_KEY --model meta-llama/Llama-3.1-70B-Instruct
"""

from __future__ import annotations

import argparse
import sys
import time

import httpx

DEFAULT_IMAGE = "runpod/pytorch:2.1.0-py3.10-cuda11.8.0-devel-ubuntu22.04"
BASE_URL = "https://rest.runpod.io/v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch NeuralScope on RunPod")
    parser.add_argument("--api-key", required=True, help="RunPod API key")
    parser.add_argument("--name", default="neuralscope")
    parser.add_argument("--gpu-type", default="NVIDIA A100 80GB PCIe")
    parser.add_argument("--gpu-count", type=int, default=1)
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--volume-gb", type=int, default=100)
    parser.add_argument("--container-disk-gb", type=int, default=50)
    parser.add_argument("--model", default="", help="Pre-download this HF model on startup")
    parser.add_argument("--poll-timeout", type=int, default=300)
    return parser.parse_args()


def create_pod(client: httpx.Client, args: argparse.Namespace) -> dict:
    env = {"NEURALSCOPE_MODE": "production"}
    if args.model:
        env["PRELOAD_MODEL"] = args.model

    response = client.post(
        "/pods",
        json={
            "name": args.name,
            "imageName": args.image,
            "gpuTypeIds": [args.gpu_type],
            "gpuCount": args.gpu_count,
            "containerDiskInGb": args.container_disk_gb,
            "volumeInGb": args.volume_gb,
            "ports": "3000/http,8000/http,22/tcp",
            "env": env,
        },
    )
    response.raise_for_status()
    return response.json()


def poll_until_running(
    client: httpx.Client, pod_id: str, timeout_seconds: int
) -> dict:
    deadline = time.time() + timeout_seconds
    last_status = None
    attempt = 0
    while time.time() < deadline:
        attempt += 1
        response = client.get(f"/pods/{pod_id}")
        response.raise_for_status()
        pod = response.json()
        status = pod.get("desiredStatus") or pod.get("status") or "unknown"
        if status != last_status:
            print(f"  status: {status}")
            last_status = status
        if status.upper() == "RUNNING":
            return pod
        time.sleep(5)
    raise TimeoutError(f"Pod {pod_id} did not reach RUNNING within {timeout_seconds}s")


def main() -> int:
    args = parse_args()

    print(f"Launching NeuralScope pod on RunPod...")
    print(f"  GPU: {args.gpu_count}x {args.gpu_type}")
    print(f"  Image: {args.image}")
    if args.model:
        print(f"  Preload model: {args.model}")

    client = httpx.Client(
        base_url=BASE_URL,
        headers={"Authorization": f"Bearer {args.api_key}"},
        timeout=30.0,
    )

    try:
        pod = create_pod(client, args)
        pod_id = pod.get("id") or pod.get("podId")
        print(f"\nPod created: {pod_id}\nWaiting for it to start...")

        running = poll_until_running(client, pod_id, args.poll_timeout)
    except httpx.HTTPStatusError as exc:
        print(f"\nRunPod API error: {exc.response.status_code}")
        print(exc.response.text)
        return 1
    finally:
        client.close()

    proxy_base = f"https://{pod_id}-{{port}}.proxy.runpod.net"
    print("\nPod is RUNNING")
    print(f"  Frontend: {proxy_base.format(port=3000)}")
    print(f"  Backend:  {proxy_base.format(port=8000)}")
    print(f"\n  In the NeuralScope UI, go to Settings and set Backend URL to:")
    print(f"  {proxy_base.format(port=8000)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
