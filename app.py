import streamlit as st
import requests
import random
from google import genai
from google.genai import types

# --- CONFIGURATION ---
st.set_page_config(page_title="Rational Alpha", layout="centered")

st.title("🏛️ The Alpha Desk")

# --- DATA CACHING ---
@st.cache_data(ttl=600)
def fetch_market_data(page):
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page={page}&sparkline=false"
    response = requests.get(url)
    if response.status_code == 429:
        st.error("SYSTEM ALERT: CoinGecko Rate Limit reached. Please wait 60 seconds.")
        return None
    response.raise_for_status()
    return response.json()

# --- UI INPUTS ---
direction = st.selectbox("Position Bias:", ["LONG", "SHORT"])
volatility = st.slider("Target Volatility (Delta):", 0, 100, 50)
obscurity = st.slider("Target Obscurity (Alpha Depth):", 0, 100, 50)

# --- EXECUTION LOGIC ---
if st.button("Run Scan"):
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("SYSTEM ERROR: API key not found in Streamlit Secrets.")
        st.stop()

    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.spinner("ISOLATING ASYMMETRIC OPPORTUNITY..."):
        page_index = max(1, int((obscurity / 100) * 10))
        coins = fetch_market_data(page_index)
        
        if coins:
            try:
                valid_coins = [c for c in coins if c.get('price_change_percentage_24h') is not None]
                coins_sorted_by_vol = sorted(valid_coins, key=lambda x: abs(x['price_change_percentage_24h']))
                
                target_idx = int((volatility / 100) * (len(coins_sorted_by_vol) - 1))
                target = coins_sorted_by_vol[max(0, min(len(coins_sorted_by_vol) - 1, target_idx))]
                
                name = target['name']
                symbol = target['symbol'].upper()
                coin_id = target['id']
                cg_url = f"https://www.coingecko.com/en/coins/{coin_id}"
                
                st.markdown(f"## **TARGET IDENTIFIED:** [{name} ({symbol})]({cg_url})")
                
                prompt = (
                    f"Research {name} ({symbol}) market dynamics. "
                    f"Provide a high-conviction, institutional-grade analysis for a {direction} position. "
                    f"Maintain a professional and enthusiastic tone appropriate for elite strategists. "
                    f"Zero fluff. Avoid clichés like 'It's not just X, it's Y' or 'gather 'round.' "
                    f"Contextualize the current Volatility ({volatility}/100) and Obscurity ({obscurity}/100) "
                    f"as precise variables in this trade thesis. Be efficient, persuasive, and grounded "
                    f"in real-time sentiment. Maximum 125 words."
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())]
                    )
                )
                
                st.subheader(f"Strategy: {direction}")
                st.info(response.text)
                
            except Exception as e:
                st.error(f"SYSTEM ERR: {e}")

st.caption("v4.7.1 // Stable // Logic Engine: Gemini 2.5 Flash")
