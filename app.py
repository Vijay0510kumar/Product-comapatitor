# price_comparator_app.py

import streamlit as st
import requests
import re
from bs4 import BeautifulSoup
import pandas as pd
from googlesearch import search

# ----------------------------- Groq LLM Matcher -----------------------------
def is_match(query, title, groq_api_key):
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {
                "role": "user",
                "content": f"Does the following product title match the search query? Reply with YES or NO only.\nQuery: {query}\nTitle: {title}"
            }
        ]
    }

    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
        result = response.json()["choices"][0]["message"]["content"].strip().upper()
        return result == "YES"
    except Exception as e:
        print("Groq error:", e)
        return False

# ----------------------------- Price Extractor -----------------------------
def extract_price(text):
    match = re.search(r'[₹$€£]\\s?[0-9,.]+', text)
    if match:
        raw = match.group()
        value = re.sub(r'[^0-9.]', '', raw)
        return value
    return None

# ----------------------------- Scraper -----------------------------
def scrape_page(url, query, groq_api_key):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        title = soup.title.string.strip() if soup.title else url
        text = soup.get_text(" ", strip=True)
        price = extract_price(text)

        if price and is_match(query, title, groq_api_key):
            currency = 'USD' if '.com' in url else 'INR' if '.in' in url else 'GBP' if '.co.uk' in url else 'UNKNOWN'
            return {
                "productName": title[:100],
                "price": price,
                "link": url,
                "currency": currency
            }
    except Exception as e:
        print(f"Error scraping {url}: {e}")
    return None

def get_prices(query, country, groq_api_key):
    search_query = f"{query} {country}"
    urls = list(search(search_query, num_results=10))
    results = []
    for url in urls:
        product = scrape_page(url, query, groq_api_key)
        if product:
            results.append(product)
    return sorted(results, key=lambda x: float(x["price"]))

# ----------------------------- Streamlit UI -----------------------------
st.set_page_config(page_title="🌍 Global Price Comparator", layout="wide")
st.title("🌍 Global Price Comparison Tool (Groq LLM Powered)")
st.markdown("🔍 Search any product globally across all websites using LLaMA 3 (Groq).")

query = st.text_input("Enter product name", "iPhone 16 Pro, 128GB")
country = st.text_input("Enter country (e.g., US, India, UK)", "US")
groq_api_key = st.text_input("Enter your Groq API Key", type="password")

if st.button("Compare Prices"):
    if not query or not country or not groq_api_key:
        st.warning("Please provide all inputs.")
    else:
        with st.spinner("Fetching and matching product info..."):
            results = get_prices(query, country, groq_api_key)
            if results:
                st.success(f"✅ Found {len(results)} matching results:")
                st.dataframe(pd.DataFrame(results))
            else:
                st.error("❌ No matching products found.")
