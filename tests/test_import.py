
import unittest
from unittest.mock import Mock


class AudacityScriptingTests(unittest.TestCase):
    def test_import(self):
        # import audacity_scripting
        # import audacity_scripting.base
        # import audacity_scripting.utils
        self.assertTrue(True)

# Mock class:
# This mock emulates the behavior of Audacity as of version 2.3.3
# https://docs.python.org/3/library/unittest.mock.html
# https://stackoverflow.com/questions/48542644/python-and-windows-named-pipes
# https://www.programcreek.com/python/example/70014/win32pipe.CreateNamedPipe
# https://codereview.stackexchange.com/questions/88672/python-wrapper-for-windows-pipes
# https://www.python-course.eu/pipes.php
# Create pipes for testing
# r, w = os.pipe(toname)
# r, w = os.pipe(fromname)
#    def __init__(self):
#        if sys.platform == 'win32':
#            logger.info('Running on windows')
#            toname = r'\\.\pipe\ToSrvPipe'
#            fromname = r'\\.\pipe\FromSrvPipe'
#            self.EOL = '\r\n\0'
#        else:
#            logger.info('Running on linux or mac')
#            toname = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
#            fromname = '/tmp/audacity_script_pipe.from.' + str(os.getuid())
#            self.EOL = '\n'
#
#        logger.info('Write to "' + toname + '"')
#        if not os.path.exists(toname):
#            raise ToSrvPipeNotExist(' ..does not exist. Ensure Audacity '
#                                    'is running with mod-script-pipe.')
#
#        logger.info('Read from "' + fromname + '"')
#        if not os.path.exists(fromname):
#            raise FromSrvPipeNotExist(' ..does not exist. Ensure Audacity '
#                                      'is running with mod-script-pipe.')
#
#        logger.info('Both pipes exist. Good.')
#
#        self.tofile = open(toname, 'wt+')
#        logger.info('File to write to has been opened')
#        self.fromfile = open(fromname, 'rt')
#        logger.info('File to read from has now been opened too')
#
#    def close(self):
#        self.tofile.close()
#        self.fromfile.close()
#
#    def _send_command(self, command):
#        self.tofile.write(command + self.EOL)
#        self.tofile.flush()
#
#    def _get_response(self):
#        result = ''
#        line = ''
#        while line != '\n':
#            result += line
#            line = self.fromfile.readline()
#        self._assert_command_success(result.split('\n')[-2])
#        return result
