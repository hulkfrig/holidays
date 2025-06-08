import streamlit as st
import pandas as pd

# Replace this with your OneDrive direct download URL
onedrive_url = "https://onedrive.live.com/download?resid=YOUR_ID_HERE"

@st.cache_data
def load_data(url):
    return pd.read_excel(url, sheet_name="Sheet1")

df = load_data(onedrive_url)

# Extract country names
countries = df['Column1'].dropna().unique().tolist()

st.title("Public Holidays by Country (2025–2026)")

selected = st.multiselect("Select countries:", countries)

if selected:
    st.markdown("### Holidays for selected countries:")
    filtered = df[df['Column1'].isin(selected)]
    st.dataframe(filtered.set_index('Column1'))

    # Export to CSV
    csv = filtered.to_csv(index=False)
    st.download_button("📄 Download CSV", csv, "selected_holidays.csv", "text/csv")
else:
    st.info("Select one or more countries to view holidays.")

