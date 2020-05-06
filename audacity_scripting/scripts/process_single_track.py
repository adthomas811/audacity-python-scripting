
from audacity_scripting.core.utils import AudacityScriptingUtils


def main():
    track_name = 'L - AT2050'  # track_name = 'SM57'
    # track_name = 'extracted-signal-1'

    command_runner = AudacityScriptingUtils()

    command_runner.join_all_clips()
    command_runner.normalize_tracks_by_clip([track_name])
    # command_runner.compress_tracks_by_clip([track_name])
    # command_runner.normalize_tracks_by_clip([track_name])

    command_runner.close()

if __name__ == '__main__':
    main()
