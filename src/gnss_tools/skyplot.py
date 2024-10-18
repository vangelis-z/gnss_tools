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
LABELS_INTERVAL = 10


# ploting functions
# *****************

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


def sky_plot_matplotlib(sv_id, az_el, labels, save):
    """Plot the satellite's ground track using `matplotlib`."""
    fig = plt.scatter_geo(
        lat=np.degrees(az_el[1]), lon=np.degrees(az_el[0]),
        hover_name=labels,
        title=f'Ground track of SV {sv_id}'
    )
    fig.show()


# check ploting package availability
try:
    import pygmt
    sky_plot = sky_plot_pygmt
except ModuleNotFoundError:
    import matplotlib.pyplot as plt
    sky_plot = sky_plot_matplotlib


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


def validate_observer_position(pos):
    """Validate the observer coordinates given as command line argument."""
    # check for range from geocenter
    grange = np.linalg.norm(pos)
    if grange < 6.3e6:
        # check geographic coordinate ranges
        if not (-180. <= float(pos[0]) <= 360. \
                and -90. <= float(pos[1]) <= 90. \
                and 0. <= float(pos[2]) < 9000.):
            raise argparse.ArgumentError("Geographic coordinates out of range.")
    else:
        # check ECEF coordianates
        if not (abs(float(pos[0])) < 6.4e6 \
                and abs(float(pos[1])) < 6.4e6 \
                and abs(float(pos[2])) < 6.4e6):
            raise argparse.ArgumentError("ECEF coordinates out of range.")

    return pos


def parse_command_line():
    """Parse and validate the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Read satellite positions from a SP3 file and create skyplots.",
        epilog="If available, `pyGMT` is used for plotting.  Otherwise `Matplotlib`."
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
        '-o', '--observer',
        metavar='CRD',
        nargs=3,
        default=[24., 38., 500.],
        type=validate_observer_position,
        help="""the observer's position.
    Either geographic or ECEF coordinates.
    Default values (λ, φ, h): 24, 38, 500"""
    )

    parser.add_argument(
        '-s', '--save',
        action='store_true',
        help="save skyplot to a PNG file"
    )

    return parser.parse_args()


# the driving function
# ********************

def main():
    """The driving function."""
    args = parse_command_line()

    # observer's position
    pos = args.observer
    if np.linalg.norm(pos) < 6.3e7:  # position is given in geographic coordinates
        pos[:-1] = np.radians(pos[:-1])
        pos = list(tools.tool_geocart_GRS80(*pos))

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

    # transform ECEF positions to azimuth/elevation pairs
    ecef = sp3[0][:, 1:-1] * 1000.
    az_el = list(tools.tool_az_ele_h(*pos, *ecef.T))

    # plot
    sky_plot(f'{sv_id[0]}{sv_id[1]:02d}', az_el, time_, args.save)


if __name__ == '__main__':
    main()
