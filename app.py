import streamlit as st
import requests
import random
import time
from google import genai
from google.genai import types

# --- CONFIGURATION ---
st.set_page_config(page_title="Sentiment Sniper", layout="centered")

# --- CUSTOM CSS FOR THE SNIPER SCOPE ---
SCOPE_CSS = """
<style>
@keyframes figureEight {
    0% { transform: translate(0, 0); }
    25% { transform: translate(60px, -30px); }
    50% { transform: translate(0, 0); }
    75% { transform: translate(-60px, 30px); }
    100% { transform: translate(0, 0); }
}

.scope-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 150px;
    margin-bottom: 20px;
}

.scope {
    width: 40px;
    height: 40px;
    border: 2px solid #FF4B4B;
    border-radius: 50%;
    position: relative;
    animation: figureEight 2s infinite ease-in-out;
}

.scope::before, .scope::after {
    content: '';
    position: absolute;
    background: #FF4B4B;
}

/* Crosshairs */
.scope::before { width: 100%; height: 1px; top: 50%; left: 0; }
.scope::after { width: 1px; height: 100%; left: 50%; top: 0; }

.targeting-text {
    font-family: monospace;
    color: #FF4B4B;
    font-weight: bold;
    margin-top: 15px;
    letter-spacing: 2px;
}
</style>
"""
st.markdown(SCOPE_CSS, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'vol_start' not in st.session_state:
    st.session_state.vol_start = random.uniform(0.0, 100.0)
if 'obs_start' not in st.session_state:
    st.session_state.obs_start = random.uniform(0.0, 100.0)

st.title("🎯 Sentiment Sniper")

# --- DATA & LOGIC (CACHED) ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_market_data(page, cg_key):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": page, "sparkline": "false"}
    headers = {"accept": "application/json", "x-cg-demo-api-key": cg_key}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else None
    except: return None

@st.cache_data(ttl=60, show_spinner=False)
def get_alpha_scan(direction, volatility, obscurity, gemini_key, cg_key):
    page_index = max(1, int((obscurity / 100) * 10))
    coins = fetch_market_data(page_index, cg_key)
    if not coins: return None, "SYSTEM ALERT: Connection error. Retry in 60s."

    valid_coins = [c for c in coins if c.get('price_change_percentage_24h') is not None]
    coins_sorted_by_vol = sorted(valid_coins, key=lambda x: abs(x['price_change_percentage_24h']))
    target_idx = int((volatility / 100) * (len(coins_sorted_by_vol) - 1))
    target = coins_sorted_by_vol[max(0, min(len(coins_sorted_by_vol) - 1, target_idx))]
    
    target_data = {"name": target['name'], "symbol": target['symbol'].upper(), "url": f"https://www.coingecko.com/en/coins/{target['id']}"}

    client = genai.Client(api_key=gemini_key)
    prompt = (f"Research {target_data['name']} ({target_data['symbol']}). "
              f"Provide a professional analysis for a {direction} position. "
              f"No 'It's not just X' format. No metaphors. Professional/Concise. Max 125 words.")
    
    response = client.models.generate_content(model='gemini-2.5-flash', contents=prompt,
                                              config=types.GenerateContentConfig(tools=[types.Tool(google_search=types.GoogleSearch())]))
    return target_data, response.text

# --- UI ---
direction = st.selectbox("Position Bias:", ["LONG", "SHORT"])
vol_val = st.slider("Target Volatility (Delta):", 0.0, 100.0, st.session_state.vol_start, step=0.00001, format="%.5f")
obs_val = st.slider("Target Obscurity (Alpha Depth):", 0.0, 100.0, st.session_state.obs_start, step=0.00001, format="%.5f")

# Placeholder for the custom loading animation
loader_placeholder = st.empty()

if st.button("Run Scan"):
    gemini_key = st.secrets.get("GEMINI_API_KEY")
    cg_key = st.secrets.get("CG_API_KEY")
    
    if gemini_key and cg_key:
        # 1. Trigger Custom Sniper Animation
        loader_placeholder.markdown(
            '<div class="scope-container"><div class="scope"></div><div class="targeting-text">TARGETING OPPORTUNITY...</div></div>', 
            unsafe_allow_html=True
        )
        
        # 2. Run logic
        target_info, analysis_text = get_alpha_scan(direction, vol_val, obs_val, gemini_key, cg_key)
        
        # 3. Clear Animation
        loader_placeholder.empty()
        
        if target_info:
            st.divider()
            st.markdown(f"## **TARGET IDENTIFIED:** [{target_info['name']} ({target_info['symbol']})]({target_info['url']})")
            st.subheader(f"Strategy: {direction}")
            st.info(analysis_text)
    else:
        st.error("SYSTEM ERROR: API keys missing.")

st.caption("v5.4.0 | Data via [CoinGecko API](https://www.coingecko.com/en/api)")
