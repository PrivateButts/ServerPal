import asyncio
import structlog

from config import load_config
from helpers.rcon import RCon

from tasks.discord import start_bot
from tasks.autosleep import AutoSleep

log = structlog.get_logger()

CONFIG = load_config()
RCON = RCon()


async def main():
    log.info("Starting tasks")
    tasks = []
    if CONFIG.discord.enabled:
        log.info("Starting discord bot")
        tasks.append(start_bot(CONFIG.discord.token))
    if CONFIG.autosleep.enabled:
        log.info("Starting autosleep monitor")
        tasks.append(AutoSleep().task())
    await asyncio.gather(*tasks)
    log.info("Stopping server")


asyncio.run(main())
