"""Hand the clip-selection step to a person or chat assistant instead of an LLM API.

With ``LLM=handoff``, the worker writes the transcript and the full selection
brief to ``HANDOFF_DIR/<id>.request.md`` and waits for ``<id>.response.json``.
Whoever answers (for example Claude in a chat that can read the shared folder)
writes a TranscriptAnalysis JSON object there. Invalid responses are renamed to
``<id>.response.invalid.json`` with the reason in ``<id>.error.txt`` and the
worker keeps waiting for a corrected file. The rest of the pipeline (bounds
validation, dedupe, clip budget, rendering) is unchanged.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

POLL_SECONDS = 3


def handoff_dir() -> Path:
    return Path(os.getenv("HANDOFF_DIR", "/app/handoff"))


def handoff_timeout_seconds() -> float:
    try:
        return float(os.getenv("HANDOFF_TIMEOUT_SECONDS", "10000"))
    except ValueError:
        return 10000.0


def _write_atomic(path: Path, text: str) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def build_request_document(
    request_id: str,
    system_prompt: str,
    task_prompt: str,
    schema: dict,
    clip_budget: int,
    source_seconds: float,
) -> str:
    minutes = source_seconds / 60 if source_seconds else 0
    return f"""# Clip selection request {request_id}

Created: {datetime.now().isoformat(timespec="seconds")}
Source length: {minutes:.1f} min. Clip budget: return the best clips, at most {clip_budget}
(the app keeps the top {clip_budget} by virality score).

## How to answer

Write ONE JSON object (the TranscriptAnalysis schema below) to:

    {request_id}.response.json

in this same folder. Use timestamps exactly as they appear in the transcript
(MM:SS or HH:MM:SS). Each clip must be 15-60 seconds and one contiguous range.
If the file is invalid, it is renamed to {request_id}.response.invalid.json and the
reason is written to {request_id}.error.txt; fix it and write the response again.

## Role

{system_prompt}

## Task

{task_prompt}

## JSON schema (TranscriptAnalysis)

```json
{json.dumps(schema, indent=2)}
```
"""


async def run_handoff_analysis(
    system_prompt: str,
    task_prompt: str,
    output_model,
    clip_budget: int,
    source_seconds: float,
):
    """Write the request, then wait for a valid response parsed as ``output_model``."""
    directory = handoff_dir()
    directory.mkdir(parents=True, exist_ok=True)
    request_id = datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
    request_path = directory / f"{request_id}.request.md"
    response_path = directory / f"{request_id}.response.json"
    invalid_path = directory / f"{request_id}.response.invalid.json"
    error_path = directory / f"{request_id}.error.txt"
    done_path = directory / f"{request_id}.done.json"

    _write_atomic(
        request_path,
        build_request_document(
            request_id,
            system_prompt,
            task_prompt,
            output_model.model_json_schema(),
            clip_budget,
            source_seconds,
        ),
    )
    logger.info("Clip selection handed off: waiting for %s", response_path.name)

    deadline = time.monotonic() + handoff_timeout_seconds()
    while time.monotonic() < deadline:
        if response_path.exists():
            raw: Optional[str] = None
            try:
                raw = response_path.read_text(encoding="utf-8")
                parsed = output_model.model_validate_json(raw)
            except Exception as error:  # invalid JSON or schema mismatch
                if raw is None:
                    await asyncio.sleep(POLL_SECONDS)
                    continue
                os.replace(response_path, invalid_path)
                _write_atomic(error_path, f"{type(error).__name__}: {error}\n")
                logger.warning("Handoff response %s rejected: %s", request_id, error)
            else:
                os.replace(response_path, done_path)
                error_path.unlink(missing_ok=True)
                invalid_path.unlink(missing_ok=True)
                request_path.unlink(missing_ok=True)
                logger.info("Handoff response %s accepted", request_id)
                return parsed
        await asyncio.sleep(POLL_SECONDS)

    request_path.unlink(missing_ok=True)
    raise RuntimeError(
        "Nobody answered the clip selection request in time. "
        "Ask Claude to pick the clips, then retry the task."
    )
