from dataclasses import dataclass
from time import sleep
import subprocess
from datetime import datetime, timedelta


WATCH_INTERVAL = 5
SHUTDOWN_TIMEOUT = 60


def run_server_command(command: str):
    result = subprocess.run(['rcon.exe', command], capture_output=True, text=True)

    if result.returncode != 0:
        raise Exception(f"Error: rcon.exe returned non-zero exit code. Check rcon log file for more information. Command: {command}")

    return result.stdout

@dataclass
class Player:
    name: str
    playeruid: int
    steamid: int

# Call rcon.exe to get server header
result = run_server_command('info')

# Print the output
print("Server Header:", result, sep='\n')


shutdown_warning = False
shutdown_at = None
last_player_count = 0

while True:
    # Call rcon.exe to get player list
    result = run_server_command('showplayers')

    players = [Player(*line.split(',')) for index,line in enumerate(result.splitlines()) if index > 0]

    if len(players) > 0:
        if last_player_count != len(players):
            print(f"There's {len(players)} players online")
            last_player_count = len(players)
        shutdown_warning = False
        shutdown_at = None
        sleep(WATCH_INTERVAL)
        continue

    if not shutdown_warning:
        print("There's no players online")
        print(f"Shutting down server in {SHUTDOWN_TIMEOUT} seconds if no players join")
        shutdown_warning = True
        shutdown_at = datetime.now() + timedelta(seconds=SHUTDOWN_TIMEOUT)
    
    if shutdown_at and datetime.now() < shutdown_at - timedelta(seconds=60):
        print(f"Shutting down server in {shutdown_at - datetime.now()} seconds")
        run_server_command('broadcast server_shutdown_warning')

    if shutdown_at and datetime.now() > shutdown_at:
        print("Shutting down server")
        run_server_command('save')
        run_server_command('Shutdown 15 shutting_down')
        break

    sleep(WATCH_INTERVAL)

print("Server shutdown")