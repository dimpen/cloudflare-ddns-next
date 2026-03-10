#!/usr/bin/env python3

import sys
import time
from configuration import getConfig, setup_logger
from update import updateRecords
import json
import threading
import signal



class GracefulExit:
    def __init__(self):
        self.kill_now = threading.Event()
        self.reload_event = threading.Event()
        signal.signal(signal.SIGINT, self.exit_gracefully)
        signal.signal(signal.SIGTERM, self.exit_gracefully)
        signal.signal(signal.SIGHUP, self.reload_config)

    def exit_gracefully(self, signum, frame):
        logger.info("Stopping main thread...")
        self.kill_now.set()
        self.reload_event.set() # Wake up main thread

    def reload_config(self, signum, frame):
        logger.info("SIGHUP received. Scheduling configuration reload...")
        self.reload_event.set()



def main():
    try:
        if sys.version_info < (3, 10):
            raise Exception("This script requires Python 3.10+")   

        CONF = getConfig()
        if not CONF:
            raise Exception(f'Failed to setup configuraion.')
        
        logger = setup_logger()
        if not logger:
            raise Exception(f'Failed to setup Logging.')
        
        logger.debug(f'Running with configuration:\n{json.dumps(CONF,sort_keys=True, indent=4)}')
        
        if "priority" in CONF.get("warnings",[]):
            logger.warning('Both "consensus" and "priority" updater methods were provided. Using "consensus".')
        
    except Exception as e:
        sys.stderr.write(f'CRITICAL - Failed Initialization.\n{e}\nExiting.\n')
        time.sleep(10)
        sys.exit(1)
           
    if CONF.get("interval"):
        killer = GracefulExit()
        logger.info(f'Updating IP records every {CONF["interval"]} seconds')
        while not killer.kill_now.is_set():
            updateRecords()
            
            # Wait for interval, or until reload/kill signal
            if killer.reload_event.wait(CONF["interval"]):
                killer.reload_event.clear()
                if killer.kill_now.is_set():
                    break
                
                logger.info("Reloading configuration now...")
                # Re-load configuration
                try:
                    from configuration import setup_config
                    setup_config() 
                    CONF = getConfig()
                    logger = setup_logger()
                    logger.info(f'Configuration reloaded. New interval: {CONF.get("interval")}')
                except Exception as e:
                    logger.error(f"Failed to reload configuration: {e}")
            
    else:
        if not updateRecords():
            sys.exit(2)
            
            
if __name__ == '__main__':
    main()