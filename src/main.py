import asyncio
import structlog
from datetime import datetime, timedelta

from config import load_config
from helpers.rcon import RCon

log = structlog.get_logger()

CONFIG = load_config()
RCON = RCon()


async def main():
    # Call rcon to get server header
    result = await RCON.get_info()

    log.info(f"Server Header:\n{result}")

    shutdown_warning = False
    shutdown_at = None
    last_player_count = 0

    while True:
        # Call rcon to get player list
        players = await RCON.get_players()

        if len(players) > 0:
            if last_player_count != len(players):
                log.info(f"There's {len(players)} players online")
                last_player_count = len(players)
            shutdown_warning = False
            shutdown_at = None
            await asyncio.sleep(CONFIG.autosleep.watch_interval)
            continue

        if not shutdown_warning:
            log.info("There's no players online")
            log.info(
                f"Shutting down server in {CONFIG.autosleep.shutdown_timeout} seconds if no players join"
            )
            shutdown_warning = True
            shutdown_at = datetime.now() + timedelta(
                seconds=CONFIG.autosleep.shutdown_timeout
            )

        if shutdown_at and datetime.now() < shutdown_at - timedelta(seconds=60):
            log.info(f"Shutting down server in {shutdown_at - datetime.now()} seconds")
            await RCON.broadcast("server_shutdown_warning")

        if shutdown_at and datetime.now() > shutdown_at:
            log.info("Shutting down server")
            await RCON.save()
            await RCON.shutdown()
            break

        await asyncio.sleep(CONFIG.autosleep.watch_interval)

    log.info("Server shutdown")


asyncio.run(main())
