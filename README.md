# Sentiment Sniper

Sentiment Sniper is a Streamlit app that selects a cryptocurrency from a volatility/obscurity coordinate space, then generates a concise trade thesis for the selected directional bias.

## How Selection Works

- CoinGecko market data is fetched across multiple market-cap pages.
- Coins with missing 24h change, missing rank, missing price, or thin volume are excluded.
- Each remaining coin receives two percentile scores:
  - volatility: rank by absolute 24h price change
  - obscurity: rank by market-cap position
- The sliders define a target coordinate.
- The app builds a nearby candidate constellation and chooses one coin with seeded randomness.
- Identical inputs return the same coin while the eligible constellation remains the same. When market data shifts enough to change that constellation, the output can shift too.

## Local Setup

Install dependencies:

```bash
pip install -r requirements.txt
```

Create `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "your-gemini-key"
CG_API_KEY = "your-coingecko-key"
```

Run the app:

```bash
streamlit run app.py
```

## Streamlit Cloud

Deploy from the GitHub repository with `app.py` as the entrypoint. Add `GEMINI_API_KEY` and `CG_API_KEY` in Streamlit Cloud secrets rather than committing them to the repository.
