import streamlit as st
import requests
import random
from google import genai
from google.genai import types

# --- CONFIGURATION ---
st.set_page_config(page_title="Sentiment Sniper", layout="centered")

# --- SESSION STATE FOR RANDOM START ---
if 'vol_start' not in st.session_state:
    st.session_state.vol_start = random.uniform(0.0, 100.0)
if 'obs_start' not in st.session_state:
    st.session_state.obs_start = random.uniform(0.0, 100.0)

st.title("Sentiment Sniper")

# --- DEFINITIONS ---
VOL_HELP = (
    "**Volatility (Delta)** measures 24-hour price velocity.\n\n"
    "* **High Delta:** Targets 'high-octane' assets with significant price swings. "
    "Ideal for aggressive momentum plays.\n"
    "* **Low Delta:** Filters for consolidation or stable action, "
    "providing a controlled environment for conviction."
)

OBS_HELP = (
    "**Obscurity (Alpha Depth)** defines market cap and liquidity tier.\n\n"
    "* **High Alpha Depth:** Targets the market periphery (micro-caps) where "
    "information asymmetry is greatest.\n"
    "* **Low Alpha Depth:** Restricts the scan to high-liquidity 'blue chip' assets."
)

# --- DATA FETCHING (CACHED FOR 1 MIN) ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_market_data(page, cg_key):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": 100,
        "page": page,
        "sparkline": "false"
    }
    headers = {
        "accept": "application/json",
        "x-cg-demo-api-key": cg_key
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code == 429:
            return None
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

# --- ANALYSIS LOGIC (CACHED FOR 1 MIN) ---
@st.cache_data(ttl=60, show_spinner=False)
def get_alpha_scan(direction, volatility, obscurity, gemini_key, cg_key):
    page_index = max(1, int((obscurity / 100) * 10))
    coins = fetch_market_data(page_index, cg_key)
    
    if not coins:
        return None, "SYSTEM ALERT: Market data rate-limit or connection error. Retry in 60s."

    valid_coins = [c for c in coins if c.get('price_change_percentage_24h') is not None]
    coins_sorted_by_vol = sorted(valid_coins, key=lambda x: abs(x['price_change_percentage_24h']))
    
    target_idx = int((volatility / 100) * (len(coins_sorted_by_vol) - 1))
    target = coins_sorted_by_vol[max(0, min(len(coins_sorted_by_vol) - 1, target_idx))]
    
    target_data = {
        "name": target['name'],
        "symbol": target['symbol'].upper(),
        "url": f"https://www.coingecko.com/en/coins/{target['id']}"
    }

    client = genai.Client(api_key=gemini_key)
    prompt = (
        f"Research current market dynamics for {target_data['name']} ({target_data['symbol']}). "
        f"Provide a high-conviction, professional, and enthusiastic analysis justifying a {direction} position. "
        f"STRICT CONSTRAINT: Do not use the 'It's not just X, it's Y' or 'This isn't just A, it's B' format. "
        f"Avoid grandiose metaphors or operational analogies. Tone: Casual but professional and well-informed. "
        f"Persuade using volume trends, specific sentiment, and price action. "
        f"Contextualize Volatility ({volatility:.5f}/100) and Obscurity ({obscurity:.5f}/100) "
        f"directly as trade variables. Max 125 words."
    )
    
    response = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )
    
    return target_data, response.text

# --- UI INPUTS ---
direction = st.selectbox("Position Bias:", ["LONG", "SHORT"])

vol_val = st.slider(
    "Target Volatility (Delta):", 
    min_value=0.0, 
    max_value=100.0, 
    value=st.session_state.vol_start, 
    step=0.00001, 
    format="%.5f",
    help=VOL_HELP
)

obs_val = st.slider(
    "Target Obscurity (Alpha Depth):", 
    min_value=0.0, 
    max_value=100.0, 
    value=st.session_state.obs_start, 
    step=0.00001, 
    format="%.5f",
    help=OBS_HELP
)

# --- EXECUTION ---
if st.button("Run Scan"):
    gemini_key = st.secrets.get("GEMINI_API_KEY")
    cg_key = st.secrets.get("CG_API_KEY")
    
    if not gemini_key or not cg_key:
        st.error("SYSTEM ERROR: API keys missing in Secrets.")
        st.stop()

    with st.spinner("ISOLATING OPPORTUNITY"):
        target_info, analysis_text = get_alpha_scan(direction, vol_val, obs_val, gemini_key, cg_key)
        
        if target_info:
            st.divider()
            st.markdown(f"## **TARGET IDENTIFIED:** [{target_info['name']} ({target_info['symbol']})]({target_info['url']})")
            st.subheader(f"Strategy: {direction}")
            st.info(analysis_text)
        else:
            st.error(analysis_text)

st.caption("v5.3.4 | Data via [CoinGecko API](https://www.coingecko.com/en/api)")
