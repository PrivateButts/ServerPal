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
BOT = commands.Bot(command_prefix="!", intents=discord.Intents.all())


@BOT.event
async def on_ready():
    log.info(f"Logged in as {BOT.user}.")
    try:
        synced = await BOT.tree.sync()
        log.info(f"Synced {synced} commands.")
    except Exception as e:
        log.exception("Failed to sync commands.", exc_info=e)

    BOT.loop.create_task(notify_shutdown())


@BOT.tree.command(name="start", description="Starts the server.")
async def start(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        try:
            await RCON.get_info()
            log.info("Server is already running.")
            await interaction.followup.send("Server is already running!")
            return
        except RconError as e:
            log.info("Server isn't running. Starting server.")

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
            await interaction.followup.send("Server failed to start!")
        except asyncio.TimeoutError:
            await interaction.followup.send("Server started!")
            log.info("started server!")
            log.info("Updating activity")
            activity = discord.Activity(
                type=discord.ActivityType.watching,
                name=f"an online server",
            )
            await BOT.change_presence(activity=activity)
            return

    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.")


@BOT.tree.command(name="status", description="Gets the status of the server.")
async def status(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        info = await RCON.get_info()
        players = await RCON.get_players()
        await interaction.followup.send(
            f"Server Status:\n{info}\nPlayers Online: {len(players)}"
        )
    except RconError as e:
        log.exception("Failed to get players.", exc_info=e)
        await interaction.followup.send(
            "Failed to get status. Server may not be online"
        )
    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.")


@BOT.tree.command(
    name="players", description="Gets the players currently on the server."
)
async def players(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        players = await RCON.get_players()
        await interaction.followup.send(
            f"Players Online: {len(players)}\n{', '.join([player.name for player in players])}"
        )
    except RconError as e:
        log.exception("Failed to get players.", exc_info=e)
        await interaction.followup.send(
            "Failed to get players. Server may not be online"
        )
    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.")


@BOT.tree.command(name="save", description="Saves the server.")
async def save(interaction: discord.Interaction):
    await interaction.response.defer(thinking=True)
    try:
        await RCON.save()
        await interaction.followup.send("Server saved!")
    except RconError as e:
        log.exception("Failed to save server.", exc_info=e)
        await interaction.followup.send(
            "Failed to save server. Server may not be online"
        )
    except Exception as e:
        log.exception("Failed to get status.", exc_info=e)
        await interaction.followup.send("Command Failed.")


async def notify_shutdown():
    queue = dispatcher.listen("server_auto_shutdown")
    if not CONFIG.discord.alert_channel:
        return
    log.info("Listening for server shutdown")
    while True:
        await queue.get()
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
    queue = dispatcher.listen("server_player_count_changed")
    if not CONFIG.discord.alert_channel:
        return
    log.info("Listening for player count changes")
    while True:
        await queue.get()
        log.info("Updating activity")
        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=f"an online server, {len(await RCON.get_players())} players active",
        )
        await BOT.change_presence(activity=activity)


async def start_bot(token):
    return await BOT.start(token)
