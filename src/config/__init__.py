from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from strictyaml import (
    load,
    Map,
    Str,
    Int,
    Bool,
    Seq,
    YAMLError,
    as_document,
    Optional as Opt,
)


SCHEMA = Map(
    {
        "autosleep": Map(
            {
                "enabled": Bool(),
                "watch_interval": Int(),
                "shutdown_timeout": Int(),
            }
        ),
        "discord": Map(
            {
                "enabled": Bool(),
                "token": Str(),
                "server_start_command": Str(),
                Opt("alert_channel"): Int(),
            }
        ),
        "rcon": Map(
            {
                "path": Str(),
                "address": Str(),
                "password": Str(),
            }
        ),
    }
)


@dataclass
class AutoSleepConfig:
    enabled: bool
    watch_interval: int
    shutdown_timeout: int


@dataclass
class DiscordConfig:
    enabled: bool
    token: str
    server_start_command: str
    alert_channel: Optional[int]


@dataclass
class RconConfig:
    path: Path
    address: str
    password: str


@dataclass
class Config:
    autosleep: AutoSleepConfig
    discord: DiscordConfig
    rcon: RconConfig

    def __post_init__(self):
        self.autosleep = AutoSleepConfig(**self.autosleep)
        self.discord = DiscordConfig(**self.discord)
        self.rcon = RconConfig(**self.rcon)


def load_config() -> Config:
    config = None
    with open("config.yaml", "r") as f:
        try:
            config = load(f.read(), SCHEMA)
        except YAMLError as e:
            print(e)
            exit(1)

    if config is None:
        raise Exception("Empty config!")

    with open("rcon.yaml", "w") as f:
        f.write(
            as_document(
                {
                    "default": {
                        "address": config.data["rcon"]["address"],
                        "password": config.data["rcon"]["password"],
                        "log": "rcon-default.log",
                        "timeout": "10s",
                    }
                }
            ).as_yaml()
        )

    return Config(**config.data)
