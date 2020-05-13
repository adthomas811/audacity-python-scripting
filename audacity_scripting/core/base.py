
# Original connection code source:
# https://github.com/audacity/audacity/blob/ \
#                          master/scripts/piped-work/pipe_test.py

from audacity_scripting import LOGGER_NAME
import json
import logging
import os
import sys

# 1. Log raised exceptions to log file
# 2. Raise not implemented exception for linux or mac

logger = logging.getLogger(LOGGER_NAME)


class ToSrvPipeNotExist(Exception):
    pass


class FromSrvPipeNotExist(Exception):
    pass


class CommandAssertFailure(Exception):
    pass


class AudacityScriptingBase(object):

    def __init__(self):
        if sys.platform == 'win32':
            logger.info('Running on windows')
            toname = r'\\.\pipe\ToSrvPipe'
            fromname = r'\\.\pipe\FromSrvPipe'
            self.EOL = '\r\n\0'
        else:
            logger.info('Running on linux or mac')
            toname = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
            fromname = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
            self.EOL = '\n'

        logger.info('Write to "' + toname + '"')
        if not os.path.exists(toname):
            raise ToSrvPipeNotExist(' ..does not exist. Ensure Audacity '
                                    'is running with mod-script-pipe.')

        logger.info('Read from "' + fromname + '"')
        if not os.path.exists(fromname):
            raise FromSrvPipeNotExist(' ..does not exist. Ensure Audacity '
                                      'is running with mod-script-pipe.')

        logger.info('Both pipes exist. Good.')

        self.tofile = open(toname, 'wt+')
        logger.info('File to write to has been opened')
        self.fromfile = open(fromname, 'rt')
        logger.info('File to read from has now been opened too')

    def close(self):
        self.tofile.close()
        self.fromfile.close()

    def _send_command(self, command):
        self.tofile.write(command + self.EOL)
        self.tofile.flush()

    def _get_response(self):
        result = ''
        line = ''
        while line != '\n':
            result += line
            line = self.fromfile.readline()
        self._assert_command_success(result.split('\n')[-2])
        return result

    def _assert_command_success(self, result_string):
        if result_string != 'BatchCommand finished: OK':
            raise CommandAssertFailure('Command finished with the '
                                       'status: {}'.format(result_string))

    def run_command(self, command):
        logger.info('Command: {}'.format(command))
        self._send_command(command)
        return self._get_response()

    def get_json(self, result):
        return json.loads('\n'.join(result.split('\n')[:-2]))
