# Prepare project

```
mkdir -p ~/soar-stack && cd ~/soar-stack
nano docker-compose.yml
```

1. Start the SOAR stack

# from ~/soar-stack
```
docker compose pull
docker compose up -d
docker compose ps
```
# Wait until health checks go green (Cassandra + ES + Postgres + OpenSearch + MISP). Check logs if anything is still starting:

```
docker logs -f es_thehive
docker logs -f cassandra
docker logs -f misp
docker logs -f thehive
docker logs -f cortex
docker logs -f shuffle-backend
```

# 2. First logins (change passwords right away)

TheHive → http://<host>:9000
Login: admin / Testing123 (from your YAML). Create an API key for automation (Administration → Users → API Keys). Save it; we’ll use it for the Wazuh bridge.

Cortex → http://<host>:9001
Login: admin / Testing123. In TheHive → Administration → Connectors → Cortex, add a server:

URL: http://cortex:9001 (use the container name so TheHive reaches Cortex inside the Docker network)

Auth: credentials from your YAML (admin/Testing123). Test & save.

MISP → http://<host>:8080
Login: admin@local / Testing123. Generate an Auth key (Administration → Users → Your user → Auth keys).
In TheHive → Administration → Connectors → MISP, add:

URL: http://misp (container‑internal) or http://<host>:8080

Key: the MISP auth key

SSL verify: Off (since you’re on HTTP)
Test & save.

Shuffle → http://<host>:3000
Login: admin / Testing123. We’ll import a ready workflow later.


# 3. Create the separate Wazuh → TheHive bridge

We’ll put a tiny Python script + .env on the Wazuh Manager that receives alerts and talks to TheHive/MISP/Cortex. This uses Wazuh’s Integrator with a custom script (name must start with custom-).

    1. Install Python deps on the Wazuh manager
    
    # on the Wazuh manager host
    sudo /var/ossec/framework/python/bin/pip3 install requests python-dotenv
    

# Add soar.env To manager path - /var/ossec/integrations  (after this edit the values in soar.env)

# 4. Add the integration script -
For custom integrations, Wazuh expects the script at /var/ossec/integrations/<name> and <name> in ossec.conf must start with custom-. We’ll name it custom-thehive.

    sudo nano /var/ossec/integrations/custom-thehive

    
# 5. Permissions:
        sudo chmod 750 /var/ossec/integrations/custom-thehive
        sudo chown root:wazuh /var/ossec/integrations/custom-thehive
        sudo chmod 640 /var/ossec/integrations/soar.env
        sudo chown root:wazuh /var/ossec/integrations/soar.env


# 6. Wire it in Wazuh (no systemd vars)

Edit the manager config:

        sudo nano /var/ossec/etc/ossec.conf

Add inside <ossec_config>:

        <integration>
        <name>custom-thehive</name>
        <alert_format>json</alert_format>

        <!-- Choose one of the filters below -->

        <!-- Option A: Only high severity -->
        <level>10</level>

        <!-- Option B: Only specific rules (comma-separated) -->
        <!-- <rule_id>5715,5716,60110</rule_id> -->

        <!-- Option C: Only a group (e.g., syscheck or malware) -->
        <!-- <group>syscheck</group> -->
        </integration>

This is using the Integrator “custom” path; the <name> maps directly to /var/ossec/integrations/custom-thehive and alert_format=json makes Wazuh send JSON to the script.

Restart Wazuh manager:

    sudo systemctl restart wazuh-manager
    sudo tail -f /var/ossec/logs/integrations.log

# 7. Make TheHive call Cortex automatically

TheHive and Cortex are already linked (we added Cortex in Administration → Cortex Servers earlier). Now we tell TheHive what to do when a new observable (file, URL, hash, etc.) is added.

# Log into TheHive

Open http://<your-server-ip>:9000

Login with your admin credentials (admin / Testing123 from your docker-compose.yml).

# Go to Administration → Analyzers

You’ll see a list of analyzers from Cortex.

Examples: VirusTotal_Url, AbuseIPDB_IP_Analyzer, UrlHaus_Url_Analyzer.

Make sure at least a couple are enabled.

# Create a Case Template

Go to Administration → Case Templates → Add New.

Give it a name (e.g., Wazuh Alert Template).

Add a default tag like From-Wazuh.

Scroll to Observable Analyzers and select analyzers you want to auto-run (e.g., VirusTotal, URLHaus).

Save.

# Test it

Create a case manually (New Case) → Add an observable (Add Observable → enter an IP, domain, hash, etc.).

If your analyzers are set in the template, TheHive will automatically send the observable to Cortex.

You’ll see results come back in the case within a few seconds.

👉 That’s it — now TheHive will automatically enrich new alerts with Cortex!



# 8. Shuffle Workflow

Wazuh finds something bad (alert 🚨).

Shuffle needs to receive that alert so it can start your workflow (TheHive case, Cortex analysis, MISP lookup).

To do this, Wazuh just has to send the alert to Shuffle’s Webhook URL (like giving a letter to the right mailbox 📬).

The “scary” curl command is simply the postman carrying the letter.
That’s all it is.

1. Create the script

On your Wazuh agent (or manager), make a new file:

    sudo nano /var/ossec/active-response/bin/send_to_shuffle.py
