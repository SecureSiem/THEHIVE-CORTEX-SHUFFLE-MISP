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
    ```
    # on the Wazuh manager host
    sudo /var/ossec/framework/python/bin/pip3 install requests python-dotenv
    ```

Add soar.env To manager path - /var/ossec/integrations



  


    

