
# Switch Configuration Compliance Checker with DNAC Integration

This application provides a Streamlit-based user interface for checking the compliance of switch configurations against predefined policies. It can fetch configurations from Cisco DNA Center (DNAC) or load them from uploaded files.  The application stores configurations in a MySQL database and allows users to define compliance rules based on templates and interface configurations.

## Features

*   **DNAC Integration:** Fetches device configurations directly from Cisco DNA Center.
*   **Configuration Upload:** Allows users to upload configuration files for analysis.
*   **Database Storage:** Stores device configurations in a MySQL database for persistence and easy retrieval.
*   **Compliance Policy Definition:** Enables users to define compliance rules based on templates and interface configurations.
*   **Compliance Reporting:** Generates reports indicating whether devices are compliant with the defined policies.
*   **Streamlit UI:** Provides an intuitive web interface for easy interaction.

## Prerequisites

*   [Docker](https://www.docker.com/get-started) 
*   Python 3.8 or higher
*   [Docker Compose](https://docs.docker.com/compose/install/) (If using Docker)

## Setup and Installation

**Option 1: Using Docker Compose (Recommended)**

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Configure the `.env` file:**

    *   Copy the `.env.example` file to `.env`:

        ```bash
        cp .env.example .env
        ```

    *   **Important:** Edit the `.env` file and set the following environment variables:

        *   `MYSQL_ROOT_PASSWORD`:  Change this to a strong password for the MySQL root user.
        *   `MYSQL_PASSWORD`: Change this to a strong password for the `compliance_user` database user.
        *   `DNAC_IP`:  Your Cisco DNAC IP address.  **This is required for DNAC integration.**
        *   `USERNAME`: Your Cisco DNAC username. **This is required for DNAC integration.**
        *   `PASSWORD`: Your Cisco DNAC password. **This is required for DNAC integration.**

        **Warning:**  Do not commit the `.env` file with your actual credentials to a public repository.  The `.gitignore` file should prevent this, but double-check.

    *   **Example `.env`:**

        ```
        MYSQL_ROOT_PASSWORD=CHANGE_ME_ROOT  # Change this to a strong password!
        MYSQL_DATABASE=compliance_db
        MYSQL_USER=compliance_user
        MYSQL_PASSWORD=CHANGE_ME_DB  # Change this to a strong password!
        DNAC_IP=10.147.26.90 # Replace with your DNAC IP
        USERNAME=jalluwat # Replace with your DNAC Username
        PASSWORD=Cisco1234 # Replace with your DNAC Password
        ```

3.  **Run the application with Docker Compose:**

    ```bash
    docker-compose up --build
    ```

    This command will build the Docker image and start the application, including the MySQL database and phpMyAdmin.

4.  **Access the application:**

    *   The Streamlit application will be available at `http://localhost:8501`.
    *   phpMyAdmin will be available at `http://localhost:8080`.  Use the `compliance_user` and `MYSQL_PASSWORD` from your `.env` file to log in.

**Option 2: Without Docker (Using Python Directly)**

1.  **Clone the repository:**

    ```bash
    git clone <repository_url>
    cd <repository_directory>
    ```

2.  **Create a virtual environment (recommended):**

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Linux/macOS
    venv\Scripts\activate  # On Windows
    ```

3.  **Install the required packages:**

    ```bash
    pip install -r requirements.txt
    ```

    The `requirements.txt` file lists the necessary Python packages.  It should contain the following (or similar) entries:

    ```
    streamlit==1.29.0
    pandas==2.1.4
    requests==2.31.0
    urllib3==2.1.0
    mysql-connector-python==8.2.0
    ```

4.  **Configure Environment Variables:**

    Set the following environment variables in your shell or terminal:

    *   `MYSQL_ROOT_PASSWORD`: The password for the MySQL root user (used during initial database setup).
    *   `MYSQL_PASSWORD`: The password for the `compliance_user` database user.
    *   `DB_HOST`: The hostname or IP address of your MySQL server (e.g., `localhost` if running locally).
    *   `DB_USER`: The MySQL username (should be `compliance_user`).
    *   `DB_NAME`: The name of the MySQL database (should be `compliance_db`).
    *   `DNAC_IP`: Your Cisco DNAC IP address.  **This is required for DNAC integration.**
    *   `USERNAME`: Your Cisco DNAC username. **This is required for DNAC integration.**
    *   `PASSWORD`: Your Cisco DNAC password. **This is required for DNAC integration.**

    **Example (Linux/macOS):**

    ```bash
    export MYSQL_ROOT_PASSWORD=your_root_password
    export MYSQL_PASSWORD=your_db_password
    export DB_HOST=localhost
    export DB_USER=compliance_user
    export DB_NAME=compliance_db
    export DNAC_IP=your_dnac_ip
    export USERNAME=your_dnac_username
    export PASSWORD=your_dnac_password
    ```

    **Example (Windows):**

    ```powershell
    $env:MYSQL_ROOT_PASSWORD = "your_root_password"
    $env:MYSQL_PASSWORD = "your_db_password"
    $env:DB_HOST = "localhost"
    $env:DB_USER = "compliance_user"
    $env:DB_NAME = "compliance_db"
    $env:DNAC_IP = "your_dnac_ip"
    $env:USERNAME = "your_dnac_username"
    $env:PASSWORD = "your_dnac_password"
    ```

5.  **Run the application:**

    ```bash
    streamlit run test19.py
    ```

## Usage

1.  **Connect to DNAC (Optional):**

    *   In the Streamlit UI, expand the "DNAC Connection" section.
    *   Enter your DNAC IP address, username, and password.
    *   If the connection is successful, you will see a "Connected to DNAC successfully!" message.

2.  **Load Device Configurations:**

    *   You can load device configurations in two ways:
        *   **Upload a Configuration File:** Upload a `.txt` file containing the device configuration. The filename (without the extension) will be used as the device name.
        *   **Fetch from DNAC:** Select devices from the list of available devices in DNAC and click "Fetch and Store DNAC Configurations."  This will retrieve the configurations and store them in the database.

3.  **Define Compliance Policies:**

    *   In the "Compliance Policy Definition" section, select the type of condition you want to create: "Template" or "Interface."
    *   **Template Conditions:**
        *   Enter a condition name.
        *   Enter the template name (a string that identifies the template in the configuration).
        *   Enter the required line that must be present in the template.
    *   **Interface Conditions:**
        *   Enter a condition name.
        *   Enter the "Line of Interest" (e.g., `switchport mode trunk`).
        *   Enter a "Condition Label" to describe the status when the line of interest is found (e.g., `Compliant`).
        *   Optionally, configure settings for "Shutdown Interfaces" and "Other Interfaces" to customize the reporting.
    *   Click "Save Condition" to add the condition to the list of saved conditions.

4.  **Run Compliance Check:**

    *   In the "Run Compliance Check" section, click "Check Compliance for Selected Devices."
    *   The application will retrieve the configurations from the database and check them against the defined policies.
    *   The results will be displayed in the "Compliance Results" section.

## Database

*   The application uses a MySQL database to store device configurations.
*   The database schema consists of a single table named `device_configs` with the following columns:
    *   `id`: INT (Primary Key, Auto-Increment)
    *   `device_name`: VARCHAR(255) (Device hostname)
    *   `config`: LONGTEXT (Device configuration)
    *   `last_saved`: TIMESTAMP (Timestamp of the last save)

*   If using Docker, you can use phpMyAdmin (available at `http://localhost:8080`) to manage the database.  Use the `compliance_user` and `MYSQL_PASSWORD` from your `.env` file to log in.  If running without Docker, you'll need to use a separate MySQL client.

## Troubleshooting

*   **DNAC Connection Issues:**
    *   Verify that the DNAC IP address, username, and password are correct.
    *   Ensure that your application can reach the DNAC instance.
*   **Database Connection Issues:**
    *   Verify that the MySQL database is running.
    *   Verify that the database credentials in the `.env` file (or environment variables if not using Docker) are correct.
*   **Configuration Errors:**
    *   Check the application logs for error messages.
    *   Ensure that the configuration files are in the correct format.

## Feel free to contact me if you have any questions !

  *Email: juma.luwati@gmail.com
