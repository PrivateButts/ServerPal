import asyncio
from config import load_config

CONFIG = load_config()


async def main():
    process = await asyncio.create_subprocess_exec(
        CONFIG.discord.server_start_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            asyncio.shield(process.communicate()), timeout=5
        )
        print("server failed to start!")
        print(stdout.decode())
        print(stderr.decode())
    except asyncio.TimeoutError:
        print("started server!")


asyncio.run(main())
