"""
Prometheus exporter for Terminus env:metrics

Usage:
  terminis_env_metrics_exporter.py [-c <config_file>] [-d]
  terminis_env_metrics_exporter.py (-h | --help)

Options:
  -c <config_file>     Path to config file [default: .config.yaml]
  -d                   Enable verbose output (DEBUG level)
  -h --help            Show this help message.
"""

import sys
import os
import logging
import json
import time
import subprocess
import yaml
from docopt import docopt
from prometheus_client import start_http_server, Gauge


# Init logging
logger = logging.getLogger("terminis_env_metrics_exporter")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def parse_yaml_config(cfg_path):
    """
    Parses a YAML configuration file and returns the data as a dictionary.

    Args:
        file_path (str): Path to the YAML file.

    Returns:
        dict: Parsed YAML content as a dictionary.
    """
    try:
        with open(cfg_path, "r", encoding="utf-8") as file:
            parsed_cfg = yaml.safe_load(file)
            return parsed_cfg
    except FileNotFoundError:
        logger.error("Error: File not found - %s", cfg_path)
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error("YAML parsing error: %s", e)
        sys.exit(1)
    return {}


def check_login():
    """
    Checks if the user is logged in to Terminus.

    Returns:
        bool: True if logged in, False otherwise.
    """
    result = subprocess.run(
        ["terminus", "auth:whoami"], capture_output=True, text=True, check=True
    )

    return False if "You are not logged in" in result.stderr else True


def terminus_auth_login(machine_token):
    """
    Authenticates with Terminus using the provided machine token if not already authenticated.

    Args:
        machine_token (str): Pantheon machine token for authentication.

    Returns:
        bool: True if authenticated or already logged in, False if login failed.
    """
    if not check_login():
        logger.info("Terminus is not authenticated. Logging in...")
        result = subprocess.run(
            ["terminus", "auth:login", f"--machine-token={machine_token}"],
            capture_output=True,
            text=True,
            check=True,
        )

        return (
            False
            if "Logged in via machine token" not in result.stderr
            and result.returncode == 0
            else True
        )

    return True


def terminus_get_env_metrics(site):
    """
    Fetches environment metrics for a specified Pantheon site and environment.

    Args:
        site (dict): Contains "site" and "env" keys for the Pantheon site.

    Returns:
        dict or None: Parsed metrics data if successful, None if an error occurs.
    """
    site_name = site.get("site")
    env = site.get("env")

    logger.debug("Getting env metrics for %s.%s", site_name, env)
    try:
        result = subprocess.run(
            [
                "terminus",
                "env:metrics",
                f"{site_name}.{env}",
                "--format=json",
                "--period=day",
                "--datapoints=1",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(result.stdout)
        return data
    except subprocess.CalledProcessError as e:
        logger.error("Command failed: %s", e)
        return None
    except json.JSONDecodeError as e:
        logger.error("Failed to parse JSON: %s", e)
        return None


def update_metrics(config_dict, machine_token):
    """
    Authenticates with Terminus, retrieves environment metrics for each site,
    and updates Prometheus metrics with the fetched data.

    Args:
        config_dict (dict): Configuration dictionary with site and environment details.
        machine_token (str): Pantheon machine token for authentication.
    """
    terminus_auth_login(machine_token)

    for site in config_dict.get("sites", []):
        site_name = site.get("site")
        env = site.get("env")
        if not site_name or not env:
            logger.warning(
                "Skipping site config due to missing 'site' or 'env': %s", site
            )
            continue
        site_data = terminus_get_env_metrics(site)
        logger.debug(site_data)
        side_data_ts = site_data["timeseries"]
        for ts, values in side_data_ts.items():
            metrics["visits"].labels(site=site["site"], env=site["env"]).set(
                values["visits"]
            )
            metrics["pages_served"].labels(site=site["site"], env=site["env"]).set(
                values["pages_served"]
            )
            metrics["cache_hits"].labels(site=site["site"], env=site["env"]).set(
                values["cache_hits"]
            )
            metrics["cache_misses"].labels(site=site["site"], env=site["env"]).set(
                values["cache_misses"]
            )
            # Convert percentage in cache_hit_ratio string to float
            ratio = float(values["cache_hit_ratio"].strip("%"))
            metrics["cache_hit_ratio"].labels(site=site["site"], env=site["env"]).set(
                ratio
            )


def validate_config(config_dict):
    """Validate required keys in the configuration."""
    required_keys = ["port", "interval", "sites"]
    for key in required_keys:
        if key not in config_dict:
            logger.error("Missing required config key: %s", key)
            sys.exit(1)


def load_token(config_dict):
    """Load the token from config or environment."""
    machine_token = config_dict.get("token") or os.getenv("TOKEN")
    if not machine_token:
        logger.error("Missing authentication token.")
        sys.exit(1)
    return machine_token


if __name__ == "__main__":
    """
    Main entry point to parse config, authenticate with Terminus,
    and periodically update Prometheus metrics.

    Reads config, validates required keys, and continuously fetches and updates metrics.

    Args:
        None
    """
    args = docopt(__doc__)
    config_path = args["-c"]
    verbose = args["-d"]

    if verbose:
        logger.setLevel(logging.DEBUG)

    logger.debug("Config path: %s", config_path)

    try:
        config = parse_yaml_config(config_path)
    except Exception as e:
        logger.error("Failed to parse config file: %s", e)
        sys.exit(1)

    validate_config(config)

    token = load_token(config)

    logger.debug("\nFinal parsed config:")
    logger.debug(config)

    metrics = {
        "visits": Gauge("terminus_env_visits", "Number of visits", ["site", "env"]),
        "pages_served": Gauge(
            "terminus_env_pages_served", "Pages served", ["site", "env"]
        ),
        "cache_hits": Gauge("terminus_env_cache_hits", "Cache hits", ["site", "env"]),
        "cache_misses": Gauge(
            "terminus_env_cache_misses", "Cache misses", ["site", "env"]
        ),
        "cache_hit_ratio": Gauge(
            "terminus_env_cache_hit_ratio", "Cache hit ratio (percent)", ["site", "env"]
        ),
    }

    start_http_server(config["port"])

    logger.info("Starting metrics update loop...")

    try:
        while True:
            update_metrics(config, token)
            time.sleep(config["interval"] * 60)
    except KeyboardInterrupt:
        logger.info("Process interrupted. Exiting...")
        sys.exit(0)
    except Exception as e:
        logger.error("An error occurred: %s", e)
        sys.exit(1)
