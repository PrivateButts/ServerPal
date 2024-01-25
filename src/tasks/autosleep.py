import asyncio
import structlog

from config import load_config
from helpers.rcon import RCon, RconError
from helpers import dispatcher

log = structlog.get_logger(module="autosleep")

CONFIG = load_config()
RCON = RCon()


class AutoSleep:
    watch_interval = CONFIG.autosleep.watch_interval
    shutdown_timeout = CONFIG.autosleep.shutdown_timeout
    server_shutdown = asyncio.Event()
    shutdown_tasks = []

    async def _delay(self, coro, seconds):
        await asyncio.sleep(seconds)
        await coro()

    def reset(self):
        self.shutting_down = False
        self.last_player_count = 0
        self.offline = False

    async def shutdown(self):
        log.info("Saving and sending shutdown command")
        await RCON.save()
        await RCON.shutdown()
        dispatcher.emit("server_auto_shutdown")

    async def shutdown_warn(self):
        log.info(f"Shutting down server in 60 seconds")
        await RCON.broadcast("server_shutdown_warning")

    async def trigger_shutdown(self):
        log.info("Triggering shutdown sequence")
        self.shutting_down = True
        self.shutdown_tasks = [
            asyncio.create_task(
                self._delay(self.shutdown_warn, self.shutdown_timeout - 60)
            ),
            asyncio.create_task(self._delay(self.shutdown, self.shutdown_timeout)),
        ]
        await asyncio.gather(*self.shutdown_tasks)
        self.reset()

    async def cancel_shutdown(self):
        log.info("Cancelling shutdown")
        for task in self.shutdown_tasks:
            task.cancel()
        self.reset()

    async def task(self):
        self.reset()

        while True:
            # Call rcon to get player list
            try:
                players = await RCON.get_players()
                if self.offline:
                    log.info("Server is back online")
                    self.offline = False
            except RconError as e:
                if not self.offline:
                    log.warning(
                        "Unable to connect to server, waiting for it to come back"
                    )
                    self.offline = True
                    if self.shutting_down:
                        await self.cancel_shutdown()
                await asyncio.sleep(self.watch_interval)
                continue

            if len(players) > 0:
                if self.last_player_count != len(players):
                    log.info(f"There's {len(players)} players online")
                    self.last_player_count = len(players)
                    dispatcher.emit("server_player_count_changed", len(players))
                if self.shutting_down:
                    await self.cancel_shutdown()

            if len(players) < 1 and not self.shutting_down:
                log.info("There's no players online")
                log.info(
                    f"Shutting down server in {self.shutdown_timeout} seconds if no players join"
                )
                dispatcher.emit("server_player_count_changed", 0)
                asyncio.create_task(self.trigger_shutdown())

            await asyncio.sleep(self.watch_interval)
