import streamlit as st
import requests
import random
from google import genai
from google.genai import types

# --- CONFIGURATION ---
st.set_page_config(page_title="Rational Alpha", layout="centered")

st.title("🏛️ The Alpha Desk")

# --- UI INPUTS ---
direction = st.selectbox("Position Bias:", ["LONG", "SHORT"])
volatility = st.slider("Target Volatility (Delta):", 0, 100, 50)
obscurity = st.slider("Target Obscurity (Alpha Depth):", 0, 100, 50)

# --- EXECUTION LOGIC ---
if st.button("RUN SCAN"):
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("SYSTEM ERROR: API key not found in Streamlit Secrets.")
        st.stop()

    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.spinner("ISOLATING ASYMMETRIC OPPORTUNITY..."):
        # Map Obscurity to CoinGecko pages
        page = max(1, int((obscurity / 100) * 10))
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page={page}&sparkline=false"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            coins = response.json()
            
            # Sort by Volatility
            coins_sorted_by_vol = sorted(
                [c for c in coins if c.get('price_change_percentage_24h') is not None], 
                key=lambda x: abs(x['price_change_percentage_24h'])
            )
            
            if not coins_sorted_by_vol:
                target = random.choice(coins)
            else:
                index = int((volatility / 100) * (len(coins_sorted_by_vol) - 1))
                target = coins_sorted_by_vol[max(0, min(len(coins_sorted_by_vol) - 1, index))]
                
            name = target['name']
            symbol = target['symbol'].upper()
            coin_id = target['id']
            cg_url = f"https://www.coingecko.com/en/coins/{coin_id}"
            
            st.markdown(f"## **TARGET IDENTIFIED:** [{name} ({symbol})]({cg_url})")
            
            # --- THE REFINED PROFESSIONAL STRATEGIST ---
            prompt = (
                f"Perform a search on current market conditions for {name} ({symbol}). "
                f"Write a high-conviction, professional, and enthusiastic analysis justifying a {direction} position. "
                f"The tone should be that of an elite institutional strategist sharing a high-signal discovery with a peer. "
                f"Avoid all marketing fluff, clichés like 'It's not just X, it's Y', or casual greetings like 'gather 'round.' "
                f"Use precise, convincing logic driven by the specific Obscurity ({obscurity}/100) and Volatility ({volatility}/100) parameters. "
                f"Be efficient, well-informed, and highly persuasive. Keep it under 130 words."
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

st.caption("v4.6.0 // Strategy Engine: Gemini 2.5 Flash")
