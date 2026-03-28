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
            # 1. Fetch Cohort
            response = requests.get(url)
            response.raise_for_status()
            coins = response.json()
            
            # 2. Sort by Volatility (Absolute 24h Price Change)
            coins_sorted_by_vol = sorted(
                [c for c in coins if c.get('price_change_percentage_24h') is not None], 
                key=lambda x: abs(x['price_change_percentage_24h'])
            )
            
            # 3. Select Asset
            if not coins_sorted_by_vol:
                target = random.choice(coins)
            else:
                index = int((volatility / 100) * (len(coins_sorted_by_vol) - 1))
                random_offset = random.randint(-2, 2)
                final_index = max(0, min(len(coins_sorted_by_vol) - 1, index + random_offset))
                target = coins_sorted_by_vol[final_index]
                
            name = target['name']
            symbol = target['symbol'].upper()
            
            st.write(f"**TARGET ACQUIRED:** {name} ({symbol})")
            
            # 4. Construct Prompt
            prompt = (
                f"Search the web for the latest news, market sentiment, and volume data for "
                f"the cryptocurrency {name} ({symbol}). Using this real-time data, write a deadpan, "
                f"hyper-rational quantitative analysis justifying a {direction} position. "
                f"The user selected a Volatility Target of {volatility}/100 and an Obscurity Target of {obscurity}/100. "
                f"Incorporate these metrics into your post-hoc financial jargon as if they were deliberate, sophisticated risk parameters. "
                f"Treat this asset as a totally legitimate and obvious play. Do not break character. "
                f"Do not admit this is random. Keep it under 150 words."
            )
            
            # 5. Generate Web-Grounded Rationalization
            model = genai.GenerativeModel('gemini-2.5-flash') 
            llm_response = model.generate_content(prompt, tools='google_search_retrieval')
            
            st.write(f"**ACTION:** {direction}")
            st.info(llm_response.text)
            
        except Exception as e:
            st.error(f"ERR: {e}")
