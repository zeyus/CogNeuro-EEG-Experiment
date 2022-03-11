# Authors: Christopher J. Bailey <cjb@cfin.au.dk>
# License: BSD (3-clause)

import json
import numpy as np
import os.path as op
from sys import argv
from collections import OrderedDict


def montage_to_mapping_triux(fname_mon):
    """Create a mapping between EEG channel index and 10/20 name.

    The channel index is given by the row number.

    Parameters
    ----------
    fname_mon : str
        Full path to the .txt-file containing an EEG montage (easycap-style)

    Returns
    -------
    mapping : dict
        The mapping between EEG channel index- and 10/20-based names.
    """
    montage = np.genfromtxt(fname_mon, dtype='str', skip_header=1)
    mapping = OrderedDict()
    for ii, row in enumerate(montage):
        mapping['EEG{:03d}'.format(ii + 1)] = row[0]
    return mapping


def read_eeg_mapping_triux(fname_map='easycap-Aar75-mapping'):
    """Read a mapping between Triux-style EEG channel names and 10/20 equivs.

    Parameters
    ----------
    fname_map : str
        EITHER: Full path to the .json-file containing an ordered mapping
        between original channel names and the replacements.
        OR: Name of existing mapping (default: 'easycap-Aar75-mapping')

    Returns
    -------
    mapping : dict
        The mapping between EEG channel index- and 10/20-based names.
    """
    try:
        with open(op.join(op.dirname(__file__), 'data', fname_map + '.json'),
                  encoding='utf-8') as fp:
            return json.load(fp)
    except FileNotFoundError:
        with open(fname_map, encoding='utf-8') as fp:
            return json.load(fp)


if __name__ == '__main__':
    if not op.exists(argv[1]):
        raise RuntimeError('No such file: {:s}'.format(argv[1]))
    if op.exists(argv[2]):
        raise RuntimeError('File already exists: {:s}'.format(argv[2]))

    mapping = montage_to_mapping_triux(argv[1])
    with open(argv[2], 'wb') as fp:
        json.dump(mapping, fp)
