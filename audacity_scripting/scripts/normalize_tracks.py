
from argparse import ArgumentParser
from audacity_scripting import LOGGER_NAME
from audacity_scripting.core.utils import AudacityScriptingUtils
import logging


def parse_args():
    parser = ArgumentParser(description='Normalize tracks by label.')
    parser.add_argument('tracks', type=str, nargs='+',
                        help='Tracks to be normalized.')
    parser.add_argument('-p', '--peak_level', dest='peak_level',
                        type=float, default=-1,
                        help='Set the PeakLevel attribute for '
                             'normalization. Default: -1')
    parser.add_argument('-g', '--apply_gain', dest='apply_gain',
                        type=bool, default=True,
                        help='Set the ApplyGain attribute for '
                             'normalization. Default: True')
    parser.add_argument('-o', '--rem_dc_offset', dest='rem_dc_offset',
                        type=bool, default=True,
                        help='Set the RemoveDcOffset attribute '
                             'for normalization. Default: True')
    parser.add_argument('-s', '--stereo_ind', dest='stereo_ind',
                        type=bool, default=False,
                        help='Set the StereoIndependent attribute '
                             'for normalization. Default: False')

    return parser.parse_args()


def main():
    logger = logging.getLogger(LOGGER_NAME)
    logger.info('Running Script: Normalize Tracks')

    args = parse_args()

    with AudacityScriptingUtils() as command_runner:
        command_runner.normalize_tracks_by_label(args.tracks,
                                                 args.peak_level,
                                                 args.apply_gain,
                                                 args.rem_dc_offset,
                                                 args.stereo_ind)

if __name__ == '__main__':
    main()
