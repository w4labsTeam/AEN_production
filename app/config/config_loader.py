import yaml
import os


def load_config():

    config_file = os.getenv(
        "TANK_SERVER_CONFIG",
        "app/config/server1_4.yaml"
    )

    with open(config_file, "r") as file:
        config = yaml.safe_load(file)

    return config