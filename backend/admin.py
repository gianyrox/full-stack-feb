import asyncio
import os

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/api/admin", tags=["admin"])

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class RunRequest(BaseModel):
    message: str


class RunResponse(BaseModel):
    output: str
    error: str | None = None


@router.post("/run", response_model=RunResponse)
async def run_claude(req: RunRequest):
    try:
        proc = await asyncio.create_subprocess_exec(
            "claude", "--print", req.message,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=PROJECT_ROOT,
        )
        stdout, stderr = await proc.communicate()
        return RunResponse(
            output=stdout.decode(),
            error=stderr.decode() if proc.returncode != 0 else None,
        )
    except FileNotFoundError:
        return RunResponse(output="", error="claude CLI not found on PATH")
