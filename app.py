import json
import os
import sqlite3

import pandas as pd
import streamlit as st

DB_FILE = "app.db"
SOURCES = {"cruises": "results.csv"}

st.set_page_config(page_title="Scraping Challenge Explorer", layout="wide")


@st.cache_resource
def get_connection():
    """Load each CSV into SQLite once per app start (data persistence layer)."""
    con = sqlite3.connect(DB_FILE, check_same_thread=False)
    for table, path in SOURCES.items():
        if os.path.exists(path):
            pd.read_csv(path, keep_default_na=False).to_sql(table, con, index=False, if_exists="replace")
    return con


@st.cache_data
def load_table(table):
    con = get_connection()
    exists = con.execute("SELECT name FROM sqlite_master WHERE name=?", (table,)).fetchone()
    return pd.read_sql(f"SELECT * FROM {table}", con) if exists else None


def disney_tab():
    df = load_table("cruises")
    if df is None:
        st.info("results.csv not found.")
        return
    df["Dates"] = pd.to_numeric(df["Number of Dates"], errors="coerce").fillna(0).astype(int)
    df["Nights"] = pd.to_numeric(df["Duration"].str.extract(r"(\d+)")[0], errors="coerce")

    pacific = (df["Sailing To"] + " " + df["Title"]).str.contains("Pacific", case=False)
    holiday = (df["Badge"] + " " + df["Title"]).str.contains("Merrytime|Holiday|Christmas", case=False)
    miami_london = df["Departing From"].str.contains("Miami|London", case=False)

    cols = st.columns(5)
    cols[0].metric("Pacific cruises", int(pacific.sum()))
    cols[1].metric("Total cruises", len(df))
    cols[2].metric("Holiday cruises", int(holiday.sum()))
    cols[3].metric("More than 2 dates", int((df["Dates"] > 2).sum()))
    cols[4].metric("Miami / London departures", int(miami_london.sum()))

    f1, f2, f3, f4 = st.columns(4)
    ports = f1.multiselect("Departing from", sorted(df["Departing From"].unique()))
    nights = f2.multiselect("Nights", sorted(df["Nights"].dropna().astype(int).unique()))
    min_dates = f3.slider("Minimum booking dates", 0, int(df["Dates"].max()), 0)
    search = f4.text_input("Search title or destination", key="disney_search")

    view = df[df["Dates"] >= min_dates]
    if ports:
        view = view[view["Departing From"].isin(ports)]
    if nights:
        view = view[view["Nights"].isin(nights)]
    if search:
        view = view[view["Title"].str.contains(search, case=False, regex=False)
                    | view["Sailing To"].str.contains(search, case=False, regex=False)]

    left, right = st.columns([2, 1])
    left.subheader(f"{len(view)} cruises")
    left.dataframe(view[["Title", "Departing From", "Sailing To", "Duration", "Price INR", "Dates"]],
                   width="stretch", hide_index=True)
    left.download_button("Download filtered CSV", view.to_csv(index=False).encode("utf-8-sig"),
                         "cruises_filtered.csv", "text/csv", key="dl_cruises")
    right.subheader("Cruises by departure port")
    right.bar_chart(view["Departing From"].value_counts())


st.title("Disney Cruise Line Explorer")
st.caption("Data scraped from disneycruise.disney.go.com, stored in SQLite.")
disney_tab()
