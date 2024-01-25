from config import load_config
from tasks.discord import start_bot

CONFIG = load_config()

start_bot(CONFIG.discord.token)
