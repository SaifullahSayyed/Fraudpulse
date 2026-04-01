# FraudPulse Dashboard: Comprehensive Reference Guide

This document provides a detailed explanation of every component, metric, and visualization within the **FraudPulse Decision Intelligence Dashboard**.

---

## 🧭 1. Sidebar: The Intelligence Layer

The sidebar is where data enters the system and where the "Human-in-the-Loop" controls reside.

### 🧩 Input Metadata

* **Account Intelligence**: Unique identifiers for the sender and receiver. The system uses these to look up historical behavioral patterns in the SQLite ledger.
* **Hardware & Location**: Device fingerprints and GPS coordinates. These are used by the **Verification Agent** to detect anomalous logins or "Impossible Traveler" scenarios.
* **Risk Heuristics (Sliders)**:
    * **ML Fraud Score**: The raw probability output from the underlying machine learning model.
    * **Amount**: The primary driver for "High Value" escalation rules.

### ⚡ Live Stream vs. Simulation

* **🚀 Load Default Live Stream**: Triggers a batch run of specifically targeted fraud cases (Mules, Velocity attacks) from `data/live_transaction_stream.csv`.
* **▶ Run Random Batch**: Generates a variety of random transactions to test the system's general robustness.
* **PR-Curve Threshold**: A strategic control. Increasing this reduces "False Positives" (Approved transactions that are actually fraud) but might increase "False Negatives."

---

## 🔗 2. The Agent Pipeline

FraudPulse doesn't rely on a single model. It orchestrates a "Mesh" of specialized agents:

1. **🕸️ Network Analyzer**: Uses graph clustering to see if an account belongs to a known "Fraud Ring."
2. **🔬 Detection Agent**: Calculates **KL-Divergence**. It asks: "Is this transaction mathematically inconsistent with this user's 100-day history?"
3. **🔎 Verification Agent**: The "Logic Core." It checks hard rules like velocity (3+ transactions in 60s) and geographical impossibility.
4. **📋 Escalation Agent**: The "Decision Finalizer." It compiles all agent logic and creates the tamper-evident audit record.

---

## 📊 3. Core Visualizations

### 🎡 Composite Risk Gauge

A holistic score from **0 to 100**.

* **0–25 (Green)**: Typically Approved.
* **25–75 (Yellow/Red)**: Requires Verification or Customer OTP.
* **75–100 (Purple)**: Escalated for human review or immediately Blocked.

### 🧠 AI Explanation (SHAP)

Explains the **"Why."** SHAP (SHapley Additive exPlanations) shows which features pushed the decision up (towards fraud) or down (towards safety).

* *Red bars* = High risk contribution (e.g., "Foreign Transaction").
* *Green bars* = Safety contribution (e.g., "Known Device").

### 🕸️ Interactive Fraud Network

Visualizes the "Fraud Graph."

* **Nodes**: Bank accounts.
* **Edges**: Transactions.
* **Colors**: Red indicates accounts that have been flagged by the system previously. It allows you to see "Cash-out" points and "Mule Chains."

---

## 🧠 4. Online Learning (Adaptive Weights)

This is the system's "Brain."

* **Dynamic Feedback**: If a rule (e.g., "Large Amount") pulls its weight too often on false positives, its influence decays.
* **Confirmation Bias Correction**: If an agent catches a real fraudster, the system "boosts" that rule's importance for the next 24 hours.

---

## 🛡️ 5. Reliability & Audit Feed

At the bottom of the dashboard is the **Tamper-Evident Audit Feed**.

* **Correlation ID**: A unique UUID that links every microservice action to a single transaction.
* **Audit Hash**: A SHA256 chain. Every event's hash is mixed with the previous event's hash. If a single byte in the SQLite database is changed, the chain breaks—providing total forensic integrity.
