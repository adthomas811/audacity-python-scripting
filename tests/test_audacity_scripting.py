
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
# https://github.com/audacity/audacity/blob/master/lib-src/mod-script-pipe/PipeServer.cpp
# http://timgolden.me.uk/pywin32-docs/win32pipe.html

# import win32pipe
# import win32file


# class AudacityMock(object):
#     def __init__(self):
#         if sys.platform == 'win32':
#             PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
#             open_mode = win32pipe.PIPE_ACCESS_DUPLEX
#             pipe_mode = (win32pipe.PIPE_TYPE_MESSAGE |
#                          win32pipe.PIPE_READMODE_MESSAGE |
#                          win32pipe.PIPE_WAIT |
#                          PIPE_REJECT_REMOTE_CLIENTS)
#             max_instances = win32pipe.PIPE_UNLIMITED_INSTANCES
#             buffer_size = 1024
#
#             self.tofile = win32pipe.CreateNamedPipe(r'\\.\pipe\ToSrvPipe',
#                                                     open_mode,
#                                                     pipe_mode,
#                                                     max_instances,
#                                                     buffer_size,
#                                                     buffer_size,
#                                                     50,
#                                                     None)
#             if self.tofile == win32file.INVALID_HANDLE_VALUE:
#                 # raise exception
#                 print('self.tofile not valid')
#
#             self.fromfile = win32pipe.CreateNamedPipe(r'\\.\pipe\FromSrvPipe',
#                                                       open_mode,
#                                                       pipe_mode,
#                                                       max_instances,
#                                                       buffer_size,
#                                                       buffer_size,
#                                                       50,
#                                                       None)
#             if self.fromfile == win32file.INVALID_HANDLE_VALUE:
#                 # raise exception
#                 print('self.fromfile not valid')
#         else:
#             # Linux and Mac not Implemented
#             toname = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
#             fromname = '/tmp/audacity_script_pipe.from.' + str(os.getuid())

#     def run_pipe_server(self):
#         if sys.platform == 'win32':
#             connected = (win32pipe.ConnectNamedPipe(
#                             self.tofile, None) == 0 and
#                          win32pipe.ConnectNamedPipe(
#                             self.fromfile, None) == 0)
#             if connected:
#                 try:
#                     while(True):
#                         success, data = win32file.ReadFile(self.tofile,
#                                                            buffer_size,
#                                                            None)
#                         if success != 0:
#                             # Raise Exception
#                             print('Read Failed!')
#                             break
#
#                         command = data.decode().split('\r')[0]
#                         response = evaluate_command(command)
#
#                         success = win32file.WriteFile(self.fromfile,
#                                                       (response +
#                                                       '\n').encode())[0]
#                         if success != 0:
#                             # Raise Exception
#                             print('Write Failed!')
#                             break
#                 finally:
#                     win32file.FlushFileBuffers(self.tofile)
#                     win32pipe.DisconnectNamedPipe(self.tofile)
#                     win32file.CloseHandle(self.tofile)
#                     win32file.FlushFileBuffers(self.fromfile)
#                     win32pipe.DisconnectNamedPipe(self.fromfile)
#                     win32file.CloseHandle(self.fromfile)
#         else:
#             # Linux and Mac not Implemented
#             pass

#     def evaluate_command(self, command):
#         scripting_id_and_args_list = command.split(':')
#
#         if len(scripting_id_and_args_list) == 1:
#
#         elif len(scripting_id_and_args_list) == 2:
#
#         elif len(scripting_id_and_args_list) > 2:
#
#         else:
