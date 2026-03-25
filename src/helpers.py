from configuration import getConfig
from collections import Counter
from logging import getLogger
from datetime import datetime
import json

CONF = getConfig()
logger = getLogger('logger')

def iplogger(records):
    if not CONF.get("iplog"): return
    try:     
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(CONF["iplog"]["filename"],"a") as ipf:
            if CONF["iplog"]["format"] == "json":
                ipf.write(f'{{ "timestamp": {timestamp} , "records": {records} }}\n')
            else:
                ipf.write(f'[{timestamp}] - {list(records.values())}\n')
                
        logger.debug(f'Logged ip to {CONF["iplog"]["filename"]}')
            
    except Exception as e:
        logger.error(f'Failed to log records to {CONF["iplog"]["filename"]}\n{e}')


"""
Args:
    arr: List of strings (may contain None values)
    majority: Minimum number of occurrences required
        
Returns the string with at least majority occurrences (the most frequent if multiple qualify), or None if no string meets the criteria or if there's a tie
"""
def find_most_frequent(arr, majority):
    # Filter out None values and count occurrences
    filtered = [s for s in arr if s is not None]
    counts = Counter(filtered)
    
    # Find strings with at least x occurrences
    candidates = {string: count for string, count in counts.items() if count >= majority}

    # Return None if no candidates
    if not candidates:
        return None
    
    # Find the maximum count
    max_count = max(candidates.values())
    
    # Find all strings with the maximum count in case there are multiple
    max_strings = [string for string, count in candidates.items() if count == max_count]
    
    # Check for tie
    if len(max_strings) > 1:
        logger.debug(f'Consensus tie. {max_count} of: {max_strings}')
        return None
    
    return max_strings[0]



"""
Checks the blacklist and returns None if there's a match or the ip if no match
"""
def check_blacklist(ip):
    try:
        if CONF.get("blacklist"):
            for badip in CONF["blacklist"]:
                if ip.startswith(badip):
                    logger.warning(f'IP {ip} is blacklisted')
                    return None
    
    except Exception as e:
        logger.error(f'Blacklist check failed. Error:\n{e}')
    
    return ip


'''
Returns False if the records are found in tmpfile otherwise it always returns True. 
'''
def changed_ips(records):
    if not CONF.get("onlyOnChange"): return True
    newrecords = {}
    oldrecords = None
    try:
        try:
            with open(CONF["tmpIpFile"]) as ipfile:
                oldrecords = json.load(ipfile)
        except Exception as e:
            logger.debug(f'Failed reading {CONF["tmpIpFile"]} or getting records.\n{e}')
        
        if oldrecords:
            if records.get("A",oldrecords.get("A","")) == oldrecords.get("A","") and records.get("AAAA",oldrecords.get("AAAA","")) == oldrecords.get("AAAA",""):
                logger.debug(f'IP records {records} are found in file {CONF["tmpIpFile"]}: {oldrecords}')            
                return False
            else:                
                newrecords.update({**oldrecords,**records})
        else:
            newrecords = records

        with open(CONF["tmpIpFile"], 'w') as ipfile: 
            json.dump(newrecords, ipfile)
        logger.debug(f'Writing new records to file {CONF["tmpIpFile"]}: {newrecords}')

    except Exception as e:
        logger.warning(f'Error while checking if IPs changed.\n{e}')

    return True



