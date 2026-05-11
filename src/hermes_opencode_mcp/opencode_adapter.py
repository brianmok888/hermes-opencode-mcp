from __future__ import annotations

import asyncio
import json
import shutil
from dataclasses import dataclass

from .sanitizer import sanitize_text


@dataclass(slots=True)
class AdapterResult:
    summary: str
    error: str | None = None
    metadata: dict | None = None
    cancelled: bool = False


class OpenCodeAdapter:
    def __init__(self, opencode_bin: str) -> None:
        self.opencode_bin = opencode_bin

    def validate(self) -> None:
        if not shutil.which(self.opencode_bin):
            raise RuntimeError(f"OpenCode binary not found in PATH: {self.opencode_bin}")

    async def run(
        self,
        *,
        text: str,
        directory: str,
        agent: str | None = None,
        session_id: str | None = None,
        timeout_ms: int = 300000,
        cancel_check=None,
    ) -> AdapterResult:
        cmd = [self.opencode_bin, "run", "--pure", "--format", "json", "--dir", directory]
        if agent:
            cmd += ["--agent", agent]
        if session_id:
            cmd += ["--session", session_id]
        cmd += [text]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        base_metadata: dict = {
            "process_id": proc.pid,
            "command": cmd,
        }
        timeout_seconds = max(1, timeout_ms / 1000)
        deadline = asyncio.get_running_loop().time() + timeout_seconds

        while True:
            if cancel_check is not None and cancel_check():
                proc.kill()
                raw, _ = await proc.communicate()
                output = raw.decode("utf-8", errors="replace")
                metadata = self._build_result_metadata(base_metadata, proc.returncode, output)
                metadata["cancelled"] = True
                return AdapterResult(
                    summary="",
                    error="opencode execution cancelled during execution",
                    metadata=metadata,
                    cancelled=True,
                )
            if proc.returncode is not None:
                break
            if asyncio.get_running_loop().time() >= deadline:
                proc.kill()
                await proc.communicate()
                timeout_metadata = dict(base_metadata)
                timeout_metadata.update({"return_code": None, "execution_handle": f"pid:{proc.pid}"})
                return AdapterResult(summary="", error="opencode execution timed out", metadata=timeout_metadata)
            try:
                await asyncio.wait_for(proc.wait(), timeout=0.05)
            except asyncio.TimeoutError:
                continue

        raw, _ = await proc.communicate()
        output = raw.decode("utf-8", errors="replace")
        summary, _ = parse_opencode_output(output)
        metadata = self._build_result_metadata(base_metadata, proc.returncode, output)
        if proc.returncode != 0 and not summary:
            return AdapterResult(summary="", error=sanitize_text(output[-4000:]), metadata=metadata)
        return AdapterResult(summary=summary or "OpenCode completed with no textual summary.", metadata=metadata)

    @staticmethod
    def _build_result_metadata(base_metadata: dict, return_code: int | None, output: str) -> dict:
        summary, session = parse_opencode_output(output)
        metadata = dict(base_metadata)
        metadata["return_code"] = return_code
        if session:
            metadata["session_id"] = session
            metadata["execution_handle"] = f"session:{session}"
        else:
            metadata["execution_handle"] = f"pid:{base_metadata['process_id']}"
        if summary:
            metadata["parsed_summary_present"] = True
        return metadata


def parse_opencode_output(output: str) -> tuple[str, str | None]:
    text_parts: list[str] = []
    session_id: str | None = None
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not session_id:
            session_id = event.get("sessionID")
        if event.get("type") == "text":
            part = event.get("part") or {}
            text = part.get("text")
            if isinstance(text, str) and text.strip():
                text_parts.append(text.strip())
    combined = "\n\n".join(text_parts).strip()
    return sanitize_text(combined), session_id
