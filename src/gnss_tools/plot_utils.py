#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Plotting functions"""

import pathlib

import numpy as np

# pygmt is required
import pygmt

# if plotly is present,
# we can choose to export alternative functions (look just before EOF)
try:
    import plotly.express as px
except ModuleNotFoundError:
    pass


# some constants
LABELS_INTERVAL = 50


# ground track
# ************

def plot_track_pygmt(sv_id, geo, labels, save):
    """Plot the satellite's ground track using `pygmt`."""
    pygmt.config(
        GMT_THEME='modern',
        FONT_TITLE='9p,Helvetica-Bold,black',
        FONT_ANNOT_PRIMARY='6p,Helvetica-Bold,black',
        FONT_ANNOT_SECONDARY='5p,Helvetica,black'
    )

    # define the map region
    region = [-180., 180., -90., 90.]

    # define map parameters
    fig = pygmt.Figure()

    fig.set_panel(clearance=['w2c', 'e2c', 'n2c', 's2c'])
    fig.coast(
        region=region,
        projection='J17c',  # Miller cylndrical
        # projection='M17c',  # Mercator cylindrical
        # projection='N17c',  # Robinson
        # resolution='h',  # uncomment for hi-res coastlines
        land='darkgray', water='skyblue'
    )
    fig.basemap(frame=['a30f10g30', f'+tGround track of SV {sv_id}'])

    # plot SV positions
    fig.plot(
        x=np.degrees(geo[0]), y=np.degrees(geo[1]),  # geo contains longitiude, latitude
        style='c0.05c', fill='red', pen='black'
    )

    # decimate lists and plot labels
    labels = [x for i, x in enumerate(labels) if i % LABELS_INTERVAL == 0]
    geo[0] = [x for i, x in enumerate(geo[0]) if i % LABELS_INTERVAL == 0]
    geo[1] = [x for i, x in enumerate(geo[1]) if i % LABELS_INTERVAL == 0]
    fig.text(
        x=np.degrees(geo[0]), y=np.degrees(geo[1]),
        text=labels,
        font='4p,Helvetica-Narrow,blue', justify='bl'
    )

    fig.show()
    if save:
        png_file = pathlib.Path(__file__).parents[2]\
                                         .joinpath('plots')\
                                         .joinpath(f'ground_track_{sv_id}.png')
        fig.savefig(png_file, transparent=True)


def plot_track_plotly(sv_id, geo, labels, save):
    """Plot the satellite's ground track using `plotly`."""
    fig = px.scatter_geo(
        lat=np.degrees(geo[1]), lon=np.degrees(geo[0]),
        hover_name=labels,
        title=f'Ground track of SV {sv_id}'
    )

    fig.show()


# skyplot
# *******

def sky_plot_pygmt(sv_id, az_el, labels, save):
    """Plot the satellite's ground track using `pygmt`."""
    pygmt.config(
        GMT_THEME='modern',
        FONT_TITLE='9p,Helvetica-Bold,black',
        FONT_ANNOT_PRIMARY='6p,Helvetica-Bold,black',
        FONT_ANNOT_SECONDARY='5p,Helvetica,black'
    )

    # define the map region
    region = [0., 360., 0., 90.]

    # define map parameters
    fig = pygmt.Figure()

    fig.set_panel(clearance=['w1c', 'e1c', 'n1c', 's1c'])
    fig.basemap(
        region=region,
        projection='P17c+a+fe',
        frame=['xa45f45g45', 'ya30f30g30', f'+tGround track of SV {sv_id}']
    )

    # plot SV positions
    fig.plot(
        x=np.degrees(az_el[0]), y=np.degrees(az_el[1]),
        style='c0.05c', fill='red', pen='black'
    )

    # decimate lists and plot labels
    labels = [x for i, x in enumerate(labels) if i % LABELS_INTERVAL == 0]
    az_el[0] = [x for i, x in enumerate(az_el[0]) if i % LABELS_INTERVAL == 0]
    az_el[1] = [x for i, x in enumerate(az_el[1]) if i % LABELS_INTERVAL == 0]
    fig.text(
        x=np.degrees(az_el[0]), y=np.degrees(az_el[1]),
        text=labels,
        font='4p,Helvetica-Narrow,blue', justify='bl'
    )

    fig.show()
    if save:
        png_file = pathlib.Path(__file__).parents[2]\
                                         .joinpath('plots')\
                                         .joinpath(f'skyplot_{sv_id}.png')
        fig.savefig(png_file, transparent=True)


def sky_plot_plotly(sv_id, az_el, labels, save):
    """Plot the satellite's ground track using `plotly`."""
    fig = px.scatter_polar(
        # r=np.degrees(.5 * np.pi - az_el[1]), theta=np.degrees(az_el[0]),
        r=np.degrees(az_el[1]), theta=np.degrees(az_el[0]),
        range_theta=[0, 360], start_angle=90, direction="clockwise",
        range_r=[90, 0],
        hover_name=labels,
        title=f'Ground track of SV {sv_id}'
    )

    fig.show()


# time series
# ***********

def plot_ts_pygmt(sv_id, data, labels, save):
    """Plot 3D time series using `pygmt`."""
    pygmt.config(
        GMT_THEME='modern',
        FONT_TITLE='9p,Helvetica-Bold,black',
        FONT_ANNOT_PRIMARY='6p,Helvetica-Bold,black',
        FONT_ANNOT_SECONDARY='5p,Helvetica,black'
    )


def plot_ts_plotly(sv_id, data, labels, save):
    """Plot 3D time series using `plotly`."""
    fig = px.scatter_polar(
        # r=np.degrees(.5 * np.pi - az_el[1]), theta=np.degrees(az_el[0]),
        r=np.degrees(data[1]), theta=np.degrees(data[0]),
        range_theta=[0, 360], start_angle=90, direction="clockwise",
        range_r=[90, 0],
        hover_name=labels,
        title=f'Ground track of SV {sv_id}'
    )

    fig.show()


# choose the functions to export
# ******************************

plot_track = plot_track_pygmt
# plot_track = plot_track_plotly
sky_plot = sky_plot_pygmt
# sky_plot = sky_plot_plotly
plot_ts = plot_ts_pygmt
plot_ts = plot_ts_plotly
