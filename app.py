import streamlit as st
import requests
import random
import google.generativeai as genai

st.set_page_config(page_title="Rational Alpha", layout="centered")

st.title("Terminal // Rational Alpha Generator")

direction = st.selectbox("Directional Bias:", ["LONG", "SHORT"])
volatility = st.slider("Volatility Target (0 - 100):", 0, 100, 50)
obscurity = st.slider("Obscurity Target (0 - 100):", 0, 100, 50)

if st.button("EXECUTE SCAN"):
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("SYSTEM ERROR: API key not found in Streamlit Secrets.")
        st.stop()

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    with st.spinner("SCANNING MARKET LIQUIDITY..."):
        # Obscurity maps to CoinGecko pages (1-10)
        page = max(1, int((obscurity / 100) * 10))
        url = f"https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&order=market_cap_desc&per_page=100&page={page}&sparkline=false"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            coins = response.json()
            
            # Sort by Volatility (Absolute 24h Price Change)
            coins_sorted_by_vol = sorted(
                [c for c in coins if c.get('price_change_percentage_24h') is not None], 
                key=lambda x: abs(x['price_change_percentage_24h'])
            )
            
            # Select Asset
            if not coins_sorted_by_vol:
                target = random.choice(coins)
            else:
                index = int((volatility / 100) * (len(coins_sorted_by_vol) - 1))
                final_index = max(0, min(len(coins_sorted_by_vol) - 1, index))
                target = coins_sorted_by_vol[final_index]
                
            name = target['name']
            symbol = target['symbol'].upper()
            
            st.write(f"**TARGET ACQUIRED:** {name} ({symbol})")
            
            prompt = (
                f"Search the web for news and volume for {name} ({symbol}). "
                f"Write a deadpan, hyper-rational quantitative analysis justifying a {direction} position. "
                f"Incorporate a Volatility Target of {volatility} and Obscurity of {obscurity} "
                f"as sophisticated risk parameters. Stay in character. Under 150 words."
            )
            
            # This is the exact configuration for the current stable SDK
            model = genai.GenerativeModel(
                model_name='gemini-2.0-flash',
                tools=[{'google_search': {}}]
            )
            
            llm_response = model.generate_content(prompt)
            
            st.write(f"**ACTION:** {direction}")
            st.info(llm_response.text)
            
        except Exception as e:
            st.error(f"ERR: {e}")
