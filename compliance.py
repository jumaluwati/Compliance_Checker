import streamlit as st
import pandas as pd
import requests, urllib3
from requests.auth import HTTPBasicAuth
import mysql.connector
import os, datetime, json
import hashlib
import uuid
import re

# Disable warnings
urllib3.disable_warnings()

st.set_page_config(page_title="Compliance Checker", layout="wide")

# === ENVIRONMENT VARIABLES ===
DNAC_IP = os.environ.get("DNAC_IP")
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

ISE_IP = os.environ.get("ISE_IP")
ISE_USERNAME = os.environ.get("ISE_USERNAME")
ISE_PASSWORD = os.environ.get("ISE_PASSWORD")

DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")

# === INFRASTRUCTURE VLAN RANGE ===
# Define the range of VLANs that should classify an interface as "Infrastructure Interface"
# This will include VLANs from 240 to 245 (inclusive).
# If you need to add other specific VLANs, you can add them to this set.
# For example, to include VLAN 224: INFRASTRUCTURE_VLAN_RANGE.add("224")
INFRASTRUCTURE_VLAN_RANGE = {str(vlan) for vlan in range(240, 246)}

# === AUTH ===
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

# === DEVICE FETCHING ===
def get_devices_from_dnac(token):
    devices = []
    limit, offset = 500, 1
    hdr = {"x-auth-token": token}
    while True:
        r = requests.get(
            f"https://{DNAC_IP}/dna/intent/api/v1/network-device?family=Switches%20and%20Hubs&limit={limit}&offset={offset}",
            headers=hdr, verify=False
        )
        if r.status_code != 200:
            st.error(f"Catalyst Center fetch error: {r.status_code}")
            break
        batch = r.json().get("response", [])
        if not batch:
            break
        for d in batch:
            dev_id = d["id"]
            # Get per-device detail for managementIpAddress
            r2 = requests.get(
                f"https://{DNAC_IP}/api/v1/network-device/{dev_id}",
                headers=hdr, verify=False
            )
            if r2.status_code == 200:
                d2 = r2.json().get("response", {})
                devices.append({
                    "id": dev_id,
                    "hostname": d2.get("hostname", ""),
                    "ip": d2.get("managementIpAddress", "")
                })
            else:
                devices.append({
                    "id": dev_id,
                    "hostname": d.get("hostname", ""),
                    "ip": ""
                })
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

def fetch_ise_switches(show_progress=False):
    url = f"https://{ISE_IP}/ers/config/networkdevice"
    headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
    switches = []
    try:
        resp = requests.get(url, headers=headers, auth=HTTPBasicAuth(ISE_USERNAME, ISE_PASSWORD), verify=False)
        resp.raise_for_status()
        total = resp.json()['SearchResult']['total']
        page_size = 100
        pages = (total // page_size) + 1
        if show_progress:
            progress = st.progress(0, text="Fetching ISE inventory...")
        fetched = 0
        for page in range(1, pages + 1):
            page_url = f"{url}?size={page_size}&page={page}"
            page_resp = requests.get(page_url, headers=headers, auth=HTTPBasicAuth(ISE_USERNAME, ISE_PASSWORD), verify=False)
            page_resp.raise_for_status()
            resources = page_resp.json()['SearchResult'].get('resources', [])
            for r in resources:
                # Get device details (name, IP)
                dev_url = f"{url}/{r['id']}"
                dev_resp = requests.get(dev_url, headers=headers, auth=HTTPBasicAuth(ISE_USERNAME, ISE_PASSWORD), verify=False)
                dev_resp.raise_for_status()
                dev = dev_resp.json()['NetworkDevice']
                switches.append({
                    "hostname": dev.get("name", ""),
                    "ip": dev.get("NetworkDeviceIPList", [{}])[0].get("ipaddress", "")
                })
                fetched += 1
                if show_progress and total > 0:
                    percent = min(fetched / total, 1.0)
                    progress.progress(percent, text=f"Fetching {fetched}/{total} ISE devices...")
        if show_progress:
            progress.empty()
    except Exception as e:
        st.error(f"Error fetching ISE switches: {e}")
    return switches

# == DOWNLOAD HELPER ==

def get_download_key(name, csv_bytes, unique_id=None):
    """
    Stable unique download-widget key.
    - unique_id: use device IP, device name, index, or a run-id for per-run files.
    - If unique_id is None we fallback to a stable derived id based on name+csv_hash.
    """
    csv_hash = hashlib.md5(csv_bytes).hexdigest()
    # prefer caller-provided unique id; otherwise derive one from name+hash (stable for same content)
    if unique_id is None:
        unique_id = f"{re.sub(r'[^0-9A-Za-z_-]', '_', name)}_{csv_hash[:8]}"

    state_key = f"dl_key_{unique_id}"
    state_hash = f"dl_hash_{unique_id}"

    # update only if content changed
    if state_hash not in st.session_state or st.session_state[state_hash] != csv_hash:
        st.session_state[state_key] = f"dl_{unique_id}_{csv_hash}_{int(datetime.datetime.now().timestamp())}"
        st.session_state[state_hash] = csv_hash

    return st.session_state[state_key]



# === DATABASE ===
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
        # Existing tables...
        c.execute("""
            CREATE TABLE IF NOT EXISTS device_configs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                device_name VARCHAR(255) UNIQUE,
                ip VARCHAR(64),
                config LONGTEXT,
                last_saved TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                id INT PRIMARY KEY,
                last_sync TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("INSERT IGNORE INTO sync_status (id) VALUES (1)")  # For CC
        c.execute("INSERT IGNORE INTO sync_status (id) VALUES (2)")  # For ISE

        # --- NEW: ISE inventory table ---
        c.execute("""
            CREATE TABLE IF NOT EXISTS ise_inventory (
                id INT AUTO_INCREMENT PRIMARY KEY,
                hostname VARCHAR(255) UNIQUE,
                ip VARCHAR(64),
                last_synced TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        db.commit(); c.close(); db.close()

def store_ise_inventory(devices):
    db = connect_db()
    if not db:
        return
    c = db.cursor()
    for d in devices:
        # Try insert/update by hostname
        c.execute("SELECT 1 FROM ise_inventory WHERE hostname = %s", (d["hostname"],))
        if c.fetchone():
            c.execute(
                "UPDATE ise_inventory SET ip=%s WHERE hostname=%s",
                (d["ip"], d["hostname"])
            )
        else:
            c.execute(
                "INSERT INTO ise_inventory (hostname, ip) VALUES (%s, %s)",
                (d["hostname"], d["ip"])
            )
    db.commit(); c.close(); db.close()

def list_ise_inventory():
    db = connect_db()
    if not db:
        return []
    c = db.cursor()
    c.execute("SELECT hostname, ip FROM ise_inventory")
    rows = [{"hostname": r[0], "ip": r[1]} for r in c.fetchall()]
    c.close(); db.close()
    return rows

def store_config(device, ip, config):
    db = connect_db()
    if not db:
        return
    c = db.cursor()
    c.execute("SELECT 1 FROM device_configs WHERE device_name = %s", (device,))
    if c.fetchone():
        c.execute("UPDATE device_configs SET config=%s, ip=%s WHERE device_name=%s", (config, ip, device))
    else:
        c.execute("INSERT INTO device_configs (device_name, ip, config) VALUES (%s, %s, %s)", (device, ip, config))
    db.commit(); c.close(); db.close()

def update_last_sync_cc():
    db = connect_db()
    if db:
        c = db.cursor()
        c.execute("UPDATE sync_status SET last_sync=NOW() WHERE id=1")
        db.commit(); c.close(); db.close()

def update_last_sync_ise():
    db = connect_db()
    if db:
        c = db.cursor()
        c.execute("UPDATE sync_status SET last_sync=NOW() WHERE id=2")
        db.commit(); c.close(); db.close()

def get_last_sync_time_cc():
    db = connect_db()
    if db:
        c = db.cursor()
        c.execute("SELECT last_sync FROM sync_status WHERE id=1")
        row = c.fetchone()
        c.close(); db.close()
        if row and row[0]:
            return row[0].strftime("%Y-%m-%d %H:%M:%S")
    return "Never"

def get_last_sync_time_ise():
    db = connect_db()
    if db:
        c = db.cursor()
        c.execute("SELECT last_sync FROM sync_status WHERE id=2")
        ts = c.fetchone()[0]
        c.close(); db.close()
        return ts.strftime("%Y-%m-%d %H:%M:%S")
    return "Never"

# === CONFIG & INTERFACE UTILS ===
def list_saved_devices():
    db = connect_db()
    if not db:
        return []
    c = db.cursor()
    c.execute("SELECT device_name, ip FROM device_configs")
    rows = [{"device_name": r[0], "ip": r[1]} for r in c.fetchall()]
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
    ints = {}; cur = None
    for l in cfg.splitlines():
        l = l.strip()
        if l.startswith("interface"):
            cur = l; ints[cur] = []
        elif cur and l:
            ints[cur].append(l)
    return ints

def parse_templates(cfg):
    tmps = {}; cur = None
    for l in cfg.splitlines():
        l = l.strip()
        if l.startswith("template"):
            cur = l; tmps[cur] = []
        elif cur and l:
            tmps[cur].append(l)
    return tmps

# === COMPLIANCE CHECKS ===
def check_classic(intfs):
    res = []
    for intf, lines in intfs.items():
        # --- NEW LOGIC: Check for Infrastructure VLANs (240-245) ---
        is_infra_vlan_by_range = False
        for line in lines:
            line = line.strip()
            if line.startswith("switchport access vlan"):
                try:
                    # Extract VLAN ID (e.g., from "switchport access vlan 224")
                    vlan_str = line.split("switchport access vlan")[1].strip().split(' ')[0]
                    if vlan_str in INFRASTRUCTURE_VLAN_RANGE:
                        is_infra_vlan_by_range = True
                        break # Found an infra VLAN, no need to check further lines
                except (IndexError, ValueError):
                    # Handle cases where the line might be malformed or VLAN not a number
                    pass
        # --- END NEW LOGIC ---

        status = ""
        # Apply the new rule with highest precedence
        if is_infra_vlan_by_range:
            status = "Infrastructure Interface"
        else:
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
    template_valid = any(
        "DefaultWiredDot1xClosedAuth" in name and
        any("access-session port-control auto" in line for line in lines)
        for name, lines in templates.items()
    )
    res = []
    for intf, lines in intfs.items():
        # --- NEW LOGIC: Check for Infrastructure VLANs (240-245) ---
        is_infra_vlan_by_range = False
        for line in lines:
            line = line.strip()
            if line.startswith("switchport access vlan"):
                try:
                    vlan_str = line.split("switchport access vlan")[1].strip().split(' ')[0]
                    if vlan_str in INFRASTRUCTURE_VLAN_RANGE:
                        is_infra_vlan_by_range = True
                        break
                except (IndexError, ValueError):
                    pass
        # --- END NEW LOGIC ---

        status = ""
        # Apply the new rule with highest precedence
        if is_infra_vlan_by_range:
            status = "Infrastructure Interface"
        else:
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

# === FULL SYNC WITH PROGRESS ===
def fetch_all_configs_from_dnac_with_progress():
    token = get_access_token()
    if not token:
        return

    # Step 1: Fetching device list with a spinner
    with st.spinner("Fetching Catalyst Center device list..."):
        devices = get_devices_from_dnac(token)

    if not devices:
        st.warning("No devices found in Catalyst Center.")
        return

    total = len(devices)
    # Step 2: Fetching device configurations with a progress bar
    progress = st.progress(0, text="Fetching device configs...")
    for idx, d in enumerate(devices):
        cfg = fetch_device_config_from_dnac(token, d["id"])
        if cfg:
            store_config(d["hostname"], d.get("ip", ""), cfg)
        progress.progress((idx + 1) / total, text=f"Fetching {idx + 1}/{total} device configs...")
    update_last_sync_cc()
    st.success("Sync complete.")
    progress.empty() # Clear the progress bar after completion


def normalize_config(raw):
    import json
    # Try to unwrap any number of JSON encodings
    for _ in range(2):
        try:
            if isinstance(raw, str) and raw.lstrip().startswith('{'):
                loaded = json.loads(raw)
                if isinstance(loaded, dict) and "response" in loaded:
                    raw = loaded["response"]
                else:
                    raw = loaded
        except Exception:
            break
    # Convert literal \n (if any) to real newlines
    if isinstance(raw, str) and r'\n' in raw:
        raw = raw.replace(r'\n', '\n')
    return raw

# === Table helpers ===

def show_limited_table_with_highlight(name, df, max_rows=1000, highlight_func=None, download_unique_id=None):
    total = len(df)
    if total == 0:
        st.info("No data to display.")
        return
    st.markdown(
        f"<span style='font-size: 0.95em; color: gray;'>Showing first {min(max_rows, total)} of {total} rows.</span>",
        unsafe_allow_html=True
    )
    if highlight_func:
        styled = df.head(max_rows).style.apply(highlight_func, axis=1)
        st.dataframe(styled, use_container_width=True)
    else:
        st.dataframe(df.head(max_rows), use_container_width=True)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    uniq = download_unique_id if download_unique_id is not None else name
    dl_key = get_download_key(name, csv_bytes, unique_id=uniq)
    file_safe = re.sub(r'[^A-Za-z0-9_.-]', '_', name)
    st.download_button(
        f"Download full {name} CSV",
        csv_bytes,
        file_name=f"{file_safe}_{uniq}.csv",
        mime="text/csv",
        key=dl_key
    )


def highlight_result_status(row):
    # Only color 'Compliant' (green), 'Non-Compliant' (red); no color for 'Infrastructure Interface'
    status = (
        row.get('Classic Compliance') or
        row.get('IBN Compliance') or
        row.get('Status') or
        ''
    )
    if status == 'Compliant':
        return ['background-color: rgba(40, 167, 69, 0.15); color: #ffffff;'] * len(row)
    elif status == 'Non-Compliant':
        return ['background-color: rgba(220, 53, 69, 0.15); color: #ffffff;'] * len(row)
    else:
        return [''] * len(row)


def show_limited_table(name, df, max_rows=1000, download_unique_id=None):
    total = len(df)
    if total == 0:
        st.info("No data to display.")
        return
    st.markdown(
        f"<span style='font-size: 0.95em; color: gray;'>Showing first {min(max_rows, total)} of {total} rows.</span>",
        unsafe_allow_html=True
    )
    st.dataframe(df.head(max_rows), use_container_width=True)
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    uniq = download_unique_id if download_unique_id is not None else name
    dl_key = get_download_key(name, csv_bytes, unique_id=uniq)
    file_safe = re.sub(r'[^A-Za-z0-9_.-]', '_', name)
    st.download_button(
        f"Download full {name} CSV",
        csv_bytes,
        file_name=f"{file_safe}_{uniq}.csv",
        mime="text/csv",
        key=dl_key
    )

def highlight_summary_status(row):
    # Row is a Series, columns might be "Compliant", "Non-Compliant", etc.
    colors = {
        "Compliant": "background-color: rgba(40, 167, 69, 0.15); color: #ffffff;",
        "Non-Compliant": "background-color: rgba(220, 53, 69, 0.15); color: #ffffff;",
        # Changed color for 'Infrastructure Interface' to white for dark mode visibility
        "Infrastructure Interface": "background-color: rgba(108, 117, 125, 0.10); color: #ffffff;"
    }
    style = []
    for col in row.index:
        if col in colors and row[col] > 0:
            style.append(colors[col])
        else:
            style.append("")
    return style

def normalize_config(raw):
    import json
    # Try to unwrap any number of JSON encodings
    for _ in range(2):
        try:
            if isinstance(raw, str) and raw.lstrip().startswith('{'):
                loaded = json.loads(raw)
                if isinstance(loaded, dict) and "response" in loaded:
                    raw = loaded["response"]
                else:
                    raw = loaded
        except Exception:
            break
    # Convert literal \n (if any) to real newlines
    if isinstance(raw, str) and r'\n' in raw:
        raw = raw.replace(r'\n', '\n')
    return raw

def filter_devices(devices, wanted, key):
    """
    Helper: Filter a list of dicts where dict[key].strip().lower() is in wanted set.
    Returns filtered list.
    """
    return [d for d in devices if d[key].strip().lower() in wanted]

# === MAIN APP === "stable version 2"

def main():
    init_db()

    st.markdown("""
        <style>
            .stButton > button {margin: 2px 8px;}
            .timestamp-badge {
                background: #23272e;
                border-radius: 6px;
                padding: 2px 10px;
                font-size: 0.94em;
                color: #6fbf73;
                margin-left: 6px;
            }
            /* Custom CSS for expander headers to ensure visibility in dark mode */
            .stExpander > div > div > div > div > p {
                color: #ffffff; /* Light color for text inside expander header */
            }
        </style>
        """, unsafe_allow_html=True)

    st.title("🔍 ISE Compliance Checker")
    st.caption("Compare and validate device configuration compliance across Catalyst Center and ISE inventories.")

    # Changed tabs: removed 'Comparison' tab, its content moved to 'Inventory'
    tab_inventory, tab_compliance = st.tabs(["Inventory", "Compliance"])

    with tab_inventory:
        st.header("Inventory Synchronization")
        with st.expander("Show/Hide Inventory Synchronization", expanded=True):
            sync_col1, sync_col2, sync_col3, sync_col4 = st.columns([1.5,1.5,1.1,1.1])
            with sync_col1:
                if st.button("🔄 Sync Catalyst Center"):
                    fetch_all_configs_from_dnac_with_progress() # Removed the outer st.spinner here
            with sync_col2:
                if st.button("🔄 Sync ISE Inventory"):
                    with st.spinner("Syncing ISE inventory..."):
                        ise_devices = fetch_ise_switches(show_progress=True)
                        if ise_devices:
                            store_ise_inventory(ise_devices)
                            update_last_sync_ise()
                            st.success(f"Stored {len(ise_devices)} ISE devices.")
                        else:
                            st.warning("No ISE devices fetched.")
            with sync_col3:
                st.markdown("**Last CC Sync**")
                st.markdown(
                    f"<span class='timestamp-badge'>{get_last_sync_time_cc()}</span>",
                    unsafe_allow_html=True
                )
            with sync_col4:
                st.markdown("**Last ISE Sync**")
                st.markdown(
                    f"<span class='timestamp-badge'>{get_last_sync_time_ise()}</span>",
                    unsafe_allow_html=True
                )
        st.markdown("---")
        st.subheader("Current Stored Inventories")
        col_cc, col_ise = st.columns(2)
        with col_cc:
            with st.expander("Catalyst Center Devices", expanded=True): # Made expandable
                cc_devices_df = pd.DataFrame(list_saved_devices())
                show_limited_table("Catalyst Center Devices", cc_devices_df, max_rows=1000) # Changed max_rows to 1000
        with col_ise:
            with st.expander("ISE Devices", expanded=True): # Made expandable
                ise_devices_df = pd.DataFrame(list_ise_inventory())
                show_limited_table("ISE Devices", ise_devices_df, max_rows=1000) # Changed max_rows to 1000

        # --- Moved Comparison Tab Content Here ---
        st.markdown("---")
        st.header("Inventory Comparison (Catalyst Center vs ISE)")
        with st.expander("Show/Hide Inventory Comparison", expanded=True): # Made expandable
            col_inv, _ = st.columns([1,3])
            if col_inv.button("Check Inventory Comparison"):
                cc_devices = list_saved_devices()
                ise_devices = list_ise_inventory()
                cc_set = set(d['ip'] for d in cc_devices if d['ip'])
                ise_set = set(d['ip'] for d in ise_devices if d['ip'])

                only_in_cc = cc_set - ise_set
                only_in_ise = ise_set - cc_set
                in_both = cc_set & ise_set

                inventory_rows = []
                for d in cc_devices:
                    norm = d['ip']
                    if norm and norm in only_in_cc: # Added check for norm
                        inventory_rows.append({
                            'Hostname': d['device_name'],
                            'IP': d['ip'],
                            'Inventory Status': 'Only in Catalyst Center'
                        })
                for d in ise_devices:
                    norm = d['ip']
                    if norm and norm in only_in_ise: # Added check for norm
                        inventory_rows.append({
                            'Hostname': d['hostname'],
                            'IP': d['ip'],
                            'Inventory Status': 'Only in ISE'
                        })
                for d in cc_devices: # Use cc_devices for 'In Both' to get consistent hostname from CC
                    norm = d['ip']
                    if norm and norm in in_both: # Added check for norm
                        inventory_rows.append({
                            'Hostname': d['device_name'],
                            'IP': d['ip'],
                            'Inventory Status': 'In Both'
                        })
                df_inventory = pd.DataFrame(inventory_rows)
                st.session_state["inventory_comparison_df"] = df_inventory
                st.session_state["inventory_comparison_ran"] = True

            if "inventory_comparison_df" in st.session_state and st.session_state.get("inventory_comparison_ran"):
                df_inventory = st.session_state["inventory_comparison_df"]
                if not df_inventory.empty:
                    # Use show_limited_table for consistency and features
                    show_limited_table(
                        "Inventory Comparison",
                        df_inventory.sort_values(by=["Inventory Status", "Hostname"]),
                        max_rows=1000 # Set max_rows for comparison table
                    )
                else:
                    st.info("No inventory data to compare. Click 'Check Inventory Comparison' to update.")


    with tab_compliance:
        st.header("Device Selection & Compliance Check")
        devices_info = list_saved_devices()
        device_names = [d["device_name"] for d in devices_info]
        ip_map = {d["device_name"]: d.get("ip", "") for d in devices_info}

        # --- MODIFIED: Wrap device selection in an expander, collapsed by default ---
        with st.expander("Select Devices for Compliance Check", expanded=False):
            if "selected_devices" not in st.session_state:
                st.session_state.selected_devices = []

            sel_col1, sel_col2, sel_col3 = st.columns([1, 1, 3])
            with sel_col1:
                if st.button("Select All Devices"):
                    st.session_state.selected_devices = device_names
            with sel_col2:
                if st.button("Unselect All"):
                    st.session_state.selected_devices = []
            with sel_col3:
                st.markdown(
                    f"<span style='color:#888;font-size:1.02em;'>Selected: <b>{len(st.session_state.selected_devices)}</b> device(s)</span>",
                    unsafe_allow_html=True
                )

            st.multiselect(
                "Pick one or more devices for compliance checking:",
                device_names,
                key="selected_devices"
            )
        # --- END MODIFIED SECTION ---

        st.markdown("") # Add some spacing after the expander

        col_run, col_clear = st.columns([1, 1])
        with col_run:
            run_check = st.button("Run Compliance Check", disabled=(len(st.session_state.selected_devices) == 0))
        with col_clear:
            clear_results = st.button("Clear Compliance Results")

        if run_check:
            st.session_state['compliance_run_id'] = datetime.datetime.now().strftime("%Y%m%d%H%M%S")

            selected = st.session_state.selected_devices
            if not selected:
                st.info("Please select one or more devices to proceed.")
            else:
                template_results, classic_data, ibn_data, combined_data = [], [], [], []

                total = len(selected)
                with st.spinner("Running compliance checks..."):
                    progress = st.progress(0, text="Checking devices...")
                    for idx, d in enumerate(selected):
                        ip = ip_map.get(d, "")
                        raw = load_config(d)
                        c = normalize_config(raw)
                        if not isinstance(c, str):
                            st.error(f"Config for {d} is not a string after normalization! Actual type: {type(c)}")
                            progress.progress((idx + 1) / total)
                            continue

                        intfs = parse_interfaces(c)
                        templates = parse_templates(c)
                        found = has_required = False
                        for name, lines in templates.items():
                            if "DefaultWiredDot1xClosedAuth" in name:
                                found = True
                                has_required = any("access-session port-control auto" in l for l in lines)
                                break

                        if found:
                            template_results.append({
                                "Device": d,
                                "IP Address": ip,
                                "Template Found": "Yes",
                                "Contains 'access-session port-control auto'": "Yes" if has_required else "No"
                            })
                            ibn = check_ibn(c, intfs)
                            for i, s in ibn:
                                ibn_data.append({"Device": d, "IP Address": ip, "Interface": i, "IBN Compliance": s})
                                combined_data.append({"Device": d, "IP Address": ip, "Method": "IBN", "Interface": i, "Status": s})
                        else:
                            cls = check_classic(intfs)
                            for i, s in cls:
                                classic_data.append({"Device": d, "IP Address": ip, "Interface": i, "Classic Compliance": s})
                                combined_data.append({"Device": d, "IP Address": ip, "Method": "Classic", "Interface": i, "Status": s})

                        progress.progress((idx + 1) / total, text=f"Checked {idx + 1}/{total} devices...")
                    progress.empty()

                st.session_state['compliance_template_results'] = template_results
                st.session_state['compliance_classic_data'] = classic_data
                st.session_state['compliance_ibn_data'] = ibn_data
                st.session_state['compliance_combined_data'] = combined_data
                st.session_state['compliance_ran'] = True

        if clear_results:
            for key in [
                'compliance_template_results',
                'compliance_classic_data',
                'compliance_ibn_data',
                'compliance_combined_data',
                'compliance_ran'
            ]:
                st.session_state.pop(key, None)

        if st.session_state.get('compliance_ran', False):
            st.subheader("Compliance Results")

            template_results = st.session_state.get('compliance_template_results', [])
            classic_data = st.session_state.get('compliance_classic_data', [])
            ibn_data = st.session_state.get('compliance_ibn_data', [])
            combined_data = st.session_state.get('compliance_combined_data', [])

            with st.expander("Template Presence (DefaultWiredDot1xClosedAuth)", expanded=False):
                show_limited_table("Template_Presence", pd.DataFrame(template_results), max_rows=1000)

            with st.expander("Classic Method Compliance", expanded=False):
                show_limited_table_with_highlight(
                    "Classic_Compliance",
                    pd.DataFrame(classic_data),
                    max_rows=1000,
                    highlight_func=highlight_result_status
                )
            with st.expander("IBN Method Compliance", expanded=False):
                show_limited_table_with_highlight(
                    "IBN_Compliance",
                    pd.DataFrame(ibn_data),
                    max_rows=1000,
                    highlight_func=highlight_result_status
                )

            with st.expander("Compliance Summary per Device and Method", expanded=True):
                df_combined = pd.DataFrame(combined_data)
                if not df_combined.empty:
                    df_combined["Status"] = df_combined["Status"].str.strip().str.title()
                    summary_method = (
                        df_combined.groupby(["Device", "Method", "Status"])
                        .size()
                        .unstack(fill_value=0)
                        .reset_index()
                    )
                    ip_map = df_combined.drop_duplicates("Device").set_index("Device")["IP Address"].to_dict()
                    summary_method["IP Address"] = summary_method["Device"].map(ip_map)
                    cols = ["Device", "IP Address", "Method", "Compliant", "Infrastructure Interface", "Non-Compliant"]
                    for col in cols:
                        if col not in summary_method:
                            summary_method[col] = 0
                    summary_method = summary_method[cols]
                    if not summary_method.empty:
                        styled_summary = summary_method.style.apply(highlight_summary_status, axis=1)
                        st.dataframe(styled_summary, use_container_width=True)
                    else:
                        st.info("No summary to display.")

                    st.info("Full per-interface results are available for download below. Only the summary above is shown for performance.")
                    csv_bytes = df_combined.to_csv(index=False).encode("utf-8")
                    dl_key = get_download_key("compliance_details", csv_bytes)
                    st.download_button(
                        "Download full compliance details (CSV)",
                        csv_bytes,
                        file_name="compliance_details.csv",
                        mime="text/csv",
                        key=dl_key
                    )
                else:
                    st.info("No data to display.")

    st.markdown(
        "<hr><center><small>Compliance Checker &copy; 2025 Cisco &middot; Version 2.1</small></center>",
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
