import streamlit as st
import requests
import random
from google import genai
from google.genai import types

# --- CONFIGURATION ---
st.set_page_config(page_title="Rational Alpha", layout="wide")

# --- SIDEBAR: SYSTEM PARAMETERS ---
st.sidebar.header("System Parameters")

st.sidebar.subheader("Target Volatility (Delta)")
st.sidebar.write(
    "**Volatility** measures the 24-hour price velocity of the asset. "
    "\n\n* **High Delta:** Targets 'high-octane' assets currently experiencing significant price swings. "
    "Ideal for aggressive momentum plays where volatility is the primary driver of opportunity."
    "\n* **Low Delta:** Filters for assets in a consolidation phase or exhibiting stable price action, "
    "providing a more controlled environment for long-term conviction."
)

st.sidebar.divider()

st.sidebar.subheader("Target Obscurity (Alpha Depth)")
st.sidebar.write(
    "**Obscurity** defines the tier of market capitalization and liquidity depth."
    "\n\n* **High Alpha Depth:** Pushes the scan into the market periphery—targeting micro-cap and low-volume assets. "
    "This is where information asymmetry is greatest, allowing for identification before institutional radar detection."
    "\n* **Low Alpha Depth:** Restricts the scan to high-liquidity 'blue chip' assets, focusing the thesis on "
    "established market leaders with deep order books."
)

# --- MAIN TERMINAL ---
st.title("🏛️ The Alpha Desk")

# --- DATA FETCHING (CACHED FOR 1 MIN) ---
@st.cache_data(ttl=60)
def fetch_market_data(page):
    url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page={page}&sparkline=false"
    try:
        response = requests.get(url)
        if response.status_code == 429:
            return None
        response.raise_for_status()
        return response.json()
    except Exception:
        return None

# --- FULL ANALYSIS LOGIC (CACHED FOR 1 MIN) ---
@st.cache_data(ttl=60)
def get_alpha_scan(direction, volatility, obscurity, api_key):
    # 1. Fetch Data
    page_index = max(1, int((obscurity / 100) * 10))
    coins = fetch_market_data(page_index)
    
    if not coins:
        return None, "SYSTEM ALERT: Market data unavailable. Please retry in 60 seconds."

    # 2. Selection (Deterministic based on sliders)
    valid_coins = [c for c in coins if c.get('price_change_percentage_24h') is not None]
    coins_sorted_by_vol = sorted(valid_coins, key=lambda x: abs(x['price_change_percentage_24h']))
    
    target_idx = int((volatility / 100) * (len(coins_sorted_by_vol) - 1))
    target = coins_sorted_by_vol[max(0, min(len(coins_sorted_by_vol) - 1, target_idx))]
    
    target_data = {
        "name": target['name'],
        "symbol": target['symbol'].upper(),
        "url": f"https://www.coingecko.com/en/coins/{target['id']}"
    }

    # 3. AI Generation
    client = genai.Client(api_key=api_key)
    prompt = (
        f"Research {target_data['name']} ({target_data['symbol']}) market dynamics. "
        f"Provide a high-conviction, institutional-grade analysis for a {direction} position. "
        f"The tone should be enthusiastic, casual but professional, and highly convincing. "
        f"Zero fluff. Avoid clichés like 'It's not just X, it's Y.' "
        f"Contextualize Volatility ({volatility}/100) and Obscurity ({obscurity}/100) "
        f"as the primary variables in this thesis. Max 125 words."
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
col1, col2, col3 = st.columns(3)
with col1:
    direction = st.selectbox("Position Bias:", ["LONG", "SHORT"])
with col2:
    vol_val = st.slider("Target Volatility (Delta):", 0, 100, 50)
with col3:
    obs_val = st.slider("Target Obscurity (Alpha Depth):", 0, 100, 50)

# --- EXECUTION ---
if st.button("Run Scan"):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        st.error("SYSTEM ERROR: API key not found.")
        st.stop()

    with st.spinner("SYNCHRONIZING MARKET DATA AND ANALYSIS..."):
        target_info, analysis_text = get_alpha_scan(direction, vol_val, obs_val, api_key)
        
        if target_info:
            st.divider()
            st.markdown(f"## **TARGET IDENTIFIED:** [{target_info['name']} ({target_info['symbol']})]({target_info['url']})")
            st.subheader(f"Strategy: {direction}")
            st.info(analysis_text)
        else:
            st.error(analysis_text)

st.caption("v5.0.0")
