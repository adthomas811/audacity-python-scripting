
from argparse import ArgumentParser
from audacity_scripting.core.utils import AudacityScriptingUtils
from copy import deepcopy


def parse_args():
    parser = ArgumentParser(description='Mix and render two tracks.')
    parser.add_argument('track_names', metavar='track_name', type=str, nargs=2,
                        help='Tracks to be mixed and rendered.')
    parser.add_argument('-g', '--track_gains', dest='track_gains',
                        type=int, nargs=2, action='append',
                        help='')

    return parser.parse_args()


def main():
    # Update script to mix and render multiple tracks, not just two
    args = parse_args()

    track_gains_list = []
    if args.track_gains is None:
        track_gains_list = [[0, 0]]
    else:
        track_gains_list = deepcopy(args.track_gains)

    with AudacityScriptingUtils() as command_runner:
        track_starting_gain_dict = {}
        for track_name in args.track_names:
            track_starting_gain = command_runner.get_track_gain(track_name)
            track_starting_gain_dict[track_name] = track_starting_gain

        for track_gains in track_gains_list:
            new_track_name = ''
            for track_num in range(len(args.track_names)):
                track_name = args.track_names[track_num]
                track_gain = track_gains[track_num]
                command_runner.set_track_gain(track_name, track_gain)
                new_track_name += '{}: {} '.format(track_name, track_gain)

            command_runner.mix_and_render_to_new_track(args.track_names)

            new_track_num = len(command_runner.get_tracks_info()) - 1
            command_runner.rename_track_by_num(new_track_name.rstrip(),
                                               new_track_num)

        for track_name in args.track_names:
            command_runner.set_track_gain(track_name,
                                          track_starting_gain_dict[track_name])

if __name__ == '__main__':
    main()
