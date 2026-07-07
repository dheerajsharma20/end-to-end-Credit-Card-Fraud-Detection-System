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
├── database.py         # SQLite helpers: user accounts, password reset, transaction history
├── fraud_model.pkl     # Pre-trained XGBoost fraud classifier
├── requirements.txt    # Python dependencies
├── .streamlit/
│   └── config.toml     # Streamlit theme config
└── style.css            # Global CSS (dark theme, buttons, inputs, tabs, scrollbar) — loaded by app.py at startup
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

## Security Features

- **Password hashing** uses `bcrypt` with a per-user random salt baked into every hash. Accounts created before this change (unsalted SHA-256) are transparently upgraded to bcrypt the next time that user signs in — no manual migration needed.
- **Password reset** is available from the Sign In screen ("Forgot password?"). It issues a 6-digit code with a 15-minute expiry. Since this demo has no email server configured, the code is shown directly on screen instead of being emailed — swap in a real email provider (SendGrid, SES, etc.) for production use.
- **Card Type** now feeds into the fraud risk score: Debit Card transactions are nudged toward higher risk (fewer chargeback protections than credit cards), especially combined with foreign/international use.
- **Session timeout**: users are auto-logged-out after 15 minutes of inactivity. Note this is checked on each Streamlit rerun (i.e. the next time the user interacts with the app), since Streamlit doesn't run a background timer — a genuinely idle browser tab won't be kicked out until the next click.

## Known Limitations / Ideas for Improvement

- No email verification on signup.
- Password reset codes are shown on-screen rather than emailed (see above) — fine for a demo, not for production.
- The fraud "model" runs on synthetic blended features rather than real transaction PCA components (see above) — fine for demoing, but should be called out if presenting this as production-grade. A "How This Analysis Works" note is now shown directly on the Detection page for transparency.

## License

No license specified yet — add one (e.g. MIT) if you want others to reuse this freely.
