#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""CLI validation functions"""

import argparse

import numpy as np


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
