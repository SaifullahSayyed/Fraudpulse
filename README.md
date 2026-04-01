<div align="center">
  <img src="https://raw.githubusercontent.com/SaifullahSayyed/Fraudpulse/main/assets/logo.png" width="120" alt="FraudPulse Logo" />
  <h1>FraudPulse</h1>
  <p><strong>Decision Intelligence & Strategic Fraud Prevention Pipeline</strong></p>

  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
  [![Python 3.10+](https://img.shields.io/badge/python-3.10+-brightgreen.svg)](https://www.python.org/downloads/)
  [![FastAPI](https://img.shields.io/badge/FastAPI-Framework-009688.svg?logo=fastapi)](https://fastapi.tiangolo.com/)
  [![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-FF4B4B.svg?logo=streamlit)](https://streamlit.io/)
</div>

<br/>

**FraudPulse** is a modular, rule-based decision intelligence platform designed to move beyond "black-box" machine learning. By utilizing an autonomous **Multi-Agent Mesh**, it detects complex fraud patterns—like **Money Mules** and **Impossible Travelers**—with total transparency and cryptographic integrity.

---

## 🔥 What Makes FraudPulse Different?

### 🎨 Genuine, "Humanized" Codebase
Unlike AI-generated boilerplate, FraudPulse features a clean, student-authored codebase. We have stripped away dense, robotic docstrings and formal AI comments to focus on **pure logic and genuine implementation**.

### 🚀 Strategic "Live Stream" Demo
Stop simulating random data. Click our **"🚀 Load Default Live Stream"** button in the dashboard to instantly process a curated dataset of coordinated fraud rings, high-velocity attacks, and mule signaling.

### 🛡️ SHA256 Tamper-Evident Ledger
Every single decision is hashed into a cryptographic `SHA-256` chain stored in a local SQLite ledger. If any record is altered after-the-fact, the hash chain breaks, providing forensic-level reliability for financial audits.

---

## 🔗 The 4-Agent Mesh Architecture

1.  **🔍 Detection Agent**: Monitors behavioral shifts using KL-Divergence and explains risk via **SHAP Feature Contributions**.
2.  **🔎 Verification Agent**: The logic core. It calculates real-world risk based on "Impossible Traveler" distances and velocity thresholds.
3.  **👤 Customer Agent**: Simulates the human-in-the-loop experience—processing OTP confirmations and biometric push notifications.
4.  **📋 Escalation Agent**: Logs the decision chain to the immutable ledger and updates the live broadcast for the dashboard.

---

## 🛠️ Installation & Rapid Deployment

### 1. Visual Studio Code / Local Setup
```bash
# Clone the repository
git clone https://github.com/SaifullahSayyed/Fraudpulse.git
cd Fraudpulse

# Install dependencies
pip install -r requirements.txt

# Start the Decision API (Backend)
python -m uvicorn src.Api.main:app --host 0.0.0.0 --port 8000

# Start the Strategic Dashboard (Frontend)
python -m streamlit run dashboard/streamlit_app.py --server.port 8505
```

---

## 📱 Running on Other Devices (Mobile/Tablet)

You can present the FraudPulse dashboard on your mobile phone or another laptop as long as they are on the **same Wi-Fi network**.

### Step 1: Find your Local IP Address
Open your terminal (CMD on Windows) and run:
`ipconfig`

Look for **IPv4 Address** (e.g., `192.168.1.15`).

### Step 2: Open the Dashboard on your Device
On your mobile phone's browser, enter:
`http://<YOUR_IP>:8505`

> [!IMPORTANT]
> Ensure your Windows **Firewall** allows traffic on port **8505**. If the page doesn't load on your phone, try disabling your public firewall temporarily or adding a "New Inbound Rule" for Port 8505.

---

## 📊 Dashboard Reference Guide
For a deep dive into every visualization (SHAP, Network Graphs, PR-Curves), check out our comprehensive guide:
📄 **[DASHBOARD_GUIDE.md](dashboard/DASHBOARD_GUIDE.md)**

---
*Created for the next generation of Financial Security and Decision Intelligence.*
