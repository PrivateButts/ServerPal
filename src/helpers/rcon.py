import asyncio
import structlog

from config import load_config
from helpers.types import Player

log = structlog.get_logger()
CONFIG = load_config()


class RconError(Exception):
    error: str
    code: int

    def __init__(self, message: str, error: str, code: int):
        super().__init__(message)
        self.error = error
        self.code = code


class RCon:
    async def _run_server_command(self, command: str):
        process = await asyncio.create_subprocess_exec(
            CONFIG.rcon.path,
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            raise RconError(
                f"Command {command} caused rcon to return non-zero exit code.",
                error=stderr,
                code=process.returncode,
            )

        return stdout.decode()

    async def get_info(self):
        return await self._run_server_command("info")

    async def get_players(self):
        result = await self._run_server_command("showplayers")

        return [
            Player(*line.split(","))
            for index, line in enumerate(result.splitlines())
            if index > 0
        ]

    async def save(self):
        return await self._run_server_command("save")

    async def broadcast(self, message: str):
        return await self._run_server_command(f"broadcast {message}")

    async def shutdown(self, seconds: int = 15, message: str = "shutting_down"):
        return await self._run_server_command(f"shutdown {seconds} {message}")
