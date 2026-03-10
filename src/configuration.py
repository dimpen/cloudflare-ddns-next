import os
import sys
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler
from string import Template
import json5
from jsonschema import validate
from argparse import ArgumentParser


DEFAULTS = {
    "updater": {
        "priority": ["1111", "1001"],
        "A": False,
        "AAAA": False,
        "ttl": 300,
        "blacklist": None,
        "onlyOnChange": False,
        "tmpIpFile": "./tmp/cloudflare-ddns-next-ip_tempfile.txt",
        "requestTimeout": 20,
    },
    "logging": {
        "stdout": {"level": "INFO"},
        "logfile": {
            "level": "INFO",
            "filename": "./logs/cloudflare-ddns-next.log",
            "max_bytes": 5 * 1024 * 1024,  # 5MB
            "max_count": 5,
            "format": "text",
        },
        "iplog": {
            "filename": "./logs/cloudflare-ddns-next-ip.log",
            "max_bytes": 1 * 1024 * 1024,  # 1MB
            "max_count": 5,
            "onlyIpChange": False,
            "format": "text",
        },
    },
}

_CONF = None


def setup_config():
    global _CONF
    config_file = None
    config = None
    cnf = {}
    env_vars = {}

    try:

        if len(sys.argv) > 1:
            try:
                parser = ArgumentParser()
                parser.suggest_on_error = True
                parser.add_argument(
                    "-c", "--config", type=Path, help="json configuration file path"
                )
                parser.add_argument(
                    "-i",
                    "--interval",
                    type=int,
                    help="set interval in seconds for updates (overrides config option)",
                )
                parser.add_argument(
                    "--docker", action="store_true", default=False, help="do not use - only for docker usage"
                )
                args = parser.parse_args()

                if args.config:
                    config_path = Path(args.config)
                    if config_path.is_file() and os.access(config_path, os.R_OK):
                        config_file = args.config
                    else:
                        raise Exception(
                            f"Cannot read json configuration file {args.config}"
                        )
            except Exception as e:
                sys.stderr.write(f"{e}\n\n")
                parser.print_help()
                sys.exit(1)
                # return None

        # Read in all environment variables that have the correct prefix
        env_vars = {
            key: value
            for (key, value) in os.environ.items()
            if key.startswith("CF_DDNS_")
        }

        if not config_file:
            for conf_file in ["config.json5", "config.jsonc", "config.json"]:
                config_file = os.path.join(
                    os.environ.get("CONFIG_PATH", os.getcwd()), conf_file
                )
                if config_file:
                    break

        with open(config_file) as cfile:
            if len(env_vars) != 0:
                config = json5.loads(Template(cfile.read()).safe_substitute(env_vars))
            else:
                config = json5.loads(cfile.read())

        if not config:
            raise Exception(f"Cannot read configuration from: {config_file}")

        try:
            with open("schema.json5", "r") as schema_file:
                SCHEMA = json5.load(schema_file)
            validate(instance=config, schema=SCHEMA)
        except Exception as e:
            raise Exception(f"Error validating config: {e}")

        cnf["warnings"] = []

        cnf.update({**DEFAULTS["updater"], **config.get("updater", {})})

        if cnf.get("consensus"):
            if config.get("updater", {}).get("priority"):
                cnf.pop("priority")
                cnf["warnings"].append("priority")

            majority = max(
                int(len(cnf.get("consensus")) / 2) + 1, cnf.get("majority", 0)
            )
            majority = min(majority, len(cnf.get("consensus")))
            cnf.update({"majority": majority})

        if len(sys.argv) > 1 and args.interval:
            cnf.update({"interval": args.interval})

        if config.get("logging"):
            # iterate all the expected keys
            for k in DEFAULTS["logging"].keys():
                # if a matching key is provided in the config
                if config["logging"].get(k) is not None:
                    # transfer the provided values to the defaults and add them to cnf
                    cnf.update(
                        {k: {**DEFAULTS["logging"].get(k), **config["logging"].get(k)}}
                    )
        else:
            # if "logging" isn't provided go with the default
            cnf.update({"stdout": DEFAULTS["logging"]["stdout"]})

        if args.docker:
            if cnf.get("logfile"):
                cnf["logfile"].update({"filename": str(Path("/data/logs") / Path(cnf["logfile"].get("filename")).name)})
            if cnf.get("iplog"):
                cnf["iplog"].update({"filename": str(Path("/data/logs") / Path(cnf["iplog"].get("filename")).name)})
            if cnf.get("tmpIpFile"):
                cnf.update({"tmpIpFile": str(Path("/data/tmp") / Path(cnf.get("tmpIpFile")).name)})
            
        # create filepaths for all files that are in the config
        for fp in [
            cnf.get("tmpIpFile"),
            cnf.get("logfile", {}).get("filename"),
            cnf.get("iplog", {}).get("filename"),
        ]:
            if fp:
                try:
                    Path(fp).parent.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    raise Exception(f"Cannot create path for: {fp}\n Error: {e}")

        cnf["accounts"] = config.get("accounts")
        for account in cnf["accounts"]:
            for zone in account.get("zones"):
                zone.update(
                    {"purgeUnknownRecords": zone.get("purgeUnknownRecords", False)}
                )
                for subdomain in zone.get("subdomains"):
                    cnf.update({subdomain.get("type"): True})

                    subd_ttl = subdomain.get("ttl", cnf["ttl"])
                    if subd_ttl != 1 and subd_ttl < 30:
                        subd_ttl = 30
                    subdomain.update({"ttl": subd_ttl})

        if cnf.get("A") and cnf.get("AAAA"):
            ipListSelected = cnf.get("consensus", cnf.get("priority",{}))
            ipListName = "consensus" if cnf.get("consensus") else "priority"
            if len(ipListSelected) > 0:
                limitedServices = ["ifconfigco", "myipcom", "cfcom"]
                for service in limitedServices:
                    if service in ipListSelected:
                        raise Exception(f'Service {service} does not support mixed A and AAAA records but you have set both A and AAAA records in your subdomains. Remove the service from the {ipListName} list.')


        
        _CONF = cnf

    except Exception as e:
        sys.stderr.write(
            f"Configuration Error:\n {e} \nCheck the wiki for correct configuration. https://github.com/dimpen/cloudflare-ddns-next/wiki\n\n"
        )
        _CONF = None


def getConfig():
    global _CONF
    if _CONF is None:
        setup_config()
    return _CONF


def setup_logger():
    logger = logging.getLogger("logger")
    logger.setLevel("DEBUG")

    # Clear any old handlers if re-running
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    stdout_formatter = logging.Formatter(
        "%(asctime)s - [Cloudflare-DDNS-Next] - %(levelname)s - %(message)s"
    )
    if _CONF["stdout"]:
        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(stdout_formatter)
        stream_handler.setLevel(_CONF["stdout"]["level"])
        logger.addHandler(stream_handler)

    if _CONF.get("logfile"):
        if _CONF["logfile"]["format"] == "json":
            file_formatter = logging.Formatter(
                '{"timestamp": %(asctime)s, "level": %(levelname)s, "message": %(message)s}'
            )
        else:
            file_formatter = logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s"
            )

        if _CONF["logfile"]["max_count"] == 0:
            file_handler = RotatingFileHandler(
                _CONF["logfile"]["filename"],
                maxBytes=_CONF["logfile"]["max_bytes"],
                backupCount=1,
            )
            file_handler.doRollover = lambda: open(
                file_handler.baseFilename, "w"
            ).close()
        else:
            file_handler = RotatingFileHandler(
                _CONF["logfile"]["filename"],
                maxBytes=_CONF["logfile"]["max_bytes"],
                backupCount=_CONF["logfile"]["max_count"],
            )
        file_handler.setFormatter(file_formatter)
        file_handler.setLevel(_CONF["logfile"]["level"])
        logger.addHandler(file_handler)

    return logger
