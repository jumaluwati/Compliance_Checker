# 🔍 ISE Compliance Checker

This application is a Streamlit-based tool that automates the validation of network device configurations. It fetches inventory and configuration data from Cisco Catalyst Center (DNAC) and Cisco ISE, stores them in a MySQL database, and checks them against predefined compliance rules.

## ✨ Features

*   **🔄 Inventory Sync:** Automatically pulls device lists from both Catalyst Center and ISE.
*   **✅ Compliance Validation:** Checks configurations against "Classic" and "IBN" (Intent-Based Networking) standards.
*   **🌐 VLAN Awareness:** Automatically marks interfaces in VLANs 240–245 as "Infrastructure."
*   **📊 Comparison Reports:** Identifies missing or mismatched devices between DNAC and ISE.
*   **📥 Easy Export:** Download full compliance reports as CSV files.

## 📋 Prerequisites

*   **🐍 Python 3.8+**
*   **🐳 Docker & Docker Compose**
*   **📚 Required Python Libraries:**
    *   `streamlit`
    *   `mysql-connector-python`
    *   `requests`

## 🛠️ Setup and Installation

1.  **📥 Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-folder>
    ```

2.  **⚙️ Configure Environment Variables:**
    *   First, copy the example file to create your local configuration:
        ```bash
        cp env.example .env
        ```
    *   Open the newly created `.env` file and replace the placeholder values with your actual DNAC, ISE, and database credentials.
    *   *Note: The `.env` file is ignored by Git to ensure your credentials remain private.*

3.  **🚀 Run the application:**
    ```bash
    docker-compose up --build -d
    ```

4.  **🌐 Access the application:**
    *   **App:** `http://localhost:8501`
    *   **Database Admin:** `http://localhost:8080` (phpMyAdmin)

## 💡 What are these technologies?

If you are new to these tools, here is a quick breakdown:

*   **🐳 Docker:** Think of itTo make the `README.md` beginner-friendly, I have added a "What is this?" section that briefly explains the technologies used.

Here is the complete, updated `README.md`:

```markdown
# 🔍 ISE Compliance Checker

This application is a Streamlit-based tool that automates the validation of network device configurations. It fetches inventory and configuration data from Cisco Catalyst Center (DNAC) and Cisco ISE, stores them in a MySQL database, and checks them against predefined compliance rules.

## ✨ Features

*   **🔄 Inventory Sync:** Automatically pulls device lists from both Catalyst Center and ISE.
*   **✅ Compliance Validation:** Checks configurations against "Classic" and "IBN" (Intent-Based Networking) standards.
*   **🌐 VLAN Awareness:** Automatically marks interfaces in VLANs 240–245 as "Infrastructure."
*   **📊 Comparison Reports:** Identifies missing or mismatched devices between DNAC and ISE.
*   **📥 Easy Export:** Download full compliance reports as CSV files.

## 🧠 What is this? (For Beginners)

*   **Docker:** Think of it as a "shipping container" for code. It bundles the app and all its requirements together so it runs perfectly on any computer.
*   **MySQL:** A reliable database system used here to store your device configurations and inventory data so they aren't lost when the app restarts.
*   **phpMyAdmin:** A web-based tool that lets you look inside your MySQL database, view your tables, and manage your data visually without needing to write code.

## 📋 Prerequisites

*   **🐍 Python 3.8+**
*   **🐳 Docker & Docker Compose**
*   **📚 Required Python Libraries:**
    *   `streamlit`
    *   `mysql-connector-python`
    *   `requests`

## 🛠️ Setup and Installation

1.  **📥 Clone the repository:**
    ```bash
    git clone <your-repository-url>
    cd <your-repository-folder>
    ```

2.  **⚙️ Configure Environment Variables:**
    *   First, copy the example file to create your local configuration:
        ```bash
        cp env.example .env
        ```
    *   Open the newly created `.env` file and replace the placeholder values with your actual DNAC, ISE, and database credentials.
    *   *Note: The `.env` file is ignored by Git to ensure your credentials remain private.*

3.  **🚀 Run the application:**
    ```bash
    docker-compose up --build -d
    ```

4.  **🌐 Access the application:**
    *   **App:** `http://localhost:8501`
    *   **Database Admin:** `http://localhost:8080` (phpMyAdmin)

## 💡 Usage

1.  **Inventory Tab:** Click the "Sync" buttons to pull the latest device data from DNAC and ISE. Use the "Check Inventory Comparison" button to find discrepancies.
2.  **Compliance Tab:** 
    *   Select the devices you want to check.
    *   Click "Run Compliance Check."
    *   Review the results in the table or download the full report as a CSV.

## 🔧 Troubleshooting

*   **🔌 Connection Issues:** Ensure your machine can reach the DNAC and ISE IP addresses.
*   **🗄️ Database Errors:** If the app won't start, check the logs with `docker-compose logs -f`.
*   **⚠️ Missing Data:** Ensure you have clicked the "Sync" buttons in the Inventory tab before running a compliance check.
