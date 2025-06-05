import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(layout="wide")
st.title("MLS Dashboard")

# Step 1: Scrape and parse both tables
def fetch_mls_tables():
    url = "https://fbref.com/en/comps/22/Major-League-Soccer-Stats"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table", class_="stats_table")
    return tables[0], tables[2]  # Eastern is 0, Western is 2

def parse_table(table):
    logos = []
    teams = []
    rows = table.find_all("tr")[1:]
    for row in rows:
        squad_cell = row.find("td", {"data-stat": "team"})
        if squad_cell:
            img_tag = squad_cell.find("img")
            if img_tag and img_tag.has_attr("src"):
                src = img_tag["src"]
                logo_url = src if src.startswith("http") else "https://fbref.com" + src
            else:
                logo_url = None
            logos.append(logo_url)
            teams.append(squad_cell.text.strip())

    df = pd.read_html(str(table))[0]
    df = df.iloc[:len(teams)].copy()
    df["Logo"] = logos
    df["Squad"] = teams
    df["Rank"] = range(1, len(df) + 1)

    # Convert for plot
    df["GF"] = pd.to_numeric(df["GF"], errors="coerce")
    df["xG"] = pd.to_numeric(df["xG"], errors="coerce")

    return df

def highlight_playoffs(row):
    if row['Rank'] <= 4:
        return ['background-color: #b3e2cd'] * len(row)  # Homefield advantage - greenish
    elif row['Rank'] <= 7:
        return ['background-color: #fdcdac'] * len(row)  # Playoffs - orange
    elif row['Rank'] <= 9:
        return ['background-color: #cbd5e8'] * len(row)  # Wildcard - blue
    return [''] * len(row)

# Step 2: Create scatter plot with logos and trendline
def create_logo_scatter(df, title):
    fig = go.Figure()

    for _, row in df.iterrows():
        if pd.notna(row["GF"]) and pd.notna(row["xG"]):
            if row["Logo"]:
                fig.add_layout_image(
                    dict(
                        source=row["Logo"],
                        x=row["xG"],
                        y=row["GF"],
                        xref="x",
                        yref="y",
                        sizex=2.5,
                        sizey=2.5,
                        xanchor="center",
                        yanchor="middle",
                        sizing="contain",
                        layer="above",
                    )
                )

    # Line of best fit
    valid_df = df.dropna(subset=["GF", "xG"])
    if not valid_df.empty:
        m, b = np.polyfit(valid_df["xG"], valid_df["GF"], 1)
        x_vals = valid_df["xG"].sort_values()
        fig.add_trace(go.Scatter(
            x=x_vals,
            y=m * x_vals + b,
            mode='lines',
            line=dict(dash='dash', color='gray'),
            name='Best Fit'
        ))

    fig.update_layout(
        title=title,
        xaxis_title="xG (Expected Goals)",
        yaxis_title="GF (Goals For)",
        height=600,
        width=800,
        xaxis=dict(range=[df["xG"].min() - 1, df["xG"].max() + 1]),
        yaxis=dict(range=[df["GF"].min() - 1, df["GF"].max() + 1]),
        showlegend=False,
    )
    return fig

# Step 3: Combine both tables
def combine_tables(df1, df2):
    return pd.concat([df1, df2], ignore_index=True).sort_values("Rank")

# Step 4: Fetch, parse, and render
with st.spinner("Loading MLS data..."):
    eastern_raw, western_raw = fetch_mls_tables()
    eastern_df = parse_table(eastern_raw)
    western_df = parse_table(western_raw)
    combined_df = combine_tables(eastern_df, western_df)

columns_to_display = ["Rank", "Squad", "MP", "W", "D", "L", "GF", "GA", "GD", "Pts"]

# Step 5: Tabs for conferences
conference_tabs = st.tabs(["Eastern Conference", "Western Conference", "Combined League"])

with conference_tabs[0]:
    st.subheader("Eastern Conference Standings")
    st.dataframe(eastern_df[columns_to_display].style.apply(highlight_playoffs, axis=1), use_container_width=True)
    
        # ✅ Add key
    st.markdown("**Playoff Qualification Key:**")
    st.markdown("""
    - 🟩 <span style='background-color:#b3e2cd;padding:2px 4px;'>Ranks 1-4</span>: Homefield Advantage  
    - 🟧 <span style='background-color:#fdcdac;padding:2px 4px;'>Ranks 5-7</span>: Standard Playoff Spots  
    - 🟦 <span style='background-color:#cbd5e8;padding:2px 4px;'>Ranks 8-9</span>: Wildcard Round  
    """, unsafe_allow_html=True)
    
    st.plotly_chart(create_logo_scatter(eastern_df, "Eastern Conference: GF vs xG"), use_container_width=True)
    

with conference_tabs[1]:
    st.subheader("Western Conference Standings")
    st.dataframe(western_df[columns_to_display].style.apply(highlight_playoffs, axis=1), use_container_width=True)
    
        # ✅ Add key
    st.markdown("**Playoff Qualification Key:**")
    st.markdown("""
    - 🟩 <span style='background-color:#b3e2cd;padding:2px 4px;'>Ranks 1-4</span>: Homefield Advantage  
    - 🟧 <span style='background-color:#fdcdac;padding:2px 4px;'>Ranks 5-7</span>: Standard Playoff Spots  
    - 🟦 <span style='background-color:#cbd5e8;padding:2px 4px;'>Ranks 8-9</span>: Wildcard Round  
    """, unsafe_allow_html=True)

    st.plotly_chart(create_logo_scatter(western_df, "Western Conference: GF vs xG"), use_container_width=True)


with conference_tabs[2]:
    st.subheader("Combined MLS Standings")
    st.dataframe(combined_df[columns_to_display].style.apply(highlight_playoffs, axis=1), use_container_width=True)
    
        # ✅ Add key
    st.markdown("**Playoff Qualification Key:**")
    st.markdown("""
    - 🟩 <span style='background-color:#b3e2cd;padding:2px 4px;'>Ranks 1-4</span>: Homefield Advantage  
    - 🟧 <span style='background-color:#fdcdac;padding:2px 4px;'>Ranks 5-7</span>: Standard Playoff Spots  
    - 🟦 <span style='background-color:#cbd5e8;padding:2px 4px;'>Ranks 8-9</span>: Wildcard Round  
    """, unsafe_allow_html=True)
    
    st.plotly_chart(create_logo_scatter(combined_df, "MLS Combined: GF vs xG"), use_container_width=True)
