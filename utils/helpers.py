import os
import random
import sys
from datetime import datetime

import pytz
import yaml


def clear_console():
    """Clear the console screen."""
    os.system("cls" if os.name == "nt" else "clear")


def get_current_time_context():
    tz = pytz.timezone("Asia/Bangkok")
    now = datetime.now(tz)
    hour = now.hour
    minute = now.minute
    weekday = now.strftime("%A")
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    # Casual time of day
    if 5 <= hour < 12:
        tod = random.choice(["morning", "early", "sun's up"])
    elif 12 <= hour < 17:
        tod = random.choice(["afternoon", "midday"])
    elif 17 <= hour < 20:
        tod = random.choice(["evening", "sunset"])
    else:
        tod = random.choice(["night", "late", "midnight"])
    return f"Today is {weekday}, {date_str}. It's {time_str} ({tod}) in Bangkok."


def resource_path(relative_path):
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_env_path():
    return resource_path("config/.env")


def load_config():
    config_path = resource_path("config/config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as file:
            config = yaml.safe_load(file)

        return config

    else:

        print(
            "Config file not found. Please provide a config file in config/config.yaml"
        )
        sys.exit(1)


def load_instructions():
    instructions_path = resource_path("config/instructions.txt")
    if os.path.exists(instructions_path):
        with open(instructions_path, "r", encoding="utf-8", errors="replace") as file:
            instructions = file.read()

        return instructions
    else:
        print("Instructions file not found. Using default instructions.")

        return ""
