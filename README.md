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

Edit the script and add your shuffle URL

2. Make it executable

       sudo chmod +x /var/ossec/active-response/bin/send_to_shuffle.py

3. Tell Wazuh to use it

   Edit Wazuh config:
   
       sudo nano /var/ossec/etc/ossec.conf

   Add this inside <active-response> block:

       <command>
        <name>send_to_shuffle</name>
        <executable>send_to_shuffle.py</executable>
        <timeout_allowed>no</timeout_allowed>
       </command>

       <active-response>
        <command>send_to_shuffle</command>
        <location>local</location>
        <rules_id>100001</rules_id>   <!-- replace with the rule ID you want -->
       </active-response>

Restart Wazuh

    sudo systemctl restart wazuh-manager


# For this step 8 you need to > Create the workflow file on your server or workstation

Open a terminal on the machine where you manage Shuffle (or any machine from which you can upload to Shuffle). Run this single command to create the file wazuh-to-soar-workflow.json in your current folder: (copy and paste to terminal the coomand inside # wazuh-to-soar-workflow

After that command completes, you will have a file named wazuh-to-soar-workflow.json in your current directory. You can verify:

    ls -l wazuh-to-soar-workflow.json

in this json much changes :

# Change these:

# TheHive

thehive_url → your TheHive server URL, e.g.
http://192.168.1.60:9000

thehive_api_key → API key you created in TheHive.

$ MISP

misp_url → your MISP URL, e.g.
http://192.168.1.70:8080

misp_api_key → API key from MISP (you create it in MISP UI).

# Cortex

cortex_url → your Cortex URL, e.g.
http://192.168.1.80:9001

cortex_api_key → API key or username/password token from Cortex.

cortex_analyzers → list of analyzers you want to run.
(In Cortex UI, check available analyzers; adjust names if needed.)

# (Optional) tlp → Traffic Light Protocol classification (default 2 = Amber).

# (Optional) default_tags → tags that will appear in TheHive case.

⚡ Steps after saving

1. Save the file as wazuh-to-soar-workflow.json.

2. Go to Shuffle → Workflows → Import workflow → Upload JSON.

3. Shuffle will load the workflow with nodes already built.

4. Check the config, replace <...> with your real URLs and keys.

5. Save workflow, then get the Webhook URL from the trigger node.

6. Configure your Wazuh script/integration to POST alerts to that Webhook.


# 9. Get the Webhook URL from the imported workflow

Open the imported workflow in Shuffle.

Click the Webhook trigger node (first node).

Shuffle will show you a generated Webhook URL (something like http://<shuffle-ip>:5001/api/v1/hooks/<id>).

Copy that URL.


# 10. Make Wazuh send alerts to Shuffle (simplest way)

You already have send_to_shuffle.py idea earlier. Replace the SHUFFLE_WEBHOOK variable with the Webhook URL you copied. Put the script on the Wazuh manager or agent that will forward alerts and configure Wazuh integrator to call that script for the rules you want.

URl PUT IN THIS SCRIPT:

    /var/ossec/integrations/send_to_shuffle.py



# BONUS

# If import fails or shuffle expects another schema

Shuffle versions and installs may expect a slightly different JSON structure. If the import gives an error:

1. Open the workflow editor and I will guide you to recreate it with drag & drop (super easy).

2. Or connect with me and share the specific error message here and I’ll fix the JSON format for your Shuffle version.
