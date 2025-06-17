import streamlit as st
import pandas as pd
import requests, urllib3
from requests.auth import HTTPBasicAuth
import mysql.connector
import os, datetime, json

urllib3.disable_warnings()

DNAC_IP = os.environ.get("DNAC_IP")
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")

def get_access_token():
    try:
        r = requests.post(f"https://{DNAC_IP}/dna/system/api/v1/auth/token",
                          auth=HTTPBasicAuth(USERNAME, PASSWORD),
                          verify=False)
        if r.status_code == 200:
            return r.json().get("Token")
        st.error(f"Catalyst Center auth failed: {r.status_code}")
    except Exception as e:
        st.error(f"Catalyst Center auth error: {e}")
    return None

def get_devices_from_dnac(token):
    devices = []
    limit, offset = 500, 1
    hdr = {"x-auth-token": token}
    while True:
        r = requests.get(
            f"https://{DNAC_IP}/dna/intent/api/v1/network-device"
            f"?family=Switches%20and%20Hubs&limit={limit}&offset={offset}",
            headers=hdr, verify=False
        )
        if r.status_code != 200:
            st.error(f"Catalyst Center fetch error: {r.status_code}")
            break
        batch = r.json().get("response", [])
        devices.extend(batch)
        if len(batch) < limit:
            break
        offset += limit
    return devices

def fetch_device_config_from_dnac(token, dev_id):
    r = requests.get(
        f"https://{DNAC_IP}/dna/intent/api/v1/network-device/{dev_id}/config",
        headers={"x-auth-token": token}, verify=False
    )
    return r.text if r.status_code == 200 else None

def connect_db():
    try:
        return mysql.connector.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASSWORD, database=DB_NAME
        )
    except Exception as e:
        st.error(f"DB connect error: {e}")
        return None

def init_db():
    db = connect_db()
    if db:
        c = db.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS device_configs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_name VARCHAR(255) UNIQUE,
                config LONGTEXT,
                last_saved TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        db.commit()
        c.close()
        db.close()

def store_config(device, config):
    db = connect_db()
    if not db:
        return
    c = db.cursor()
    c.execute("SELECT 1 FROM device_configs WHERE device_name = %s", (device,))
    if c.fetchone():
        c.execute("UPDATE device_configs SET config=%s WHERE device_name=%s", (config, device))
    else:
        c.execute("INSERT INTO device_configs (device_name, config) VALUES (%s, %s)", (device, config))
    db.commit(); c.close(); db.close()

def fetch_all_configs_from_dnac():
    token = get_access_token()
    if not token:
        return
    for d in get_devices_from_dnac(token):
        cfg = fetch_device_config_from_dnac(token, d["id"])
        if cfg:
            store_config(d["hostname"], cfg)

def list_saved_devices():
    db = connect_db()
    if not db:
        return []
    c = db.cursor()
    c.execute("SELECT device_name FROM device_configs")
    rows = [r[0] for r in c.fetchall()]
    c.close(); db.close()
    return rows

def load_config(device):
    db = connect_db()
    if not db:
        return ""
    c = db.cursor()
    c.execute("SELECT config FROM device_configs WHERE device_name=%s", (device,))
    r = c.fetchone()
    c.close(); db.close()
    return r[0] if r else ""

def parse_interfaces(cfg):
    ints = {}
    cur = None
    for l in cfg.splitlines():
        l = l.strip()
        if l.startswith("interface"):
            cur = l
            ints[cur] = []
        elif cur and l:
            ints[cur].append(l)
    return ints

def parse_templates(cfg):
    tmps = {}
    cur = None
    for l in cfg.splitlines():
        l = l.strip()
        if l.startswith("template"):
            cur = l
            tmps[cur] = []
        elif cur and l:
            tmps[cur].append(l)
    return tmps

def check_classic(intfs):
    res = []
    for intf, lines in intfs.items():
        has_access = "switchport mode access" in lines
        has_auth = "authentication port-control auto" in lines

        if has_access and has_auth:
            status = "Compliant"
        elif has_access:
            status = "Non-Compliant"
        elif not has_access and not has_auth:
            status = "Infrastructure Interface"
        else:
            status = "Non-Compliant"
        res.append((intf, status))
    return res


def check_ibn(cfg, intfs):
    templates = parse_templates(cfg)

    # Check if the template contains the correct line
    template_valid = any(
        "DefaultWiredDot1xClosedAuth" in name and
        any("access-session port-control auto" in line for line in lines)
        for name, lines in templates.items()
    )

    res = []
    for intf, lines in intfs.items():
        has_access = "switchport mode access" in lines
        has_template = any("source template DefaultWiredDot1xClosedAuth" in line for line in lines)

        if has_access and has_template and template_valid:
            status = "Compliant"
        elif has_access:
            status = "Non-Compliant"
        elif not has_access and not has_template:
            status = "Infrastructure Interface"
        else:
            status = "Non-Compliant"
        res.append((intf, status))
    return res

def highlight_status(row):
    status = row.get('Status', row.get('Classic Compliance', row.get('IBN Compliance', '')))
    if status == 'Compliant':
        return ['background-color: rgba(40, 167, 69, 0.15); color: #ffffff;'] * len(row)
    elif status == 'Non-Compliant':
        return ['background-color: rgba(220, 53, 69, 0.15); color: #ffffff;'] * len(row)
    
    return [''] * len(row)



# === END FUNCTIONS ===

def main():
    st.title("Compliance Checker - Simplified")
    init_db()
    st.info("Auto-fetching all switch configs from Catalyst Center...")
    fetch_all_configs_from_dnac()

    devices = list_saved_devices()
    # Initialize session state once
    if "selected_devices" not in st.session_state:
        st.session_state.selected_devices = devices

    # Handle Unselect All BEFORE rendering the multiselect
    if st.button("Unselect All"):
        st.session_state.selected_devices = []

    # Now draw the multiselect, using session state
    sel = st.multiselect("Pick devices to check", devices, default=st.session_state.selected_devices, key="selected_devices")



    if not sel:
        st.warning("No devices selected.")
        return

    if st.button("Run Compliance"):
    # Table 1 – Template Check Summary
        template_results = []

        # Table 2 & 3 – Classic and IBN Compliance
        classic_data = []
        ibn_data = []

        # Table 4 – Combined View
        combined_data = []

        for d in sel:
            raw = load_config(d)
            try:
                c = json.loads(raw).get("response", raw)
            except:
                c = raw
            intfs = parse_interfaces(c)

            # === Template Check (Table 1) ===
            templates = parse_templates(c)
            found = False
            has_required = False
            for name, lines in templates.items():
                if "DefaultWiredDot1xClosedAuth" in name:
                    found = True
                    has_required = any("access-session port-control auto" in l for l in lines)
                    break
            template_results.append({
                "Device": d,
                "Template Found": "Yes" if found else "No",
                "Contains 'access-session port-control auto'": "Yes" if has_required else "No"
            })

            # === Classic Compliance (Table 2) ===
            cls = check_classic(intfs)
            for i, s in cls:
                classic_data.append({"Device": d, "Interface": i, "Classic Compliance": s})
                combined_data.append({"Device": d, "Method": "Classic", "Interface": i, "Status": s})

            # === IBN Compliance (Table 3) ===
            ibn = check_ibn(c, intfs)
            for i, s in ibn:
                ibn_data.append({"Device": d, "Interface": i, "IBN Compliance": s})
                combined_data.append({"Device": d, "Method": "IBN", "Interface": i, "Status": s})

        # === Show all tables ===

        st.subheader("1. Template Presence Check")
        st.markdown("<span style='font-size: 0.85em; color: gray;'>Template: <code>DefaultWiredDot1xClosedAuth</code></span>", unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(template_results), use_container_width=True)  # No styling here


        st.subheader("2. Classic Method Compliance")
        st.markdown("<span style='font-size: 0.85em; color: gray;'>Compliant if both <code>switchport mode access</code> and <code>authentication port-control auto</code> exist</span>", unsafe_allow_html=True)
        styled_classic = pd.DataFrame(classic_data).style.apply(highlight_status, axis=1)
        st.dataframe(styled_classic, use_container_width=True)

        st.subheader("3. IBN Method Compliance")
        st.markdown("<span style='font-size: 0.85em; color: gray;'>Compliant if <code>switchport mode access</code> and <code>source template DefaultWiredDot1xClosedAuth</code> exist, and template includes <code>access-session port-control auto</code></span>", unsafe_allow_html=True)
        styled_ibn = pd.DataFrame(ibn_data).style.apply(highlight_status, axis=1)
        st.dataframe(styled_ibn, use_container_width=True)

        st.subheader("4. Combined View")
        st.markdown("<span style='font-size: 0.85em; color: gray;'>Comparison of Classic and IBN compliance results per interface</span>", unsafe_allow_html=True)
        styled_combined = pd.DataFrame(combined_data).style.apply(highlight_status, axis=1)
        st.dataframe(styled_combined, use_container_width=True)



if __name__ == "__main__":
    main()
