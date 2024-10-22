#! /usr/bin/env python
# -*- coding: utf-8 -*-


import argparse

import numpy as np

import gpsdatetime as gpst
import gnsstoolbox.orbits as orbits
import gnsstoolbox.gnsstools as tools

from src.gnss_tools import cli_utils
from src.gnss_tools import orbit_tools
from src.gnss_tools import plot_utils


def parse_command_line():
    """Parse and validate the command line arguments."""
    parser = argparse.ArgumentParser(
        description="""Read satellite positions from a SP3 file and a RINEX NAV file.
Interpolate the RINEX NAV ephemeris at times of the SP3 file and plot satellite state differences.
""",
        epilog="The S/W currently uses `pyGMT` for the plotting, but it's `plotly`-ready."
    )

    parser.add_argument(
        'sp3',
        type=cli_utils.validate_sp3,
        help="the reference orbit"
    )

    parser.add_argument(
        'nav',
        type=cli_utils.validate_nav,
        help="the test orbit"
    )

    parser.add_argument(
        '--sv_id',
        type=cli_utils.validate_sv_id,
        help="""the satellite to test.
    Use RINEX v.3 notation eg. G09, R17, E21, etc.
    If not given, the first common satellite in the files will be used (usually G01)"""
    )

    parser.add_argument(
        '-t', '--type',
        default='local',
        choices=['body', 'ecef', 'local'],
        help="""what to plot.
    For the time being, only 'ecef' and 'local' plots are supported.
    Default: '%(default)s'."""
    )

    parser.add_argument(
        '-s', '--save',
        action='store_true',
        help="save the plot to a PNG file"
    )

    return parser.parse_args()


def main():
    """The driving function."""
    args = parse_command_line()

    # load the orbit files
    sp3 = orbits.orbit()
    orbit_tools.load_orbit(sp3, args.sp3)
    nav = orbits.orbit()
    orbit_tools.load_orbit(nav, args.nav)

    # get the satellite info
    sv_id = args.sv_id
    if sv_id is None:  # try to find a common satellite
        sv_id = orbit_tools.find_common_sv(nav, sp3)

    # get the epochs (MJD) from the SP3 file
    mjds = orbit_tools.get_epochs(sp3, sv_id)

    # get SV states (positions)
    sp3_states = orbit_tools.get_sv_states(sp3, sv_id, mjds)
    nav_states = orbit_tools.get_sv_states(nav, sv_id, mjds)

    # concatenate the two state arrays
    # time, x0, y0, z0, bias0, x1, y1, z1, bias1
    states = orbit_tools.concatenate_states(sp3_states, nav_states)

    # create labels for plotting
    labels = [gpst.gpsdatetime(mjd=t).st_iso_epoch() for t in states[:, 0]]

    # compute local coordinates
    # for each epoch the origin of the local frame is the state from the SP3 file
    local = np.array([tools.toolCartLocGRS80(*row[1:4], *row[5:-1]) for row in states])
    # and concatenate with the states
    # time, x0, y0, z0, bias0, x1, y1, z1, bias1, e, n, u
    states = np.hstack((states, local))

    # compute the differences
    diffs = np.array(
        [[row[1] - row[5], row[2] - row[6], row[3] - row[7], row[4] - row[8]] for row in states]
    )
    # and concatenate with the states
    # time, x0, y0, z0, bias0, x1, y1, z1, bias1, e, n, u, dx, dy, dz, dbias
    states = np.hstack((states, diffs))

    # plot
    if args.type == 'local':
        plot_utils.plot_ts(
            sv_id, states[:, np.array([9, 10, 11, 15])],
            labels, args.type,
            args.save
        )
    elif args.type == 'ecef':
        plot_utils.plot_ts(sv_id, states[:, 12:], labels, args.type, args.save)


if __name__ == '__main__':
    main()
