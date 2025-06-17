# 🔍 Compliance Checker – Simplified

This tool analyzes network switch configurations to assess compliance using two primary methods: **Classic** and **IBN**.

---

## ✅ Classic Method

An interface is marked **Compliant** if it contains:

- `switchport mode access`  
- `authentication port-control auto`

---

## ✅ IBN Method

An interface is marked **Compliant** if it contains:

- `switchport mode access`  
- `source template DefaultWiredDot1xClosedAuth`  
- The template includes: `access-session port-control auto`

---

## 🎯 What This Tool Does

- Parses saved switch configuration files
- Identifies interfaces as:
  - ✅ **Compliant**
  - ❌ **Non-Compliant**
  - 🛠 **Infrastructure Interface** (not subject to compliance check)
- Displays all findings in clear, color-coded tables:
  - Template Presence Summary
  - Classic Compliance View
  - IBN Compliance View
  - Combined Compliance Overview

---

Feel free to clone, test, and adapt this tool for your environment!
