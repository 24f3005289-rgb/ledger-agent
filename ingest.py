import sqlite3
import pandas as pd
import requests

# Your exact assignment endpoints
EXPORT_URL = "https://exam.sanand.workers.dev/questionData?email=24f3005289%40ds.study.iitm.ac.in&quizSign=mmJsNQVCEvaftGgrvPbniA2Teytbglg61CrAUbynIGyVasGXPyaXuL3QIjhGdAP9vz79OqcRrW1uAOljJ6YOV%2FL3DRm1R3buRvlTudd6fPWOAPLXAmGw4rh7jgkqSIt0EJeblT6p%2FD6nKCs8DHeWnlMEpFQPxKa3v0MJaEoDcUZPyj2C1exdBBtrvGxxMr5e3W4UTHc5fqXe1SzBz7EXRWSVl1KsvuoSwN%2BS3A2fIiF18Qp8bT8YyA0TT6fMnP1Jj85%2FGfXKNn5SzogHLOwmU5MGwyG4g7mWyTgM9h%2FmAIDka5UzbNdIZMEFvYSXesCI0TLHM8zEn1qehXvz08xvTQ%3D%3D&questionId=q-ledger-agent-server&path=%2Fexport"
RATES_URL = "https://exam.sanand.workers.dev/questionData?email=24f3005289%40ds.study.iitm.ac.in&quizSign=mmJsNQVCEvaftGgrvPbniA2Teytbglg61CrAUbynIGyVasGXPyaXuL3QIjhGdAP9vz79OqcRrW1uAOljJ6YOV%2FL3DRm1R3buRvlTudd6fPWOAPLXAmGw4rh7jgkqSIt0EJeblT6p%2FD6nKCs8DHeWnlMEpFQPxKa3v0MJaEoDcUZPyj2C1exdBBtrvGxxMr5e3W4UTHc5fqXe1SzBz7EXRWSVl1KsvuoSwN%2BS3A2fIiF18Qp8bT8YyA0TT6fMnP1Jj85%2FGfXKNn5SzogHLOwmU5MGwyG4g7mWyTgM9h%2FmAIDka5UzbNdIZMEFvYSXesCI0TLHM8zEn1qehXvz08xvTQ%3D%3D&questionId=q-ledger-agent-server&path=%2Frates"


def fetch_rates():
  """Fetches USD conversion rates."""
  res = requests.get(RATES_URL).json()
  return res.get(
      "usd_per_unit", {"USD": 1.0, "EUR": 1.02, "INR": 0.01231}
  )


def build_database():
  print("Downloading export records...")
  res = requests.get(EXPORT_URL)

  # Parse line-delimited JSON (NDJSON)
  lines = res.text.strip().split("\n")
  data = [pd.read_json(line, typ="series") for line in lines if line.strip()]
  df = pd.DataFrame(data)

  # 1. Deduplicate by order ID (keep row with latest updated_at)
  df["updated_at_dt"] = pd.to_datetime(df["updated_at"], utc=True)
  df = df.sort_values("updated_at_dt").groupby("id").last().reset_index()

  # 2. Convert timestamps to Asia/Kolkata timezone
  df["created_at_kolkata"] = (
      pd.to_datetime(df["created_at"], utc=True)
      .dt.tz_convert("Asia/Kolkata")
      .dt.strftime("%Y-%m-%d %H:%M:%S")
  )

  # 3. Currency Conversion to USD
  rates = fetch_rates()
  df["rate"] = df["currency"].map(rates)
  df["amount_usd"] = (df["amount"] * df["rate"]).round(2)

  # 4. Save clean data to SQLite database
  conn = sqlite3.connect("ledger.db")
  df.to_sql("orders", conn, if_exists="replace", index=False)
  conn.close()

  print(
      f"Database build complete! Processed {len(df)} unique orders into 'ledger.db'."
  )


if __name__ == "__main__":
  build_database()
