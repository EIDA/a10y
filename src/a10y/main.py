import argparse
import requests
import os
import logging
import tomli
from datetime import datetime, timedelta
from a10y.app import AvailabilityUI
from pathlib import Path
from appdirs import user_cache_dir 
import json 
from urllib.parse import urlparse
import time
import threading
import itertools
import sys
from urllib.parse import urlparse
# Common constants
DEFAULT_NODES = [
    ("GFZ", "https://geofon.gfz.de/fdsnws/", True),
    ("ODC", "https://orfeus-eu.org/fdsnws/", True),
    ("ETHZ", "https://eida.ethz.ch/fdsnws/", True),
    ("RESIF", "https://ws.resif.fr/fdsnws/", True),
    ("INGV", "https://webservices.ingv.it/fdsnws/", True),
    ("LMU", "https://erde.geophysik.uni-muenchen.de/fdsnws/", True),
    ("ICGC", "https://ws.icgc.cat/fdsnws/", True),
    ("NOA", "https://eida.gein.noa.gr/fdsnws/", True),
    ("BGR", "https://eida.bgr.de/fdsnws/", True),
    ("BGS", "https://eida.bgs.ac.uk/fdsnws/", True),
    ("NIEP", "https://eida-sc3.infp.ro/fdsnws/", True),
    ("KOERI", "https://eida.koeri.boun.edu.tr/fdsnws/", True),
    ("UIB-NORSAR", "https://eida.geo.uib.no/fdsnws/", True),
]

CACHE_DIR = Path(user_cache_dir("a10y"))
CACHE_FILE = CACHE_DIR / "nodes_cache.json"
QUERY_URL = "https://www.orfeus-eu.org/eidaws/routing/1/globalconfig?format=fdsn"

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Availability UI application")
    parser.add_argument("-p", "--post", default=None, help="Default file path for POST requests")
    parser.add_argument("-c", "--config", default=None, help="Configuration file path")
    return parser.parse_args()

def ensure_cache_dir():
    """Ensure the cache directory exists."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)



QUERY_URL = "https://www.orfeus-eu.org/eidaws/routing/1/globalconfig?format=fdsn"

def loading_animation(stop_event):
    """Display a loading animation while nodes are being fetched."""
    for frame in itertools.cycle(['|', '/', '-', '\\']):  # Simple animation
        if stop_event.is_set():
            break
        sys.stdout.write(f"\rPlease wait... {frame} ")  # Overwrite the same line
        sys.stdout.flush()
        time.sleep(0.5)
    sys.stdout.write("\rFetching complete! ✅\n")  # Clear animation

def fetch_nodes_from_api():
    """Fetch fresh nodes from API and save to cache, with a loading animation."""
    nodes_urls = []
    stop_event = threading.Event()

    # Start loading animation in a separate thread
    animation_thread = threading.Thread(target=loading_animation, args=(stop_event,))
    animation_thread.start()

    try:
        response = requests.get(QUERY_URL, timeout=60)
        response.raise_for_status()
        data = response.json()

        for node in data.get("datacenters", []):
            node_name = node["name"]
            fdsnws_url = None

            for repo in node.get("repositories", []):
                for service in repo.get("services", []):
                    if service["name"] == "fdsnws-station-1":
                        fdsnws_url = service["url"]
                        break
                if fdsnws_url:
                    break

            if fdsnws_url:
                parsed_url = urlparse(fdsnws_url)
                base_url = f"{parsed_url.scheme}://{parsed_url.netloc}/fdsnws/"
                nodes_urls.append((node_name, base_url, True))

        if nodes_urls:
            save_nodes_to_cache(nodes_urls)

    except requests.RequestException as e:
        logging.warning(f"Failed to fetch nodes from API: {e}")

    finally:
        stop_event.set()  # Stop loading animation
        animation_thread.join()  # Wait for the animation to stop

    return nodes_urls if nodes_urls else None


def save_nodes_to_cache(nodes):
    """Save nodes to cache file."""
    ensure_cache_dir()
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump({"nodes": nodes}, f)

def load_cached_nodes():
    """Load cached nodes, fetch from API if missing or invalid."""
    ensure_cache_dir()

    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
                nodes = cache_data.get("nodes", [])

                if not all(isinstance(n, list) and len(n) == 3 for n in nodes):
                    raise ValueError("Invalid cache format")

                return [(str(name), str(url), True) for name, url, _ in nodes]

        except (json.JSONDecodeError, ValueError) as e:
            logging.warning(f"Cache file is corrupted: {e}. Deleting it.")
            CACHE_FILE.unlink()

    nodes_from_api = fetch_nodes_from_api()
    if nodes_from_api:
        return nodes_from_api

    return DEFAULT_NODES

def load_nodes():
    """Always load from cache if available, otherwise use fallback values."""
    cached_nodes = load_cached_nodes()
    return cached_nodes if cached_nodes else DEFAULT_NODES

def load_defaults():
    """Return default configuration values."""
    return {
        "default_file": None,
        "default_starttime": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%S"),
        "default_endtime": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "default_quality_D": True,
        "default_quality_R": True,
        "default_quality_Q": True,
        "default_quality_M": True,
        "default_mergegaps": "1.0",
        "default_merge_samplerate": False,
        "default_merge_quality": False,
        "default_merge_overlap": True,
        "default_includerestricted": True,
    }

def load_config(config_path, defaults):
    """Load configuration from a TOML file and update defaults."""
    if not config_path:
        config_dir = os.getenv("XDG_CONFIG_DIR", "")
        config_path = os.path.join(config_dir, "a10y", "config.toml") if config_dir else "./config.toml"

    if not os.path.isfile(config_path):
        return defaults

    try:
        with open(config_path, "rb") as f:
            config = tomli.load(f)
    except (tomli.TOMLDecodeError, OSError):
        logging.error(f"Invalid format in config file {config_path}")
        raise ValueError(f"Invalid TOML format in config file: {config_path}")

    # Process starttime
    if "starttime" in config:
        try:
            parts = config["starttime"].split()
            if len(parts) == 2 and parts[1].lower() == "days":
                num = int(parts[0])
                defaults["default_starttime"] = (datetime.now() - timedelta(days=num)).strftime("%Y-%m-%dT%H:%M:%S")
            else:
                datetime.strptime(config["starttime"], "%Y-%m-%dT%H:%M:%S")
                defaults["default_starttime"] = config["starttime"]
        except (ValueError, IndexError):
            raise ValueError(f"Invalid starttime format in {config_path}")

    # Process other config options
    if "endtime" in config:
        if config["endtime"].lower() != "now":
            try:
                datetime.strptime(config["endtime"], "%Y-%m-%dT%H:%M:%S")
                defaults["default_endtime"] = config["endtime"]
            except ValueError:
                raise ValueError(f"Invalid endtime format in {config_path}")

    if "mergegaps" in config:
        try:
            defaults["default_mergegaps"] = str(float(config["mergegaps"]))
        except ValueError:
            raise ValueError(f"Invalid mergegaps format in {config_path}")

    if "quality" in config:
        if not isinstance(config["quality"], list) or any(q not in ["D", "R", "Q", "M"] for q in config["quality"]):
            raise ValueError(f"Invalid quality codes in {config_path}")
        for code in ["D", "R", "Q", "M"]:
            defaults[f"default_quality_{code}"] = code in config["quality"]

    if "merge" in config:
        if not isinstance(config["merge"], list) or any(m not in ["samplerate", "quality", "overlap"] for m in config["merge"]):
            raise ValueError(f"Invalid merge options in {config_path}")
        defaults["default_merge_samplerate"] = "samplerate" in config["merge"]
        defaults["default_merge_quality"] = "quality" in config["merge"]
        defaults["default_merge_overlap"] = "overlap" in config["merge"]

    if "includerestricted" in config:
        defaults["default_includerestricted"] = bool(config["includerestricted"])

    return defaults

def main():
    args = parse_arguments()
    nodes_urls = load_nodes()
    defaults = load_defaults()
    defaults["default_file"] = args.post
    defaults = load_config(args.config, defaults)

    app = AvailabilityUI(
        nodes_urls=nodes_urls,
        routing="https://www.orfeus-eu.org/eidaws/routing/1/query?",
        **defaults
    )
    app.run()

if __name__ == "__main__":
    main()