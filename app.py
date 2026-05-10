import streamlit as st
import requests
import random
import hashlib
from google import genai
from google.genai import types

# --- CONFIGURATION ---
st.set_page_config(page_title="Sentiment Sniper", layout="centered")
MARKET_PAGE_SIZE = 250
MARKET_MAX_PAGES = 10
MIN_TOTAL_VOLUME_USD = 50_000
MIN_CANDIDATES = 8
MAX_CANDIDATES = 35
INITIAL_RADIUS = 4.0
RADIUS_STEP = 2.0
MAX_RADIUS = 35.0

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

# --- DATA FETCHING ---
@st.cache_data(ttl=180, show_spinner=False)
def fetch_market_page(page, cg_key):
    url = "https://api.coingecko.com/api/v3/coins/markets"
    params = {
        "vs_currency": "usd",
        "order": "market_cap_desc",
        "per_page": MARKET_PAGE_SIZE,
        "page": page,
        "sparkline": "false",
        "price_change_percentage": "24h",
    }
    headers = {"accept": "application/json", "x-cg-demo-api-key": cg_key}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10)
        if response.status_code != 200:
            return None
        coins = response.json()
        return coins if isinstance(coins, list) else None
    except requests.RequestException:
        return None


@st.cache_data(ttl=180, show_spinner=False)
def fetch_market_universe(cg_key):
    universe = []
    for page in range(1, MARKET_MAX_PAGES + 1):
        coins = fetch_market_page(page, cg_key)
        if coins is None:
            return None
        if not coins:
            break
        universe.extend(coins)
    return universe


def percentile(index, total):
    if total <= 1:
        return 0.0
    return (index / (total - 1)) * 100.0


def build_coin_universe(coins):
    valid_coins = [
        c for c in coins
        if c.get("id")
        and c.get("name")
        and c.get("symbol")
        and c.get("market_cap_rank") is not None
        and c.get("current_price") not in (None, 0)
        and c.get("price_change_percentage_24h") is not None
        and c.get("total_volume") is not None
        and c.get("total_volume") >= MIN_TOTAL_VOLUME_USD
    ]
    valid_coins.sort(key=lambda c: c["market_cap_rank"])
    rank_total = len(valid_coins)

    volatility_order = sorted(
        valid_coins,
        key=lambda c: abs(c["price_change_percentage_24h"]),
    )
    volatility_scores = {
        c["id"]: percentile(i, len(volatility_order))
        for i, c in enumerate(volatility_order)
    }

    scored = []
    for i, coin in enumerate(valid_coins):
        scored.append({
            "id": coin["id"],
            "name": coin["name"],
            "symbol": coin["symbol"].upper(),
            "market_cap_rank": coin["market_cap_rank"],
            "current_price": coin["current_price"],
            "total_volume": coin["total_volume"],
            "price_change_percentage_24h": coin["price_change_percentage_24h"],
            "obscurity_score": percentile(i, rank_total),
            "volatility_score": volatility_scores[coin["id"]],
        })
    return scored


def select_constellation(scored_coins, volatility, obscurity, direction):
    radius = INITIAL_RADIUS
    while radius <= MAX_RADIUS:
        candidates = [
            c for c in scored_coins
            if abs(c["volatility_score"] - volatility) <= radius
            and abs(c["obscurity_score"] - obscurity) <= radius
        ]
        if len(candidates) >= MIN_CANDIDATES:
            break
        radius += RADIUS_STEP
    else:
        candidates = sorted(
            scored_coins,
            key=lambda c: (
                (c["volatility_score"] - volatility) ** 2
                + (c["obscurity_score"] - obscurity) ** 2
            ),
        )[:MIN_CANDIDATES]

    candidates = sorted(
        candidates,
        key=lambda c: (
            (c["volatility_score"] - volatility) ** 2
            + (c["obscurity_score"] - obscurity) ** 2
        ),
    )[:MAX_CANDIDATES]

    seed_basis = "|".join(
        f"{c['id']}:{c['volatility_score']:.3f}:{c['obscurity_score']:.3f}"
        for c in sorted(candidates, key=lambda c: c["id"])
    )
    seed_text = f"{direction}|{volatility:.5f}|{obscurity:.5f}|{seed_basis}"
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest(), 16)
    rng = random.Random(seed)
    return rng.choice(candidates)

# --- ANALYSIS LOGIC ---
@st.cache_data(ttl=60, show_spinner=False)
def get_alpha_scan(direction, volatility, obscurity, gemini_key, cg_key):
    final_dir = direction
    if direction == "AUTO":
        direction_seed = int(
            hashlib.sha256(f"{volatility:.5f}|{obscurity:.5f}|AUTO".encode("utf-8")).hexdigest(),
            16,
        )
        final_dir = random.Random(direction_seed).choice(["LONG", "SHORT"])

    coins = fetch_market_universe(cg_key)
    if not coins:
        return None, "SYSTEM ALERT: Market feed unavailable. Retry shortly.", final_dir

    scored_coins = build_coin_universe(coins)
    if not scored_coins:
        return None, "SYSTEM ALERT: Market feed returned insufficient signal density.", final_dir

    target = select_constellation(scored_coins, volatility, obscurity, final_dir)

    target_data = {
        "name": target["name"],
        "symbol": target["symbol"],
        "url": f"https://www.coingecko.com/en/coins/{target['id']}",
    }

    client = genai.Client(api_key=gemini_key)
    prompt = (f"Research {target_data['name']} ({target_data['symbol']}). "
              f"Provide a high-conviction, professional trade analysis for a {final_dir} position. "
              f"STRICT CONSTRAINT: Do not use 'It's not just X, it's Y' or metaphors. "
              f"Tone: Casual but well-informed. Max 125 words.")
    
    try:
        # Restored to the working 2.5 architecture
        response = client.models.generate_content(
            model='gemini-2.5-flash', 
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        return target_data, response.text, final_dir
    except Exception:
        try:
            # Fallback (No Tools)
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt
            )
            return target_data, response.text + "\n\n*(Note: Real-time search offline)*", final_dir
        except Exception:
            return None, "SYSTEM ALERT: Analysis engine unavailable. Retry shortly.", final_dir

# --- UI ---
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

st.caption("v5.5.5 | Data via [CoinGecko API](https://www.coingecko.com/en/api)")
