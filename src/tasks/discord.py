import asyncio
import discord
import structlog
from discord.ext import commands
from config import load_config
from helpers.rcon import RCon, RconError
from helpers import dispatcher

log = structlog.get_logger(module="discord")
CONFIG = load_config()
RCON = RCon()
BOT = commands.Bot(
    command_prefix="!",
    intents=discord.Intents.all(),
    activity=discord.Activity(
        name="an offline server", type=discord.ActivityType.watching
    ),
)

SHUTTING_DOWN = False


@BOT.event
async def on_ready():
    log.info(f"Logged in as {BOT.user}.")
    try:
        synced = await BOT.tree.sync()
        log.info(f"Synced {synced} commands.")
    except Exception as e:
        log.exception("Failed to sync commands.", exc_info=e)

    BOT.loop.create_task(notify_shutdown())
    BOT.loop.create_task(update_player_count())


async def _start_server() -> bool:
    """Starts the server."""
    process = await asyncio.create_subprocess_exec(
        CONFIG.discord.server_start_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    try:
        stdout, stderr = await asyncio.wait_for(
            asyncio.shield(process.communicate()), timeout=5
        )
        log.error(
            "server failed to start!",
            stdout=stdout.decode(),
            stderr=stderr.decode(),
        )
        return False
    except asyncio.TimeoutError:
        log.info("started server!")
        log.info("Updating activity")
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"an online server",
        )
        await BOT.change_presence(activity=activity)
        global SHUTTING_DOWN
        SHUTTING_DOWN = False
        return True


@BOT.tree.command(name="start", description="Starts the server.")
async def start(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        try:
            await RCON.get_info()
            log.info("Server is already running.")
            await interaction.followup.send(
                "Server is already running!", ephemeral=True
            )
            return
        except RconError as e:
            log.info("Server isn't running. Starting server.")

        if await _start_server():
            await interaction.followup.send("Server started!", ephemeral=True)
        else:
            await interaction.followup.send("Server failed to start!", ephemeral=True)

    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.", ephemeral=True)


@BOT.tree.command(name="restart", description="Restarts the server.")
async def restart(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        try:
            await RCON.get_info()
        except RconError as e:
            log.info("Server isn't running.")
            await interaction.followup.send("Server isn't running", ephemeral=True)
            return

        log.info("Starting server restart sequence")
        await RCON.save()
        await RCON.shutdown(message="server_restart")
        await BOT.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"the server restart",
            )
        )
        log.info("Server shutdown. Waiting 60 seconds before restarting server")
        await asyncio.sleep(60)

        if await _start_server():
            await interaction.followup.send("Server restarted!", ephemeral=True)
        else:
            await interaction.followup.send(
                "Server failed to restart! Server may not be online", ephemeral=True
            )

    except RconError as e:
        log.exception("Failed to save server.", exc_info=e)
        await interaction.followup.send(
            "Failed to restart. Server may not be online", ephemeral=True
        )
    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.", ephemeral=True)


@BOT.tree.command(name="status", description="Gets the status of the server.")
async def status(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        info = await RCON.get_info()
        players = await RCON.get_players()
        await interaction.followup.send(
            f"Server Status:\n{info}\nPlayers Online: {len(players)}", ephemeral=True
        )
    except RconError as e:
        log.exception("Failed to get players.", exc_info=e)
        await interaction.followup.send(
            "Failed to get status. Server may not be online", ephemeral=True
        )
    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.", ephemeral=True)


@BOT.tree.command(
    name="players", description="Gets the players currently on the server."
)
async def players(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        players = await RCON.get_players()
        await interaction.followup.send(
            f"Players Online: {len(players)}\n{', '.join([player.name for player in players])}",
            ephemeral=True,
        )
    except RconError as e:
        log.exception("Failed to get players.", exc_info=e)
        await interaction.followup.send(
            "Failed to get players. Server may not be online", ephemeral=True
        )
    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.", ephemeral=True)


@BOT.tree.command(name="save", description="Saves the server.")
async def save(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True, ephemeral=True)
    try:
        await RCON.save()
        await interaction.followup.send("Server saved!", ephemeral=True)
    except RconError as e:
        log.exception("Failed to save server.", exc_info=e)
        await interaction.followup.send(
            "Failed to save server. Server may not be online", ephemeral=True
        )
    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.", ephemeral=True)


async def notify_shutdown():
    global SHUTTING_DOWN
    queue = dispatcher.listen("server_auto_shutdown")
    if not CONFIG.discord.alert_channel:
        return
    log.info("Listening for server shutdown")
    while True:
        await queue.get()
        SHUTTING_DOWN = True
        log.info("Sending shutdown alert")
        channel = BOT.get_channel(CONFIG.discord.alert_channel)
        await channel.send("Server is shutting down due to inactivity")
        log.info("Updating activity")
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"an offline server",
        )
        await BOT.change_presence(activity=activity)


async def update_player_count():
    global SHUTTING_DOWN
    queue = dispatcher.listen("server_player_count_changed")
    if not CONFIG.discord.alert_channel:
        return
    log.info("Listening for player count changes")
    while True:
        await queue.get()
        if SHUTTING_DOWN:
            continue
        log.info("Updating activity")
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"an online server, {len(await RCON.get_players())} players active",
        )
        await BOT.change_presence(activity=activity)


async def start_bot(token):
    return await BOT.start(token)
