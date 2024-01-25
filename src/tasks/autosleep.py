import asyncio
import structlog
from datetime import datetime, timedelta

from config import load_config
from helpers.rcon import RCon, RconError

log = structlog.get_logger()

CONFIG = load_config()
RCON = RCon()


class AutoSleep:
    watch_interval = CONFIG.autosleep.watch_interval
    shutdown_timeout = CONFIG.autosleep.shutdown_timeout
    server_shutdown = asyncio.Event()

    async def task(self):
        shutdown_warning = False
        shutdown_at = None
        last_player_count = 0
        offline = False

        while True:
            # Call rcon to get player list
            try:
                players = await RCON.get_players()
                if offline:
                    log.info("Server is back online")
                    offline = False
            except RconError as e:
                if not offline:
                    log.warning(
                        "Unable to connect to server, waiting for it to come back"
                    )
                    offline = True
                await asyncio.sleep(self.watch_interval)
                continue

            if len(players) > 0:
                if last_player_count != len(players):
                    log.info(f"There's {len(players)} players online")
                    last_player_count = len(players)
                shutdown_warning = False
                shutdown_at = None
                await asyncio.sleep(self.watch_interval)
                continue

            if not shutdown_warning:
                log.info("There's no players online")
                log.info(
                    f"Shutting down server in {self.shutdown_timeout} seconds if no players join"
                )
                shutdown_warning = True
                shutdown_at = datetime.now() + timedelta(seconds=self.shutdown_timeout)

            if shutdown_at and datetime.now() < shutdown_at - timedelta(seconds=60):
                log.info(
                    f"Shutting down server in {shutdown_at - datetime.now()} seconds"
                )
                await RCON.broadcast("server_shutdown_warning")

            if shutdown_at and datetime.now() > shutdown_at:
                log.info("Shutting down server")
                await RCON.save()
                await RCON.shutdown()
                self.server_shutdown.set()

            await asyncio.sleep(self.watch_interval)
