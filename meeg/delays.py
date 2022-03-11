from mne import find_events, pick_channels, pick_types, pick_events, Epochs
from mne.io import Raw, BaseRaw, read_raw_fif, read_raw_brainvision
from six import string_types
import numpy as np


def _next_crossing(a, offlevel, onlimit):
    try:
        trig = np.where(np.abs(a - offlevel) >=
                        np.abs(onlimit))[0][0]
    except IndexError:
        raise RuntimeError('ERROR: No analogue trigger found within %d '
                           'samples of the digital trigger' % len(a))
    else:
        return(trig)


def _find_next_analogue_trigger(ana_data, ind, offlevel, onlimit,
                                maxdelay_samps=100):
    return _next_crossing(ana_data[ind:ind + maxdelay_samps].squeeze(),
                          offlevel, onlimit)


def _find_analogue_trigger_limit(ana_data):
    return 2.5*ana_data.mean()


def _find_analogue_trigger_limit_sd(raw, events, anapick, tmin=-0.2, tmax=0.0,
                                    sd_limit=5.):
    epochs = Epochs(raw, events, tmin=tmin, tmax=tmax, picks=anapick,
                    baseline=(None, 0), preload=True)
    epochs._data = np.sqrt(epochs._data**2)  # RECTIFY!
    # ave = epochs.average(picks=[0])
    ave = np.mean(np.mean(epochs.get_data(), axis=2))
    std = np.mean(np.std(epochs.get_data(), axis=2))
    return(ave, sd_limit * std)


def _filter_events_too_close(events, min_samps):
    """Filter out events based on proximity to previous events.

    Potentially useful when presenting rapid stimuli, and want
    e.g. delay estimation to be based on the first in a block only.
    """
    filtered_events = []
    prev_eve = 0
    for eve in events:
        if eve[0] - prev_eve >= min_samps:
            filtered_events.append(eve)
        prev_eve = eve[0]
    print('{} events remain after filtering.'.format(len(filtered_events)))
    return(np.array(filtered_events))


def extract_delays(raw, stim_chan='STI101', misc_chan='MISC001',
                   trig_codes=None, epoch_t_max=0.5,
                   baseline=(-0.100, 0), l_freq=None,
                   h_freq=None, plot_figures=True, crop_plot_time=None,
                   time_shift=None, min_separation=None,
                   return_values='delays', trig_limit_sd=5.,
                   plot_title_str=None):
    """Estimate onset delay of analogue (misc) input relative to trigger

    Parameters
    ==========
    raw : str | Raw
        File name (string), or an instance of Raw.
    stim_chan : str
        Default stim channel is 'STI101'
    misc_chan : str
        Default misc channel is 'MISC001' (default, usually visual)
    trig_codes : int | list of int | None
        Trigger values to compare analogue signal to. If None (default), all
        trigger codes will be used.
    baseline : tuple of int
        Pre- and post-trigger time to calculate trigger limits from.
        Defaults to (-0.100, 0.)
    epoch_t_max : float
        Time after trigger to include in epoch (relevant for plotting).
        Defaults to 0.5 sec
    l_freq : float | None
        Low cut-off frequency in Hz. Uses mne.io.Raw.filter.
    h_freq : float | None
        High cut-off frequency in Hz. Uses mne.io.Raw.filter.
    plot_figures : bool
        Plot histogram and "ERP image" of delays (default: True)
    plot_title_str : str | None
        If None (default), the name of the channel is plotted above the
        epochs-image. Alternatively, enter a string.
    crop_plot_time : tuple, optional
        A 2-tuple with (tmin, tmax) being the limits to plot in the figure
    time_shift : None | float
        Shift event markers by specified amount of time in seconds (or None)
    min_separation : None | float
        Minimum allowed separation of successive triggers used for delay
        estimation (in seconds).
    return_values : str
        What should the function return? Valid options are 'delays' for an
        array of delay values in milliseconds, 'stats' for delay value
        statistics on all triggers considered, or 'events' for a timing-
        corrected trigger events array (mne-style). Note that trigger codes
        note specified in `trig_codes` are removed from the events array.
        Defaults to 'delays'.
    trig_limit_sd : float
        For debugging only.

    Returns (see `return_values`-parameter)
    -------
    delays : ndarray
        Estimated delay values (in ms) for each trigger.
    stats : dict
        Delay value statitics (in ms) for all triggers.
    events : n x 3 ndarray
        Corrected events matrix for triggers in `trig_codes`. NB: The second
        column of the array contains the amount of samples used for correction.
    """
    if return_values not in ['events', 'delays', 'stats']:
        raise ValueError('Invalid return_value: {}'.format(return_values))

    if isinstance(raw, string_types):
        if raw.endswith('fif'):
            raw = read_raw_fif(raw, preload=True)
        elif raw.endswith('vhdr'):
            raw = read_raw_brainvision(raw, misc=[misc_chan])
    elif isinstance(raw, BaseRaw):
        raw.load_data()  # does nothing if data already (pre)loaded
    else:
        raise ValueError('First argument should either be a Raw object, '
                         'or a string containing the path to a file.')

    if l_freq is not None or h_freq is not None:
        picks = pick_types(raw.info, misc=True)
        raw.filter(l_freq, h_freq, picks=picks)

    include_trigs = trig_codes  # do some checking here!

    # for MEG, use 2 ms, for EEG it's shorter!
    min_duration = 0.002 if isinstance(raw, Raw) else 0
    events = pick_events(find_events(raw, stim_channel=stim_chan,
                                     min_duration=min_duration),
                         include=include_trigs)
    if min_separation is not None:
        events = _filter_events_too_close(
            events, int(min_separation * raw.info['sfreq']))
    if time_shift is not None:
        events[:, 0] += int(time_shift * raw.info['sfreq'])

    delay_samps = np.zeros(events.shape[0], dtype=events.dtype)
    pick = pick_channels(raw.info['ch_names'], include=[misc_chan])

    ana_data = np.sqrt(raw._data[pick, :].squeeze()**2)  # rectify!

    # don't use all events for trigger level determination (memory-heavy)
    decim_eve = 1
    if len(events) > 300:
        decim_eve = int(len(events) / 300.)
        print('Warning: Using only every {}th event for trigger limit '
              'calculations'.format(decim_eve))
    # from IPython.core.debugger import set_trace; set_trace()
    tmin, tmax = baseline
    offlevel, onlimit = \
        _find_analogue_trigger_limit_sd(raw, events[::decim_eve], pick,
                                        tmin=tmin, tmax=tmax,
                                        sd_limit=trig_limit_sd)

    for row, unpack_me in enumerate(events):
        ind, _, after = unpack_me
        raw_ind = ind - raw.first_samp  # really indices into raw!
        try:
            anatrig_ind = _find_next_analogue_trigger(ana_data, raw_ind,
                                                      offlevel, onlimit,
                                                      maxdelay_samps=1000)
        except RuntimeError as e:
            # assume data collection ended after event, but before response
            # continue silently
            if row == (len(events) - 1):
                continue
            extra_info = ('Event #{:d} of category {:d}, at {:d} samples into '
                          'the file'.format(row, after, raw_ind))
            raise RuntimeError('{}\n{}'.format(e, extra_info))
        delay_samps[row] = anatrig_ind

        delays = delay_samps / raw.info['sfreq'] * 1.e3

    if plot_figures:
        import matplotlib.pyplot as plt
        plt.figure()
        evoked = True
        hist = True
        axes_list = []

        # image
        axes_list.append(plt.subplot2grid(
            (3, 14), (0, 0), colspan=10 if hist else 14,
            rowspan=2 if evoked else 3))
        # evoked
        axes_list.append(plt.subplot2grid(
            (3, 14), (2, 0), colspan=10 if hist else 14, rowspan=1))
        # colorbar
        axes_list.append(plt.subplot2grid((3, 14), (2, 10),
                                          colspan=1, rowspan=1))
        # histogram
        axes_list.append(plt.subplot2grid(
            (3, 14), (0, 10), colspan=4, rowspan=2))

        axes_list[-1].hist(delays, orientation=u'horizontal')
        axes_list[-1].set_title('Delay values (ms)')
        axes_list[-1].yaxis.tick_right()

        if crop_plot_time is not None:
            if not (isinstance(crop_plot_time, (list, tuple)) and
                    len(crop_plot_time) == 2):
                raise RuntimeError('crop_plot_time must be length-2 tuple')
            epo_t_min, epo_t_max = crop_plot_time
        else:
            epo_t_min, epo_t_max = -0.2, 0.5
        epochs = Epochs(raw, events, tmax=epo_t_max, preload=True)
        epochs.crop(epo_t_min, epo_t_max)
        # This calls plt.show, which in inline-plotting settings causes the
        # figure to be burnt in. All axes mods have to happen prior to it.
        epochs.plot_image(pick, axes=axes_list[:3], title=plot_title_str)

    if return_values == 'events':
        events[:, 0] += delay_samps  # these are of same dtype
        events[:, 1] = delay_samps  # might as well keep the correction terms!
        return(events)
    elif return_values == 'delays':
        return(delays)
    elif return_values == 'stats':
        stats = dict()
        stats['mean'] = np.mean(delays)
        stats['std'] = np.std(delays)
        stats['median'] = np.median(delays)
        stats['q10'] = np.percentile(delays, 10.)
        stats['q90'] = np.percentile(delays, 90.)
        stats['max_amp'] = np.max(epochs._data[:, pick, :])  # ovr epochs&times
        stats['min_amp'] = np.min(epochs._data[:, pick, :])  # ovr epochs&times
        return(stats)



if __name__ == '__main__':
    from stormdb.access import Query
    proj_name = 'MEG_service'
    subj_id = '0032'
    qy = Query(proj_name)

    series = qy.filter_series('audvis*', subjects=subj_id)
    cur_series = series[0]

    delays = extract_delays(cur_series, stim_chan='STI101',
                            misc_chan='MISC001', trig_codes=[2],
                            plot_figures=True)
