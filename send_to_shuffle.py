#!/usr/bin/env python3
import sys, json, requests

# Shuffle Webhook (replace with your real one from Step 3)
SHUFFLE_WEBHOOK = "http://<shuffle-ip>:5001/api/v1/hooks/<id>"

if __name__ == "__main__":
    # Read alert from Wazuh
    data = sys.stdin.readline()
    alert = json.loads(data)

    # Send alert to Shuffle
    try:
        r = requests.post(
            SHUFFLE_WEBHOOK,
            headers={"Content-Type": "application/json"},
            json=alert,
            timeout=10
        )
        print(f"Sent to Shuffle: {r.status_code}")
    except Exception as e:
        print(f"Error sending to Shuffle: {e}")
