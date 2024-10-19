#! /usr/bin/env python
# -*- coding: utf-8 -*-


import argparse
import logging
import sys

import gpsdatetime as gpst
import gnsstoolbox.orbits as orb
import gnsstoolbox.gnsstools as tools

from ..src.gnss_tools import cli_utils
from ..src.gnss_tools import plot_utils


# some constants
EXIT_CODE_FILE_NOT_FOUND = -99
EXIT_CODE_SV_MISSING = -98
LABELS_INTERVAL = 50


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
        type=cli_utils.validate_sv_id,
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
    plot_utils.plot_track(f'{sv_id[0]}{sv_id[1]:02d}', geo, time_, args.save)


if __name__ == '__main__':
    main()
