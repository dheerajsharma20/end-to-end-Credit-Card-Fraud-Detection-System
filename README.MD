# 🛡️ FraudGuard — Credit Card Fraud Detection System

An end-to-end credit card fraud detection web app built with **Streamlit** and an **XGBoost** classifier. Users can register, log in, analyze transactions for fraud risk in real time, and review their transaction history.

## Features

- 🔐 **User authentication** — registration and login backed by SQLite, passwords stored as SHA-256 hashes
- 🔍 **Real-time fraud detection** — enter transaction details (amount, time of day, merchant type, location, risk flags) and get an instant fraud/legit verdict with a confidence score from the trained XGBoost model
- 📊 **Dashboard** — at-a-glance stats: total checks, legitimate count, fraud count, fraud rate
- 📋 **Transaction history** — full log of past fraud checks per user
- 🚨 **Quick test presets** — one-click "Test Fraud" / "Test Legit" sample transactions for demoing the model

## Tech Stack

| Layer        | Tool                          |
|--------------|--------------------------------|
| Frontend/App | [Streamlit](https://streamlit.io) |
| ML Model     | XGBoost (trained offline, loaded via `joblib`) |
| Database     | SQLite                        |
| Styling      | Custom CSS injected via Streamlit markdown |

## Project Structure

```
.
├── app.py              # Main Streamlit app — UI, routing, auth flow, detection logic
├── database.py         # SQLite helpers: user accounts + transaction history
├── fraud_model.pkl     # Pre-trained XGBoost fraud classifier
├── requirements.txt    # Python dependencies
├── .streamlit/
│   └── config.toml     # Streamlit theme config
└── style.css            # (currently unused placeholder)
```

## Setup & Run

1. **Clone the repo**
   ```bash
   git clone https://github.com/dheerajsharma20/end-to-end-Credit-Card-Fraud-Detection-System.git
   cd end-to-end-Credit-Card-Fraud-Detection-System
   ```

2. **Create a virtual environment (recommended)**
   ```bash
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the app**
   ```bash
   streamlit run app.py
   ```

   The app will open at `http://localhost:8501`. A local `fraudguard.db` SQLite file is created automatically on first run — it's gitignored so each environment gets its own.

## How Detection Works

The model expects 30 input features (time, 28 PCA-derived components `V1`–`V28`, and amount) — the standard shape of the classic Kaggle credit card fraud dataset. Since real PCA components aren't meaningful for manually entered demo transactions, the app:

1. Picks a baseline feature vector for the selected merchant **type** (Online Shopping, ATM Withdrawal, etc.)
2. Blends it with a "fraud-like" reference vector, weighted by a heuristic **risk score** built from the checkboxes (new merchant, foreign currency, unusual amount, multiple transactions, night-time, international, large amount)
3. Feeds the resulting vector + amount + time into the trained XGBoost model for a final prediction and confidence score

This makes the demo interactive and educational, but it's worth knowing the inputs are a simulated approximation rather than genuine PCA-transformed transaction data — a real production system would feed the model live, properly transformed transaction features.

## Known Limitations / Ideas for Improvement

- **Password hashing** uses unsalted SHA-256. For anything beyond a demo, switch to `bcrypt` or `argon2` with per-user salts.
- **Card Type** is currently captured in the UI but not yet factored into the risk score — could be a small enhancement.
- No password reset, email verification, or session timeout.
- The fraud "model" runs on synthetic blended features rather than real transaction PCA components (see above) — fine for demoing, but should be called out if presenting this as production-grade.

## License

No license specified yet — add one (e.g. MIT) if you want others to reuse this freely.
