from logging import getLogger
from configuration import getConfig
import requests
import ipaddress
from cloudflare_api import cloudflare_update
from helpers import *
import subprocess

logger = getLogger('logger')
CONF = getConfig()


SERVICES = {
    "1111": {
        "A": "https://1.1.1.1/cdn-cgi/trace",
        "AAAA": "https://[2606:4700:4700::1111]/cdn-cgi/trace",
        "host": "one.one.one.one",
        "format": "linedtext"
    },
    "1001": {
        "A": "https://1.0.0.1/cdn-cgi/trace",
        "AAAA": "https://[2606:4700:4700::1001]/cdn-cgi/trace",
        "host": "one.one.one.one",
        "format": "linedtext"
    },
    "cfcom": {
        "A": "https://cloudflare.com/cdn-cgi/trace",
        "AAAA": "https://cloudflare.com/cdn-cgi/trace",
        "format": "linedtext"
    },
    "ipify": {
        "A": "https://api.ipify.org",
        "AAAA": "https://api6.ipify.org",
        "format": "ip"
    },
    "icanhazip": {
        "A": "https://ipv4.icanhazip.com",
        "AAAA": "https://ipv6.icanhazip.com",
        "format": "ip"
    },
    "identme": {
        "A": "https://4.ident.me",
        "AAAA": "https://6.ident.me",
        "format": "ip"
    },
    "amazonaws": {
        "A": "https://checkip.amazonaws.com",
        "AAAA": "https://checkip.amazonaws.com",
        "format": "ip"
    },
    "ifconfigco": {
        "A": "https://ifconfig.co/json",
        "AAAA": "https://ifconfig.co/json",
        "format": "json"
    },
    "myipcom": {
        "A": "https://api.myip.com",
        "AAAA": "https://api.myip.com",
        "format": "json"
    },
}

def updateRecords():
    missing = False
    recsChanged = True
    cf_errors = None
    
    records = getConsensusIPs() if CONF.get("consensus") else getPriorityIPs()
    if not records:
        logger.error(f'Failed to get valid records!')
        if CONF.get("betterstack_token"):
            betterstack_heartbeat(2)
    else:        
        for typeRec in ["A","AAAA"]:
            if CONF.get(typeRec) and not records.get(typeRec):
                logger.error(f'Failed to get valid IP for record {typeRec}')
                missing = True

        recsChanged = changed_ips(records)
        if CONF.get("iplog"):
            if CONF["iplog"].get("onlyIpChange") and recsChanged:
                iplogger(records)
            elif not CONF["iplog"].get("onlyIpChange"):
                iplogger(records)
        
        if CONF.get("onlyOnChange") and not recsChanged:
            logger.info(f'onlyOnChange is set. No records changed. Nothing to do.')
            if CONF.get("betterstack_token"):
                betterstack_heartbeat()
            return False
        
        if not missing:
            logger.info(f'Valid IP records: {records}')
            logger.info(f'Updating Cloudflare...')
            # if recsChanged: updateReady = True
        else:
            logger.error(f'Partial valid records: {records}')
            logger.error(f'Partially Updating Cloudflare...')
        
        cf_errors = cloudflare_update(records)

        if not cf_errors:
            logger.info(f'Successfully updated Cloudflare records!')
            if CONF.get("betterstack_token"):
                betterstack_heartbeat()
            return True
        
        if missing or cf_errors:
            logger.error(f'Failed to fully update Cloudflare records!')
            if cf_errors: 
                logger.debug(f'Cloudflare update Errors: {cf_errors}')
            try:
                if CONF.get("betterstack_token"):
                    betterstack_heartbeat("fail" if cf_errors else 1)
                    
                if CONF.get("externalScript"):
                    logger.debug(f'Running command: {" ".join(CONF.get("externalScript"))}')
                    subproc = subprocess.run(CONF.get("externalScript"), capture_output=True, text=True)
                    if CONF.get("logExternalOutput"):
                        logger.info(f'{" ".join(CONF.get("externalScript"))} returned with code {subproc.returncode}. Output:\n{subproc.stdout}')
            except Exception as e:
                logger.error(f'Failed to run command: {" ".join(CONF.get("externalScript"))}\n{e}')
        
    return False

"""
Does all the technical error checks and either returns a valid IP or None
"""
def get_ip(session, service, typeRec):
    ip = None
    try:      
        response = session.get(SERVICES[service][typeRec], headers={"Host": SERVICES[service]["host"]} if SERVICES[service].get("host") else None, timeout=CONF["requestTimeout"])
        response.raise_for_status()
        
        frmt = SERVICES[service]["format"]
        if frmt == "json":
            data = response.json()
            ip = data.get("ip")            

        elif frmt == "ip":
            ip = response.text.strip()

        elif frmt == "linedtext":
            data = response.text.split("\n")
            data.pop()
            ip = dict(s.split("=") for s in data).get("ip","")

        else: # shouldn't be reached since SERVICES are hardcoded
            logger.critical(f'Unsupported format {frmt}')
        
        if not ip:
            logger.warning(f'Empty IP string from {SERVICES[service][typeRec]}')
        else:
            try:
                v = ipaddress.ip_address(ip).version
                if typeRec == "A" and v == 4:
                    return check_blacklist(ip)
                elif typeRec == "AAAA" and v == 6:
                    return check_blacklist(ip)
                else:
                    raise ValueError(f'Invalid IPv4/IPv6 address from {SERVICES[service][typeRec]}')          
            except Exception as e:
                logger.warning(f'While checking IP version: {typeRec}.Error:\n{e}')

    except requests.RequestException as e:
        logger.error(f'Network error while fetching IP from {SERVICES[service][typeRec]}\n{e}')
    except Exception as e:
        logger.error(f'Unexpected error while fetching IP from {SERVICES[service][typeRec]}\n{e}')
    
    return None
    
   
    


"""
Returns records that could be either (partially) empty or filled with valid records
"""
def getConsensusIPs():
    records = {}
    sess = requests.Session()
    
    try:
        for typeRec in ["A","AAAA"]:
            if CONF.get(typeRec):
                ips = []
                ip = None
                for service in CONF["consensus"]:
                    ip = get_ip(sess, service, typeRec)
                    logger.debug(f'Obtained type {typeRec} IP from {service}: {ip}')
                    if ip is None:
                        logger.warning(f'Failed to get type {typeRec} from: {service}')
                    ips.append(ip)            
                
                ip = find_most_frequent(ips, CONF["majority"])
                
                if ip is None:
                    logger.warning(f'Failed to get consensus IP for record type {typeRec}')
                else:
                    records.update({typeRec: ip})
    
    except Exception as e:
        logger.error(f'Unexpected error while getting consensus IPs.\n{e}')
        return None  
                     
    return records



"""
Returns records that could be either (partially) empty or filled with valid records
"""
def getPriorityIPs():
    records = {}
    sess = requests.Session()
    
    try:
        for typeRec in ["A","AAAA"]:
            if CONF.get(typeRec):
                ip = None
                for service in CONF["priority"]:
                    ip = get_ip(sess, service, typeRec)
                    logger.debug(f'Obtained type {typeRec} IP from {service}: {ip}')
                    if ip is not None:
                        records.update({typeRec: ip})
                        break
                    logger.warning(f'Failed to get type {typeRec} from: {service}')
    
    except Exception as e:
        logger.error(f'Unexpected error while getting priority IPs.\n{e}')
        return None
        
    return records




def betterstack_heartbeat(code = ""):
    if not CONF.get("betterstack_token"): return
    try:
        endpoint = f'https://uptime.betterstack.com/api/v1/heartbeat/{CONF.get("betterstack_token")}/{code}'
        
        if code:
            logger.warning(f'Sending Betterstack heartbeat for failure {code}')
        else:
            logger.debug(f'Sending Betterstack heartbeat GET request to {endpoint}')
        
        r = requests.get(endpoint, timeout=CONF["requestTimeout"])
        r.raise_for_status()
        
        if r.status_code != 200:
            raise Exception(f'Betterstack heartbeat GET request returned HTTP code: {r.status_code}')
        else:
            logger.debug(f'Betterstack heartbeat GET request returned HTTP code: {r.status_code}')
            
        logger.info(f'Sent Betterstack heartbeat')
    
    except requests.RequestException as e:
        logger.error(f'Network error while sending Betterstack heartbeat.\n{e}')
        
    except Exception as e:
        logger.error(f'Error while sending Betterstack heartbeat.\n{e}')
        