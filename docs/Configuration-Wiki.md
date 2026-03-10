# Cloudflare-DDNS-Next Wiki
Cloudflare DDNS Next for System Administrators!
**[Github Repository](https://github.com/dimpen/cloudflare-ddns-next)**

## Contents
- [Cloudflare-DDNS-Next Wiki](#cloudflare-ddns-next-wiki)
  - [Contents](#contents)
  - [Obtaining IP Algorithms](#obtaining-ip-algorithms)
    - [Priority Algorithm](#priority-algorithm)
    - [Consensus Algorithm](#consensus-algorithm)
    - [Services](#services)
  - [Configuration Overview](#configuration-overview)
  - [Cloudflare](#cloudflare)
    - [Accounts](#accounts)
    - [Zones](#zones)
      - ["zone\_name"](#zone_name)
      - ["ttl"](#ttl)
      - ["comment"](#comment)
      - ["purgeUnknowRecords"](#purgeunknowrecords)
  - [Updater Configuration](#updater-configuration)
      - ["blacklist"](#blacklist)
      - ["onlyOnChange"](#onlyonchange)
      - ["tmpIpFile"](#tmpipfile)
      - ["ttl"](#ttl-1)
      - ["disableComments"](#disablecomments)
      - ["requestTimeout"](#requesttimeout)
      - ["interval"](#interval)
      - ["externalScript"](#externalscript)
      - ["logExternalOutput"](#logexternaloutput)
      - ["betterstack\_token"](#betterstack_token)
  - [Logging](#logging)
    - [Overview](#overview)
    - [Defaults](#defaults)
    - ["iplog"](#iplog)
  - [BetterStack Integration](#betterstack-integration)
    - [Why betterstack?](#why-betterstack)
    - [Setup](#setup)
    - [Behavior](#behavior)
  - [Cloudflare Notifications](#cloudflare-notifications)


## Obtaining IP Algorithms


### Priority Algorithm

This is called **"priority"** mechanism and now you can configure the list to add even more of the available services.

```json5
"priority": ["1111", "1001", "ipify", "icanhazip", "identme", "amazonaws", "ifconfigco", "myipcom"]
```

 The services in the **"priority" list** will be **checked in order** until a valid IP (*not blacklisted*) is obtained.

The old behavior was to check 1.1.1.1 and if it fails then check 1.0.0.1. 

***The new default is:***

```json5
"priority": ["ipify", "identme", "icanhazip"]
```

### Consensus Algorithm

This **checks all the services in the "consensus" list** and returns a valid IP (*not blacklisted*) if the **majority** of the services have returned the same IP.

```json5
"consensus":["1111", "1001", "ipify", "icanhazip", "identme", "amazonaws", "ifconfigco", "myipcom"],
"majority": 5
```

**Why "consensus"?**

Can we trust the result of one service?! 

A service can malfunction and return a bad IP address.

If we were using the consensus algorithm we would have avoided the **cloudflare fiasco** ([issue 216](https://github.com/timothymiller/cloudflare-ddns/issues/216)).

We're not relying only on one service but multiple to agree on an IP which is safer and a more **hardened approach** to obtain an IP.

This is my preferred method and depending on your situation and use case you may prefer this too.

**"majority"**

The consensus majority is calculated as X/2+1 where X is the number of services in the "consensus" list.

*Examples:* 

- **3** services used / 2 + 1 => at least **2** services must return the same IP

- **4** services used / 2 + 1 => at least  **3** services must return the same IP 

You can harden the consensus even more by **increasing the "majority"** in the configuration. 

*But be careful* if for example you want 5 out of 5 to agree and 1 service malfunctions you won't get a valid final IP and so you won't update your Cloudflare IP. 

### Services

| Service Name | URL                                          | IP Version | Format    |
| ------------ | -------------------------------------------- | ---------- | --------- |
| 1111         | https://1.1.1.1/cdn-cgi/trace                | IPv4       | linedtext |
|              | https://[2606:4700:4700::1111]/cdn-cgi/trace | IPv6       | linedtext |
| 1001         | https://1.0.0.1/cdn-cgi/trace                | IPv4       | linedtext |
|              | https://[2606:4700:4700::1001]/cdn-cgi/trace | IPv6       | linedtext |
| ipify        | https://api.ipify.org                        | IPv4       | ip        |
|              | https://api6.ipify.org                       | IPv6       | ip        |
| icanhazip    | https://ipv4.icanhazip.com                   | IPv4       | ip        |
|              | https://ipv6.icanhazip.com                   | IPv6       | ip        |
| identme      | https://4.ident.me                           | IPv4       | ip        |
|              | https://6.ident.me                           | IPv6       | ip        |
|              |                                              |            |           |
| *ifconfigco* | https://ifconfig.co/json                     | IPv4/IPv6  | json      |
| *myipcom*    | https://api.myip.com                         | IPv4/IPv6  | json      |
| *cfcom*      | https://cloudflare.com/cdn-cgi/trace         | IPv4/IPv6  | linedtext |

*Open an issue or a pull request to add more.*

***Note:*** You only **specify the service name** in the list used (*"priority" or "consensus"*) and the relevant IPv4/IPv6 URLs will be checked according to the type of records (A/AAAA) you've set in the configuration.

`ifconfigco`, `myipcom`, `cfcom` do not work with mixed A/AAAA records. So if you want both A and AAAA records do NOT use these or you'll get a configuration error.


## Configuration Overview

The configuration now **supports comments** (**// or /* */**) which makes it more readable and easier to use.

Many more configuration options were added so comments are helpful to easily make changes.

The configuration is **validated against a json schema** to decrease errors and help with error handling.

You can change the **configuration file** used with the run argument: 

`--config <configuration_filename>` 

**"CF_DDNS_"** environment variables are still supported and you can also set the configuration file with `CONFIG_PATH`.

If no `--config` or `CONFIG_PATH` are set then the **default** is to read `config.json` in the current working directory.


## Cloudflare

### Accounts

Now you can have **multiple Cloudflare accounts** each with different authentication method (api_token or api_key) and each one with multiple zones.

```json5
{
  "accounts": [
    {
      "authentication": {
        "api_token": "api_token"
      },
      "zones": [{ ... }, { ... }]
    },
    {
      "authentication": {
        "api_key": {
          "auth_key": "auth_key",
          "account_email": "email@example.com"
        }
      },
      "zones": [{ ... }, { ... }]
    }
  ]
}
```

***Note:***   **authentication is set once per account** and not per zone (*old behavior*).

### Zones

**Modular per zone and per subdomain settings**

```json5
"zones": [
    {
        "id": "zone_id", // REQUIRED
        // name is only required if your Cloudflare Zone has no A/AAAA entries
        "zone_name": "example.com",
        // "purgeUnknownRecords": false // optional
        // subdomains is REQUIRED with at least one entry
        "subdomains": [
        {
            "name": "", // REQUIRED. Empty for root dns record @
            "proxied": true, // REQUIRED true / false
            "type": "A", // REQUIRED "A"/"AAAA"
            // set if you want to override global ttl setting in "updater"
            "ttl": 300, // optional
            "comment": "Updated by Cloudflare DDNS Next" // optional
        },
        {
            // only use subdomain. so only "test" for test.example.com
            "name": "test", // REQUIRED
            "proxied": false, // REQUIRED true / false
            // notice we can have mixed "A" and "AAAA" records
            "type": "AAAA", // REQUIRED "A"/"AAAA"
            "ttl": 600, // optional
            "comment": "Test record" // optional
        }
        ]
    },
    {
        "id": "another_zone_id",
        "subdomains": [{...},{...}]
    }
]
```

`"name", "proxied", "type"` are **required** for every subdomain.

#### "zone_name"

Can be set per zone. It's **optional** if your Cloudflare zone already has the A/AAAA records. 

Otherwise **if it's the first time setting A/AAAA records you must provide it**.

Anyway it's good to set it for configuration readability.

#### "ttl"

In seconds. Optional. **Overrides** for the subdomain the **global "ttl" value** set in `updater`. 

#### "comment"

Optional. Comment for the record that will be shown in Cloudflare (*next to the Name column in the DNS records*). **If not set** the default is a comment like:

`Updated by Cloudflare DDNS Next at 2025-10-10 11:48:12`

You can set it as empty string like `"comment": ""` to **disable the comment** for the specific subdomain or **remove the comment** from Cloudflare it has been previously set.

You can set "disableComments: true" in "updater" section to **disable all comments**. This will remove all comments from all zones/subdomains in Cloudflare. 

#### "purgeUnknowRecords" 

Optional. true/false. Is set **per zone**. 

If set **true** any A/AAAA records of the zone in Cloudflare that are NOT included in this configuration **WILL BE DELETED** from Cloudflare!

In other words it will **only keep A/AAAA records that are in your configuration**.

## Updater Configuration

This configuration **applies to all** accounts/zones/subdomains.

**"updater"** and all its settings are **optional**. 

These are the default values:

```json5
"updater": {
    "priority": ["1111", "1001"],
    "ttl": 300,
    "blacklist": [],
    "onlyOnChange": false,
    "tmpIpFile": "./.tmp/cloudflare-ddns-next-ip_tempfile.txt",
    "requestTimeout": 20,
    "disableComments": false,
    
    
    // "interval": 300
    // "externalScript": ["./on-error-script.sh", "-with", "args"],
    // "logExternalOutput": true,
    
    // "betterstack_token": "dsfgsdfgsdfgsdfgsdfg",
}
```

If both "priority" and "consensus" are set then "consensus" will be used and you'll get a warning log notifying you.

#### "blacklist"

Any IP returned from any service is checked against this **blacklist**. 

The check is if it ***starts with*** any of the strings specified in the blacklist. 

So you can specify *partial IP strings* like:

"104.18" or "104.18.0" or ""2606:4700"

*Of course be careful!* "10" will blacklist any IP starting with "10".

These are the IPs that Cloudflare returned during the **cloudflare fiasco** ([issue 216](https://github.com/timothymiller/cloudflare-ddns/issues/216)). You could add these to avoid another error, especially if you don't use "consensus".

```json
"blacklist": ["104.18.0.0", "2606:4700:7::"]
```

#### "onlyOnChange" 

If set **true** the IP will be obtained normally BUT Cloudflare won't be contacted at all unless the IP has changed. This avoids unnecessary HTTP requests so it minimizes errors.

***Note:*** if you set this **true** and you make any changes to the records in the configuration these changes won't be updated in Cloudflare until the IP changes.

#### "tmpIpFile"

File used to keep track of IP changes if using "onlyOnChange". This is considered a temporary file so leaving the default in *tmp* is fine. 
You can delete this created file to force an IP update to Cloudflare.

#### "ttl" 

Can be set here globally but can be overriden per subdomain. 

From Cloudflare:

> Time To Live (TTL) of the DNS record in seconds. Setting to 1 means 'automatic'. Value must be between 60 and 86400, with the minimum reduced to 30 for Enterprise zones.

If you set a lower value than your account allows, Cloudflare will set it to "auto".

*Also note that Cloudflare allows setting **TTL only for non proxied records**.*

*So the program will set all proxied records to "auto" before submitting them.*

#### "disableComments"

true/false. If set **true** DNS record comments for A/AAAA records are disabled and if there are previously set comments in Cloudflare A/AAAA records they will be removed in all zones/subdomains.

#### "requestTimeout"

In seconds. Can be set to avoid requests hanging. 

The new code now uses **Session** so it's faster but could still hang if there is no timeout. Check [Timeouts Requests Documentation](https://requests.readthedocs.io/en/latest/user/advanced/#timeouts)

#### "interval" 

In seconds. If set the **script runs continuously** (without exiting) and it runs updates every "interval" seconds. This is also the docker behavior.

*This is the old "--repeat" behavior. Be careful with cron jobs.*

#### "externalScript"

A command split into a string list to be run with python's *subprocess*. 

If set it'll run the command if there is an error obtaining a valid IP or updating Cloudflare records.

It may be helpful to run an external script/command to take some extra action in case of error. 

I use it to run a shell script that sends an email and an apprise message.

Example: `"externalScript": ["./notify_script.sh", "--email", "--apprise"]`

#### "logExternalOutput"

If set true will log (*level INFO*) the return code and stdout from the "externalScript".

#### "betterstack_token"
String. For Betterstack integration. Check [BetterStack Integration](#betterstack-integration)


## Logging

### Overview

**"logging"** configuration is optional. 

The default behavior is to log only to stdout with log level `INFO`.

If you configure "logging" you MUST include all the logging methods you want to enable 

`"stdout":{},"logfile":{},"iplog":{}` 

Ommitting a section disables it. You can leave them empty to get the defaults. 

i.e. `"logfile": {}` enables **logfile** with all the defaults.

All logs are **timestamped**.

**logfile** and **iplog** can be set to **json format** to make further parsing easier. 

**logfile** and **iplog** are rotating files logs. When the file reaches *max_bytes* they rotate the files up to *max_count* files. 

The rotated filenames will be like: filename.1 , filename.2, ... so by default for "lofgile" it'll be: cloudflare-ddns-next.log.1, cloudflare-ddns-next.log.2, ...

If "max_count" is 0 then rotating will be disabled and the file will be rewritten every time it reaches "max_bytes".

### Defaults

These are the default values for all the sections *if they are set* otherwise if nothing is set only stdout is enabled.

```json5
"logging": {
    "stdout": { "level": "INFO" },
    "logfile": { // rotating logfile
        "level": "INFO",
        // make sure the directory exists
        "filename": "./logs/cloudflare-ddns-next.log",
        "max_bytes": 5242880, // 5MB
        // how many log files to keep rotating
        "max_count": 5,
        "format": "text" // text/json
    },
// separate rotating logfile that logs only the obtained IPs
    "iplog": {
        "filename": "./logs/cloudflare-ddns-next-ip.log",
        "max_bytes": 1048576, // 1MB
        // how many log files to keep rotating
        "max_count": 5,
// if true will log the obtained IP only if it has changed
        "onlyIpChange": false, // true/false
        "format": "text" // text/json
    }
}
```

**Valid Log Levels:** `"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"`

### "iplog"

Logs only the IPs in a separate file. It's helpful for easily tracking IP changes and keeping them logged separately.


## BetterStack Integration

### Why betterstack?

*Not sponsored*. It's free, easy to setup (it took me 5min to setup an account and create a heartbeat) and has the best free tier limits compared to similar services.

For now their free-tier plan offers:

-  10 monitors & heartbeats, 1 status page

-  Slack & e-mail alerts

-  100,000 exceptions per month

-  3 GB logs retained for 3 days

-  2B metrics retained for 30 days

-  3 GB warehouse events stored for 30 days


### Setup

Register at [Sign up | Better Stack](https://betterstack.com/users/sign-up)

*It asks for a phone number but I skipped that step because I'm only interested in email alerts.*

Create a heartbeat at [Heartbeats | Better Stack](https://uptime.betterstack.com/team/0/heartbeats)

Set "Expect a heartbeat every" the same period as you've configured the program to run (via "interval" or cronjob). I suggest setting "with a grace period" the same period of time, so effectively doubling the heartbeat failure timeout. That way you allow for request/response delays.

Copy the `<HEARTBEAT_TOKEN>` from the heartbeat URL and set it to "betterstack_token" in `updater`
[Heartbeat Documentation | Better Stack Documentation](https://betterstack.com/docs/uptime/cron-and-heartbeat-monitor)


### Behavior

The program will sent a heartbeat to betterstack every time it runs and betterstack expects that heartbeat otherwise it will send an alert. 

If IPs are **partially obtained** (only one of IPv4 or IPv6 if you've set both) it hits the error code endpoint `/1`. 

If it fails to obtain **any valid IPs** it hits the error code endpoint `/2`

If there's an **error while updating** the Cloudflare records it hits the general failure endpoint `/fail`

That's an easy way to get a glimspe of what's wrong before you dig into the logs.

Note: You can also set [Monitors | Better Stack](https://uptime.betterstack.com/team/0/monitors) to do a periodic healthcheck for you website or API. 

**PR or issue to integrate you favorite service.**


## Cloudflare Notifications

You can also setup [Cloudflare Notifications](https://developers.cloudflare.com/notifications) for status checks and maintenace alerts (also available on free plans) but having a third party service like betterstack would be more secure in case of a Cloudflare failure.