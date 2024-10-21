#! /usr/bin/env python
# -*- coding: utf-8 -*-


import argparse

import gpsdatetime as gpst
import gnsstoolbox.orbits as orbits
import gnsstoolbox.gnsstools as tools

from src.gnss_tools import cli_utils
from src.gnss_tools import orbit_tools
from src.gnss_tools import plot_utils


def parse_command_line():
    """Parse and validate the command line arguments."""
    parser = argparse.ArgumentParser(
        description="Read satellite positions from a SP3 or NAV RINEX file and plot ground tracks.",
        epilog="The S/W currently uses `pyGMT` for the plotting, but it's `plotly`-ready."
    )

    parser.add_argument(
        'orbit',
        help="the file to query"
    )

    parser.add_argument(
        '--sv_id',
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

    # load the orbit file
    orbit = orbits.orbit()
    orbit_tools.load_orbit(orbit, args.orbit)

    # get the satellite info
    sv_id = args.sv_id
    if sv_id is None:
        sv_id = orbit_tools.get_sv_id(orbit)

    # get the epochs (MJD)
    mjds = orbit_tools.get_epochs(orbit, sv_id)
    labels = [gpst.gpsdatetime(mjd=t).st_iso_epoch() for t in mjds]  # for plotting

    # get SV states (positions)
    states = orbit_tools.get_sv_states(orbit, sv_id, mjds)

    # transform ECEF positions to geographic
    ecef = states[:, 1:-1]
    geo = list(tools.toolCartGeoGRS80(*ecef.T))  # note use of unpack operator (*)

    # plot
    plot_utils.plot_track(sv_id, geo, labels, args.save)


if __name__ == '__main__':
    main()
