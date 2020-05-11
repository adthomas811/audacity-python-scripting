
from argparse import ArgumentParser
from audacity_scripting.core.utils import AudacityScriptingUtils


def main():
    parser = ArgumentParser(description='Join all clips on all tracks.')
    parser.parse_args()

    with AudacityScriptingUtils() as command_runner:
        command_runner.join_all_clips()

if __name__ == '__main__':
    main()
