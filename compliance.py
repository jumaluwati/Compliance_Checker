import streamlit as st
import pandas as pd
import requests
import urllib3
from requests.auth import HTTPBasicAuth
import mysql.connector
import os
import datetime
import json

urllib3.disable_warnings()

DNAC_IP = os.environ.get("DNAC_IP")
USERNAME = os.environ.get("USERNAME")
PASSWORD = os.environ.get("PASSWORD")

DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_NAME = os.environ.get("DB_NAME")

def get_access_token():
    token_url = f"https://{DNAC_IP}/dna/system/api/v1/auth/token"
    try:
        response = requests.post(token_url, auth=HTTPBasicAuth(USERNAME, PASSWORD), verify=False)
        if response.status_code == 200:
            token_dict = response.json()
            return token_dict.get('Token')
        else:
            st.error(f"Failed to retrieve token: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        st.error(f"Error retrieving token: {e}")
        return None

def get_devices_from_dnac(token):
    url_device_id = f"https://{DNAC_IP}/dna/intent/api/v1/network-device"
    headers = {"x-auth-token": token, 'content-type': 'application/json'}
    try:
        response_devices = requests.get(url_device_id, headers=headers, verify=False)
        if response_devices.status_code == 200:
            return response_devices.json()['response']
        else:
            st.error(f"Failed to fetch devices: {response_devices.status_code} - {response_devices.text}")
            return None
    except Exception as e:
        st.error(f"Error fetching devices: {e}")
        return None

def fetch_device_config_from_dnac(token, device_id):
    url_device_config = f"https://{DNAC_IP}/dna/intent/api/v1/network-device/{device_id}/config"
    headers = {"x-auth-token": token, 'content-type': 'application/json'}
    try:
        response = requests.get(url_device_config, headers=headers, verify=False)
        st.write(f"Fetching config for device ID: {device_id}")
        st.write(f"API Response Status Code: {response.status_code}")

        if response.status_code == 200:
            return response.text
        else:
            st.error(f"Failed to fetch config for device {device_id}: {response.status_code} - {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Request Exception: {e}")
        return None
    except Exception as e:
        st.error(f"Error fetching device config: {e}")
        return None

def parse_templates(config):
    templates = {}
    current_template = None
    
    for line in config.splitlines():
        line = line.strip()
        if line.startswith("template"):
            current_template = line
            templates[current_template] = set()
        elif current_template and line:
            templates[current_template].add(line)
    
    return templates

def parse_interfaces(config):
    interfaces = {}
    current_interface = None
    
    for line in config.splitlines():
        line = line.strip()
        if line.startswith("interface"):
            current_interface = line
            interfaces[current_interface] = []
        elif current_interface and line:
            interfaces[current_interface].append(line)
    
    return interfaces

def check_compliance(templates, interfaces, conditions):
    template_results = []
    interface_results = []

    for cond in conditions:
        if cond['type'] == 'Template':
            template_name = cond['template']
            required_line = cond['line']

            for device_name, device_templates in templates.items():
                compliant = False
                for template, lines in device_templates.items():
                    if template_name in template:  # Check if the template name is in the template string
                        if required_line in lines:
                            status = "Compliant"
                            compliant = True
                            break  # No need to check other templates for this device
                        else:
                            status = "Non-Compliant (Missing Line)"
                            compliant = True
                            break
                if not compliant:
                    status = "Non-Compliant (Template Missing)"
                template_results.append((device_name, cond['name'], template_name, required_line, status))

        elif cond['type'] == 'Interface':
            user_specified_line = cond['line_of_interest']
            user_defined_condition = cond['condition']
            shutdown_label = cond['shutdown_label']
            other_interfaces_label = cond['other_interfaces_label']
            include_shutdown = cond['include_shutdown']
            include_other_interfaces = cond['include_other_interfaces']

            for device_name, device_interfaces in interfaces.items():
                for interface_name, interface_lines in device_interfaces.items():
                    if any("shutdown" in line for line in interface_lines):
                        if include_shutdown:
                            status = f"{interface_name}: {shutdown_label}"
                            interface_results.append((device_name, cond['name'], interface_name, user_specified_line, status))
                        continue  # Skip further checks for shutdown interfaces if included

                    if user_specified_line in interface_lines:
                        status = f"{interface_name}: {user_defined_condition}"
                    elif include_other_interfaces:
                        status = f"{interface_name}: {other_interfaces_label}"
                    else:
                        continue  # Skip interfaces that do not match the user-specified line

                    interface_results.append((device_name, cond['name'], interface_name, user_specified_line, status))

    return template_results, interface_results

def connect_to_db():
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return mydb
    except Exception as e:
        st.error(f"Database Connection Error: {e}")
        return None

def store_config_in_db(device_name, config):
    mydb = connect_to_db()
    if mydb:
        try:
            mycursor = mydb.cursor()
            sql_check = "SELECT COUNT(*) FROM device_configs WHERE device_name = %s"
            val_check = (device_name,)
            mycursor.execute(sql_check, val_check)
            result = mycursor.fetchone()[0]

            if result > 0:
                sql = "UPDATE device_configs SET config = %s, last_saved = %s WHERE device_name = %s"
                val = (config, datetime.datetime.now(), device_name)
            else:
                sql = "INSERT INTO device_configs (device_name, config, last_saved) VALUES (%s, %s, %s)"
                val = (device_name, config, datetime.datetime.now())
            mycursor.execute(sql, val)
            mydb.commit()
            st.success(f"Configuration saved to DB for {device_name}")
        except Exception as e:
            st.error(f"Error saving config to DB: {e}")
        finally:
            if hasattr(mycursor, 'close'):
                mycursor.close()
            if hasattr(mydb, 'close'):
                mydb.close()

def create_table():
    mydb = connect_to_db()
    if mydb:
        mycursor = None
        try:
            mycursor = mydb.cursor()
            mycursor.execute("""
                CREATE TABLE IF NOT EXISTS device_configs (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    device_name VARCHAR(255) NOT NULL,
                    config LONGTEXT,
                    last_saved TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            mydb.commit()
            st.success("Table 'device_configs' created (if it didn't exist).")
        except Exception as e:
            st.error(f"Error creating table: {e}")
        finally:
            if mycursor:
                mycursor.close()
            if hasattr(mydb, 'close'):
                mydb.close()

def get_existing_devices():
    mydb = connect_to_db()
    if mydb:
        try:
            mycursor = mydb.cursor()
            sql = "SELECT device_name, last_saved FROM device_configs"
            mycursor.execute(sql)
            results = mycursor.fetchall()
            return results
        except Exception as e:
            st.error(f"Error fetching existing devices: {e}")
            return []
        finally:
            if hasattr(mycursor, 'close'):
                mycursor.close()
            if hasattr(mydb, 'close'):
                mydb.close()
    return []

def delete_device_from_db(device_name):
    mydb = connect_to_db()
    if mydb:
        try:
            mycursor = mydb.cursor()
            sql = "DELETE FROM device_configs WHERE device_name = %s"
            val = (device_name,)
            mycursor.execute(sql, val)
            mydb.commit()
            st.success(f"Device '{device_name}' deleted from DB.")
        except Exception as e:
            st.error(f"Error deleting device: {e}")
        finally:
            if hasattr(mycursor, 'close'):
                mycursor.close()
            if hasattr(mydb, 'close'):
                mydb.close()

def main():
    # Step 0: Title
    st.title("Switch Configuration Compliance Checker with DNAC Integration")

    # Initialize session state variables
    if 'condition' not in st.session_state:
        st.session_state.condition = ""
    if 'conditions' not in st.session_state:
        st.session_state.conditions = []  # Initialize conditions if not present

    create_table()

    # Step 1: DNAC Connection Section
    with st.expander("DNAC Connection", expanded=False):
        dnac_ip = st.text_input("Enter Cisco DNAC IP (e.g., 10.48.90.136)", value=DNAC_IP, key="dnac_ip")
        username = st.text_input("Enter Cisco DNAC Username", value=USERNAME, key="dnac_username")
        password = st.text_input("Enter Cisco DNAC Password", value=PASSWORD, type="password", key="dnac_password")

        token = None  # Initialize token outside the conditional block
        if dnac_ip and username and password:
            token = get_access_token()
            if token:
                st.success("Connected to DNAC successfully!")

    # Step 2: Device Configuration Source
    st.subheader("Device Configuration Source")
    uploaded_file = st.file_uploader("Upload a configuration file", type=["txt"], key="config_upload")

    existing_devices = get_existing_devices()
    device_names = [device[0] for device in existing_devices]

    # Step 3: Select Saved Devices
    selected_saved_devices = st.multiselect("Select Saved Devices for Compliance Check", device_names, key="saved_devices")

    if uploaded_file is not None:
        config_content = uploaded_file.read().decode('utf-8-sig')
        device_name = uploaded_file.name.split('.')[0]  # Use the file name as the device name
        st.text_area(label="Uploaded Config", value=config_content, height=150, key=f"uploaded_config_{device_name}")

        if st.button(f"Add '{device_name}' Configuration to Database", key=f"save_{device_name}"):
            store_config_in_db(device_name, config_content)
            st.success(f"Uploaded configuration added as {device_name} in the database.")
            st.rerun()
    
    # Step 4: DNAC Device Selection
    selected_dnac_devices = []
    if token:
        devices = get_devices_from_dnac(token)
        if devices:
            available_devices = [device for device in devices if device['hostname'] not in device_names]
            dnac_device_names = [device['hostname'] for device in available_devices]
            selected_dnac_devices = st.multiselect("Select Devices from DNAC", dnac_device_names, key="dnac_devices")

            if selected_dnac_devices:
                st.write(f"Selected Devices from DNAC: {', '.join(selected_dnac_devices)}")

                if st.button("Fetch and Store DNAC Configurations", key="fetch_dnac"):
                    for device in available_devices:
                        if device['hostname'] in selected_dnac_devices:
                            device_config = fetch_device_config_from_dnac(token, device['id'])
                            if device_config:
                                store_config_in_db(device['hostname'], device_config)
                            else:
                                st.warning(f"No configuration available for device: {device['hostname']}")
                    st.rerun()

    # Step 5: Compliance Policy Definition (AFTER Device Selection)
    st.subheader("Compliance Policy Definition")
    condition_type = st.selectbox("Select Condition Type", ["Template", "Interface"], index=0, key="condition_type")

    if condition_type == "Template":
        st.write("### Add a Template Condition")
        new_name = st.text_input("Condition Name", key="template_name")
        template_name = st.text_input("Template Name", key="template_template_name")
        required_line = st.text_input("Required Line", key="template_required_line")

        if st.button("Save Template Condition", key="save_template_condition"):
            if new_name and template_name and required_line:
                st.session_state.conditions.append({
                    "name": new_name,
                    "type": "Template",
                    "template": template_name,
                    "line": required_line
                })
                st.success("Template condition saved!")
            else:
                st.warning("Please fill in all fields.")

    elif condition_type == "Interface":
        st.write("### Add an Interface Condition")
        new_name = st.text_input("Condition Name", key="interface_name")
        line_of_interest = st.text_input("Line of Interest (e.g., switchport mode trunk)", key="interface_line_of_interest")
        user_defined_condition = st.text_input("Condition Label for User-Specified Line (e.g., Compliant, Good, Warning, etc.)", key="interface_condition_label")

        st.write("#### Optional Settings")
        include_shutdown = st.checkbox("Include Shutdown Interfaces", value=False, key="include_shutdown")
        shutdown_label = st.text_input("Label for Shutdown Interfaces (default: Shutdown)", value="Shutdown", disabled=not include_shutdown, key="shutdown_label")

        include_other_interfaces = st.checkbox("Include Other Interfaces", value=False, key="include_other_interfaces")
        other_interfaces_label = st.text_input("Label for Other Interfaces (default: Not Good Interfaces)", value="Not Good Interfaces", disabled=not include_other_interfaces, key="other_interfaces_label")

        if st.button("Save Interface Condition", key="save_interface_condition"):
            if new_name and line_of_interest and user_defined_condition:
                st.session_state.conditions.append({
                    "name": new_name,
                    "type": "Interface",
                    "line_of_interest": line_of_interest.strip(),
                    "condition": user_defined_condition.strip(),
                    "include_shutdown": include_shutdown,
                    "shutdown_label": shutdown_label.strip(),
                    "include_other_interfaces": include_other_interfaces,
                    "other_interfaces_label": other_interfaces_label.strip()
                })
                st.success("Interface condition saved!")
            else:
                st.warning("Please fill in all required fields.")

    # Display Saved Conditions
    st.subheader("Saved Conditions")
    if st.session_state.conditions:
        for i, cond in enumerate(st.session_state.conditions):
            col1, col2, col3 = st.columns([5, 1, 1])  # Adjust column widths as needed
            with col1:
                st.write(f"{i+1}. **{cond['name']}** - {cond['type']} Condition")
            with col2:
                # Add a delete button for each condition
                if st.button("Delete", key=f"delete_condition_{i}"):
                    del st.session_state.conditions[i]
                    st.rerun()
            with col3:
                pass  # Placeholder for potential future use

    # Step 6: Compliance Check
    st.subheader("Run Compliance Check")
    if st.button("Check Compliance for Selected Devices", key="run_compliance"):
        all_selected_devices = selected_saved_devices + selected_dnac_devices
        templates = {}
        interfaces = {}

        for device_name in all_selected_devices:
            mydb = connect_to_db()
            if mydb:
                try:
                    mycursor = mydb.cursor()
                    sql = "SELECT config FROM device_configs WHERE device_name = %s"
                    val = (device_name,)
                    mycursor.execute(sql, val)
                    result = mycursor.fetchone()

                    if result:
                        config_text = result[0]
                        try:
                            config_json = json.loads(config_text)  # Convert JSON string to dictionary
                            config_text = config_json.get("response", "")  # Extract plain text config
                        except json.JSONDecodeError:
                            # If it's not a JSON, assume it's plain text
                            pass

                        st.write(f"Configuration for device {device_name}:")
                        st.text_area(label=f"Config for {device_name}", value=config_text, height=300, key=f"config_{device_name}")

                        parsed_templates = parse_templates(config_text)
                        parsed_interfaces = parse_interfaces(config_text)
                        templates[device_name] = parsed_templates
                        interfaces[device_name] = parsed_interfaces
                    else:
                        st.error(f"Could not retrieve config for {device_name} from DB")
                except Exception as e:
                    st.error(f"Error during compliance check: {e}")
                finally:
                    if hasattr(mycursor, 'close'):
                        mycursor.close()
                    if hasattr(mydb, 'close'):
                        mydb.close()
        # Run compliance check
        template_results, interface_results = check_compliance(
            templates, interfaces, st.session_state.conditions
        )

        st.write("### Compliance Results")
        st.write("#### Template Conditions Results:")
        template_preview_df = pd.DataFrame(
            template_results,
            columns=["Device", "Condition Name", "Template", "Required Line", "Status"]
        )
        st.dataframe(template_preview_df)

        st.write("#### Interface Conditions Results:")
        interface_preview_df = pd.DataFrame(
            interface_results,
            columns=["Device", "Condition Name", "Interface", "Required Lines", "Status"]
        )
        st.dataframe(interface_preview_df)

if __name__ == "__main__":
    main()