<h1 align="center">Cloudflare DDNS Next 🚀</h1>

<p align="center">
  <b>Cloudflare DDNS Next for System Administrators!</b><br>
  <b>The robust, "set and forget" Dynamic DNS solution for Cloudflare.</b><br>
  <i>A modern, hardened continuation of the classic tool.</i>
</p>

<p align="center">
  • <a href="#-new-features">New Features</a> •
  <a href="#-installation">Installation</a> •
  <a href="https://github.com/dimpen/cloudflare-ddns-next/wiki">Configuration</a> •
</p>

---

## 🌟 Origin Story

This project is a complete rewrite of the original [original cloudflare-ddns repo](https://github.com/timothymiller/cloudflare-ddns) by [timothymiller](https://github.com/timothymiller/).  
The original tool kept our DDNS records updated for years but unfortunately it is not being maintained anymore.

So after the recent **Cloudflare Fiasco** ([issue 216](https://github.com/timothymiller/cloudflare-ddns/issues/216)) I made this repo focusing on **System Administrators** who need reliability above all else.

I've also **included ideas and fixes from most of the pull requests** from the original repo.

**Checkout the new Consensus Algorithm** to ensure your DNS records are *never* updated with a bad IP.

## ✨ New Features

- 🛡️ **NEW Hardened Consensus Algorithm**: Queries multiple IP services; updates only if the majority agree.
- 🔍 **Smart Logging**: JSON logs, rotation, timestamps, and separate IP history logs.
- 🔄 **Multi-Account**: Manage multiple Cloudflare accounts and zones in one place.
- 📝 **JSON5 Config**: Add comments (`//`,`/* */`) to your configuration files.
- 💓 **BetterStack Integration**: Native integration for heartbeat monitoring and alerts.
- **Blacklist** IPs ([issue 216](https://github.com/timothymiller/cloudflare-ddns/issues/216))
- **A/AAAA** mixed type of records and **TTL** set **per subdomain**
- Increased **security**, **performance** and easier **debugging**
- Run **external script on error** to take action or notify
- **Config validation** (`jsonschema`), minimizing errors 
- **Timestamped or custom comment** in Cloudflare DNS records
- Increased **error checking** and **exception handling**. *If one fails the rest go on*
- ⚡ **Modern Core**: Upgraded to **Python 3.10+** and `Session` requests for performance and security.
- 🐳 **Docker Ready**
- **More services for obtaining IP** and even more to come
- **Supported Services: ["1.1.1.1", "1.0.0.1", "cloudflare.com", "ipify", "icanhazip", "identme", "ifconfigco", "myipcom"]**


## 🚀 Installation

- **[Docker](#docker)**
- **[User Cronjob](#user-cronjob)**
- **[Systemd Service](#systemd-service)**

### Docker

**1. Get docker-compose.yml**

```bash
curl -L -O https://raw.githubusercontent.com/dimpen/cloudflare-ddns-next/master/docker/docker-compose.yml
```

**2. Get the example configuration**

```bash
curl -L -o config.json5 https://raw.githubusercontent.com/dimpen/cloudflare-ddns-next/master/config-example.json5

chmod 600 config.json5
```

**3. [Read the Wiki](https://github.com/dimpen/cloudflare-ddns-next/wiki)**  
Edit the config file to add your Cloudflare credentials and settings

**4. Run the container**

```bash
sudo docker-compose up -d
```


### User Cronjob  

**No Root Required**

This method installs the application locally in your user directory and relies on a cron job to trigger updates.

**1. Go to your installation directory and extract the release:**

```bash
curl -fsSL "https://github.com/dimpen/cloudflare-ddns-next/releases/latest/download/cloudflare-ddns-next.tar.gz" | tar -xz

cd cloudflare-ddns-next
```

**2. Create a virtual environment and install dependencies:**

```bash
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

**3. Set up the configuration file:**

**[Read the Wiki](https://github.com/dimpen/cloudflare-ddns-next/wiki)**  
Edit the config file to add your Cloudflare credentials and settings.  
*Remember NOT to set the "interval" in the config*

```bash
cp config-example.json5 config.json5
chmod 600 config.json5
```

**4. Create the cron helper launch script:**

```bash
cat > cronjob.sh << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT/src"
exec "$PROJECT_ROOT/venv/bin/python3" main.py --config "$PROJECT_ROOT/config.json5"
EOF

chmod +x cronjob.sh
```

**5. Add the job to your crontab:**

Open your crontab editor:

```bash
crontab -e
```

Add the following line to run the updater every 5 minutes (adjust the interval as needed):

```bash
*/5 * * * * /<ABSOLUTE PATH TO YOUR INSTALLATION DIR>/cloudflare-ddns-next/cronjob.sh
```

### Systemd Service  

**Requires Root for installation but runs as www-data**

This method installs the application to `/opt` and runs it as a dedicated service user (e.g., `www-data`).

**1. Create the installation directory and download the release:**

```bash
cd /opt

sudo curl -fsSL "https://github.com/dimpen/cloudflare-ddns-next/releases/latest/download/cloudflare-ddns-next.tar.gz" | sudo tar -xz

cd cloudflare-ddns-next
```

**2. Create a virtual environment and install dependencies:**

```bash
sudo python3 -m venv venv
sudo venv/bin/pip install -r requirements.txt
```

**3. Set up the configuration file:**  

**[Read the Wiki](https://github.com/dimpen/cloudflare-ddns-next/wiki)**  
Edit the config file to add your Cloudflare credentials and settings

```bash
sudo cp config-example.json5 config.json5
```

**4. Create the helper launch script:**

```bash
sudo tee systemd-service.sh > /dev/null << 'EOF'
#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT/src"
exec "$PROJECT_ROOT/venv/bin/python3" main.py --config "$PROJECT_ROOT/config.json5"
EOF
```

**5. Create the systemd service file:**

```bash
sudo tee /etc/systemd/system/cloudflare-ddns-next.service > /dev/null << 'EOF'
[Unit]
Description=Cloudflare DDNS Next Service
Wants=network-online.target
After=network-online.target

[Service]
Type=simple
ExecStart=/opt/cloudflare-ddns-next/systemd-service.sh
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
User=www-data
Group=www-data

[Install]
WantedBy=multi-user.target
EOF
```

**6. Set the correct permissions:**

```bash
sudo chown -R www-data:www-data /opt/cloudflare-ddns-next
sudo chmod 755 /opt/cloudflare-ddns-next/systemd-service.sh
sudo chmod 600 /opt/cloudflare-ddns-next/config.json5
```

**7. Enable and start the service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now cloudflare-ddns-next.service
sudo systemctl status cloudflare-ddns-next.service
```

## 📚 Documentation

**Read the Wiki for the complete configuration breakdown**  
**[Go to Wiki](https://github.com/dimpen/cloudflare-ddns-next/wiki)**


## Discussion

This script and configuration might seem a bit overkill for a simple IP update but I see it as a **set and forget** script.

That means we have to minimize all errors, handle errors and IF an error occurs there is plenty of tooling to debug it easily.

As a system administrator I appreciate extensive logging that can help easily keep track of and debug errors with this script, Cloudflare or even with other system processes that may be impacted by DNS or IPs.


## 🗺️ Roadmap

- [ ] Mixed IPv4 and IPv6 support for all services
- [ ] Load balancer support
- [ ] CNAME support
- [ ] Static records of all types


## Contributions

I'd like to harden this even more and make it as bulletproof as possible with more fixes and features.
So any **issues or pull requests are appreciated**.

I'd also like to add more services for obtaining IPs. So feel free to propose your own favorite services.

Any contributions, PRs and issues are welcome!

---

<p align="center">
  <i>Made with ❤️ for the Open Source community.</i>
</p>
