import streamlit as st
import requests
import random
from google import genai
from google.genai import types

# --- CONFIGURATION ---
st.set_page_config(page_title="Rational Alpha", layout="centered")

st.title("Terminal // Rational Alpha Generator")

# --- UI INPUTS ---
direction = st.selectbox("Directional Bias:", ["LONG", "SHORT"])
volatility = st.slider("Volatility Target (0 - 100):", 0, 100, 50)
obscurity = st.slider("Obscurity Target (0 - 100):", 0, 100, 50)

# --- EXECUTION LOGIC ---
if st.button("EXECUTE SCAN"):
    # Security check for API Key
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("SYSTEM ERROR: API key not found in Streamlit Secrets.")
        st.stop()

    # Initialize the current Google GenAI Client
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.spinner("SCANNING MARKET LIQUIDITY..."):
        # Map Obscurity slider to CoinGecko pages (1-10)
        page = max(1, int((obscurity / 100) * 10))
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page={page}&sparkline=false"
        
        try:
            # 1. Fetch market data cohort
            response = requests.get(url)
            response.raise_for_status()
            coins = response.json()
            
            # 2. Sort by Volatility (Absolute 24h Price Change)
            coins_sorted_by_vol = sorted(
                [c for c in coins if c.get('price_change_percentage_24h') is not None], 
                key=lambda x: abs(x['price_change_percentage_24h'])
            )
            
            # 3. Select Asset based on Volatility slider
            if not coins_sorted_by_vol:
                target = random.choice(coins)
            else:
                index = int((volatility / 100) * (len(coins_sorted_by_vol) - 1))
                target = coins_sorted_by_vol[max(0, min(len(coins_sorted_by_vol) - 1, index))]
                
            name = target['name']
            symbol = target['symbol'].upper()
            coin_id = target['id']
            cg_url = f"https://www.coingecko.com/en/coins/{coin_id}"
            
            # Display target with clickable link
            st.markdown(f"### **TARGET ACQUIRED:** [{name} ({symbol})]({cg_url})")
            
            # 4. Construct AI Analysis Prompt
            prompt = (
                f"Search the web for news, sentiment, and volume for {name} ({symbol}). "
                f"Write a deadpan, hyper-rational quantitative analysis justifying a {direction} position. "
                f"Reference the user's chosen Volatility ({volatility}) and Obscurity ({obscurity}) "
                f"as sophisticated risk parameters. Stay in character as a cold, logic-driven "
                f"trading terminal. Do not admit this is random. Keep it under 150 words."
            )
            
            # 5. Generate Content with Grounding (Google Search)
            # Model: gemini-2.5-flash is the stable 2026 production model
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            
            # Output analysis
            st.write(f"**ACTION:** {direction}")
            st.info(response.text)
            
        except Exception as e:
            st.error(f"SYSTEM ERR: {e}")

# --- FOOTER ---
st.caption("v4.0.1 // Stable // Logic Engine: Gemini 2.5 Flash")
