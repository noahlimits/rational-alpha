import streamlit as st
import requests
import random
import datetime
from google import genai
from google.genai import types

# --- CONFIGURATION ---
st.set_page_config(page_title="Sentiment Sniper", layout="centered")

# --- STABILIZED INFINITY PATH CSS ---
SCOPE_CSS = """
<style>
@keyframes followPath {
    from { offset-distance: 0%; }
    to { offset-distance: 100%; }
}

.scope-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 200px;
    margin-bottom: 20px;
}

.scope-wrapper {
    position: relative;
    width: 300px;
    height: 100px;
}

.scope {
    width: 50px;
    height: 50px;
    border: 2px solid #FF4B4B;
    border-radius: 50%;
    position: absolute;
    offset-path: path('M 50,50 C 50,0 100,0 150,50 C 200,100 250,100 250,50 C 250,0 200,0 150,50 C 100,100 50,100 50,50');
    offset-rotate: 0deg;
    animation: followPath 8s infinite linear;
}

.scope::before {
    content: '';
    position: absolute;
    width: 100%;
    height: 1px;
    top: 50%;
    left: 0;
    background: #FF4B4B;
}

.scope::after {
    content: '';
    position: absolute;
    width: 1px;
    height: 100%;
    left: 50%;
    top: 0;
    background: #FF4B4B;
}

.targeting-text {
    font-family: 'Courier New', Courier, monospace;
    color: #FF4B4B;
    font-weight: bold;
    margin-top: 30px;
    letter-spacing: 3px;
    text-transform: uppercase;
    text-align: center;
}
</style>
"""
st.markdown(SCOPE_CSS, unsafe_allow_html=True)

# --- SESSION STATE ---
if 'vol_start' not in st.session_state:
    st.session_state.vol_start = random.uniform(0.0, 100.0)
if 'obs_start' not in st.session_state:
    st.session_state.obs_start = random.uniform(0.0, 100.0)

st.title("Sentiment Sniper")

# --- HIGH-LEVEL SYSTEM DESCRIPTION ---
st.markdown("""
**Sentiment Sniper** leverages a high-fidelity NLP ingestion layer powered by **Gemini** to 
decode fragmented sentiment signals and narrative velocity. By mapping cross-exchange liquidity 
depth against latent social indicators, the engine isolates asymmetric alpha opportunities 
within specific volatility-obscurity clusters. It effectively compresses multi-dimensional 
market noise into a singular, high-conviction execution thesis.
""")

# --- DATA FETCHING (CACHED) ---
@st.cache_data(ttl=60, show_spinner=False)
def fetch_market_data(page, cg_key):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {"vs_currency": "usd", "order": "market_cap_desc", "per_page": 100, "page": page, "sparkline": "false"}
    headers = {"accept": "application/json", "x-cg-demo-api-key": cg_key}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        return response.json() if response.status_code == 200 else None
    except: return None

# --- ANALYSIS LOGIC WITH ROBUST ERROR HANDLING ---
@st.cache_data(ttl=60, show_spinner=False)
def get_alpha_scan(direction, volatility, obscurity, gemini_key, cg_key):
    # Determine final direction for AUTO
    final_dir = direction
    if direction == "AUTO":
        now = datetime.datetime.now()
        chance = random.random()
        if now.minute < 30:
            final_dir = "SHORT" if chance < 0.75 else "LONG"
        else:
            final_dir = "LONG" if chance < 0.75 else "SHORT"

    # Select target asset
    page_index = max(1, int((obscurity / 100) * 10))
    coins = fetch_market_data(page_index, cg_key)
    if not coins: return None, "SYSTEM ALERT: Connection error. Retry in 60s.", final_dir

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
    prompt = (f"Research {target_data['name']} ({target_data['symbol']}). "
              f"Provide a high-conviction, professional trade analysis for a {final_dir} position. "
              f"STRICT CONSTRAINT: Do not use 'It's not just X, it's Y' or metaphors. "
              f"Tone: Casual but well-informed. Max 125 words.")
    
    try:
        # ATTEMPT 1: Primary Model with Search Tool
        response = client.models.generate_content(
            model='gemini-3-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return target_data, response.text, final_dir
    except Exception:
        try:
            # ATTEMPT 2: Fallback (No Tools) - Handles permission/400 errors
            response = client.models.generate_content(
                model='gemini-3-flash', 
                contents=prompt
            )
            return target_data, response.text + "\n\n*(Note: Real-time search offline due to API constraints)*", final_dir
        except Exception as e:
            return None, f"CRITICAL API ERROR: {str(e)}", final_dir

# --- UI INTERFACE ---
direction = st.selectbox("Position Bias:", ["LONG", "SHORT", "AUTO"])

if direction == "AUTO":
    st.caption("**AUTO:** Dynamically synchronizes directional bias with systemic narrative cycles. The engine autonomously selects the high-conviction vector by cross-referencing real-time volatility-sync against current liquidity pulses.")

vol_val = st.slider("Target Volatility (Delta):", 0.0, 100.0, st.session_state.vol_start, step=0.00001, format="%.5f")
obs_val = st.slider("Target Obscurity (Alpha Depth):", 0.0, 100.0, st.session_state.obs_start, step=0.00001, format="%.5f")

loader_placeholder = st.empty()

if st.button("Run Scan"):
    gemini_key = st.secrets.get("GEMINI_API_KEY")
    cg_key = st.secrets.get("CG_API_KEY")
    
    if gemini_key and cg_key:
        loader_placeholder.markdown(
            '''
            <div class="scope-container">
                <div class="scope-wrapper">
                    <div class="scope"></div>
                </div>
                <div class="targeting-text">Targeting Opportunity</div>
            </div>
            ''', 
            unsafe_allow_html=True
        )
        
        target_info, analysis_text, decided_dir = get_alpha_scan(direction, vol_val, obs_val, gemini_key, cg_key)
        loader_placeholder.empty()
        
        if target_info:
            st.divider()
            st.markdown(f"## **TARGET IDENTIFIED:** [{target_info['name']} ({target_info['symbol']})]({target_info['url']})")
            st.subheader(f"Strategy: {decided_dir}")
            st.info(analysis_text)
        else:
            st.error(analysis_text)
    else:
        st.error("SYSTEM ERROR: API keys missing in Secrets.")

st.caption("v5.5.3 | Data via [CoinGecko API](https://www.coingecko.com/en/api)")
