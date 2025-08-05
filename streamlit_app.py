import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import plotly.graph_objects as go
import numpy as np

st.set_page_config(layout="wide")
st.title("MLS Dashboard")

# ------------------- DATA SCRAPING -------------------
def fetch_mls_tables():
    url = "https://fbref.com/en/comps/22/Major-League-Soccer-Stats"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    tables = soup.find_all("table", class_="stats_table")
    return tables[0], tables[2]  # Eastern = 0, Western = 2

def parse_table(table):
    logos, teams = [], []
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

    df["GF"] = pd.to_numeric(df["GF"], errors="coerce")
    df["xG"] = pd.to_numeric(df["xG"], errors="coerce")
    df["Pts"] = pd.to_numeric(df["Pts"], errors="coerce")
    df["GD"] = pd.to_numeric(df["GD"], errors="coerce")
    return df

def combine_tables(df1, df2):
    combined = pd.concat([df1, df2], ignore_index=True)
    combined = combined.sort_values(by=["Pts", "GD", "GF"], ascending=[False, False, False]).reset_index(drop=True)
    combined["Rank"] = range(1, len(combined) + 1)
    return combined

# ------------------- SCATTER GRAPH -------------------
def create_logo_scatter(df, title):
    fig = go.Figure()
    for _, row in df.iterrows():
        if pd.notna(row["GF"]) and pd.notna(row["xG"]):
            if row["Logo"]:
                fig.add_layout_image(
                    dict(
                        source=row["Logo"],
                        x=row["xG"], y=row["GF"],
                        xref="x", yref="y",
                        sizex=2.5, sizey=2.5,
                        xanchor="center", yanchor="middle",
                        sizing="contain", layer="above",
                    )
                )
    valid_df = df.dropna(subset=["GF", "xG"])
    if not valid_df.empty:
        m, b = np.polyfit(valid_df["xG"], valid_df["GF"], 1)
        x_vals = valid_df["xG"].sort_values()
        fig.add_trace(go.Scatter(
            x=x_vals, y=m * x_vals + b,
            mode='lines', line=dict(dash='dash', color='gray'),
            name='Best Fit'
        ))
    fig.update_layout(
        title=title,
        xaxis_title="xG (Expected Goals)",
        yaxis_title="GF (Goals For)",
        height=600, width=800,
        xaxis=dict(range=[df["xG"].min() - 1, df["xG"].max() + 1]),
        yaxis=dict(range=[df["GF"].min() - 1, df["GF"].max() + 1]),
        showlegend=False,
    )
    return fig

# ------------------- SORTABLE TABLE -------------------
def render_standings_table_sortable(df, conference_name, table_id, use_colors=True):
    row_count = len(df)
    table_height = 100 + (row_count * 40)
    table_html = f"""
    <style>
        table.dataframe {{
            border-collapse: collapse;
            width: 100%;
            border-radius: 8px;
            overflow: hidden;
        }}
        table.dataframe th, table.dataframe td {{
            border: 1px solid #ccc;
            padding: 6px;
            text-align: center;
        }}
        table.dataframe th {{
            background-color: #f2f2f2;
            text-align: center;
        }}
        table.dataframe tbody tr:hover {{
            background-color: #f5f5f5;
        }}
    </style>

    <h3 style='margin-bottom:10px;'>{conference_name} Standings</h3>
    <table id="{table_id}" class="display dataframe" style="width:100%;">
        <thead>
            <tr>
                <th>Rank</th><th>Team</th><th>MP</th><th>W</th>
                <th>D</th><th>L</th><th>GF</th><th>GA</th>
                <th>GD</th><th>Pts</th>
            </tr>
        </thead>
        <tbody>
    """
    for _, row in df.iterrows():
        if use_colors:
            if row["Rank"] <= 4:
                bgcolor = "#d6f5e0"  # slightly darker green
            elif row["Rank"] <= 7:
                bgcolor = "#ffe6cc"  # slightly darker orange
            elif row["Rank"] <= 9:
                bgcolor = "#dce6f7"  # slightly darker blue
            else:
                bgcolor = "white"
        else:
            bgcolor = "white"

        team_cell = f"<img src='{row['Logo']}' style='height:22px;vertical-align:middle;margin-right:6px;'> {row['Squad']}"
        table_html += f"""
            <tr style="background-color:{bgcolor};">
                <td>{row['Rank']}</td>
                <td style="text-align:left;">{team_cell}</td>
                <td>{row['MP']}</td>
                <td>{row['W']}</td>
                <td>{row['D']}</td>
                <td>{row['L']}</td>
                <td>{row['GF']}</td>
                <td>{row['GA']}</td>
                <td>{row['GD']}</td>
                <td>{row['Pts']}</td>
            </tr>
        """
    table_html += f"""
        </tbody>
    </table>
    <link rel="stylesheet" type="text/css" 
          href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.css">
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script type="text/javascript" 
            charset="utf8" 
            src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.js"></script>
    <script>
        $(document).ready( function () {{
            $('#{table_id}').DataTable({{
                "paging": false,
                "info": false,
                "searching": false,
                "ordering": true,
                "dom": 't'
            }});
        }});
    </script>
    """
    st.components.v1.html(table_html, height=table_height)

def render_key():
    st.markdown("""
    **Key:**  
    - <span style="background-color:#d6f5e0;">&nbsp;&nbsp;&nbsp;&nbsp;</span> 1-4: Homefield Advantage  
    - <span style="background-color:#ffe6cc;">&nbsp;&nbsp;&nbsp;&nbsp;</span> 5-7: Playoffs  
    - <span style="background-color:#dce6f7;">&nbsp;&nbsp;&nbsp;&nbsp;</span> 8-9: Wildcard  
    """, unsafe_allow_html=True)

# ------------------- MAIN APP -------------------
with st.spinner("Loading MLS data..."):
    eastern_raw, western_raw = fetch_mls_tables()
    eastern_df = parse_table(eastern_raw)
    western_df = parse_table(western_raw)
    combined_df = combine_tables(eastern_df, western_df)

tabs = st.tabs(["Eastern Conference", "Western Conference", "Overall Standings"])

with tabs[0]:
    render_standings_table_sortable(eastern_df, "Eastern Conference", "east_table", use_colors=True)
    render_key()
    st.plotly_chart(create_logo_scatter(eastern_df, "Eastern Conference: GF vs xG"), use_container_width=True)

with tabs[1]:
    render_standings_table_sortable(western_df, "Western Conference", "west_table", use_colors=True)
    render_key()
    st.plotly_chart(create_logo_scatter(western_df, "Western Conference: GF vs xG"), use_container_width=True)

with tabs[2]:
    render_standings_table_sortable(combined_df, "Overall Standings", "combined_table", use_colors=False)
    st.plotly_chart(create_logo_scatter(combined_df, "Overall: GF vs xG"), use_container_width=True)
