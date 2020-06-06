
# Original connection code source:
# https://github.com/audacity/audacity/blob/ \
#                          master/scripts/piped-work/pipe_test.py

from audacity_scripting import LOGGER_NAME
import json
import logging
import os
import sys

# TODO(adthomas811): Log raised exceptions to the log file.

logger = logging.getLogger(LOGGER_NAME)


class ToSrvPipeNotExist(Exception):
    """
    An exception that is raised if the tofile file object doesn't exist.
    """
    pass


class FromSrvPipeNotExist(Exception):
    """
    An exception that is raised if the fromfile file object doesn't exist.
    """
    pass


class CommandAssertFailure(Exception):
    """
    An exception that is raised if the result string from a command indicates
    that the command did not succeed.
    """
    pass


class AudacityScriptingBase(object):
    """
    A class that provides the basic functionality for communicating with the
    Audacity scripting pipes.

    Attributes
    ----------
    tofile : <file object>
        The file object to write commands to Audacity.
    fromfile : <file object>
        The file object to read responses from Audacity.
    EOL : str
        The end of line character used depending on the OS.

    Methods
    -------
    run_command(command)
        Writes a command to the Audacity scripting pipe, reads and checks the
        output, then returns the result.
    get_json(result)
        Parses a JSON data structure from the result from Audacity.
    close()
        Closes the tofile and fromfile file objects.
    """

    def __init__(self):
        """
        Opens the tofile and fromfile file objects.

        Raises
        ------
        ToSrvPipeNotExist
            If the tofile file object doesn't exist.
        FromSrvPipeNotExist
            If the fromfile file object doesn't exist.
        """

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
        """
        Closes the tofile and fromfile file objects.
        """

        self.tofile.close()
        self.fromfile.close()

    def _send_command(self, command):
        """
        Writes a command to the tofile file object.

        Parameters
        ----------
        command : str
            Command to write to the tofile file object.
        """

        self.tofile.write(command + self.EOL)
        self.tofile.flush()

    def _get_response(self):
        """
        Reads a response from the fromfile file object, asserts that the
        command succeeded, and returns the result.
        """

        result = ''
        line = ''
        line = self.fromfile.readline()
        # Remove leading newline character on Mac OSX
        if line == '\n':
            line = ''
        while line != '\n':
            result += line
            line = self.fromfile.readline()
        # TODO(adthomas811): Would it be better to assert command success in
        #                    utils?
        self._assert_command_success(result.split('\n')[-2])
        return result

    def _assert_command_success(self, result_string):
        """
        Checks the result string and raises an exception if the command did
        not succeed.

        Parameters
        ----------
        result_string : str
            Parsed result string read from the fromfile object.

        Raises
        ------
        CommandAssertFailure
            If the result string indicates that the command did not succeed.
        """

        if result_string != 'BatchCommand finished: OK':
            # TODO(adthomas811): Make sure the full error message is printed,
            #                    not just the last line.
            raise CommandAssertFailure('Command finished with the '
                                       'status: {}'.format(result_string))

    def run_command(self, command):
        """
        Writes a command to the Audacity scripting pipe, reads and checks the
        output, then returns the result.

        Parameters
        ----------
        command : str
            Command to be sent to Audacity.
        """

        logger.info('Command: {}'.format(command))
        self._send_command(command)
        return self._get_response()

    # TODO(adthomas811): Move get_json out of this class?
    def get_json(self, result):
        """
        Parses a JSON data structure from the result from Audacity.

        Parameters
        ----------
        result : str
            Result returned from an Audacity command, containing a JSON object.
        """

        raw_result_item_list = result.split('\n')[:-2]
        result_item_list = []
        for result_item in raw_result_item_list:
            new_result_item = result_item.replace('\\', '\\\\')
            new_result_item = new_result_item.replace('\\\\"', '\\"')
            result_item_list.append(new_result_item)
        return json.loads('\n'.join(result_item_list))
