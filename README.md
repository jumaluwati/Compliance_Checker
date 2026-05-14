# Configuration Compliance Checker with Catalyst Center and ISE Integration

This application provides a Streamlit-based user interface for checking the compliance of network device configurations against predefined policies. It fetches device inventories and configurations from both Cisco Catalyst Center (DNAC) and Cisco ISE, stores them in a MySQL database, and allows users to validate configurations against specific compliance standards (Classic vs. IBN).

## Features

*   **Catalyst Center Integration:** Automatically fetches and stores device inventories and configurations from Cisco Catalyst Center.
*   **ISE Integration:** Synchronizes device inventory from Cisco ISE to ensure a comprehensive view of the network.
*   **Database Storage:** Uses a MySQL database for persistent storage of device configurations and inventory data.
*   **Compliance Validation:** Supports validation of both "Classic" configurations and "Intent-Based Networking" (IBN) templates.
*   **Infrastructure Awareness:** Automatically identifies and classifies interfaces within specific VLAN ranges (240–245) as "Infrastructure Interfaces."
*   **Compliance Reporting:** Generates detailed reports indicating the compliance status of each interface and device.
*   **Streamlit UI:** Provides an intuitive, modern web interface for synchronization, comparison, and reporting.

## Prerequisites

*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)

## Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone <your-repository-url>
    cd <your-repository-folder>
    ```

2.  **Configure the environment variables:**

    Update the `docker-compose.yml` file with your specific environment details. It is highly recommended to change the default database credentials for enhanced security:

    *   `DNAC_IP`, `USERNAME`, `PASSWORD`: Your Cisco Catalyst Center credentials.
    *   `ISE_IP`, `ISE_USERNAME`, `ISE_PASSWORD`: Your Cisco ISE credentials.
    *   `DB_PASSWORD`: Set a strong password for the MySQL database.

    **Important:** Ensure your `.env` file or `docker-compose.yml` is excluded from version control to protect your credentials.

3.  **Run the application with Docker Compose:**

    ```bash
    docker-compose up --build -d
    ```

    This command builds the Docker image and starts the application, including the MySQL database and phpMyAdmin, in detached mode.

4.  **Access the application:**

    *   The Streamlit application will be available at `http://localhost:8501`.
    *   phpMyAdmin will be available at `http://localhost:8080` for database management.

## Usage

1.  **Inventory Synchronization:**
    *   Navigate to the **Inventory** tab.
    *   Click **"Sync Catalyst Center"** and **"Sync ISE Inventory"** to populate the database with the latest device data.
    *   Use the **"Check Inventory Comparison"** button to identify discrepancies between your Catalyst Center and ISE inventories.

2.  **Compliance Check:**
    *   Navigate to the **Compliance** tab.
    *   **Select Devices:** Use the multi-select tool to choose the devices you wish to audit.
    *   **Run Check:** Click **"Run Compliance Check."** The application will evaluate configurations against Classic and IBN rules.
    *   **Review Results:** View the compliance status per device and per interface in the interactive tables. You can download the full report as a CSV file.

## Database

*   The application uses a MySQL database to store configurations and inventory.
*   Key tables include:
    *   `device_configs`: Stores device hostnames, IPs, and raw configuration data.
    *   `ise_inventory`: Stores the synchronized list of ISE devices.
    *   `sync_status`: Tracks the last successful sync time for both systems.

*   You can manage the database via phpMyAdmin at `http://localhost:8080`.

## Troubleshooting

*   **Connection Issues:** Verify that the IP addresses, usernames, and passwords for both Catalyst Center and ISE are correct and that the application has network reachability to these instances.
*   **Database Errors:** Ensure the MySQL container is running. Check logs using `docker-compose logs -f`.
*   **Sync Failures:** If a sync fails, check the "Last Sync" timestamps in the UI to identify which system is failing to respond.
