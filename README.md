# Fraudpulse

Fraudpulse is an automated, real-time fraud detection and decision engine pipeline.

## Project Structure

- **`src.Api`**: The FastAPI backend for handling requests and orchestrating fraud checks.
- **`dashboard`**: The Streamlit frontend for monitoring transactions and viewing real-time alerts.
- **`src.decision_engine`**: The rule-based analytical engine for classifying transactions.
- **`main_data_pipeline.py`**: The main entry script that pipelines transaction data into the decision engine.

## How to Run the Project

Follow these steps to get the project up and running on your local machine:

### 1. Prerequisites & Installation

Make sure you have Python 3.8+ installed. 
First, clone the repository and install the required dependencies:

```bash
git clone https://github.com/SaifullahSayyed/Fraudpulse.git
cd Fraudpulse

# (Optional but recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate   # On Windows
# source venv/bin/activate # On Mac/Linux

# Install dependencies
pip install -r requirements.txt
```

### 2. Start the Backend API

The backend is built with FastAPI. It needs to be running for the dashboard and pipeline to communicate properly. Open a new terminal, activate your virtual environment, and run:

```bash
python -m uvicorn src.Api.main:app --reload --host 0.0.0.0 --port 8000
```
*The API will be available at http://localhost:8000. You can view the docs at http://localhost:8000/docs.*

### 3. Start the Streamlit Dashboard

To start the interactive frontend dashboard, open a second terminal, activate your environment, and run:

```bash
python -m streamlit run dashboard/streamlit_app.py
```
*Your browser should automatically open the dashboard at http://localhost:8501.*

### 4. Run the Data Pipeline

Finally, to simulate or run the transaction data through the system, run the main pipeline script in a third terminal:

```bash
python main_data_pipeline.py
```

This will begin feeding data into the decision engine, and you will see the updates reflect on your Streamlit dashboard in real-time!
