#! /usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import logging
import sys

import gpsdatetime as gpst
import gnsstoolbox.orbits as orb
import gnsstoolbox.gnsstools as tools

import numpy as np
# import matplotlib.pyplot as plt
import folium
import pygmt
import plotly.express as px
# from mpl_toolkits.basemap import Basemap


# some constants
LABELS_INTERVAL = 50


def validate_sv_id(sv_id):
    """Validate the satellite ID given as command line argument."""
    # 1st character should denote the GNSS system
    if not sv_id.startswith(('G', 'R', 'E')):
        raise argparse.ArgumentTypeError("Invalid SV constellation.")

    # the next 2 should be the ID
    try:
        id_ = int(sv_id[1:])  # noqa: F841
    except ValueError:
        raise argparse.ArgumentTypeError("Invalid SV ID.")

    return sv_id


def parse_command_line():
    """Parse and validate the command line arguments."""
    parser = argparse.ArgumentParser()

    parser.add_argument('--sp3',
        metavar='SP3_FILE',
        dest='sp3',
        required=True,
        help='SP3 file; the file to query.')

    parser.add_argument('--sv_id',
        metavar='SV_ID',
        dest='sv_id',
        required=False,
        type=validate_sv_id,
        default = None,
        help='''SV ID; the satellite to plot.
    Use RINEX v.3 notation eg. G09, R17, E21, etc.
    If not given, the first satellite in the file will be used (usually G01).''')

    parser.add_argument('--save',
        required=False,
        default=False,
        action='store_true',
        help='Save ground plot to a PNG file.')

    return parser.parse_args()


def plot_track(sv_id, geo, labels, save):
    """Plot the satellite's ground track using `pygmt`."""
    pygmt.config(GMT_THEME='modern')
    pygmt.config(FONT_TITLE='9p,Helvetica-Bold,black')
    pygmt.config(FONT_ANNOT_PRIMARY='6p,Helvetica-Bold,black')
    pygmt.config(FONT_ANNOT_SECONDARY='5p,Helvetica,black')
    # pygmt.config(TITLE_FONT='12p,Helvetica-Bold,black')
    # pygmt.config(GMT_THEME='modern')

    # define the map region
    region = [-180., 180., -90., 90.]

    # define map parameters
    fig = pygmt.Figure()

    fig.set_panel(clearance=['w1c', 'e1c', 'n1c', 's1c'])
    fig.coast(region=region, projection='J17c', # resolution='h',
              land='darkgray', water='skyblue')
    fig.basemap(frame=['a30f10g30', f'+tGround track of SV {sv_id}'])

    # plot SV positions
    fig.plot(x=np.degrees(geo[0]), y=np.degrees(geo[1]),
             style='c0.05c', fill='red', pen='black')

    # decimate lists and plot labels
    labels = [x for i, x in enumerate(labels) if i % LABELS_INTERVAL == 0]
    geo[0] = [x for i, x in enumerate(geo[0]) if i % LABELS_INTERVAL == 0]
    geo[1] = [x for i, x in enumerate(geo[1]) if i % LABELS_INTERVAL == 0]
    fig.text(x=np.degrees(geo[0]), y=np.degrees(geo[1]),
             text=labels,
             font='4p,Helvetica-Narrow,blue', justify='bl',
            #  fill='black', pen='black'
             )

    fig.show()
    if save:
        fig.savefig(f'ground_track_{sv_id}.png', transparent=True)


def plot_track_2(sv_id, geo, labels, save):
    """Plot the satellite's ground track using `folium`."""
    m = folium.Map(location=[0., 0.], zoom_start=3)

    # Add markers or pop-ups as needed
    # labels = [x if i % LABELS_INTERVAL == 0 else None for i, x in enumerate(labels)]
    for p in range(len(geo[0])):
        m.add_child(folium.Marker(location=[np.degrees(geo[1][p]), np.degrees(geo[0][p])],
                    popup=labels[p]))

    # Save the map as an HTML file
    if save:
        m.save(f'ground_track_{sv_id}.html')


def plot_track_3(sv_id, geo, labels, save):
    """Plot the satellite's ground track using `plotly`."""
    fig = px.scatter_geo(lat=np.degrees(geo[1]),
                         lon=np.degrees(geo[0]),
                         hover_name=labels,
                         title=f'Ground track of SV {sv_id}')
    fig.show()


def plot_track_4(sv_id, geo, labels, save):
    """Plot the satellite's ground track using `plotly`."""
    fig = px.scatter_map(lat=np.degrees(geo[1]),
                         lon=np.degrees(geo[0]),
                         hover_name=labels,
                         zoom=2,
                         map_style='satellite-streets',
# 'basic',
# 'carto-darkmatter', 'carto-darkmatter-nolabels', 'carto-positron', 'carto-positron-nolabels',
# 'carto-voyager', 'carto-voyager-nolabels', 'dark', 'light', 'open-street-map', 'outdoors',
# 'satellite', 'satellite-streets', 'streets', 'white-bg'
                         title=f'Ground track of SV {sv_id}')
    fig.show()


def main():
    """The driving function."""
    args = parse_command_line()

    # load the SP3 file
    orbit = orb.orbit()
    failure = orbit.loadSp3(args.sp3)
    if failure:
        logging.error(f"File \'{args.sp3}\' not found.  Exiting.")
        sys.exit(-1)

    # get the SV info
    try:
        sv_id = (args.sv_id[0], int(args.sv_id[1:]))
    except TypeError:
        # most likely sv_id is None, so we use the 1st satellite in the file
        sv_id = (orbit.ListSat[0][0], int(orbit.ListSat[0][1:]))

    # get SV positions
    sp3 = orbit.getSp3(*sv_id)

    # time (to use as labels)
    time_ = [gpst.gpsdatetime(mjd=x).st_iso_epoch() for x in sp3[0][:, 0]]

    # transform ECEF positions to geographic
    ecef = sp3[0][:, 1:-1] * 1000.
    geo = list(tools.toolCartGeoGRS80(*ecef.T))

    # plot
    plot_track(f'{sv_id[0]}{sv_id[1]:02d}', geo, time_, args.save)


if __name__ == "__main__":
    main()
