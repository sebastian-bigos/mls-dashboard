import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os
import base64
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("MLS Dashboard")

# --- Scrape ESPN MLS Standings ---
ESPN_URL = "https://www.espn.com/soccer/standings/_/league/usa.1/group/season/2025"
headers = {
    "User-Agent":
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}
resp = requests.get(ESPN_URL, headers=headers)
resp.raise_for_status()

soup = BeautifulSoup(resp.text, "html.parser")
tables = soup.find_all("table")

names_table = pd.read_html(str(tables[0]))[0]
stats_table = pd.read_html(str(tables[1]))[0]

num_teams = len(names_table)
half = num_teams // 2

def promote_header(df):
    df = df.copy()
    df.columns = df.iloc[0].str.strip()
    df = df[1:].reset_index(drop=True)
    return df

# --- Local logos folder ---
TEAM_LOGOS = {abbr: f"logos/{abbr}.png" for abbr in [
    "ATL","ATX","CHI","CIN","CLB","CLT","COL","DAL","DC","HOU","MIA",
    "LA","LAFC","MIN","MTL","NE","NSH","NY","NYC","ORL","PHI","POR",
    "RSL","SD","SJ","SEA","SKC","STL","TOR","VAN"
]}

def encode_logo(path):
    if not path or not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        return f"data:image/png;base64,{b64}"

def split_team_col(df):
    first_col = df.columns[0]
    ranks, abbrs, teams, logos = [], [], [], []

    exceptions = {
        "New York Red Bulls": 2,
        "New England Revolution": 2,
        "D.C. United": 2,
        "San Diego FC": 2,
        "San Jose Earthquakes": 2,
        "LAFC": 4,
        "LA Galaxy": 2,
    }

    for val in df[first_col]:
        val = str(val).strip()
        m = re.match(r"^(\d+)", val)
        rank = int(m.group(1)) if m else None
        rest = val[len(str(rank)):] if m else val

        abbr_len = 3
        for name, ln in exceptions.items():
            if rest.endswith(name):
                abbr_len = ln
                break

        abbr = rest[:abbr_len]
        team_name = rest[abbr_len:].strip()

        ranks.append(rank)
        abbrs.append(abbr)
        teams.append(team_name)

        logo_path = TEAM_LOGOS.get(abbr)
        logos.append(encode_logo(logo_path))

    df = df.drop(columns=[first_col])
    df.insert(0, "Rank", ranks)
    df.insert(1, "Abbr", abbrs)
    df.insert(2, "Team", teams)
    df.insert(3, "Logo", logos)
    return df

# --- Build dataframes ---
east_df = promote_header(names_table.iloc[:half])
east_stats = promote_header(stats_table.iloc[:half])
east_df = pd.concat([east_df, east_stats.iloc[:, 1:]], axis=1)
east_df = split_team_col(east_df)

west_df = promote_header(names_table.iloc[half:])
west_stats = promote_header(stats_table.iloc[half:])
west_df = pd.concat([west_df, west_stats.iloc[:, 1:]], axis=1)
west_df = split_team_col(west_df)

# --- Convert numeric columns dynamically ---
numeric_cols = [col for col in east_df.columns if col not in ["Rank", "Abbr", "Team", "Logo"]]
for df in [east_df, west_df]:
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# --- Save top 1-9 teams per conference for coloring ---
top_east_teams = east_df.loc[east_df['Rank'] <= 9, 'Team'].tolist()
top_west_teams = west_df.loc[west_df['Rank'] <= 9, 'Team'].tolist()

# --- Sort and create overall standings ---
overall_df = pd.concat([east_df, west_df], ignore_index=True)
overall_df = overall_df.sort_values(
    by=['P', 'W', 'GD'], ascending=[False, False, False]
).reset_index(drop=True)
overall_df['Rank'] = range(1, len(overall_df)+1)

# --- Function to render tables ---
def render_mls_table(df, table_title, table_id):
    stat_cols = [col for col in df.columns if col not in ["Rank","Abbr","Team","Logo"]]
    row_count = len(df)
    table_height = 250 + (row_count * 48)

    html = f"""
    <link rel="stylesheet" type="text/css" 
          href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.css">
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script type="text/javascript" charset="utf8" 
            src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.js"></script>
    <style>
        table {{
            border-collapse: collapse;
            width: 100%;
            border-radius: 8px;
            overflow: hidden;
        }}
        th, td {{
            border: 1px solid #ccc;
            padding: 6px;
            text-align: center;
        }}
        th {{
            background-color: #f5f5f5;
            font-weight: bold;
        }}
        tbody tr:hover {{
            background-color: #f5f5f5;
        }}
        img {{
            height: 24px;
            vertical-align: middle;
            margin-right: 6px;
        }}
    </style>

    <h3 style='margin-bottom:10px;'>{table_title}</h3>
    <table id="{table_id}" class="display" style="width:100%;">
        <thead>
            <tr>
                <th>Rank</th>
                <th>Team</th>
    """
    for col in stat_cols:
        html += f"<th>{col}</th>"
    html += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        team_name = row['Team']
        if table_id == "overall_table":
            if team_name in top_east_teams:
                orig_rank = east_df.loc[east_df['Team'] == team_name, 'Rank'].values[0]
            elif team_name in top_west_teams:
                orig_rank = west_df.loc[west_df['Team'] == team_name, 'Rank'].values[0]
            else:
                orig_rank = None
        else:
            orig_rank = row['Rank']

        if orig_rank:
            if orig_rank <= 4:
                bgcolor = "#d6f5e0"
            elif orig_rank <= 7:
                bgcolor = "#ffe6cc"
            elif orig_rank <= 9:
                bgcolor = "#dce6f7"
            else:
                bgcolor = "white"
        else:
            bgcolor = "white"

        team_cell = f"<img src='{row['Logo']}'>{team_name}" if row['Logo'] else team_name
        html += f"<tr style='background-color:{bgcolor};'>"
        html += f"<td>{row['Rank']}</td>"
        html += f"<td style='text-align:left'>{team_cell}</td>"
        for col in stat_cols:
            html += f"<td>{row[col]}</td>"
        html += "</tr>"

    html += "</tbody></table>"

    html += f"""
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
    st.components.v1.html(html, height=table_height)

# --- Function to plot GD vs Points with hover tooltips ---
def plot_points_vs_gd(df, title):
    df_plot = df.copy()
    df_plot["GD"] = pd.to_numeric(df_plot["GD"], errors="coerce")
    df_plot["P"] = pd.to_numeric(df_plot["P"], errors="coerce")

    x_min, x_max = df_plot["P"].min() - 1, df_plot["P"].max() + 1
    y_min, y_max = df_plot["GD"].min() - 1, df_plot["GD"].max() + 1

    fig = go.Figure()

    # Add team logos as scatter points
    for _, row in df_plot.iterrows():
        if row["Logo"]:
            fig.add_layout_image(
                dict(
                    source=row["Logo"],
                    x=row["P"],
                    y=row["GD"],
                    xref="x",
                    yref="y",
                    sizex=3,
                    sizey=3,
                    xanchor="center",
                    yanchor="middle",
                    layer="above"
                )
            )

    # Transparent scatter points for hover tooltips
    fig.add_trace(
        go.Scatter(
            x=df_plot["P"],
            y=df_plot["GD"],
            mode="markers",
            marker=dict(size=20, opacity=0),
            text=df_plot["Team"],
            hoverinfo="text",
            showlegend=False
        )
    )

    # Linear regression line
    x = df_plot["P"].values
    y = df_plot["GD"].values
    slope, intercept = np.polyfit(x, y, 1)
    y_fit = slope * x + intercept
    fig.add_trace(
        go.Scatter(
            x=x,
            y=y_fit,
            mode="lines",
            line=dict(color="red", dash="dash"),
            name="Best Fit"
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title="Points (P)",
        yaxis_title="Goal Difference (GD)",
        xaxis=dict(range=[x_min, x_max], showgrid=True),
        yaxis=dict(range=[y_min, y_max], showgrid=True),
        height=600,
        template="plotly_white",
    )

    st.plotly_chart(fig, use_container_width=True)

# --- Streamlit Tabs ---
tabs = st.tabs(["Eastern Conference", "Western Conference", "Overall MLS Standings"])

def render_key():
    st.markdown("""
    **Key:**  
    - <span style="background-color:#d6f5e0;">&nbsp;&nbsp;&nbsp;&nbsp;</span> 1-4: Homefield Advantage  
    - <span style="background-color:#ffe6cc;">&nbsp;&nbsp;&nbsp;&nbsp;</span> 5-7: Playoffs  
    - <span style="background-color:#dce6f7;">&nbsp;&nbsp;&nbsp;&nbsp;</span> 8-9: Wildcard  
    """, unsafe_allow_html=True)

with tabs[0]:
    render_mls_table(east_df, "Eastern Conference", "east_table")
    render_key()
    st.subheader("Eastern Conference: GD vs Points")
    plot_points_vs_gd(east_df, "Eastern Conference: Points vs Goal Difference")

with tabs[1]:
    render_mls_table(west_df, "Western Conference", "west_table")
    render_key()
    st.subheader("Western Conference: GD vs Points")
    plot_points_vs_gd(west_df, "Western Conference: Points vs Goal Difference")

with tabs[2]:
    render_mls_table(overall_df, "Overall MLS Standings", "overall_table")
    render_key()
    st.subheader("Overall MLS Standings: GD vs Points")
    plot_points_vs_gd(overall_df, "Overall MLS Standings: Points vs Goal Difference")
