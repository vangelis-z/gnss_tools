#! /usr/bin/env python
# -*- coding: utf-8 -*-

"""Orbit functions."""

import logging
import sys

import numpy as np

# import gpsdatetime as gpst
# import gnsstoolbox.orbits as orb
# import gnsstoolbox.gnsstools as tools


# some constants
MAX_PRN_OR_SLOT = 40

EXIT_CODE_INVALID_FILE = -99
EXIT_CODE_FILE_ERROR = -98

EXIT_CODE_INVALID_SV_ID = -89
EXIT_CODE_INVALID_CONSTELLATION = -88
EXIT_CODE_INVALID_PRN_OR_SLOT = -87
EXIT_CODE_SV_MISSING = -86

EXIT_CODE_NOT_COMMON_SATELLITES = -79


logging.basicConfig(
    level=logging.ERROR,
    style='{',
    format='{levelname}: {name} ({funcName}) [{lineno}]:  {message}'
)
logger = logging.getLogger(__name__)


def _first_nav_element(nav_data):
    """Return the first non None element of a nested list of NAV_data, or None."""
    return next((item for sublist in nav_data for item in sublist if item is not None), None)


def load_orbit(orbit, filename):
    """Load a RINEX NAV or SP3 orbit from filename.

    Updates the gnsstoolbox.orbits.orbit object that was passed as the first argument.
    Returns the exit code of the loading function.

    The orbit loading functions exit codes are:
    * None: successful loading of the orbit (RINEX NAV),
    * 0: successful loading of the orbit (SP3),
    * -1: filename is empty string,
    * -2: missing file,
    * -3: unreadable file, and
    * -4: invalid file format.

    Moreover, loadRinexN will succeed for all RINEX files (OBS, CLK, etc.).
    We avoid this by checking for valid NAV_data in the file, and acting accordingly.
    """
    retries = 0
    max_retries = 2

    exit_code = orbit.loadSp3(filename)  # 1st try is for SP3

    while retries < max_retries:
        if not exit_code:  # 0 and None are False
            break
            # return orbit
        elif exit_code == -4:  # filename is not SP3; trying RINEX NAV
            exit_code = orbit.loadRinexN(filename)
            retries += 1
        else:
            logger.error("Either the file is empty, or missing.  Exiting.")
            sys.exit(EXIT_CODE_FILE_ERROR)

    if exit_code is None:  # a RINEX file **seems** to be loaded
        for constellation in ['G', 'R', 'E']:
            nav_data = eval(f'orbit.NAV_data{constellation}')  # variable representing the attribute
            nav_element = _first_nav_element(nav_data) # get the first non None item, if any
            if nav_element is not None:  # a valid RINEX NAV file
                break
            else:  # not a valid RINEX NAV file
                logger.error("File is invalid.  Exiting.")
                sys.exit(EXIT_CODE_INVALID_FILE)

    return exit_code


def get_sv_id(orbit):
    """Return the id of the 'first' satellite encountered in the file.

    The definition of the 'first' satellite is scketchy, since the order that gnsstoolbox stores
    data is not clear.
    For SP3 orbits, gnsstoolbox provides a list of satellites.  We get the first item.
    For RINEX NAV orbits, we first have to check for the constellation (GPS, GLONASS or Galileo),
    and then to find the first satellite.
    """
    if orbit.type == 'sp3':  # this is easy
        return orbit.ListSat[0]

    elif orbit.type == 'nav':  # we have to check all constellations
        for constellation in ['G', 'R', 'E']:
            nav_data = eval(f'orbit.NAV_data{constellation}')  # variable representing the attribute
            nav_element = _first_nav_element(nav_data) # get the first non None item
            if nav_element:
                return f'{nav_element.const}{nav_element.PRN:02d}'

    # if everything fails, the file is invalid
    logger.error("No NAV data information in the file.  Exiting")
    sys.exit(EXIT_CODE_INVALID_FILE)


def find_common_sv(nav, sp3):
    """Return the id of the 'first' common satellite encountered in the files.

    We find the first satellite in the RINEX NAV file, and check if it's present in the SP3 file.
    If not, we try the second satellite in the RINEX NAV file, and so on, until we succeed.
    """
    for constellation in ['G', 'R', 'E']:  # we'll check all constellations
        nav_data = eval(f'nav.NAV_data{constellation}')  # variable representing the attribute
        nav_elements = [item for sublist in nav_data for item in sublist if item is not None]
        if nav_elements:  # the list is not empty
            for nav_element in nav_elements:
                sv_id = f'{nav_element.const}{nav_element.PRN:02d}'  # construct sv_id
                if sv_id in sp3.ListSat:  # check its existence in the SP3 file
                    return sv_id

    # if we don't find a match
    logger.error("No NAV data information in the file.  Exiting")
    sys.exit(EXIT_CODE_NOT_COMMON_SATELLITES)


def get_epochs(orbit, sv_id):
    """Return a list of epochs (MJDs) on which we have information for the specific satellite."""
    # SP3 orbits have EpochList attribute (list of gpsdatetime.gpsdatetime objects)
    if orbit.type == 'sp3':
        return {t.mjd for t in orbit.EpochList}  # set comprehension since EpochList has duplicates

    # RINEX NAV has no EpochList attribute
    elif orbit.type == 'nav':
        mjds = []
        constellation = sv_id[0]  # get the GNSS system
        nav_data = f'orbit.NAV_data{constellation}'  # variable representing the attribute
        for epoch in eval(nav_data):  # evaluating nav_data returns the corresponding data
            for element in epoch:
                if element.PRN == int(sv_id[1:]):  # identify the corresponding element
                    mjds.append(element.mjd)
        return mjds


def get_sv_states(orbit, sv_id, mjds):
    """Read a gnsstoolbox.orbits.orbit object and return satellite states.

    Returns a 2D numpy.array with rows [t, x, y, z, bias].

    sv_id must be in RINEX v.3 notation; eg. G09, R14, E21, etc.
    mjds is an iterable containing the times (in MJD) for which the state is to be retreived.
    """
    # split sv_id into its components
    try:
        constellation = sv_id[0]
        prn = int(sv_id[1:])

        if constellation not in ['G', 'R', 'E']:
            logger.error("Constellation is invalid.  Exiting")
            sys.exit(EXIT_CODE_INVALID_CONSTELLATION)
        if prn > MAX_PRN_OR_SLOT:
            logger.error("Invalid PRN or slot number.  Exiting")
            sys.exit(EXIT_CODE_INVALID_PRN_OR_SLOT)

    except TypeError:
        logger.error("sv_id is invalid.  Exiting")
        sys.exit(EXIT_CODE_INVALID_SV_ID)

    # get satellite states; note the use of the unpack operator (*)
    states = np.array([[t, *orbit.calcSatCoord(constellation, prn, t)] for t in mjds])

    # check for validity
    # if RINEX NAV, calcSatCoord returns an empty list for missing satellites
    if orbit.type == 'nav' and len(states) == 0:
        logger.error(f"Satellite \'{sv_id}\' not in file.  Exiting.")
        sys.exit(EXIT_CODE_SV_MISSING)

    # if SP3, drop rows with numpy.nan values (missing epoch or missing satellite)
    if orbit.type == 'sp3':
        mask = ~np.isnan(states).any(axis=1)
        states = states[mask]
        if len(states) == 0:
            logger.error(f"Satellite \'{sv_id}\' not in file.  Exiting.")
            sys.exit(EXIT_CODE_SV_MISSING)

    return np.array(states)


def concatenate_states(states0, states1):
    """Given two arrays of states, concatenate them on their common epochs."""
    # extract the common columns (epochs) from both state arrays
    epochs0 = states0[:, 0]
    epochs1 = states1[:, 0]

    # find indices in state arrays on the same epoch
    matched_epochs0 = []
    matched_epochs1 = []
    for i, val in enumerate(epochs0):  # iterate through the epoch column of states0
        match = np.where(epochs1 == val)[0]  # find matching rows in states1
        if len(match) > 0:
            matched_epochs0.append(i)
            matched_epochs1.append(match[0])

    # select the matched rows from both state arrays
    matched_states0 = states0[matched_epochs0, :]
    matched_states1 = states1[matched_epochs1, :]

    # concatenate the two arrays horizontally, excluding the epochs column from states1
    result = np.hstack((matched_states0, matched_states1[:, 1:]))

    return result

