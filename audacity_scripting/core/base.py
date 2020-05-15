
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
            base_path = '\\\\.\\pipe\\'
            toname = 'ToSrvPipe'
            fromname = 'FromSrvPipe'
            self.EOL = '\r\n\0'
        else:
            logger.info('Running on linux or mac')
            base_path = '/tmp/'
            toname = 'audacity_script_pipe.to.' + str(os.getuid())
            fromname = 'audacity_script_pipe.from.' + str(os.getuid())
            self.EOL = '\n'

        logger.info('Write to "' + toname + '"')
        if toname not in os.listdir(base_path):
            raise ToSrvPipeNotExist(' ..does not exist. Ensure Audacity '
                                    'is running with mod-script-pipe.')

        logger.info('Read from "' + fromname + '"')
        if fromname not in os.listdir(base_path):
            raise FromSrvPipeNotExist(' ..does not exist. Ensure Audacity '
                                      'is running with mod-script-pipe.')

        logger.info('Both pipes exist. Good.')

        self.tofile = open(base_path + toname, 'w')
        logger.info('File to write to has been opened')

        self.fromfile = open(base_path + fromname, 'rt')
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
        raw_result_item_list = result.split('\n')[:-2]
        result_item_list = []
        for result_item in raw_result_item_list:
            new_result_item = result_item.replace('\\', '\\\\')
            new_result_item = new_result_item.replace('\\\\"', '\\"')
            result_item_list.append(new_result_item)
        return json.loads('\n'.join(result_item_list))
