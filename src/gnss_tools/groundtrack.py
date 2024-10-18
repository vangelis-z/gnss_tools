#! /usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import logging
import pathlib
import sys

import numpy as np

import gpsdatetime as gpst
import gnsstoolbox.orbits as orb
import gnsstoolbox.gnsstools as tools


# some constants
EXIT_CODE_FILE_NOT_FOUND = -99
EXIT_CODE_SV_MISSING = -98
LABELS_INTERVAL = 50


# ploting functions
# *****************

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

    fig.set_panel(clearance=['w1c', 'e1c', 'n1c', 's1c'])
    fig.coast(
        region=region,
        projection='J17c',
        # resolution='h',
        land='darkgray', water='skyblue'
    )
    fig.basemap(frame=['a30f10g30', f'+tGround track of SV {sv_id}'])

    # plot SV positions
    fig.plot(
        x=np.degrees(geo[0]), y=np.degrees(geo[1]),
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


# check ploting package availability
try:
    import plotly.express as px
    plot_track = plot_track_plotly
except ModuleNotFoundError:
    import pygmt
    plot_track = plot_track_pygmt


# functions for the command line parser
# *************************************

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
    parser = argparse.ArgumentParser(
        description="Read satellite positions from a SP3 file and plot ground tracks.",
        epilog="The S/W currently uses `pyGMT` for the plotting, but it's `plotly`-ready."
    )

    parser.add_argument(
        'sp3',
        help="the file to query"
    )

    parser.add_argument('--sv_id',
        type=validate_sv_id,
        help="""the satellite to plot.
    Use RINEX v.3 notation eg. G09, R17, E21, etc.
    If not given, the first satellite in the file will be used (usually G01)"""
    )

    parser.add_argument(
        '-s', '--save',
        action='store_true',
        help="save groundplot to a PNG file"
    )

    return parser.parse_args()


# the driving function
# ********************

def main():
    """The driving function."""
    args = parse_command_line()

    # load the SP3 file
    orbit = orb.orbit()
    failure = orbit.loadSp3(args.sp3)
    if failure:
        logging.error(f"File \'{args.sp3}\' not found.  Exiting.")
        sys.exit(EXIT_CODE_FILE_NOT_FOUND)

    # get the SV info
    try:
        sv_id = (args.sv_id[0], int(args.sv_id[1:]))
    except TypeError:
        # most likely sv_id is None, so we use the 1st satellite in the file
        sv_id = (orbit.ListSat[0][0], int(orbit.ListSat[0][1:]))

    # get SV positions
    sp3 = orbit.getSp3(*sv_id)
    # if requested satellite is not present (ie. the length of the orbit is 0), exit
    if sp3[1] == 0:
        logging.error(f"Satellite \'{args.sv_id}\' not in file.  Exiting.")
        sys.exit(EXIT_CODE_SV_MISSING)

    # time (to use as labels)
    time_ = [gpst.gpsdatetime(mjd=x).st_iso_epoch() for x in sp3[0][:, 0]]

    # transform ECEF positions to geographic
    ecef = sp3[0][:, 1:-1] * 1000.
    geo = list(tools.toolCartGeoGRS80(*ecef.T))

    # plot
    plot_track(f'{sv_id[0]}{sv_id[1]:02d}', geo, time_, args.save)


if __name__ == '__main__':
    main()
