# Configuration Compliance Checker with Catalyst Center Integration

This application provides a Streamlit-based user interface for checking the compliance of switch configurations against predefined policies. It can fetch configurations from Cisco Catalyst Center (formerly Dna Center) or load them from uploaded files. The application stores configurations in a MySQL database and allows users to define compliance rules based on templates and interface configurations.

## Features

*   **Catalyst Center Integration:** Fetches device configurations directly from Cisco Catalyst Center.
*   **Configuration Upload:** Allows users to upload configuration files for analysis.
*   **Database Storage:** Stores device configurations in a MySQL database for persistence and easy retrieval.
*   **Compliance Policy Definition:** Enables users to define compliance rules based on templates and interface configurations.
*   **Compliance Reporting:** Generates reports indicating whether devices are compliant with the defined policies.
*   **Streamlit UI:** Provides an intuitive web interface for easy interaction.

## Prerequisites

*   [Docker](https://www.docker.com/get-started)
*   [Docker Compose](https://docs.docker.com/compose/install/)

## Setup and Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/jumaluwati/Compliance_Checker
    cd Compliance_Checker
    ```

2.  **Configure the `.env` file:**

    Edit the `.env` file by setting the appropriate values for your environment. It is highly recommended to change the default MySQL credentials for enhanced security:

    *   `MYSQL_ROOT_PASSWORD`: Change this to a strong password for the MySQL root user.
    *   `MYSQL_DATABASE`: This is the name of the MySQL database. You can typically leave this as `compliance_db`.
    *   `MYSQL_USER`: This is the MySQL username. You can typically leave this as `compliance_user`.
    *   `MYSQL_PASSWORD`: Change this to a strong password for the `compliance_user` database user.
    *   `DNAC_IP`: Your Cisco Catalyst Center (DNAC) IP address. This is required for Catalyst Center integration.
    *   `USERNAME`: Your Cisco Catalyst Center (DNAC) username. This is required for Catalyst Center integration.
    *   `PASSWORD`: Your Cisco Catalyst Center (DNAC) password. This is required for Catalyst Center integration.

    **Important:** Do not commit the `.env` file with your actual credentials to a public repository. The `.gitignore` file should prevent this, but double-check.

3.  **Run the application with Docker Compose:**

    ```bash
    docker-compose up --build -d
    ```

    This command will build the Docker image and start the application, including the MySQL database and phpMyAdmin, in detached mode (running in the background). The necessary Python packages are automatically installed within the Docker container as defined in the `Dockerfile` and `requirements.txt`.

4.  **Access the application:**

    *   The Streamlit application will be available at `http://localhost:8501`.
    *   phpMyAdmin will be available at `http://localhost:8080`. Use the `compliance_user` and `MYSQL_PASSWORD` from your `.env` file to log in.
  
    
## Usage

1.  **Connect to Catalyst Center:**

    *   In the Streamlit UI, expand the "DNAC Connection" section.
    *   Enter your Catalyst Center IP address, username, and password.
    *   If the connection is successful, you will see a "Connected to DNAC successfully!" message.

2.  **Load Device Configurations:**

    *   You can load device configurations in two ways:
        *   **Upload a Configuration File:** Upload a `.txt` file containing the device configuration. The filename (without the extension) will be used as the device name.
        *   **Fetch from DNAC:** Select devices from the list of available devices in Catalyst Center and click "Fetch and Store DNAC Configurations." This will retrieve the configurations and store them in the database.

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

*   You can use phpMyAdmin (available at `http://localhost:8080`) to manage the database. Use the `compliance_user` and `MYSQL_PASSWORD` from your `.env` file to log in.

## Troubleshooting

*   **DNAC Connection Issues:**
    *   Verify that the Catalyst Center IP address, username, and password are correct.
    *   Ensure that your application can reach the Catalyst Center instance.
*   **Database Connection Issues:**
    *   Verify that the MySQL database is running.
    *   Verify that the database credentials in the `.env` file are correct.
*   **Application Errors:**
    *   Check the application logs for error messages.  You can view the logs of the running Docker containers using `docker-compose logs -f`.
*   **Configuration Errors:**
    *   Ensure that the configuration files are in the correct format.
