import streamlit as st
import pandas as pd
import calendar
import plotly.graph_objects as go
from datetime import datetime
from io import BytesIO
from fpdf import FPDF
from pathlib import Path
from st_aggrid import AgGrid, GridOptionsBuilder

# --- Load Data ---
@st.cache_data
def load_data():
    file_path = Path("public_holidays_2025_2026.csv")
    df = pd.read_csv(file_path)

    df = df.melt(id_vars=['Column1'], var_name='Date', value_name='Holiday')
    df['Holiday'] = df['Holiday'].astype(str)
    df = df[df['Holiday'] != '0']
    df['Date'] = pd.to_datetime(df['Date'], dayfirst=True, errors='coerce')
    df.dropna(subset=['Date'], inplace=True)
    df.rename(columns={'Column1': 'Country'}, inplace=True)

    df['Year'] = df['Date'].dt.year
    df['Month'] = df['Date'].dt.strftime('%B')
    df['Month_Num'] = df['Date'].dt.month
    df['Day'] = df['Date'].dt.day

    return df

# --- Country Groups ---
steering_group = [
    "Canada", "Denmark", "France", "Germany", "Italy", "Norway", 
    "South Africa", "Spain", "United Kingdom", "United States"
]

member_countries = [
    "Australia", "Austria", "Belgium", "Canada", "China", "Denmark", "Finland",
    "France", "Germany", "Italy", "Netherlands", "Norway", "Poland",
    "South Africa", "Spain", "Switzerland", "United Kingdom", "United States"
]

df = load_data()
st.title("WORK-NET Meeting Planner")

# --- Sidebar Filters ---
st.sidebar.header("Filters")

# All available countries
all_countries = sorted(df['Country'].unique())

# --- Country selection mode ---
selection_mode = st.sidebar.radio("Start with:", ["No Countries", "Steering Group", "Member Countries", "All Countries"])

# Base selection based on radio choice
if selection_mode == "Steering Group":
    base_selection = steering_group
elif selection_mode == "Member Countries":
    base_selection = member_countries
elif selection_mode == "All Countries":
    base_selection = all_countries
else:
    base_selection = []

# Manual country selection (can add/remove from base)


# Ensure base_selection only includes valid countries from options
valid_base_selection = [c for c in base_selection if c in all_countries]

selected_countries = st.sidebar.multiselect("Select countries:", options=all_countries, default=valid_base_selection)

# Year, month, search
selected_year = st.sidebar.selectbox("Select year:", sorted(df['Year'].unique()))
month_names = list(calendar.month_name)[1:]
selected_month_name = st.sidebar.selectbox("Select month:", month_names)
selected_month = month_names.index(selected_month_name) + 1
search_term = st.sidebar.text_input("Search holidays (e.g. 'Christmas')", key='holiday_search').lower()

# --- Filter Data ---
filtered = df.copy()
if selected_countries:
    filtered = filtered[filtered['Country'].isin(selected_countries)]
if search_term:
    filtered = filtered[filtered['Holiday'].str.lower().str.contains(search_term)]

filtered = filtered[(filtered['Year'] == selected_year) & (filtered['Month_Num'] == selected_month)]

# --- Calendar Heatmap ---
st.markdown("## 🗓️ Calendar View: Days with No Holidays in Any Selected Country")

def get_month_matrix(year, month):
    cal = calendar.Calendar(firstweekday=0)
    return list(cal.itermonthdates(year, month))

if selected_countries:
    month_dates = get_month_matrix(selected_year, selected_month)

    df_month = df[
        (df['Year'] == selected_year) &
        (df['Month_Num'] == selected_month) &
        (df['Country'].isin(selected_countries))
    ]
    holiday_dates = set(pd.to_datetime(df_month['Date']).dt.date)

    z_vals = []
    annotations = []
    week_colors = []
    week_labels = []

    for i, d in enumerate(month_dates):
        if d.month == selected_month:
            color_val = 1 if d not in holiday_dates else 0
            label = str(d.day)
        else:
            color_val = -1
            label = ""

        week_colors.append(color_val)
        week_labels.append(label)

        if (i + 1) % 7 == 0:
            z_vals.append(week_colors)
            annotations.append(week_labels)
            week_colors = []
            week_labels = []

    color_map = {-1: 'lightgray', 0: 'lightcoral', 1: 'lightgreen'}

    fig = go.Figure()
    for i, row in enumerate(z_vals):
        for j, val in enumerate(row):
            fig.add_shape(type="rect",
                          x0=j, y0=-i, x1=j+1, y1=-i+1,
                          line=dict(color="white"),
                          fillcolor=color_map[val])
            fig.add_annotation(x=j+0.5, y=-i+0.5, text=annotations[i][j],
                               showarrow=False, font=dict(color="black"))

    fig.update_layout(
        width=700, height=400,
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 7]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, scaleanchor="x", range=[-len(z_vals), 1]),
        title=f"{selected_month_name} {selected_year}",
    )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("""
    **Legend:**  
    🟩 Green = No holiday  
    🟥 Red = Holiday  
    ⬜ Grey = Day from other month
    """)
else:
    st.info("Select at least one country to see the calendar.")

# --- Table of Holidays ---
st.markdown("## 🕛 Public Holidays by Country")
if not filtered.empty:
    for month, group in filtered.groupby('Month'):
        st.markdown(f"### 🗓️ {month}")

        gb = GridOptionsBuilder.from_dataframe(group[['Date', 'Country', 'Holiday']])
        gb.configure_default_column(wrapText=True, autoHeight=True)
        gb.configure_column("Holiday", width=300)
        grid_options = gb.build()

        AgGrid(group[['Date', 'Country', 'Holiday']].sort_values(by='Date'),
               gridOptions=grid_options,
               enable_enterprise_modules=False,
               height=300,
               fit_columns_on_grid_load=True)

    # --- Download Buttons ---
    excel_buffer = BytesIO()
    filtered.to_excel(excel_buffer, index=False, sheet_name='Holidays')
    st.download_button("📅 Download Excel", excel_buffer.getvalue(), "holidays.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="Public Holidays", ln=True, align='C')
    for idx, row in filtered.iterrows():
        pdf.cell(200, 10, txt=f"{row['Date'].date()} | {row['Country']} | {row['Holiday']}", ln=True)

    pdf_buffer = BytesIO()
    pdf_bytes = pdf.output(dest='S').encode('latin1')
    pdf_buffer.write(pdf_bytes)
    pdf_buffer.seek(0)
    st.download_button("📄 Download PDF", pdf_buffer, "holidays.pdf", "application/pdf")
else:
    st.warning("No holidays match your filters.")

# --- Show country groups at the bottom ---
st.markdown("---")
st.subheader("Country Groups")
st.markdown("**Steering Group Countries:**")
st.markdown(", ".join(sorted(steering_group)))
st.markdown("**Member Countries:**")
st.markdown(", ".join(sorted(member_countries)))
