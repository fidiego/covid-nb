from datetime import datetime, timedelta
import time
import json
import math
import os

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def download_geojson(geojson_local_path):
    data_source = "https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json"
    resp = requests.get(data_source, stream=True)
    resp.raise_for_status()
    with open(geojson_local_path, "wb") as openfile:
        for block in resp.iter_content(1024):
            openfile.write(block)


@st.cache
def load_geojson(geojson_local_path):
    print(f'Preparing to load geojson from:"{geojson_local_path}"')
    if not os.path.isfile(geojson_local_path):
        print("  downloading from the web")
        download_geojson(geojson_local_path)

    with open(geojson_local_path, "r") as openfile:
        print("  opening file")
        geojson = json.loads(openfile.read())

    return geojson


@st.cache
def load_data(local_path):
    print(f'Preparing to load data from:"{local_path}"')
    if os.path.isfile(local_path):
        mtime = int(os.stat(local_path).st_mtime)
        now = int(time.time())
        age = (now - mtime) / 60 / 60  # to horus
        if age >= 8:
            print("Local Data: is stale - downloading")
            download_data_source(local_path)
    else:
        print("Local Data: not found - downloading")
        download_data_source(local_path)

    print(f" Loading {local_path} into DataFrame")
    df = pd.read_csv("us-counties.csv", dtype={"fips": str})
    df = df[df.state == "Indiana"]  # filter to only indiana data
    df = df[df.county != "Unknown"]  # filter out unknown county

    with open("in-county-populations--modified.json", "r") as openfile:
        in_county_data = json.loads(openfile.read())

    df["population"] = df.county.apply(lambda county: in_county_data[county]["Pop"])
    df["cases_pop"] = df.apply(lambda row: (row.cases / row.population) * 100, axis=1)
    df["deaths_pop"] = df.apply(lambda row: (row.deaths / row.population) * 100, axis=1)
    return df


def download_data_source(local_path):
    """Download latest data and save to 'local_path'"""
    data_source = (
        "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-counties.csv"
    )
    resp = requests.get(data_source, stream=True)
    resp.raise_for_status()
    with open(local_path, "wb") as openfile:
        for block in resp.iter_content(1024):
            openfile.write(block)


def make_figure(df, title):
    """draw plotly figure"""
    pass


def plot_states_and_counties_curve(df, state_county_map: dict, name):
    """for metropolitan area. i.e. chicagoland"""
    states = state_county_map.keys()
    # trim dataset to relevant states, counties
    state_counties_df = df[
        df.apply(
            lambda x: x["state"] in states
            and x["county"] in state_county_map[x["state"]],
            axis=1,
        )
    ]
    # arrange by day
    day_df = (
        state_counties_df.drop(columns=["fips", "state", "county"])
        .groupby(by="date")
        .agg(["sum"])
    )
    day_df.columns = {("cases", "sum"): "cases_sum", ("deaths", "sum"): "deaths_sum"}
    p = make_figure(day_df, name)
    st.bokeh_chart(p)


geojson_local_path = os.path.join(BASE_DIR, "geojson-counties-fips.json")
geojson = load_geojson(geojson_local_path)

local_path = os.path.join(BASE_DIR, "us-counties.csv")
df = load_data(local_path)

print("\nPreparing to render\n")
st.title("Indiana Covid Cases")

st.markdown(
    """The data used on this site can be found [here](https://www.github.com/nytimes/covid-19-data/master/us-counties.csv).
""".strip()
)

# Set some defaults for cloropleth maps
in_center = {"lat": 39.766028, "lon": -86.441278}
default_cloropleth_kwargs = dict(
    geojson=geojson,
    locations="fips",
    color_continuous_scale="Plasma",
    mapbox_style="carto-positron",
    zoom=5.4,
    center=in_center,
    opacity=0.5,
)


def map_cases_by_pop(df):
    """Map cases by county normalized by population"""
    cases_pop_values = df.cases_pop.unique()
    _min = min(cases_pop_values)
    _max = max(cases_pop_values)
    fig_1 = px.choropleth_mapbox(
        df,
        color="cases_pop",
        range_color=(_min, _max),
        labels={"cases_pop": "% Infected"},
        hover_data=["county", "cases"],
        **default_cloropleth_kwargs,
    )
    fig_1.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig_1


fig_1 = map_cases_by_pop(df)
st.plotly_chart(fig_1)
st.markdown(
    """
This map shows which counties have the highest number of infections per capita. The map colors are determined by the number of infections divided by the total population for the county which gives us the percentage of inhabitants infected. This is useful to see an infection rate normalized by population.
""".strip()
)


def map_cases_by_total(df):
    """Map two: cases by county normalized by population"""
    cases_values = df.cases.unique()
    _min = min(cases_values)
    _max = max(cases_values)
    fig = px.choropleth_mapbox(
        df,
        color="cases",
        range_color=(_min, _max),
        labels={"cases": "Number of Cases"},
        hover_data=["county", "cases"],
        **default_cloropleth_kwargs,
    )
    fig.update_layout(margin={"r": 0, "t": 0, "l": 0, "b": 0})
    return fig


fig_2 = map_cases_by_total(df)
st.plotly_chart(fig_2)
st.markdown(
    """
This map simply shows which counties have the highest number of infections. Counties with higher population densities will naturally have a higher number of cases.
""".strip()
)

## Stat Curves
@st.cache
def plot_state_curve(df, title):
    """plot state curve"""
    # "date", "cases", "deaths"]
    day_df = (
        df.drop(
            columns=["fips", "state", "county", "population", "cases_pop", "deaths_pop"]
        )
        .groupby(by="date")
        .agg(["sum"])
    )
    day_df.columns = {("cases", "sum"): "cases_sum", ("deaths", "sum"): "deaths_sum"}
    fig = go.Figure(
        data=[
            go.Bar(x=day_df.index, y=day_df[("cases", "sum")], name="Cases"),
            go.Bar(x=day_df.index, y=day_df[("deaths", "sum")], name="Deaths"),
        ],
        layout=dict(title_text=title, margin={"r": 0, "t": 0, "l": 0, "b": 0}),
        layout_legend_x=0,
    )
    return fig


st.markdown("""## Growth Curve""")
fig_state_curve = plot_state_curve(df, "Indiana: Cases")
st.plotly_chart(fig_state_curve, use_container_width=True)


## Stat Curves
@st.cache
def plot_state_counties_curve(df):
    """plot state and county data"""
    day_df = (
        df.drop(columns=["fips", "state", "population", "cases_pop", "deaths_pop"])
        .groupby(by="date")
        .agg(["sum"])
    )
    day_df.columns = {
        ("county", "sum"): "county",
        ("cases", "sum"): "cases_sum",
        ("deaths", "sum"): "deaths_sum",
    }
    print(day_df.head())
    fig = go.Figure(
        data=[go.Bar(x=df.index, y=day_df[("cases", "sum")], name="Cases")],
        layout=dict(
            title_text="Indiana Counties", margin={"r": 0, "t": 0, "l": 0, "b": 0}
        ),
        layout_legend_x=0,
    )
    return fig


st.markdown("""## Growth Curve By County: Total Cases""")
# fig_state_counties = plot_state_counties_curve(df)
fig = px.line(
    df,
    x="date",
    y="cases",
    color="county",
    title="Total Number of Cases",
    hover_data=["county", "date", "cases", "cases_pop"],
)
fig.update_layout(dict(margin={"r": 0, "t": 0, "l": 0, "b": 0}))
st.plotly_chart(fig, use_container_width=True)

st.markdown("""## Growth Curve By County: Cases per Capita""")
fig = px.line(
    df,
    x="date",
    y="cases_pop",
    color="county",
    title="Percent of Population Infected",
    hover_data=["county", "date", "cases", "cases_pop"],
)
fig.update_layout(dict(margin={"r": 0, "t": 0, "l": 0, "b": 0}))
st.plotly_chart(fig, use_container_width=True)
