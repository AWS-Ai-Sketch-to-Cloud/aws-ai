from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError


SYSTEM_PROMPT = (
    "Return JSON only with this exact shape: "
    '{"ok": boolean, "service": "bedrock", "region": string}. '
    "No extra keys."
)


def load_backend_env() -> None:
    script_dir = Path(__file__).resolve().parent
    env_path = script_dir.parent / "backend" / ".env"
    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> int:
    load_backend_env()

    parser = argparse.ArgumentParser(description="Verify direct AWS Bedrock Runtime connectivity.")
    parser.add_argument(
        "--region",
        default=os.getenv("AWS_REGION", "ap-northeast-2"),
        help="AWS region for Bedrock runtime client",
    )
    parser.add_argument(
        "--model-id",
        default=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0"),
        help="Bedrock model id",
    )
    args = parser.parse_args()

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 120,
        "temperature": 0,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": [{"type": "text", "text": "ping"}]}],
    }

    try:
        client = boto3.client("bedrock-runtime", region_name=args.region)
        response = client.invoke_model(
            modelId=args.model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body),
        )
        payload = json.loads(response["body"].read())
        text_blocks = [block.get("text", "") for block in payload.get("content", []) if block.get("type") == "text"]
        text = "\n".join(x for x in text_blocks if x).strip()
        print("bedrock_verify=PASSED")
        print(f"region={args.region}")
        print(f"modelId={args.model_id}")
        print(f"rawResponse={text}")
        return 0
    except (ClientError, BotoCoreError) as e:
        print("bedrock_verify=FAILED")
        print(f"region={args.region}")
        print(f"modelId={args.model_id}")
        print(f"error={e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
