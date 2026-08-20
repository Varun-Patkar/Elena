import argparse
import asyncio
import base64
import json
import time
from pathlib import Path
from typing import Any

import httpx

from elena.runtime import default_data_dir

RED_PIXEL_PNG = base64.b64encode(
    bytes.fromhex(
        "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de"
        "0000000c4944415408d763f8cfc0000003010100c9fe92ef0000000049454e44ae426082"
    )
).decode("ascii")


async def request_probe(
    client: httpx.AsyncClient, endpoint: str, payload: dict[str, Any]
) -> dict[str, Any]:
    started = time.perf_counter()
    try:
        response = await client.post(f"{endpoint}/chat/completions", json=payload)
        elapsed = round(time.perf_counter() - started, 2)
        response.raise_for_status()
        body = response.json()
        message = body["choices"][0]["message"]
        return {
            "ok": True,
            "seconds": elapsed,
            "content": message.get("content"),
            "reasoning": message.get("reasoning_content") or message.get("reasoning"),
            "tool_calls": message.get("tool_calls"),
            "finish_reason": body["choices"][0].get("finish_reason"),
        }
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        return {
            "ok": False,
            "seconds": round(time.perf_counter() - started, 2),
            "error": str(error),
        }


async def probe_model(
    client: httpx.AsyncClient, endpoint: str, model: str
) -> dict[str, Any]:
    base = {"model": model, "temperature": 0, "max_tokens": 96, "stream": False}
    text = await request_probe(
        client,
        endpoint,
        {
            **base,
            "messages": [
                {"role": "user", "content": "Reply with exactly ELENA_TEXT_OK"}
            ],
        },
    )
    tools = await request_probe(
        client,
        endpoint,
        {
            **base,
            "messages": [
                {
                    "role": "user",
                    "content": "Call probe_tool with value 7. Do not answer directly.",
                }
            ],
            "tools": [
                {
                    "type": "function",
                    "function": {
                        "name": "probe_tool",
                        "description": "Capability test",
                        "parameters": {
                            "type": "object",
                            "properties": {"value": {"type": "integer"}},
                            "required": ["value"],
                        },
                    },
                }
            ],
        },
    )
    image = await request_probe(
        client,
        endpoint,
        {
            **base,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What color is this pixel?"},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{RED_PIXEL_PNG}"
                            },
                        },
                    ],
                }
            ],
        },
    )
    return {"model": model, "text": text, "tools": tools, "image": image}


async def discover(endpoint: str, token: str | None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    async with httpx.AsyncClient(headers=headers, timeout=180) as client:
        response = await client.get(f"{endpoint}/models")
        response.raise_for_status()
        model_ids = [item["id"] for item in response.json().get("data", [])]
        generative_models = [
            model for model in model_ids if "embed" not in model.lower()
        ]
        results = []
        for model in generative_models:
            print(f"Probing {model}...")
            results.append(await probe_model(client, endpoint, model))
    return {"endpoint": endpoint, "models": results}


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe LM Studio model capabilities")
    parser.add_argument("--endpoint", default="http://127.0.0.1:1234/v1")
    parser.add_argument("--token")
    parser.add_argument(
        "--output", type=Path, default=default_data_dir() / "model-capabilities.json"
    )
    arguments = parser.parse_args()
    report = asyncio.run(discover(arguments.endpoint.rstrip("/"), arguments.token))
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Capability report written to {arguments.output}")


if __name__ == "__main__":
    main()