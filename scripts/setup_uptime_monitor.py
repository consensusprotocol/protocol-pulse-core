#!/usr/bin/env python3
"""
UptimeRobot monitoring setup for Protocol Pulse.

Prerequisites:
  1. Create a free account at https://uptimerobot.com (50 monitors, 5-min checks)
  2. Go to My Settings > API Settings > Main API Key (or create a Monitor-Specific key)
  3. Add to ~/protocol_pulse/.env:
       UPTIMEROBOT_API_KEY=ur...
       PBX_PHONE_NUMBER=+1XXXXXXXXXX
       PBX_EMAIL=you@example.com

Usage:
  python3 scripts/setup_uptime_monitor.py            # Create monitors + alert contacts
  python3 scripts/setup_uptime_monitor.py --status    # Check current uptime stats
  python3 scripts/setup_uptime_monitor.py --delete    # Remove all PP monitors
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

API_BASE = "https://api.uptimerobot.com/v2"

MONITORS = [
    {
        "friendly_name": "PP Health Endpoint",
        "url": "https://protocolpulse.io/health",
        "type": 2,  # keyword
        "sub_type": 2,  # keyword exists
        "keyword_type": 2,  # keyword exists
        "keyword_value": "ok",
    },
    {
        "friendly_name": "PP Homepage",
        "url": "https://protocolpulse.io/",
        "type": 1,  # HTTP(s)
    },
    {
        "friendly_name": "PP Relay",
        "url": "https://relay.protocolpulse.io/exec",
        "type": 1,  # HTTP(s)
    },
]

PP_PREFIX = "PP "


def get_api_key():
    key = os.getenv("UPTIMEROBOT_API_KEY")
    if not key:
        print("ERROR: UPTIMEROBOT_API_KEY not set in .env")
        sys.exit(1)
    return key


def post(endpoint, data=None):
    """POST to UptimeRobot API with form-encoded data."""
    api_key = get_api_key()
    payload = {"api_key": api_key, "format": "json"}
    if data:
        payload.update(data)
    resp = requests.post(
        f"{API_BASE}/{endpoint}",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


# ── Alert contacts ──────────────────────────────────────────────────────────

def create_alert_contacts():
    """Create SMS and email alert contacts, return 'id_0_0-id_0_0' string."""
    contact_ids = []

    phone = os.getenv("PBX_PHONE_NUMBER")
    email = os.getenv("PBX_EMAIL")

    if phone:
        result = post("newAlertContact", {
            "type": 1,  # SMS
            "friendly_name": "PP SMS Alert",
            "value": phone,
        })
        if result.get("stat") == "ok":
            cid = result["alertcontact"]["id"]
            contact_ids.append(str(cid))
            print(f"  SMS alert contact created: id={cid}")
        else:
            err = result.get("error", {}).get("message", "unknown")
            print(f"  SMS alert contact failed: {err}")
            # Check if already exists
            if "already" in err.lower():
                print("  (contact may already exist, continuing)")
    else:
        print("  PBX_PHONE_NUMBER not set, skipping SMS alert")

    if email:
        result = post("newAlertContact", {
            "type": 2,  # email
            "friendly_name": "PP Email Alert",
            "value": email,
        })
        if result.get("stat") == "ok":
            cid = result["alertcontact"]["id"]
            contact_ids.append(str(cid))
            print(f"  Email alert contact created: id={cid}")
        else:
            err = result.get("error", {}).get("message", "unknown")
            print(f"  Email alert contact failed: {err}")
            if "already" in err.lower():
                print("  (contact may already exist, continuing)")
    else:
        print("  PBX_EMAIL not set, skipping email alert")

    # Format: "id_threshold_recurrence-id_threshold_recurrence"
    # threshold=0 (default), recurrence=0 (every time)
    if contact_ids:
        return "-".join(f"{cid}_0_0" for cid in contact_ids)
    return ""


def get_existing_alert_contacts():
    """Fetch existing alert contacts and return formatted string for PP ones."""
    result = post("getAlertContacts")
    if result.get("stat") != "ok":
        return ""
    contacts = result.get("alert_contacts", [])
    pp_ids = [
        str(c["id"]) for c in contacts
        if c.get("friendly_name", "").startswith("PP ")
    ]
    if pp_ids:
        return "-".join(f"{cid}_0_0" for cid in pp_ids)
    # Fall back to all contacts
    all_ids = [str(c["id"]) for c in contacts[:5]]
    if all_ids:
        return "-".join(f"{cid}_0_0" for cid in all_ids)
    return ""


# ── Create monitors ─────────────────────────────────────────────────────────

def create_monitors():
    print("=== Creating UptimeRobot alert contacts ===")
    alert_string = create_alert_contacts()
    if not alert_string:
        print("  No new contacts created, checking existing...")
        alert_string = get_existing_alert_contacts()

    print(f"\n=== Creating UptimeRobot monitors ===")
    if alert_string:
        print(f"  Alert contacts: {alert_string}")
    else:
        print("  WARNING: No alert contacts configured, monitors will have no alerts")

    for mon in MONITORS:
        payload = {
            "friendly_name": mon["friendly_name"],
            "url": mon["url"],
            "type": mon["type"],
        }
        if mon.get("sub_type"):
            payload["sub_type"] = mon["sub_type"]
        if mon.get("keyword_type"):
            payload["keyword_type"] = mon["keyword_type"]
        if mon.get("keyword_value"):
            payload["keyword_value"] = mon["keyword_value"]
        if alert_string:
            payload["alert_contacts"] = alert_string

        result = post("newMonitor", payload)
        if result.get("stat") == "ok":
            mid = result["monitor"]["id"]
            print(f"  CREATED: {mon['friendly_name']} -> id={mid}")
        else:
            err = result.get("error", {}).get("message", "unknown")
            print(f"  FAILED:  {mon['friendly_name']} -> {err}")


# ── Status ───────────────────────────────────────────────────────────────────

STATUS_MAP = {0: "PAUSED", 1: "NOT CHECKED", 2: "UP", 8: "SEEMS DOWN", 9: "DOWN"}


def show_status():
    print("=== UptimeRobot Monitor Status ===\n")
    result = post("getMonitors", {"response_times": 1, "response_times_limit": 1})
    if result.get("stat") != "ok":
        print(f"Error: {result}")
        sys.exit(1)

    monitors = result.get("monitors", [])
    pp_monitors = [m for m in monitors if m["friendly_name"].startswith(PP_PREFIX)]

    if not pp_monitors:
        print("No Protocol Pulse monitors found.")
        print("Run without flags to create them: python3 scripts/setup_uptime_monitor.py")
        return

    for m in pp_monitors:
        status = STATUS_MAP.get(m["status"], f"UNKNOWN({m['status']})")
        url = m["url"]
        mid = m["id"]
        rts = m.get("response_times", [])
        rt_str = f"{rts[0]['value']}ms" if rts else "N/A"
        indicator = "OK" if m["status"] == 2 else "!!"
        print(f"  [{indicator}] {m['friendly_name']}")
        print(f"       URL:      {url}")
        print(f"       Status:   {status}")
        print(f"       Latency:  {rt_str}")
        print(f"       ID:       {mid}")
        print()

    up = sum(1 for m in pp_monitors if m["status"] == 2)
    total = len(pp_monitors)
    print(f"Summary: {up}/{total} monitors UP")


# ── Delete ───────────────────────────────────────────────────────────────────

def delete_monitors():
    print("=== Deleting Protocol Pulse monitors ===\n")
    result = post("getMonitors")
    if result.get("stat") != "ok":
        print(f"Error: {result}")
        sys.exit(1)

    monitors = result.get("monitors", [])
    pp_monitors = [m for m in monitors if m["friendly_name"].startswith(PP_PREFIX)]

    if not pp_monitors:
        print("No Protocol Pulse monitors found.")
        return

    for m in pp_monitors:
        del_result = post("deleteMonitor", {"id": m["id"]})
        if del_result.get("stat") == "ok":
            print(f"  DELETED: {m['friendly_name']} (id={m['id']})")
        else:
            err = del_result.get("error", {}).get("message", "unknown")
            print(f"  FAILED:  {m['friendly_name']} -> {err}")

    print(f"\nRemoved {len(pp_monitors)} monitor(s).")


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="UptimeRobot monitoring for Protocol Pulse")
    parser.add_argument("--status", action="store_true", help="Show current monitor status")
    parser.add_argument("--delete", action="store_true", help="Delete all PP monitors")
    args = parser.parse_args()

    if args.status:
        show_status()
    elif args.delete:
        delete_monitors()
    else:
        create_monitors()


if __name__ == "__main__":
    main()
