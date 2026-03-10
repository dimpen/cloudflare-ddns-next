from datetime import datetime
from requests import Session
from logging import getLogger
from configuration import getConfig
import json

logger = getLogger('logger')
CONF = getConfig()



def cloudflare_update(new_records):
    errors = []    
    s = Session()
    try:
        for account_index, account in enumerate(CONF["accounts"]):
            try:
                if account["authentication"].get("api_token"):
                    auth_header = {"Authorization": "Bearer " + account["authentication"]["api_token"]}
                elif account["authentication"].get("api_key"):
                    auth_header = {
                        "X-Auth-Email": account["authentication"]["api_key"]["account_email"],
                        "X-Auth-Key": account["authentication"]["api_key"]["auth_key"]
                    }
                if not auth_header:
                    raise Exception(f'Failed to determine authentication method.\n{e}')
                # security concerns to have this logged?! enable only if needed.
                # logger.debug(f'Authentication Header for account {account_index+1}:\n{json.dumps(auth_header, sort_keys=True, indent=2)}')

                for zone in account.get("zones"):
                    try:
                        zone_id = zone.get("id")
                        subdomains = zone.get("subdomains")
                        s.headers.update(auth_header)
                        if not (CONF.get("A") and CONF.get("AAAA")): # not both enabled
                            typeRec = "A" if CONF.get("A") else "AAAA"
                            r = s.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?order=type&type={typeRec}&per_page=100', timeout=CONF["requestTimeout"]) 
                            r.raise_for_status()
                            
                            data = r.json()
                            logger.debug(f'Response from GET dns_records {typeRec}. Zone ID: {zone_id}\n{json.dumps(data, sort_keys=True, indent=2)}')
                            if not data.get("success"):
                                raise Exception(f'GET dns_records {typeRec} was unsuccessful.\nResponse Errors: {data.get("errors",[])}') 
                            cfrecs = data.get("result")
                        else:
                            ra = s.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?order=type&type=A&per_page=100', timeout=CONF["requestTimeout"])
                            ra.raise_for_status()
                            data_a = ra.json()                            
                            logger.debug(f'Response from GET dns_records A. Zone ID: {zone_id}\n{json.dumps(data_a, sort_keys=True, indent=2)}')     
                            if not data_a.get("success"):
                                raise Exception(f'GET dns_records A was unsuccessful.\nResponse Errors: {data_a.get("errors",[])}') 
                            cfArecs = data_a.get("result")    
                            
                            raaaa = s.get(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?order=type&type=AAAA&per_page=100', timeout=CONF["requestTimeout"])
                            raaaa.raise_for_status()
                            data_aaaa = raaaa.json()
                            logger.debug(f'Response from GET dns_records AAAA. Zone ID: {zone_id}\n{json.dumps(data_aaaa, sort_keys=True, indent=2)}')
                            if not data_aaaa.get("success"):
                                raise Exception(f'GET dns_records AAAA was unsuccessful.\nResponse Errors: {data_aaaa.get("errors",[])}') 
                            cfAAAArecs = data_aaaa.get("result")    
                            
                            cfrecs = [*cfArecs, *cfAAAArecs]
                        
                        if not cfrecs:
                            zone_name = zone.get("zone_name") 
                            logger.info(f'GET dns_records returned no records. Zone ID: {zone_id}')
                        else:
                            zone_name = ".".join(cfrecs[0].get("name").split('.')[-2:])                        
                        if not zone_name:
                            raise Exception(f'Failed to determine zone name. Zone ID: {zone_id}')
                        
                        logger.debug(f'Checking Zone ID: {zone_id} with Zone Name: {zone_name}')
                        for subd in subdomains:
                            try:
                                rr = None
                                rec = None
                                rec_type = subd["type"]
                                rec_ip = new_records.get(rec_type)
                                rec_name = ".".join([subd.get("name").strip(". "),zone_name]).strip(". ")
                                
                                logger.debug(f'Checking Subdomain: {rec_name}')
                                if not rec_ip:
                                    raise Exception(f'No valid type {rec_type} IP for: {rec_name}')
                                
                                # find record in cf records
                                cfsubd = next((x for x in cfrecs if x["name"] == rec_name), {})
                                
                                # because cf allows only auto ttl for proxied records
                                rec_ttl = 1 if subd.get("proxied") else subd["ttl"] 
                                rec_comment = "" if CONF.get("disableComments") else subd.get("comment", f'Updated by Cloudflare DDNS Next at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}' )
                                
                                rec = {
                                        "name": rec_name,
                                        "content": rec_ip,
                                        "ttl": rec_ttl,
                                        "type": rec_type,
                                        "proxied": subd["proxied"],
                                        "comment": rec_comment
                                }
                                    
                                if cfsubd:
                                    if (
                                        rec_type != cfsubd.get("type")
                                        or rec_ip != cfsubd.get("content")
                                        or subd["proxied"] != cfsubd.get("proxied")
                                        or rec_ttl != cfsubd.get("ttl")
                                        or (rec_comment != "" and rec_comment != cfsubd.get("comment"))
                                        or (rec_comment == "" and cfsubd.get("comment"))
                                    ):
                                        rec.update({"id": cfsubd.get("id")})
                                        
                                        logger.debug(f'Patching Existing DNS Record:\n{json.dumps(rec, sort_keys=True, indent=2)}')
                                        
                                        logger.debug(f'Comment existing: {cfsubd.get("comment","SOME")}')
                                        
                                        rr = s.patch(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rec["id"]}', json=rec, headers={"Content-Type": "application/json"}, timeout=CONF["requestTimeout"])
                                        
                                    else:
                                        logger.debug(f'No update needed for {rec_name} DNS Record:\n{json.dumps(rec, sort_keys=True, indent=2)}')
                                        
                                else:
                                    logger.debug(f'Creating New DNS Record:\n{json.dumps(rec, sort_keys=True, indent=2)}')
                                    
                                    rr = s.post(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records', json=rec, headers={"Content-Type": "application/json"}, timeout=CONF["requestTimeout"])
                                    
                                if rr:
                                    rr.raise_for_status()
                                    rr_data = rr.json()
                                    logger.debug(f'Response from PATCH/POST DNS Record for {rec["name"]}\n{json.dumps(rr_data, sort_keys=True, indent=2)}')
                                    
                                    if not rr_data.get("success"):
                                        raise Exception(f'Unsuccessful PATCH/POST DNS Record: {rec["name"]}\nResponse Errors: {rr_data.get("errors",[])}') 

                            except Exception as e:
                                logger.error(f'Update failed for {rec_name or subd.get("name","")}. Zone ID: {zone_id}\n{e}')
                                errors.append(5)

                        if zone.get("purgeUnknownRecords"):
                            try:
                                for cfrec in cfrecs:
                                    found_rec = next((x for x in subdomains if x["name"] == ".".join(cfrec.get("name").split('.')[:-2])), {})
                                    if not found_rec and cfrec.get("type") in ["A","AAAA"]: 
                                        logger.debug(f'Deleting DNS Record:\n{json.dumps(cfrec, sort_keys=True, indent=2)}')
                                        rd = s.delete(f'https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{cfrec.get("id")}', timeout=CONF["requestTimeout"])
                                        rd.raise_for_status()
                                        rd_data = rd.json()

                                        logger.debug(f'Response from DELETE DNS Record: {cfrec.get("name")}\n{json.dumps(rd_data, sort_keys=True, indent=2)}')                                    
                                        if not rd_data.get("success"):
                                            raise Exception(f'Unsuccessful DELETE DNS Record: {cfrec.get("name")}\nResponse Errors: {rd_data.get("errors",[])}') 
                            except Exception as e:
                                logger.error(f'Deleting DNS Records failed for Zone ID: {zone_id}. Error:\n{e}')
                                errors.append(4)
                                
                    except Exception as e:
                        logger.critical(f'Updates failed for Zone ID: {zone_id}. Error:\n{e}')
                        errors.append(3)

            except Exception as e:
                logger.critical(f'Cloudflare Updates failed for account: {account_index+1}. Error:\n{e}')
                errors.append(2)

    except Exception as e:
        logger.critical(f'Cloudflare Updates failed. Error:\n{e}')
        errors.append(1)

    return errors
