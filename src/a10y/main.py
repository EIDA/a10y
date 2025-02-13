import argparse
import requests
import os
import logging
import tomli
from datetime import datetime, timedelta
from .app import AvailabilityUI  # Import the main UI application


def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Availability UI application")
    parser.add_argument("-p", "--post", default=None, help="Default file path for POST requests")
    parser.add_argument("-c", "--config", default=None, help="Configuration file path")
    return parser.parse_args()


def load_nodes():
    """Fetch node URLs dynamically or use fallback values if request fails."""
    nodes_urls = []
    try:
        response = requests.get("https://orfeus-eu.org/epb/nodes", timeout=5)
        if response.status_code == 200:
            nodes_urls = [(n["node_code"], f"https://{n['node_url_base']}/fdsnws/", True) for n in response.json()]
    except requests.RequestException:
        pass  # Fall back to default nodes if request fails

    # Fallback nodes
    if not nodes_urls:
        nodes_urls = [
            ("GFZ", "https://geofon.gfz-potsdam.de/fdsnws/", True),
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
    return nodes_urls


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
        # No config file provided, try the default location
        config_dir = os.getenv("XDG_CONFIG_DIR", "")
        config_path = os.path.join(config_dir, "a10y", "config.toml") if config_dir else "./config.toml"

    if not os.path.isfile(config_path):
        # Config file is missing, return defaults without modification
        return defaults

    # Try to load the config file
    try:
        with open(config_path, "rb") as f:
            config = tomli.load(f)
    except (tomli.TOMLDecodeError, OSError):
        logging.error(f"Invalid format in config file {config_path}")
        raise ValueError(f"Invalid TOML format in config file: {config_path}")

    # Handle starttime
    if "starttime" in config:
        try:
            parts = config["starttime"].split()
            if len(parts) == 2 and parts[1].lower() == "days":
                num = int(parts[0])
                defaults["default_starttime"] = (datetime.now() - timedelta(days=num)).strftime("%Y-%m-%dT%H:%M:%S")
            else:
                datetime.strptime(config["starttime"], "%Y-%m-%dT%H:%M:%S")  # Validate format
                defaults["default_starttime"] = config["starttime"]
        except (ValueError, IndexError):
            raise ValueError(f"Invalid starttime format in {config_path}")

    # Handle endtime
    if "endtime" in config:
        if config["endtime"].lower() == "now":
            pass  # Keep default
        else:
            try:
                datetime.strptime(config["endtime"], "%Y-%m-%dT%H:%M:%S")  # Validate format
                defaults["default_endtime"] = config["endtime"]
            except ValueError:
                raise ValueError(f"Invalid endtime format in {config_path}")

    # Handle mergegaps
    if "mergegaps" in config:
        try:
            defaults["default_mergegaps"] = str(float(config["mergegaps"]))  # Ensure it's a valid number
        except ValueError:
            raise ValueError(f"Invalid mergegaps format in {config_path}")

    # Handle quality settings
    if "quality" in config:
        if not isinstance(config["quality"], list) or any(q not in ["D", "R", "Q", "M"] for q in config["quality"]):
            raise ValueError(f"Invalid quality codes in {config_path}")
        defaults["default_quality_D"] = "D" in config["quality"]
        defaults["default_quality_R"] = "R" in config["quality"]
        defaults["default_quality_Q"] = "Q" in config["quality"]
        defaults["default_quality_M"] = "M" in config["quality"]

    # Handle merge options
    if "merge" in config:
        if not isinstance(config["merge"], list) or any(m not in ["samplerate", "quality", "overlap"] for m in config["merge"]):
            raise ValueError(f"Invalid merge options in {config_path}")
        defaults["default_merge_samplerate"] = "samplerate" in config["merge"]
        defaults["default_merge_quality"] = "quality" in config["merge"]
        defaults["default_merge_overlap"] = "overlap" in config["merge"]

    # Handle restricted data setting
    if "includerestricted" in config:
        defaults["default_includerestricted"] = bool(config["includerestricted"])

    return defaults  # Return updated defaults




def main():
 

    # Parse command-line arguments
    args = parse_arguments()

    # Load network nodes
    nodes_urls = load_nodes()

    # Load default settings
    defaults = load_defaults()

    # Load configuration from file (if provided)
    defaults["default_file"] = args.post  # Overwrite default POST file if provided
    defaults = load_config(args.config, defaults)

    routing = "https://www.orfeus-eu.org/eidaws/routing/1/query?"

    # Run the application with loaded settings
    app = AvailabilityUI(
        nodes_urls=nodes_urls,
        routing=routing,  # Pass routing URL
        **defaults  # Pass unpacked defaults
    )
    app.run()


# Ensure the script can still be executed manually
if __name__ == "__main__":
    main()
