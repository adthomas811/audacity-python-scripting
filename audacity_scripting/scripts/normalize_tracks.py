
from argparse import ArgumentParser
from audacity_scripting.core.utils import AudacityScriptingUtils


def parse_args():
    parser = ArgumentParser(description='Normalize tracks.')
    parser.add_argument('tracks', dest='tracks', type=str, nargs='+',
                        help='Tracks to be normalized.')
    parser.add_argument('-j', '--join_all_clips', dest='join_all_clips',
                        type=bool, default=True,
                        help='Join all clips on the track before normalizing.')
    parser.add_argument('-p', '--peak_level', dest='peak_level',
                        type=float, default=-1,
                        help='Set the PeakLevel attribute for normalization.')
    parser.add_argument('-g', '--apply_gain', dest='apply_gain',
                        type=bool, default=True,
                        help='Set the ApplyGain attribute for normalization.')
    parser.add_argument('-o', '--rem_dc_offset', dest='rem_dc_offset',
                        type=bool, default=True,
                        help='Set the RemoveDcOffset attribute '
                             'for normalization.')
    parser.add_argument('-s', '--stereo_ind', dest='stereo_ind',
                        type=bool, default=False,
                        help='Set the StereoIndependent attribute '
                             'for normalization.')
    
    return parser.parse_args()


def main():
    args = parse_args()

    command_runner = AudacityScriptingUtils()

    if args.join_all_clips:
        command_runner.join_all_clips()

    command_runner.normalize_tracks_by_clip(args.tracks, args.peak_level,
                                            args.apply_gain,
                                            args.rem_dc_offset,
                                            args.stereo_ind)

    command_runner.close()

if __name__ == '__main__':
    main()
