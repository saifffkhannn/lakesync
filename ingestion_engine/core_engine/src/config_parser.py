import configparser
import os
from src.pipeline_logger import get_logger
logger = get_logger()

# Determine project base directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


SOURCE_NAME_ALIASES = {
    "sap_sqlserver": "sapsqlserver",
    "sap sqlserver": "sapsqlserver",
    "sap-sqlserver": "sapsqlserver",
    "sql_server": "sqlserver",
    "sql server": "sqlserver",
    "sql-server": "sqlserver",
}


def normalize_platform_name(name):
    if name is None:
        return name

    lowered = str(name).strip().lower()
    return SOURCE_NAME_ALIASES.get(lowered, lowered)


def parse_config(filename):
    """
    Reads configuration from a .cfg file and converts it into a dictionary.

    Parameters
    ----------
    filename : str
        Path to the configuration file

    Returns
    -------
    dict
        Dictionary containing configuration sections and key-value pairs
    """

    try:
        config = configparser.ConfigParser(interpolation=None)

        # Validate config file existence
        if not os.path.exists(filename):
            logger.info(f"Config file not found: {filename}")
            raise FileNotFoundError(f"Config file not found: {filename}")

        # Read configuration file
        config.read(filename)

        parsed_config = {}

        # Convert configparser structure to dictionary
        for section in config.sections():
            normalized_section = normalize_platform_name(section)
            section_items = dict(config.items(section))
            parsed_config[normalized_section] = section_items

            # Keep the original spelling available for backward compatibility.
            parsed_config.setdefault(section.lower(), section_items)

        return parsed_config

    except configparser.Error as e:
        logger.info(f"Error parsing configuration file: {str(e)}")
        raise Exception(f"Error parsing configuration file: {str(e)}")

    except Exception as e:
        logger.info(f"Failed to read configuration: {str(e)}")
        raise Exception(f"Failed to read configuration: {str(e)}")


def save_config(source, cloud, target, credentials):
    """
    Saves credentials to a configuration (.cfg) file.

    Parameters
    ----------
    source : str
        Source system name (e.g., sapsqlserver)
    cloud : str
        Cloud provider (e.g., aws)
    target : str
        Target system (e.g., databricks)
    credentials : dict
        Dictionary where keys are section names and values are key-value pairs

    Returns
    -------
    str
        Path to the generated configuration file
    """

    try:
        config = configparser.ConfigParser(interpolation=None)
        normalized_source = normalize_platform_name(source)
        normalized_cloud = normalize_platform_name(cloud)
        normalized_target = normalize_platform_name(target)

        # Add sections and values to config
        for section, items in credentials.items():
            config[normalize_platform_name(section)] = items

        # Ensure config directory exists
        config_dir = os.path.join(base_dir, "config")
        os.makedirs(config_dir, exist_ok=True)

        # Build config file path
        filename = f"{normalized_source}_{normalized_cloud}_{normalized_target}.cfg"
        config_path = os.path.join(config_dir, filename)

        # Write configuration file
        with open(config_path, "w") as configfile:
            config.write(configfile)

        return config_path

    except PermissionError:
        logger.info(f"No permission to write config file in {config_dir}")
        raise PermissionError(f"No permission to write config file in {config_dir}")

    except Exception as e:
        logger.info(f"Failed to save configuration file: {str(e)}")
        raise Exception(f"Failed to save configuration file: {str(e)}")