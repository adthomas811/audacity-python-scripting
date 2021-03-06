
from audacity_scripting.core.utils import AudacityScriptingUtils
from datetime import datetime
import logging
import os
from os import mkdir
from os.path import abspath, dirname, isdir, isfile, join
from parameterized import parameterized
import re
import stat
import sys
import threading
from time import sleep
import unittest

# Try to import modules for Windows
try:
    import pywintypes
    import win32pipe
    import win32file
except ImportError:
    pass

package_path = dirname(abspath(__file__))
log_dir_path = join(package_path, '_logs')
if not isdir(log_dir_path):
    mkdir(log_dir_path)

current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_file_path = join(log_dir_path, current_time + '.log')

# If the log file already exists, wait a second and rename it
if isfile(log_file_path):
    sleep(1)
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file_path = join(log_dir_path, current_time + '.log')

# Create the Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create the Handler for logging data to a file
logger_handler = logging.FileHandler(log_file_path)
logger_handler.setLevel(logging.DEBUG)

# Create a Formatter for formatting the log messages
logger_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - '
                                     '%(message)s')

# Add the Formatter to the Handler
logger_handler.setFormatter(logger_formatter)

# Add the Handler to the Logger
logger.addHandler(logger_handler)

# Audacity command responses
SUCCESS_RESPONSE = 'BatchCommand finished: OK\n'
MISSING_CHAR_RESPONSE = 'Syntax error!\nCommand is missing \':\'\n'
BAD_COMMAND_RESPONSE = ('Your batch command of {} was not recognized.\n'
                        'BatchCommand finished: Failed!\n')


class AudacityScriptingTests(unittest.TestCase):
    """
    A class containing the tests for the audacity_scripting package. Run with
    pytest.

    Attributes
    ----------
    use_mock : bool
        A hard-coded flag to run the tests in this class against the Audacity
        mock. Set to True by default, must be set to False to run the tests
        against Audacity.
    aud_mock_proc : AudacityMock
        The thread running the Audacity mock that the tests run against. Used
        if use_mock is True.
    """

    def setUp(self):
        """
        Starts the Audacity mock thread if the use_mock flag is True.
        """

        # Set use_mock flag to False if running against Audacity
        self.use_mock = True
        logger.info('Using Mock: {}'.format(self.use_mock))

        if self.use_mock:
            self.aud_mock_proc = AudacityMock()
            self.aud_mock_proc.start()

            if sys.platform == 'win32':
                base_path = '\\\\.\\pipe\\'
                toname = 'ToSrvPipe'
                fromname = 'FromSrvPipe'
            else:
                base_path = '/tmp/'
                toname = 'audacity_script_pipe.to.' + str(os.getuid())
                fromname = 'audacity_script_pipe.from.' + str(os.getuid())

            # TODO(adthomas811): Remove check for pipes.
            while toname not in os.listdir(base_path):
                logger.info('{} not found!'.format(toname))
                sleep(0.5)
            while fromname not in os.listdir(base_path):
                logger.info('{} not found!'.format(fromname))
                sleep(0.5)
            logger.info('Both named pipes exist!')

    def tearDown(self):
        """
        Ends the Audacity mock thread if the use_mock flag is True.
        """

        logger.info('Test Teardown')
        if self.use_mock:
            self.aud_mock_proc.join()

    # TODO(adthomas811): Parameterize and add more tests.
    def test_command_runner(self):
        """
        Tests to exercise the run_command method in AudacityScriptingBase.
        """

        logger.info('test_command_runner test run!')
        with AudacityScriptingUtils() as command_runner:
            response = command_runner.run_command('SelectAll:')
        self.assertEqual(response, SUCCESS_RESPONSE)

    @parameterized.expand([
        [AudacityScriptingUtils.join_all_clips],
        [AudacityScriptingUtils.split_all_audio_on_labels],
        [AudacityScriptingUtils.export_multiple_prompt],
        [AudacityScriptingUtils.close_project_prompt],
    ])
    def test_no_args_no_return_value_commands(self, command):
        """
        Tests to exercise the methods in AudacityScriptingUtils that pass no
        args and return no value.

        Parameters
        ----------
        command : <class method object>
            Command to be called and exercised.
        """

        logger.info('command: {}'.format(command))
        with AudacityScriptingUtils() as command_runner:
            res = command(command_runner)
        self.assertIsNone(res)

    # TODO(adthomas811): Improve check for returned objects.
    @parameterized.expand([
        [AudacityScriptingUtils.get_commands_info, type([])],
        [AudacityScriptingUtils.get_menus_info, type([])],
        [AudacityScriptingUtils.get_preferences_info, type([])],
        [AudacityScriptingUtils.get_tracks_info, type([])],
        [AudacityScriptingUtils.get_clips_info, type([])],
        [AudacityScriptingUtils.get_envelopes_info, type([])],
        [AudacityScriptingUtils.get_labels_info, type([])],
        [AudacityScriptingUtils.get_boxes_info, type([])],
        [AudacityScriptingUtils.get_audio_tracks_info, type([])],
        [AudacityScriptingUtils.get_scripting_id_list, type([])],
    ])
    def test_no_args_return_value_commands(self, command, target_type):
        """
        Tests to exercise the methods in AudacityScriptingUtils that pass no
        args, but return a value.

        Parameters
        ----------
        command : <class method object>
            Command to be called and exercised.
        target_type : type
            Type of the expected return value.
        """

        logger.info('command: {}'.format(command))
        with AudacityScriptingUtils() as command_runner:
            res = command(command_runner)
        self.assertEqual(type(res), target_type)

    @parameterized.expand([
        [AudacityScriptingUtils.rename_track_by_num, ("New Track Name", 0)],
        [AudacityScriptingUtils.rename_track_by_num, ("L - AT2050", 0)],
        [AudacityScriptingUtils.normalize_tracks_by_label, (["L - AT2050"],)],
        [AudacityScriptingUtils.compress_tracks_by_label, (["L - AT2050"],)],
        [AudacityScriptingUtils.set_track_gain, ("L - AT2050", -1.5)],
        [AudacityScriptingUtils.mix_and_render_to_new_track,
            (["L - AT2050", "R - SM57"],)],
    ])
    def test_args_no_return_value_commands(self, command, args):
        """
        Tests to exercise the methods in AudacityScriptingUtils that pass args,
        but return no value.

        Parameters
        ----------
        command : <class method object>
            Command to be called and exercised.
        args : tuple
            Tuple containing the args for the command.
        """

        logger.info('command: {}'.format(command))
        with AudacityScriptingUtils() as command_runner:
            res = command(command_runner, *args)
        self.assertIsNone(res)

    @parameterized.expand([
        [AudacityScriptingUtils.get_track_gain, ("L - AT2050",), type(1.0)],
    ])
    def test_args_return_value_commands(self, command, args, target_type):
        """
        Tests to exercise the methods in AudacityScriptingUtils that pass args
        and return a value.

        Parameters
        ----------
        command : <class method object>
            Command to be called and exercised.
        args : tuple
            Tuple containing the args for the command.
        target_type : type
            Type of the expected return value.
        """

        logger.info('command: {}'.format(command))
        with AudacityScriptingUtils() as command_runner:
            res = command(command_runner, *args)
        self.assertEqual(type(res), target_type)


class AudacityMock(threading.Thread):
    """
    A class used as a mock for Audacity. Creates named pipes to communicate
    with AudacityScriptingBase, evaluates commands it receives, and returns
    appropriate output.

    Attributes
    ----------
    tofile : <named pipe object>
        File object that AudacityScriptingBase writes to and this mock reads
        from.
    fromfile : <named pipe object>
        File object that this mock writes to and AudacityScriptingBase reads
        from.
    last_getinfo_str : str
        Stores the value of the last info returned by the GetInfo command.
        Defaults to getinfo_commands_str.
    toname : str
        File name for tofile. Used on Unix only.
    fromname : str
        File name for fromfile. Used on Unix only.
    buffer_size : int
        Buffer size for the named pipes. Used on Windows only.

    Methods
    -------
    run()
        Runs the named pipe server.
    kill()
        Kills the named pipe server.
    """

    def __init__(self):
        """
        Calls parent init, initializes the named pipes, and sets the initial
        value of last_getinfo_str.
        """

        threading.Thread.__init__(self)

        if sys.platform == 'win32':
            self._init_mock_win()
        else:
            self._init_mock_unix()

        self.last_getinfo_str = getinfo_commands_str

    def _init_mock_win(self):
        """
        Initialize named pipes on Windows.
        """

        PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
        open_mode = win32pipe.PIPE_ACCESS_DUPLEX
        pipe_mode = (win32pipe.PIPE_TYPE_MESSAGE |
                     win32pipe.PIPE_READMODE_MESSAGE |
                     win32pipe.PIPE_WAIT |
                     PIPE_REJECT_REMOTE_CLIENTS)
        max_instances = win32pipe.PIPE_UNLIMITED_INSTANCES
        self.buffer_size = 1024

        self.tofile = win32pipe.CreateNamedPipe('\\\\.\\pipe\\ToSrvPipe',
                                                open_mode,
                                                pipe_mode,
                                                max_instances,
                                                self.buffer_size,
                                                self.buffer_size,
                                                50,
                                                None)
        if self.tofile == win32file.INVALID_HANDLE_VALUE:
            # TODO(adthomas811): Log the error (using logger.error)
            #                    and raise an Exception.
            logger.info('tofile not valid')
        else:
            logger.info('tofile is valid')

        self.fromfile = win32pipe.CreateNamedPipe('\\\\.\\pipe\\FromSrvPipe',
                                                  open_mode,
                                                  pipe_mode,
                                                  max_instances,
                                                  self.buffer_size,
                                                  self.buffer_size,
                                                  50,
                                                  None)
        if self.fromfile == win32file.INVALID_HANDLE_VALUE:
            # TODO(adthomas811): Log the error (using logger.error)
            #                    and raise an Exception.
            logger.info('fromfile not valid')
        else:
            logger.info('fromfile is valid')

    def _init_mock_unix(self):
        """
        Initialize named pipes on Unix.

        Raises
        ------
        IOError
            If the fifos are not created.
        """

        self.toname = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
        self.fromname = '/tmp/audacity_script_pipe.from.' + str(os.getuid())

        try:
            os.unlink(self.toname)
            os.unlink(self.fromname)
        except IOError as err:
            logger.info(err)

        try:
            os.mkfifo(self.toname, stat.S_IRWXU)
            os.mkfifo(self.fromname, stat.S_IRWXU)
        except IOError as err:
            logger.info(err)
            # TODO(adthomas811): Log the error (using logger.error)
            #                    and raise an Exception.
            raise

    def run(self):
        """
        Runs the named pipe server.
        """

        if sys.platform == 'win32':
            self._run_pipe_server_win()
        else:
            self._run_pipe_server_unix()

    def _run_pipe_server_win(self):
        """
        Runs the named pipe server on Windows.
        """

        logger.info('Running Windows Pipe Server!')
        tofile_conn_res = win32pipe.ConnectNamedPipe(self.tofile, None)
        fromfile_conn_res = win32pipe.ConnectNamedPipe(self.fromfile, None)

        logger.info('tofile connected: {}'.format(str(tofile_conn_res == 0)))
        logger.info('fromfile connected: '
                    '{}'.format(str(fromfile_conn_res == 0)))

        try:
            while(True):
                success, data = win32file.ReadFile(self.tofile,
                                                   self.buffer_size,
                                                   None)
                if success != 0:
                    # TODO(adthomas811): Log the error (using logger.error)
                    #                    and raise an Exception.
                    logger.info('Read Failed!')
                    break
                else:
                    logger.info('Read succeeded!')

                command = data.decode().split('\r')[0]
                response = self._evaluate_command(command)

                success = win32file.WriteFile(self.fromfile,
                                              response.encode())[0]
                if success != 0:
                    # TODO(adthomas811): Log the error (using logger.error)
                    #                    and raise an Exception.
                    logger.info('Write Failed!')
                    break
                else:
                    logger.info('Write succeeded!')
        except pywintypes.error as err:
            logger.info(err)
            # TODO(adthomas811): Log the error (using logger.error)
            #                    and raise an Exception.
        finally:
            self.kill()

    def _run_pipe_server_unix(self):
        """
        Runs the named pipe server on Unix.

        Raises
        ------
        IOError
            If reading from or writing to the named pipes fails.
        """

        try:
            self.tofile = open(self.toname, 'r')
            self.fromfile = open(self.fromname, 'w')

            while(True):
                command = self.tofile.readline()
                if len(command) == 0:
                    break

                response = self._evaluate_command(command)

                self.fromfile.write(response)
                self.fromfile.flush()
        except IOError as err:
            logger.info(err)
            # TODO(adthomas811): Log the error (using logger.error)
            #                    and raise an Exception.
            raise
        except BrokenPipeError as err:
            logger.info(err)
        finally:
            self.kill()

    def _evaluate_command(self, command):
        """
        Evaluates the command from AudacityScriptingBase, and returns the
        appropriate response.

        Parameters
        ----------
        command : str
            The command read by the mock to be evaluated.
        """

        command_list = command.split(':')
        scripting_id = command_list[0].strip().lower()
        logger.info('command: {}'.format(command))
        logger.info('scripting_id: {}'.format(scripting_id))

        response = ''
        if scripting_id == 'getinfo':
            if len(command_list) < 2:
                getinfo_args = ''
            else:
                getinfo_args = ' '.join(command_list[1:])
            response = self._getinfo_command(getinfo_args)
            response += SUCCESS_RESPONSE
        elif scripting_id in scripting_id_list:
            response = SUCCESS_RESPONSE
        elif len(command_list) == 1 and ' ' in scripting_id:
            response = MISSING_CHAR_RESPONSE
        else:
            response = BAD_COMMAND_RESPONSE.format(scripting_id)

        return response + '\n'

    def _getinfo_command(self, getinfo_args):
        """
        Determines which info gets returned for the GetInfo command.

        Parameters
        ----------
        getinfo_args : str
            The args for the GetInfo command.
        """

        if 'type' in getinfo_args.lower():
            getinfo_type = re.split('(?i)type=', getinfo_args)[-1]
            getinfo_type = getinfo_type.split('\n')[0]
            if getinfo_type == 'Commands':
                self.last_getinfo_str = getinfo_commands_str
                return getinfo_commands_str
            elif getinfo_type == 'Menus':
                self.last_getinfo_str = getinfo_menus_str
                return getinfo_menus_str
            elif getinfo_type == 'Preferences':
                self.last_getinfo_str = getinfo_preferences_str
                return getinfo_preferences_str
            elif getinfo_type == 'Tracks':
                self.last_getinfo_str = getinfo_tracks_str
                return getinfo_tracks_str
            elif getinfo_type == 'Clips':
                self.last_getinfo_str = getinfo_clips_str
                return getinfo_clips_str
            elif getinfo_type == 'Envelopes':
                self.last_getinfo_str = getinfo_envelopes_str
                return getinfo_envelopes_str
            elif getinfo_type == 'Labels':
                self.last_getinfo_str = getinfo_labels_str
                return getinfo_labels_str
            elif getinfo_type == 'Boxes':
                self.last_getinfo_str = getinfo_boxes_str
                return getinfo_boxes_str
            else:
                return self.last_getinfo_str
        else:
            return getinfo_commands_str

    def kill(self):
        """
        Kills the named pipe server.
        """

        if sys.platform == 'win32':
            self._kill_pipe_server_win()
        else:
            self._kill_pipe_server_unix()
        logger.info('Handles Closed')

    def _kill_pipe_server_win(self):
        """
        Kills the named pipe server on Windows.
        """

        # TODO(adthomas811): Clean up method.
        # win32file.FlushFileBuffers(self.tofile)
        # win32pipe.DisconnectNamedPipe(self.tofile)
        win32file.CloseHandle(self.tofile)

        # win32file.FlushFileBuffers(self.fromfile)
        # win32pipe.DisconnectNamedPipe(self.fromfile)
        win32file.CloseHandle(self.fromfile)

    def _kill_pipe_server_unix(self):
        """
        Kills the named pipe server on Unix.
        """

        self.tofile.close()
        os.unlink(self.toname)

        self.fromfile.close()
        os.unlink(self.fromname)

# List of unique scripting ids compiled from 'Commands' info and 'Menus' info
scripting_id_list = [
    'cursnextclipboundary', 'silencefinder', 'repeat', 'align_starttoselstart',
    'dtmf tones...', 'findclipping', 'selprevclip', 'cutlabels', 'wahwah',
    'selcursortonextclipboundary', 'scrub', 'setpreference', 'undohistory',
    'mixandrender', 'managetools', 'truncatesilence', 'showextramenus',
    'clipfix', 'cursselend', 'repeat...', 'showscrubbingtb', 'exportmidi',
    'joinlabels', 'record2ndchoice', 'fade out', 'importaudio',
    'seltrackstarttocursor', 'new', 'setrightselection', 'export2',
    'cursprojectend', 'disjoinlabels', 'vocalremover', 'newstereotrack',
    'editlabels', 'reverb', 'setleftselection', 'nyquistprompt',
    'nextlowerpeakfrequency', 'seek', 'addlabel', 'showclipping',
    'showtranscriptiontb', 'autoduck', 'fitinwindow', 'join', 'deletelabels',
    'showedittb', 'record1stchoice', 'align_endtoend', 'vocoder', 'paste',
    'newmonotrack', 'typetocreatelabel', 'silence...', 'sliding stretch...',
    'splitlabels', 'selalltracks', 'selsave', 'nexthigherpeakfrequency',
    'align_starttozero', 'beatfinder', 'pagesetup', 'selecttracks',
    'vocalreductionandisolation', 'highpassfilter', 'showtoolstb', 'help',
    'plotspectrum', 'mutealltracks', 'selrestore', 'overdub',
    'nyquistplug-ininstaller', 'zoomout', 'soundfinder', 'select',
    'sortbyname', 'export', 'compressor...', 'timerrecord', 'getpreference',
    'duplicate', 'savecopy', 'repeatlasteffect', 'quickhelp', 'copylabels',
    'panleft', 'reverb...', 'repair', 'print', 'removetracks',
    'noise reduction...', 'copy', 'curstrackstart', 'importmidi',
    'showdevicetb', 'delay', 'import2', 'moveselectionwithtracks', 'log',
    'normalize', 'fancyscreenshot', 'mixandrendertonewtrack', 'crossfadeclips',
    'editmetadata', 'setenvelope', 'bassandtreble', 'rissetdrum',
    'low pass filter...', 'showplaymetertb', 'pancenter', 'distortion',
    'selectnone', 'save', 'zoomnormal', 'managegenerators', 'sc4...',
    'exportogg', 'high pass filter...', 'open', 'rescandevices', 'setproject',
    'unmutealltracks', 'exportwav', 'settrack', 'zerocross', 'screenshot',
    'addlabelplaying', 'sampledataexport', 'click removal...', 'rhythmtrack',
    'managemacros', 'pastenewlabel', 'curstrackend', 'saveproject2',
    'contrastanalyser', 'savecompressed', 'manageeffects', 'cut',
    'macro_mp3conversion', 'undo', 'splitcutlabels', 'bass and treble...',
    'advancedvzoom', 'cursprevclipboundary', 'amplify', 'noise', 'skipselend',
    'selprevclipboundarytocursor', 'low-passfilter', 'sortbytime',
    'lockplayregion', 'preferences', 'echo', 'spectraleditparametriceq',
    'crashreport', 'setlabel', 'paulstretch', 'checkdeps',
    'regular interval labels...', 'sampledataimport', 'about', 'clickremoval',
    'exportmp3', 'selsynclocktracks', 'nyquist plug-in installer...',
    'playstop', 'tone', 'cursprojectstart', 'playstopselect', 'delete',
    'collapsealltracks', 'cursselstart', 'studiofadeout', 'zoomsel',
    'adjustablefade', 'resettoolbars', 'manual', 'showmixertb',
    'low-pass filter...', 'selcursorstoredcursor', 'truncate silence...',
    'change pitch...', 'settrackvisuals', 'auto duck...', 'zoomtoggle',
    'normalize...', 'tone...', 'tremolo', 'silencelabels', 'echo...',
    'crossfadetracks', 'align_endtoselend', 'message', 'slidingstretch',
    'splitnew', 'synclock', 'compressor', 'phaser', 'wahwah...',
    'splitdeletelabels', 'demo', 'disjoin', 'changetempo', 'change tempo...',
    'newlabeltrack', 'storecursorposition', 'high-pass filter...',
    'spectraleditmultitool', 'soundactivation', 'exportsel', 'mixerboard',
    'pluck', 'openproject2', 'splitcut', 'midideviceinfo', 'phaser...', 'exit',
    'benchmark', 'panright', 'updates', 'exportmultiple', 'distortion...',
    'expandalltracks', 'split', 'changepitch', 'lowpassfilter', 'amplify...',
    'notchfilter', 'drag', 'macro_fadeends', 'importlabels', 'chirp', 'trim',
    'splitdelete', 'skipselstart', 'getinfo', 'pause', 'nyquist prompt...',
    'spectraleditshelves', 'deviceinfo', 'unlockplayregion', 'selecttime',
    'playlooped', 'stereo to mono', 'settrackstatus', 'selectfrequencies',
    'high-passfilter', 'changespeed', 'redo', 'showrecordmetertb',
    'newtimetrack', 'paulstretch...', 'resample', 'swplaythrough', 'chirp...',
    'change speed...', 'zoomin', 'togglescrubruler', 'close',
    'align_starttoselend', 'fade in', 'invert', 'exportlabels', 'importraw',
    'dtmftones', 'reverse', 'align_endtoselstart', 'togglespectralselection',
    'find clipping...', 'setclip', 'limiter', 'karaoke', 'compareaudio',
    'settrackaudio', 'selnextclip', 'pinnedhead', 'noise...',
    'showspectralselectiontb', 'regularintervallabels', 'selectall', 'saveas',
    'punchandroll', 'silence', 'seltrackstarttoend', 'soundactivationlevel',
    'align_together', 'showselectiontb', 'manageanalyzers', 'showtransporttb',
    'applymacrospalette', 'selcursortotrackend', 'fitv']

# Sample return data for 'GetInfo: Type=Commands'
getinfo_commands_str = (
    '[ \n'
    '  { "id":"Amplify", "name":"Amplify", "params":\n'
    '      [ \n'
    '        { "key":"Ratio", "type":"float", "default":0.9 },\n'
    '        { "key":"AllowClipping", "type":"bool", "default":"False" } ], '
    '"url":"Amplify", \n'
    '    "tip":"Increases or decreases the volume of the audio you have '
    'selected" },\n'
    '  { "id":"AutoDuck", "name":"Auto Duck", "params":\n'
    '      [ \n'
    '        { "key":"DuckAmountDb", "type":"double", "default":-12 },\n'
    '        { "key":"InnerFadeDownLen", "type":"double", "default":0 },\n'
    '        { "key":"InnerFadeUpLen", "type":"double", "default":0 },\n'
    '        { "key":"OuterFadeDownLen", "type":"double", "default":0.5 },\n'
    '        { "key":"OuterFadeUpLen", "type":"double", "default":0.5 },\n'
    '        { "key":"ThresholdDb", "type":"double", "default":-30 },\n'
    '        { "key":"MaximumPause", "type":"double", "default":1 } ], '
    '"url":"Auto_Duck", \n'
    '    "tip":"Reduces (ducks) the volume of one or more tracks whenever '
    'the volume of a specified \\"control\\" track reaches a particular '
    'level" },\n'
    '  { "id":"BassAndTreble", \n'
    '    "name":"Bass and Treble", "params":\n'
    '      [ \n'
    '        { "key":"Bass", "type":"double", "default":0 },\n'
    '        { "key":"Treble", "type":"double", "default":0 },\n'
    '        { "key":"Gain", "type":"double", "default":0 },\n'
    '        { "key":"Link Sliders", "type":"bool", "default":"False" } ], \n'
    '    "url":"Bass_and_Treble", \n'
    '    "tip":"Simple tone control effect" },\n'
    '  { "id":"ChangePitch", "name":"Change Pitch", "params":\n'
    '      [ \n'
    '        { "key":"Percentage", "type":"double", "default":0 },\n'
    '        { "key":"SBSMS", "type":"bool", "default":"False" } ], '
    '"url":"Change_Pitch", \n'
    '    "tip":"Changes the pitch of a track without changing its tempo" },\n'
    '  { "id":"ChangeSpeed", "name":"Change Speed", "params":\n'
    '      [ \n'
    '        { "key":"Percentage", "type":"double", "default":0 } ], '
    '"url":"Change_Speed", \n'
    '    "tip":"Changes the speed of a track, also changing its pitch" },\n'
    '  { "id":"ChangeTempo", "name":"Change Tempo", "params":\n'
    '      [ \n'
    '        { "key":"Percentage", "type":"double", "default":0 },\n'
    '        { "key":"SBSMS", "type":"bool", "default":"False" } ], '
    '"url":"Change_Tempo", \n'
    '    "tip":"Changes the tempo of a selection without changing its pitch" '
    '},\n'
    '  { "id":"Chirp", "name":"Chirp", "params":\n'
    '      [ \n'
    '        { "key":"StartFreq", "type":"double", "default":440 },\n'
    '        { "key":"EndFreq", "type":"double", "default":1320 },\n'
    '        { "key":"StartAmp", "type":"double", "default":0.8 },\n'
    '        { "key":"EndAmp", "type":"double", "default":0.1 },\n'
    '        { "key":"Waveform", "type":"enum", "default":"Sine", "enum":\n'
    '            [ "Sine", "Square", "Sawtooth", \n'
    '              "Square, no alias" ] },\n'
    '        { "key":"Interpolation", "type":"enum", "default":"Linear", '
    '"enum":\n'
    '            [ "Linear", "Logarithmic" ] } ], "url":"Chirp", \n'
    '    "tip":"Generates an ascending or descending tone of one of four '
    'types" },\n'
    '  { "id":"ClickRemoval", "name":"Click Removal", "params":\n'
    '      [ \n'
    '        { "key":"Threshold", "type":"int", "default":200 },\n'
    '        { "key":"Width", "type":"int", "default":20 } ], '
    '"url":"Click_Removal", \n'
    '    "tip":"Click Removal is designed to remove clicks on audio tracks" '
    '},\n'
    '  { "id":"Compressor", "name":"Compressor", "params":\n'
    '      [ \n'
    '        { "key":"Threshold", "type":"double", "default":-12 },\n'
    '        { "key":"NoiseFloor", "type":"double", "default":-40 },\n'
    '        { "key":"Ratio", "type":"double", "default":2 },\n'
    '        { "key":"AttackTime", "type":"double", "default":0.2 },\n'
    '        { "key":"ReleaseTime", "type":"double", "default":1 },\n'
    '        { "key":"Normalize", "type":"bool", "default":"True" },\n'
    '        { "key":"UsePeak", "type":"bool", "default":"False" } ], '
    '"url":"Compressor", \n'
    '    "tip":"Compresses the dynamic range of audio" },\n'
    '  { "id":"DtmfTones", "name":"DTMF Tones", "params":\n'
    '      [ \n'
    '        { "key":"Sequence", "type":"string", "default":"audacity" },\n'
    '        { "key":"Duty Cycle", "type":"double", "default":55 },\n'
    '        { "key":"Amplitude", "type":"double", "default":0.8 } ], '
    '"url":"DTMF_Tones", \n'
    '    "tip":"Generates dual-tone multi-frequency (DTMF) tones like those '
    'produced by the keypad on telephones" },\n'
    '  { "id":"Distortion", "name":"Distortion", "params":\n'
    '      [ \n'
    '        { "key":"Type", "type":"enum", "default":"Hard Clipping", '
    '"enum":\n'
    '            [ "Hard Clipping", "Soft Clipping", "Soft Overdrive", \n'
    '              "Medium Overdrive", "Hard Overdrive", \n'
    '              "Cubic Curve (odd harmonics)", "Even Harmonics", \n'
    '              "Expand and Compress", "Leveller", \n'
    '              "Rectifier Distortion", \n'
    '              "Hard Limiter 1413" ] },\n'
    '        { "key":"DC Block", "type":"bool", "default":"False" },\n'
    '        { "key":"Threshold dB", "type":"double", "default":-6 },\n'
    '        { "key":"Noise Floor", "type":"double", "default":-70 },\n'
    '        { "key":"Parameter 1", "type":"double", "default":50 },\n'
    '        { "key":"Parameter 2", "type":"double", "default":50 },\n'
    '        { "key":"Repeats", "type":"int", "default":1 } ], '
    '"url":"Distortion", \n'
    '    "tip":"Waveshaping distortion effect" },\n'
    '  { "id":"Echo", "name":"Echo", "params":\n'
    '      [ \n'
    '        { "key":"Delay", "type":"float", "default":1 },\n'
    '        { "key":"Decay", "type":"float", "default":0.5 } ], '
    '"url":"Echo", \n'
    '    "tip":"Repeats the selected audio again and again" },\n'
    '  { "id":"FindClipping", "name":"Find Clipping", "params":\n'
    '      [ \n'
    '        { "key":"Duty Cycle Start", "type":"int", "default":3 },\n'
    '        { "key":"Duty Cycle End", "type":"int", "default":3 } ], '
    '"url":"Find_Clipping", \n'
    '    "tip":"Creates labels where clipping is detected" },\n'
    '  { "id":"Noise", "name":"Noise", "params":\n'
    '      [ \n'
    '        { "key":"Type", "type":"enum", "default":"White", "enum":\n'
    '            [ "White", "Pink", "Brownian" ] },\n'
    '        { "key":"Amplitude", "type":"double", "default":0.8 } ], '
    '"url":"Noise", \n'
    '    "tip":"Generates one of three different types of noise" },\n'
    '  { "id":"Normalize", "name":"Normalize", "params":\n'
    '      [ \n'
    '        { "key":"PeakLevel", "type":"double", "default":-1 },\n'
    '        { "key":"ApplyGain", "type":"bool", "default":"True" },\n'
    '        { "key":"RemoveDcOffset", "type":"bool", "default":"True" },\n'
    '        { "key":"StereoIndependent", "type":"bool", "default":"False" } '
    '], "url":"Normalize", \n'
    '    "tip":"Sets the peak amplitude of one or more tracks" },\n'
    '  { "id":"Paulstretch", "name":"Paulstretch", "params":\n'
    '      [ \n'
    '        { "key":"Stretch Factor", "type":"float", "default":10 },\n'
    '        { "key":"Time Resolution", "type":"float", "default":0.25 } ], '
    '"url":"Paulstretch", \n'
    '    "tip":"Paulstretch is only for an extreme time-stretch or '
    '\\"stasis\\" effect" },\n'
    '  { "id":"Phaser", "name":"Phaser", "params":\n'
    '      [ \n'
    '        { "key":"Stages", "type":"int", "default":2 },\n'
    '        { "key":"DryWet", "type":"int", "default":128 },\n'
    '        { "key":"Freq", "type":"double", "default":0.4 },\n'
    '        { "key":"Phase", "type":"double", "default":0 },\n'
    '        { "key":"Depth", "type":"int", "default":100 },\n'
    '        { "key":"Feedback", "type":"int", "default":0 },\n'
    '        { "key":"Gain", "type":"double", "default":-6 } ], '
    '"url":"Phaser", \n'
    '    "tip":"Combines phase-shifted signals with the original signal" },\n'
    '  { "id":"Repeat", "name":"Repeat", "params":\n'
    '      [ \n'
    '        { "key":"Count", "type":"int", "default":1 } ], '
    '"url":"Repeat", \n'
    '    "tip":"Repeats the selection the specified number of times" },\n'
    '  { "id":"Reverb", "name":"Reverb", "params":\n'
    '      [ \n'
    '        { "key":"RoomSize", "type":"double", "default":75 },\n'
    '        { "key":"Delay", "type":"double", "default":10 },\n'
    '        { "key":"Reverberance", "type":"double", "default":50 },\n'
    '        { "key":"HfDamping", "type":"double", "default":50 },\n'
    '        { "key":"ToneLow", "type":"double", "default":100 },\n'
    '        { "key":"ToneHigh", "type":"double", "default":100 },\n'
    '        { "key":"WetGain", "type":"double", "default":-1 },\n'
    '        { "key":"DryGain", "type":"double", "default":-1 },\n'
    '        { "key":"StereoWidth", "type":"double", "default":100 },\n'
    '        { "key":"WetOnly", "type":"bool", "default":"False" } ], '
    '"url":"Reverb", \n'
    '    "tip":"Adds ambience or a \\"hall effect\\"" },\n'
    '  { "id":"SlidingStretch", \n'
    '    "name":"Sliding Stretch", "params":\n'
    '      [ \n'
    '        { "key":"RatePercentChangeStart", "type":"double", "default":0 '
    '},\n'
    '        { "key":"RatePercentChangeEnd", "type":"double", "default":0 '
    '},\n'
    '        { "key":"PitchHalfStepsStart", "type":"double", "default":0 },\n'
    '        { "key":"PitchHalfStepsEnd", "type":"double", "default":0 },\n'
    '        { "key":"PitchPercentChangeStart", "type":"double", "default":0 '
    '},\n'
    '        { "key":"PitchPercentChangeEnd", "type":"double", "default":0 } '
    '], \n'
    '    "url":"Sliding_Stretch", \n'
    '    "tip":"Allows continuous changes to the tempo and/or pitch" },\n'
    '  { "id":"Tone", "name":"Tone", "params":\n'
    '      [ \n'
    '        { "key":"Frequency", "type":"double", "default":440 },\n'
    '        { "key":"Amplitude", "type":"double", "default":0.8 },\n'
    '        { "key":"Waveform", "type":"enum", "default":"Sine", "enum":\n'
    '            [ "Sine", "Square", "Sawtooth", \n'
    '              "Square, no alias" ] },\n'
    '        { "key":"Interpolation", "type":"enum", "default":"Linear", '
    '"enum":\n'
    '            [ "Linear", "Logarithmic" ] } ], "url":"Tone", \n'
    '    "tip":"Generates a constant frequency tone of one of four types" '
    '},\n'
    '  { "id":"TruncateSilence", \n'
    '    "name":"Truncate Silence", "params":\n'
    '      [ \n'
    '        { "key":"Threshold", "type":"double", "default":-20 },\n'
    '        { "key":"Action", "type":"enum", \n'
    '          "default":"Truncate Detected Silence", "enum":\n'
    '            [ "Truncate Detected Silence", \n'
    '              "Compress Excess Silence" ] },\n'
    '        { "key":"Minimum", "type":"double", "default":0.5 },\n'
    '        { "key":"Truncate", "type":"double", "default":0.5 },\n'
    '        { "key":"Compress", "type":"double", "default":50 },\n'
    '        { "key":"Independent", "type":"bool", "default":"False" } ], \n'
    '    "url":"Truncate_Silence", \n'
    '    "tip":"Automatically reduces the length of passages where the '
    'volume is below a specified level" },\n'
    '  { "id":"Wahwah", "name":"Wahwah", "params":\n'
    '      [ \n'
    '        { "key":"Freq", "type":"double", "default":1.5 },\n'
    '        { "key":"Phase", "type":"double", "default":0 },\n'
    '        { "key":"Depth", "type":"int", "default":70 },\n'
    '        { "key":"Resonance", "type":"double", "default":2.5 },\n'
    '        { "key":"Offset", "type":"int", "default":30 },\n'
    '        { "key":"Gain", "type":"double", "default":-6 } ], '
    '"url":"Wahwah", \n'
    '    "tip":"Rapid tone quality variations, like that guitar sound so '
    'popular in the 1970\'s" },\n'
    '  { "id":"SilenceFinder", "name":"Silence Finder", "params":\n'
    '      [ \n'
    '        { "key":"sil-lev", "type":"double", "default":0 },\n'
    '        { "key":"sil-dur", "type":"double", "default":0 },\n'
    '        { "key":"labelbeforedur", "type":"double", "default":0 } ], '
    '"url":"Silence_Finder", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SilenceFinder", "name":"Silence Finder", "params":\n'
    '      [ \n'
    '        { "key":"sil-lev", "type":"double", "default":0 },\n'
    '        { "key":"sil-dur", "type":"double", "default":0 },\n'
    '        { "key":"labelbeforedur", "type":"double", "default":0 } ], '
    '"url":"Silence_Finder", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"BeatFinder", "name":"Beat Finder", "params":\n'
    '      [ \n'
    '        { "key":"thresval", "type":"int", "default":0 } ], '
    '"url":"Beat_Finder", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"BeatFinder", "name":"Beat Finder", "params":\n'
    '      [ \n'
    '        { "key":"thresval", "type":"int", "default":0 } ], '
    '"url":"Beat_Finder", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"NyquistPrompt", "name":"Nyquist Prompt", "params":\n'
    '      [ \n'
    '        { "key":"Command", "type":"string", "default":"" },\n'
    '        { "key":"Version", "type":"int", "default":3 } ], '
    '"url":"Nyquist_Prompt", "tip":"n/a" },\n'
    '  { "id":"ClipFix", "name":"Clip Fix", "params":\n'
    '      [ \n'
    '        { "key":"threshold", "type":"double", "default":0 },\n'
    '        { "key":"gain", "type":"double", "default":0 } ], '
    '"url":"Clip_Fix", \n'
    '    "tip":"Licensing confirmed under terms of the GNU General Public '
    'License version 2" },\n'
    '  { "id":"ClipFix", "name":"Clip Fix", "params":\n'
    '      [ \n'
    '        { "key":"threshold", "type":"double", "default":0 },\n'
    '        { "key":"gain", "type":"double", "default":0 } ], '
    '"url":"Clip_Fix", \n'
    '    "tip":"Licensing confirmed under terms of the GNU General Public '
    'License version 2" },\n'
    '  { "id":"Pluck", "name":"Pluck", "params":\n'
    '      [ \n'
    '        { "key":"pitch", "type":"int", "default":0 },\n'
    '        { "key":"fade", "type":"enum", "default":"Abrupt", "enum":\n'
    '            [ "Abrupt", "Gradual" ] },\n'
    '        { "key":"dur", "type":"double", "default":0 } ], '
    '"url":"Pluck", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Pluck", "name":"Pluck", "params":\n'
    '      [ \n'
    '        { "key":"pitch", "type":"int", "default":0 },\n'
    '        { "key":"fade", "type":"enum", "default":"Abrupt", "enum":\n'
    '            [ "Abrupt", "Gradual" ] },\n'
    '        { "key":"dur", "type":"double", "default":0 } ], '
    '"url":"Pluck", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"HighPassFilter", \n'
    '    "name":"High Pass Filter", "params":\n'
    '      [ \n'
    '        { "key":"frequency", "type":"double", "default":0 },\n'
    '        { "key":"rolloff", "type":"enum", "default":"dB6", "enum":\n'
    '            [ "dB6", "dB12", "dB24", "dB36", "dB48" ] } ], \n'
    '    "url":"High-Pass_Filter", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"High-passFilter", \n'
    '    "name":"High-Pass Filter", "params":\n'
    '      [ \n'
    '        { "key":"frequency", "type":"double", "default":0 },\n'
    '        { "key":"rolloff", "type":"enum", "default":"dB6", "enum":\n'
    '            [ "dB6", "dB12", "dB24", "dB36", "dB48" ] } ], \n'
    '    "url":"High-Pass_Filter", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"LowPassFilter", \n'
    '    "name":"Low Pass Filter", "params":\n'
    '      [ \n'
    '        { "key":"frequency", "type":"double", "default":0 },\n'
    '        { "key":"rolloff", "type":"enum", "default":"dB6", "enum":\n'
    '            [ "dB6", "dB12", "dB24", "dB36", "dB48" ] } ], \n'
    '    "url":"Low-Pass_Filter", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Low-passFilter", \n'
    '    "name":"Low-Pass Filter", "params":\n'
    '      [ \n'
    '        { "key":"frequency", "type":"double", "default":0 },\n'
    '        { "key":"rolloff", "type":"enum", "default":"dB6", "enum":\n'
    '            [ "dB6", "dB12", "dB24", "dB36", "dB48" ] } ], \n'
    '    "url":"Low-Pass_Filter", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"RhythmTrack", "name":"Rhythm Track", "params":\n'
    '      [ \n'
    '        { "key":"tempo", "type":"double", "default":0 },\n'
    '        { "key":"timesig", "type":"int", "default":0 },\n'
    '        { "key":"swing", "type":"double", "default":0 },\n'
    '        { "key":"bars", "type":"int", "default":0 },\n'
    '        { "key":"click-track-dur", "type":"double", "default":0 },\n'
    '        { "key":"offset", "type":"double", "default":0 },\n'
    '        { "key":"click-type", "type":"enum", "default":"Metronome", '
    '"enum":\n'
    '            [ "Metronome", "Ping (short)", "Ping (long)", "Cowbell", '
    '"ResonantNoise", "NoiseClick", "Drip (short)", "Drip (long)" ] },\n'
    '        { "key":"high", "type":"int", "default":0 },\n'
    '        { "key":"low", "type":"int", "default":0 } ], '
    '"url":"Rhythm_Track", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"RhythmTrack", "name":"Rhythm Track", "params":\n'
    '      [ \n'
    '        { "key":"tempo", "type":"double", "default":0 },\n'
    '        { "key":"timesig", "type":"int", "default":0 },\n'
    '        { "key":"swing", "type":"double", "default":0 },\n'
    '        { "key":"bars", "type":"int", "default":0 },\n'
    '        { "key":"click-track-dur", "type":"double", "default":0 },\n'
    '        { "key":"offset", "type":"double", "default":0 },\n'
    '        { "key":"click-type", "type":"enum", "default":"Metronome", '
    '"enum":\n'
    '            [ "Metronome", "Ping (short)", "Ping (long)", "Cowbell", '
    '"ResonantNoise", "NoiseClick", "Drip (short)", "Drip (long)" ] },\n'
    '        { "key":"high", "type":"int", "default":0 },\n'
    '        { "key":"low", "type":"int", "default":0 } ], '
    '"url":"Rhythm_Track", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Vocoder", "name":"Vocoder", "params":\n'
    '      [ \n'
    '        { "key":"dst", "type":"double", "default":0 },\n'
    '        { "key":"mst", "type":"enum", "default":"BothChannels", '
    '"enum":\n'
    '            [ "BothChannels", "RightOnly" ] },\n'
    '        { "key":"bands", "type":"int", "default":0 },\n'
    '        { "key":"track-vl", "type":"double", "default":0 },\n'
    '        { "key":"noise-vl", "type":"double", "default":0 },\n'
    '        { "key":"radar-vl", "type":"double", "default":0 },\n'
    '        { "key":"radar-f", "type":"double", "default":0 } ], '
    '"url":"Vocoder", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Vocoder", "name":"Vocoder", "params":\n'
    '      [ \n'
    '        { "key":"dst", "type":"double", "default":0 },\n'
    '        { "key":"mst", "type":"enum", "default":"BothChannels", '
    '"enum":\n'
    '            [ "BothChannels", "RightOnly" ] },\n'
    '        { "key":"bands", "type":"int", "default":0 },\n'
    '        { "key":"track-vl", "type":"double", "default":0 },\n'
    '        { "key":"noise-vl", "type":"double", "default":0 },\n'
    '        { "key":"radar-vl", "type":"double", "default":0 },\n'
    '        { "key":"radar-f", "type":"double", "default":0 } ], '
    '"url":"Vocoder", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SoundFinder", "name":"Sound Finder", "params":\n'
    '      [ \n'
    '        { "key":"sil-lev", "type":"double", "default":0 },\n'
    '        { "key":"sil-dur", "type":"double", "default":0 },\n'
    '        { "key":"labelbeforedur", "type":"double", "default":0 },\n'
    '        { "key":"labelafterdur", "type":"double", "default":0 },\n'
    '        { "key":"finallabel", "type":"int", "default":0 } ], '
    '"url":"Sound_Finder", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SoundFinder", "name":"Sound Finder", "params":\n'
    '      [ \n'
    '        { "key":"sil-lev", "type":"double", "default":0 },\n'
    '        { "key":"sil-dur", "type":"double", "default":0 },\n'
    '        { "key":"labelbeforedur", "type":"double", "default":0 },\n'
    '        { "key":"labelafterdur", "type":"double", "default":0 },\n'
    '        { "key":"finallabel", "type":"int", "default":0 } ], '
    '"url":"Sound_Finder", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SpectralEditMultiTool", \n'
    '    "name":"Spectral edit multi tool", "params":\n'
    '      [  ], \n'
    '    "url":"Spectral_edit_multi_tool", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SpectralEditMultiTool", \n'
    '    "name":"Spectral edit multi tool", "params":\n'
    '      [  ], \n'
    '    "url":"Spectral_edit_multi_tool", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SpectralEditParametricEq", \n'
    '    "name":"Spectral edit parametric EQ", "params":\n'
    '      [ \n'
    '        { "key":"control-gain", "type":"double", "default":0 } ], \n'
    '    "url":"Spectral_edit_parametric_EQ", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SpectralEditParametricEq", \n'
    '    "name":"Spectral edit parametric EQ", "params":\n'
    '      [ \n'
    '        { "key":"control-gain", "type":"double", "default":0 } ], \n'
    '    "url":"Spectral_edit_parametric_EQ", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SpectralEditShelves", \n'
    '    "name":"Spectral edit shelves", "params":\n'
    '      [ \n'
    '        { "key":"control-gain", "type":"double", "default":0 } ], \n'
    '    "url":"Spectral_edit_shelves", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SpectralEditShelves", \n'
    '    "name":"Spectral edit shelves", "params":\n'
    '      [ \n'
    '        { "key":"control-gain", "type":"double", "default":0 } ], \n'
    '    "url":"Spectral_edit_shelves", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"VocalReductionAndIsolation", \n'
    '    "name":"Vocal Reduction and Isolation", "params":\n'
    '      [ \n'
    '        { "key":"action", "type":"enum", "default":"Remove", "enum":\n'
    '            [ "Remove", "Isolate", "IsolateInvert", "RemoveCenter", '
    '"IsolateCenter", \n'
    '              "IsolateCenterInvert", "RemoveCenter", "Analyze" ] },\n'
    '        { "key":"strength", "type":"double", "default":0 },\n'
    '        { "key":"low-transition", "type":"double", "default":0 },\n'
    '        { "key":"high-transition", "type":"double", "default":0 } ], \n'
    '    "url":"Vocal_Reduction_and_Isolation", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"VocalReductionAndIsolation", \n'
    '    "name":"Vocal Reduction and Isolation", "params":\n'
    '      [ \n'
    '        { "key":"action", "type":"enum", "default":"RemoveToMono", '
    '"enum":\n'
    '            [ "RemoveToMono", "Remove", "Isolate", "IsolateInvert", \n'
    '              "RemoveCenterToMono", "RemoveCenter", "IsolateCenter", \n'
    '              "IsolateCenterInvert", "Analyze" ] },\n'
    '        { "key":"strength", "type":"double", "default":0 },\n'
    '        { "key":"low-transition", "type":"double", "default":0 },\n'
    '        { "key":"high-transition", "type":"double", "default":0 } ], \n'
    '    "url":"Vocal_Reduction_and_Isolation", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"NotchFilter", "name":"Notch Filter", "params":\n'
    '      [ \n'
    '        { "key":"frequency", "type":"double", "default":0 },\n'
    '        { "key":"q", "type":"double", "default":0 } ], '
    '"url":"Notch_Filter", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"NotchFilter", "name":"Notch Filter", "params":\n'
    '      [ \n'
    '        { "key":"frequency", "type":"double", "default":0 },\n'
    '        { "key":"q", "type":"double", "default":0 } ], '
    '"url":"Notch_Filter", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"AdjustableFade", \n'
    '    "name":"Adjustable Fade", "params":\n'
    '      [ \n'
    '        { "key":"type", "type":"enum", "default":"Up", "enum":\n'
    '            [ "Up", "Down", "SCurveUp", "SCurveDown" ] },\n'
    '        { "key":"curve", "type":"double", "default":0 },\n'
    '        { "key":"units", "type":"enum", "default":"Percent", "enum":\n'
    '            [ "Percent", "dB" ] },\n'
    '        { "key":"gain0", "type":"double", "default":0 },\n'
    '        { "key":"gain1", "type":"double", "default":0 },\n'
    '        { "key":"preset", "type":"enum", "default":"None", "enum":\n'
    '            [ "None", "LinearIn", "LinearOut", "ExponentialIn", '
    '"ExponentialOut", "LogarithmicIn", "LogarithmicOut", "RoundedIn", '
    '"RoundedOut", "CosineIn", "CosineOut", "SCurveIn", "SCurveOut" ] } ], \n'
    '    "url":"Adjustable_Fade", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"AdjustableFade", \n'
    '    "name":"Adjustable Fade", "params":\n'
    '      [ \n'
    '        { "key":"type", "type":"enum", "default":"Up", "enum":\n'
    '            [ "Up", "Down", "SCurveUp", "SCurveDown" ] },\n'
    '        { "key":"curve", "type":"double", "default":0 },\n'
    '        { "key":"units", "type":"enum", "default":"Percent", "enum":\n'
    '            [ "Percent", "dB" ] },\n'
    '        { "key":"gain0", "type":"double", "default":0 },\n'
    '        { "key":"gain1", "type":"double", "default":0 },\n'
    '        { "key":"preset", "type":"enum", "default":"None", "enum":\n'
    '            [ "None", "LinearIn", "LinearOut", "ExponentialIn", '
    '"ExponentialOut", "LogarithmicIn", "LogarithmicOut", "RoundedIn", '
    '"RoundedOut", "CosineIn", "CosineOut", "SCurveIn", "SCurveOut" ] } ], \n'
    '    "url":"Adjustable_Fade", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"CrossfadeClips", \n'
    '    "name":"Crossfade Clips", "params":\n'
    '      [  ], \n'
    '    "url":"Crossfade_Clips", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"CrossfadeClips", \n'
    '    "name":"Crossfade Clips", "params":\n'
    '      [  ], \n'
    '    "url":"Crossfade_Clips", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"CrossfadeTracks", \n'
    '    "name":"Crossfade Tracks", "params":\n'
    '      [ \n'
    '        { "key":"type", "type":"enum", "default":"ConstantGain", '
    '"enum":\n'
    '            [ "ConstantGain", "ConstantPower1", "ConstantPower2", '
    '"CustomCurve" ] },\n'
    '        { "key":"curve", "type":"double", "default":0 },\n'
    '        { "key":"direction", "type":"enum", "default":"Automatic", '
    '"enum":\n'
    '            [ "Automatic", "OutIn", "InOut" ] } ], \n'
    '    "url":"Crossfade_Tracks", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"CrossfadeTracks", \n'
    '    "name":"Crossfade Tracks", "params":\n'
    '      [ \n'
    '        { "key":"type", "type":"enum", "default":"ConstantGain", '
    '"enum":\n'
    '            [ "ConstantGain", "ConstantPower1", "ConstantPower2", '
    '"CustomCurve" ] },\n'
    '        { "key":"curve", "type":"double", "default":0 },\n'
    '        { "key":"direction", "type":"enum", "default":"Automatic", '
    '"enum":\n'
    '            [ "Automatic", "OutIn", "InOut" ] } ], \n'
    '    "url":"Crossfade_Tracks", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Delay", "name":"Delay", "params":\n'
    '      [ \n'
    '        { "key":"delay-type", "type":"enum", "default":"Regular", '
    '"enum":\n'
    '            [ "Regular", "BouncingBall", \n'
    '              "ReverseBouncingBall" ] },\n'
    '        { "key":"dgain", "type":"double", "default":0 },\n'
    '        { "key":"delay", "type":"double", "default":0 },\n'
    '        { "key":"pitch-type", "type":"enum", "default":"PitchTempo", '
    '"enum":\n'
    '            [ "PitchTempo", "LQPitchShift" ] },\n'
    '        { "key":"shift", "type":"double", "default":0 },\n'
    '        { "key":"number", "type":"int", "default":0 },\n'
    '        { "key":"constrain", "type":"enum", "default":"Yes", "enum":\n'
    '            [ "Yes", "No" ] } ], "url":"Delay", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Delay", "name":"Delay", "params":\n'
    '      [ \n'
    '        { "key":"delay-type", "type":"enum", "default":"Regular", '
    '"enum":\n'
    '            [ "Regular", "BouncingBall", \n'
    '              "ReverseBouncingBall" ] },\n'
    '        { "key":"dgain", "type":"double", "default":0 },\n'
    '        { "key":"delay", "type":"double", "default":0 },\n'
    '        { "key":"pitch-type", "type":"enum", "default":"PitchTempo", '
    '"enum":\n'
    '            [ "PitchTempo", "LQPitchShift" ] },\n'
    '        { "key":"shift", "type":"double", "default":0 },\n'
    '        { "key":"number", "type":"int", "default":0 },\n'
    '        { "key":"constrain", "type":"enum", "default":"Yes", "enum":\n'
    '            [ "Yes", "No" ] } ], "url":"Delay", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Limiter", "name":"Limiter", "params":\n'
    '      [ \n'
    '        { "key":"type", "type":"enum", "default":"SoftLimit", "enum":\n'
    '            [ "SoftLimit", "HardLimit", "SoftClip", "HardClip" ] },\n'
    '        { "key":"gain-L", "type":"double", "default":0 },\n'
    '        { "key":"gain-R", "type":"double", "default":0 },\n'
    '        { "key":"thresh", "type":"double", "default":0 },\n'
    '        { "key":"hold", "type":"double", "default":0 },\n'
    '        { "key":"makeup", "type":"enum", "default":"No", "enum":\n'
    '            [ "No", "Yes" ] } ], "url":"Limiter", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Limiter", "name":"Limiter", "params":\n'
    '      [ \n'
    '        { "key":"type", "type":"enum", "default":"SoftLimit", "enum":\n'
    '            [ "SoftLimit", "HardLimit", "SoftClip", "HardClip" ] },\n'
    '        { "key":"gain-L", "type":"double", "default":0 },\n'
    '        { "key":"gain-R", "type":"double", "default":0 },\n'
    '        { "key":"thresh", "type":"double", "default":0 },\n'
    '        { "key":"hold", "type":"double", "default":0 },\n'
    '        { "key":"makeup", "type":"enum", "default":"No", "enum":\n'
    '            [ "No", "Yes" ] } ], "url":"Limiter", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"NyquistPlug-inInstaller", \n'
    '    "name":"Nyquist Plug-in Installer", "params":\n'
    '      [ \n'
    '        { "key":"plug-in", "type":"string", "default":"" } ], \n'
    '    "url":"Nyquist_Plug-in_Installer", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"RegularIntervalLabels", \n'
    '    "name":"Regular Interval Labels", "params":\n'
    '      [ \n'
    '        { "key":"mode", "type":"enum", "default":"Both", "enum":\n'
    '            [ "Both", "Number", "Interval" ] },\n'
    '        { "key":"totalnum", "type":"int", "default":0 },\n'
    '        { "key":"interval", "type":"double", "default":0 },\n'
    '        { "key":"region", "type":"double", "default":0 },\n'
    '        { "key":"adjust", "type":"enum", "default":"No", "enum":\n'
    '            [ "No", "Yes" ] },\n'
    '        { "key":"labeltext", "type":"string", "default":"" },\n'
    '        { "key":"zeros", "type":"enum", "default":"TextOnly", "enum":\n'
    '            [ "TextOnly", "OneBefore", "TwoBefore", "ThreeBefore", '
    '"OneAfter", "TwoAfter", "ThreeAfter" ] },\n'
    '        { "key":"firstnum", "type":"int", "default":0 },\n'
    '        { "key":"verbose", "type":"enum", "default":"Details", "enum":\n'
    '            [ "Details", "Warnings", "None" ] } ], \n'
    '    "url":"Regular_Interval_Labels", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"RegularIntervalLabels", \n'
    '    "name":"Regular Interval Labels", "params":\n'
    '      [ \n'
    '        { "key":"mode", "type":"enum", "default":"Both", "enum":\n'
    '            [ "Both", "Number", "Interval" ] },\n'
    '        { "key":"totalnum", "type":"int", "default":0 },\n'
    '        { "key":"interval", "type":"double", "default":0 },\n'
    '        { "key":"region", "type":"double", "default":0 },\n'
    '        { "key":"adjust", "type":"enum", "default":"No", "enum":\n'
    '            [ "No", "Yes" ] },\n'
    '        { "key":"labeltext", "type":"string", "default":"" },\n'
    '        { "key":"zeros", "type":"enum", "default":"TextOnly", "enum":\n'
    '            [ "TextOnly", "OneBefore", "TwoBefore", "ThreeBefore", '
    '"OneAfter", "TwoAfter", "ThreeAfter" ] },\n'
    '        { "key":"firstnum", "type":"int", "default":0 },\n'
    '        { "key":"verbose", "type":"enum", "default":"Details", "enum":\n'
    '            [ "Details", "Warnings", "None" ] } ], \n'
    '    "url":"Regular_Interval_Labels", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SampleDataExport", \n'
    '    "name":"Sample Data Export", "params":\n'
    '      [ \n'
    '        { "key":"number", "type":"int", "default":0 },\n'
    '        { "key":"units", "type":"enum", "default":"dB", "enum":\n'
    '            [ "dB", "Linear" ] },\n'
    '        { "key":"filename", "type":"string", "default":"" },\n'
    '        { "key":"fileformat", "type":"enum", "default":"None", "enum":\n'
    '            [ "None", "Count", "Time" ] },\n'
    '        { "key":"header", "type":"enum", "default":"None", "enum":\n'
    '            [ "None", "Minimal", "Standard", "All" ] },\n'
    '        { "key":"optext", "type":"string", "default":"" },\n'
    '        { "key":"channel-layout", "type":"enum", "default":"SameLine", '
    '"enum":\n'
    '            [ "SameLine", "Alternate", "LFirst" ] },\n'
    '        { "key":"messages", "type":"enum", "default":"Yes", "enum":\n'
    '            [ "Yes", "Errors", "None" ] } ], \n'
    '    "url":"Sample_Data_Export", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SampleDataExport", \n'
    '    "name":"Sample Data Export", "params":\n'
    '      [ \n'
    '        { "key":"number", "type":"int", "default":0 },\n'
    '        { "key":"units", "type":"enum", "default":"dB", "enum":\n'
    '            [ "dB", "Linear" ] },\n'
    '        { "key":"filename", "type":"string", "default":"" },\n'
    '        { "key":"fileformat", "type":"enum", "default":"None", "enum":\n'
    '            [ "None", "Count", "Time" ] },\n'
    '        { "key":"header", "type":"enum", "default":"None", "enum":\n'
    '            [ "None", "Minimal", "Standard", "All" ] },\n'
    '        { "key":"optext", "type":"string", "default":"" },\n'
    '        { "key":"channel-layout", "type":"enum", "default":"SameLine", '
    '"enum":\n'
    '            [ "SameLine", "Alternate", "LFirst" ] },\n'
    '        { "key":"messages", "type":"enum", "default":"Yes", "enum":\n'
    '            [ "Yes", "Errors", "None" ] } ], \n'
    '    "url":"Sample_Data_Export", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SampleDataImport", \n'
    '    "name":"Sample Data Import", "params":\n'
    '      [ \n'
    '        { "key":"filename", "type":"string", "default":"" },\n'
    '        { "key":"bad-data", "type":"enum", "default":"ThrowError", '
    '"enum":\n'
    '            [ "ThrowError", "ReadAsZero" ] } ], \n'
    '    "url":"Sample_Data_Import", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"SampleDataImport", \n'
    '    "name":"Sample Data Import", "params":\n'
    '      [ \n'
    '        { "key":"filename", "type":"string", "default":"" },\n'
    '        { "key":"bad-data", "type":"enum", "default":"ThrowError", '
    '"enum":\n'
    '            [ "ThrowError", "ReadAsZero" ] } ], \n'
    '    "url":"Sample_Data_Import", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"StudioFadeOut", \n'
    '    "name":"Studio Fade Out", "params":\n'
    '      [  ], \n'
    '    "url":"Fades#studio_fadeout", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"StudioFadeOut", \n'
    '    "name":"Studio Fade Out", "params":\n'
    '      [  ], \n'
    '    "url":"Fades#studio_fadeout", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Tremolo", "name":"Tremolo", "params":\n'
    '      [ \n'
    '        { "key":"wave", "type":"enum", "default":"Sine", "enum":\n'
    '            [ "Sine", "Triangle", "Sawtooth", \n'
    '              "InverseSawtooth", "Square" ] },\n'
    '        { "key":"phase", "type":"int", "default":0 },\n'
    '        { "key":"wet", "type":"int", "default":0 },\n'
    '        { "key":"lfo", "type":"double", "default":0 } ], '
    '"url":"Tremolo", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"Tremolo", "name":"Tremolo", "params":\n'
    '      [ \n'
    '        { "key":"wave", "type":"enum", "default":"Sine", "enum":\n'
    '            [ "Sine", "Triangle", "Sawtooth", \n'
    '              "InverseSawtooth", "Square" ] },\n'
    '        { "key":"phase", "type":"int", "default":0 },\n'
    '        { "key":"wet", "type":"int", "default":0 },\n'
    '        { "key":"lfo", "type":"double", "default":0 } ], '
    '"url":"Tremolo", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"VocalRemover", "name":"Vocal Remover", "params":\n'
    '      [ \n'
    '        { "key":"action", "type":"enum", "default":"Remove Vocals", '
    '"enum":\n'
    '            [ "Remove Vocals", "View Help" ] },\n'
    '        { "key":"band-choice", "type":"enum", "default":"Simple", '
    '"enum":\n'
    '            [ "Simple", "Remove", "Retain" ] },\n'
    '        { "key":"low-range", "type":"double", "default":0 },\n'
    '        { "key":"high-range", "type":"double", "default":0 } ], '
    '"url":"Vocal_Remover", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"VocalRemover", "name":"Vocal Remover", "params":\n'
    '      [ \n'
    '        { "key":"action", "type":"enum", "default":"Remove Vocals", '
    '"enum":\n'
    '            [ "Remove Vocals", "View Help" ] },\n'
    '        { "key":"band-choice", "type":"enum", "default":"Simple", '
    '"enum":\n'
    '            [ "Simple", "Remove", "Retain" ] },\n'
    '        { "key":"low-range", "type":"double", "default":0 },\n'
    '        { "key":"high-range", "type":"double", "default":0 } ], '
    '"url":"Vocal_Remover", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"RissetDrum", "name":"Risset Drum", "params":\n'
    '      [ \n'
    '        { "key":"freq", "type":"double", "default":0 },\n'
    '        { "key":"decay", "type":"double", "default":0 },\n'
    '        { "key":"cf", "type":"double", "default":0 },\n'
    '        { "key":"bw", "type":"double", "default":0 },\n'
    '        { "key":"noise", "type":"double", "default":0 },\n'
    '        { "key":"gain", "type":"double", "default":0 } ], '
    '"url":"Risset_Drum", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"RissetDrum", "name":"Risset Drum", "params":\n'
    '      [ \n'
    '        { "key":"freq", "type":"double", "default":0 },\n'
    '        { "key":"decay", "type":"double", "default":0 },\n'
    '        { "key":"cf", "type":"double", "default":0 },\n'
    '        { "key":"bw", "type":"double", "default":0 },\n'
    '        { "key":"noise", "type":"double", "default":0 },\n'
    '        { "key":"gain", "type":"double", "default":0 } ], '
    '"url":"Risset_Drum", \n'
    '    "tip":"Released under terms of the GNU General Public License '
    'version 2" },\n'
    '  { "id":"CompareAudio", "name":"Compare Audio", "params":\n'
    '      [ \n'
    '        { "key":"Threshold", "type":"float", "default":0 } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#compare_Audio", \n'
    '    "tip":"Compares a range on two tracks." },\n'
    '  { "id":"Demo", "name":"Demo", "params":\n'
    '      [ \n'
    '        { "key":"Delay", "type":"float", "default":1 },\n'
    '        { "key":"Decay", "type":"float", "default":0.5 } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I", \n'
    '    "tip":"Does the demo action." },\n'
    '  { "id":"Drag", "name":"Drag", "params":\n'
    '      [ \n'
    '        { "key":"Id", "type":"int", "default":"unchanged" },\n'
    '        { "key":"Window", "type":"string", "default":"unchanged" },\n'
    '        { "key":"FromX", "type":"double", "default":"unchanged" },\n'
    '        { "key":"FromY", "type":"double", "default":"unchanged" },\n'
    '        { "key":"ToX", "type":"double", "default":"unchanged" },\n'
    '        { "key":"ToY", "type":"double", "default":"unchanged" },\n'
    '        { "key":"RelativeTo", "type":"enum", "default":"unchanged", '
    '"enum":\n'
    '            [ "Panel", "App", "Track0", "Track1" ] } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#move_mouse", \n'
    '    "tip":"Drags mouse from one place to another." },\n'
    '  { "id":"Export2", "name":"Export2", "params":\n'
    '      [ \n'
    '        { "key":"Filename", "type":"string", "default":"exported.wav" '
    '},\n'
    '        { "key":"NumChannels", "type":"int", "default":1 } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#export", \n'
    '    "tip":"Exports to a file." },\n'
    '  { "id":"GetInfo", "name":"Get Info", "params":\n'
    '      [ \n'
    '        { "key":"Type", "type":"enum", "default":"Commands", "enum":\n'
    '            [ "Commands", "Menus", "Preferences", "Tracks", "Clips", '
    '"Envelopes", "Labels", "Boxes" ] },\n'
    '        { "key":"Format", "type":"enum", "default":"JSON", "enum":\n'
    '            [ "JSON", "LISP", "Brief" ] } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#get_info", \n'
    '    "tip":"Gets information in JSON format." },\n'
    '  { "id":"GetPreference", "name":"Get Preference", "params":\n'
    '      [ \n'
    '        { "key":"Name", "type":"string", "default":"" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#get_preference", \n'
    '    "tip":"Gets the value of a single preference." },\n'
    '  { "id":"Help", "name":"Help", "params":\n'
    '      [ \n'
    '        { "key":"Command", "type":"string", "default":"Help" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#help", \n'
    '    "tip":"Gives help on a command." },\n'
    '  { "id":"Import2", "name":"Import2", "params":\n'
    '      [ \n'
    '        { "key":"Filename", "type":"string", "default":"" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#import", \n'
    '    "tip":"Imports from a file." },\n'
    '  { "id":"Message", "name":"Message", "params":\n'
    '      [ \n'
    '        { "key":"Text", "type":"string", "default":"Some message" } '
    '], \n'
    '    "url":"Extra_Menu:_Scriptables_II#message", \n'
    '    "tip":"Echos a message." },\n'
    '  { "id":"OpenProject2", "name":"Open Project2", "params":\n'
    '      [ \n'
    '        { "key":"Filename", "type":"string", "default":"test.aup" },\n'
    '        { "key":"AddToHistory", "type":"bool", "default":"unchanged" } '
    '], \n'
    '    "url":"Extra_Menu:_Scriptables_II#open_project", \n'
    '    "tip":"Opens a project." },\n'
    '  { "id":"SaveProject2", "name":"Save Project2", "params":\n'
    '      [ \n'
    '        { "key":"Filename", "type":"string", "default":"name.aup" },\n'
    '        { "key":"AddToHistory", "type":"bool", "default":"False" },\n'
    '        { "key":"Compress", "type":"bool", "default":"False" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#save_project", \n'
    '    "tip":"Saves a project." },\n'
    '  { "id":"Screenshot", "name":"Screenshot", "params":\n'
    '      [ \n'
    '        { "key":"Path", "type":"string", "default":"" },\n'
    '        { "key":"CaptureWhat", "type":"enum", "default":"Window", '
    '"enum":\n'
    '            [ "Window", "FullWindow", "WindowPlus", "Fullscreen", '
    '"Toolbars", "Effects", "Scriptables", "Preferences", "Selectionbar", \n'
    '              "SpectralSelection", "Tools", "Transport", "Mixer", '
    '"Meter", "PlayMeter", "RecordMeter", "Edit", "Device", "Scrub", '
    '"Play-at-Speed", "Trackpanel", "Ruler", "Tracks", "FirstTrack", '
    '"FirstTwoTracks", \n'
    '              "FirstThreeTracks", \n'
    '              "FirstFourTracks", "SecondTrack", "TracksPlus", '
    '"FirstTrackPlus", "AllTracks", "AllTracksPlus" ] },\n'
    '        { "key":"Background", "type":"enum", "default":"None", "enum":\n'
    '            [ "Blue", "White", "None" ] },\n'
    '        { "key":"ToTop", "type":"bool", "default":"True" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#screenshot_short_format", \n'
    '    "tip":"Takes screenshots." },\n'
    '  { "id":"SelectFrequencies", \n'
    '    "name":"Select Frequencies", "params":\n'
    '      [ \n'
    '        { "key":"High", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Low", "type":"double", "default":"unchanged" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#select_frequencies", \n'
    '    "tip":"Selects a frequency range." },\n'
    '  { "id":"SelectTime", "name":"Select Time", "params":\n'
    '      [ \n'
    '        { "key":"Start", "type":"double", "default":"unchanged" },\n'
    '        { "key":"End", "type":"double", "default":"unchanged" },\n'
    '        { "key":"RelativeTo", "type":"enum", "default":"unchanged", '
    '"enum":\n'
    '            [ "ProjectStart", "Project", "ProjectEnd", '
    '"SelectionStart", "Selection", "SelectionEnd" ] } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#select_time", \n'
    '    "tip":"Selects a time range." },\n'
    '  { "id":"SelectTracks", "name":"Select Tracks", "params":\n'
    '      [ \n'
    '        { "key":"Track", "type":"double", "default":"unchanged" },\n'
    '        { "key":"TrackCount", "type":"double", "default":"unchanged" '
    '},\n'
    '        { "key":"Mode", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Set", "Add", "Remove" ] } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#select_tracks", \n'
    '    "tip":"Selects a range of tracks." },\n'
    '  { "id":"Select", "name":"Select", "params":\n'
    '      [ \n'
    '        { "key":"Start", "type":"double", "default":"unchanged" },\n'
    '        { "key":"End", "type":"double", "default":"unchanged" },\n'
    '        { "key":"RelativeTo", "type":"enum", "default":"unchanged", '
    '"enum":\n'
    '            [ "ProjectStart", "Project", "ProjectEnd", '
    '"SelectionStart", "Selection", "SelectionEnd" ] },\n'
    '        { "key":"High", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Low", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Track", "type":"double", "default":"unchanged" },\n'
    '        { "key":"TrackCount", "type":"double", "default":"unchanged" '
    '},\n'
    '        { "key":"Mode", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Set", "Add", "Remove" ] } ], \n'
    '    "url":"Extra_Menu:_Scriptables_II#select", "tip":"Selects Audio." '
    '},\n'
    '  { "id":"SetClip", "name":"Set Clip", "params":\n'
    '      [ \n'
    '        { "key":"At", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Color", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Color0", "Color1", "Color2", "Color3" ] },\n'
    '        { "key":"Start", "type":"double", "default":"unchanged" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#set_clip", \n'
    '    "tip":"Sets various values for a clip." },\n'
    '  { "id":"SetEnvelope", "name":"Set Envelope", "params":\n'
    '      [ \n'
    '        { "key":"Time", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Value", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Delete", "type":"bool", "default":"unchanged" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#set_envelope", \n'
    '    "tip":"Sets an envelope point position." },\n'
    '  { "id":"SetLabel", "name":"Set Label", "params":\n'
    '      [ \n'
    '        { "key":"Label", "type":"int", "default":0 },\n'
    '        { "key":"Text", "type":"string", "default":"unchanged" },\n'
    '        { "key":"Start", "type":"double", "default":"unchanged" },\n'
    '        { "key":"End", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Selected", "type":"bool", "default":"unchanged" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#set_label", \n'
    '    "tip":"Sets various values for a label." },\n'
    '  { "id":"SetPreference", "name":"Set Preference", "params":\n'
    '      [ \n'
    '        { "key":"Name", "type":"string", "default":"" },\n'
    '        { "key":"Value", "type":"string", "default":"" },\n'
    '        { "key":"Reload", "type":"bool", "default":"False" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#set_preference", \n'
    '    "tip":"Sets the value of a single preference." },\n'
    '  { "id":"SetProject", "name":"Set Project", "params":\n'
    '      [ \n'
    '        { "key":"Name", "type":"string", "default":"unchanged" },\n'
    '        { "key":"Rate", "type":"double", "default":"unchanged" },\n'
    '        { "key":"X", "type":"int", "default":"unchanged" },\n'
    '        { "key":"Y", "type":"int", "default":"unchanged" },\n'
    '        { "key":"Width", "type":"int", "default":"unchanged" },\n'
    '        { "key":"Height", "type":"int", "default":"unchanged" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#set_project", \n'
    '    "tip":"Sets various values for a project." },\n'
    '  { "id":"SetTrackAudio", \n'
    '    "name":"Set Track Audio", "params":\n'
    '      [ \n'
    '        { "key":"Mute", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"Solo", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"Gain", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Pan", "type":"double", "default":"unchanged" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#set_track_audio", \n'
    '    "tip":"Sets various values for a track." },\n'
    '  { "id":"SetTrackStatus", \n'
    '    "name":"Set Track Status", "params":\n'
    '      [ \n'
    '        { "key":"Name", "type":"string", "default":"unchanged" },\n'
    '        { "key":"Selected", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"Focused", "type":"bool", "default":"unchanged" } ], \n'
    '    "url":"Extra_Menu:_Scriptables_I#set_track_status", \n'
    '    "tip":"Sets various values for a track." },\n'
    '  { "id":"SetTrackVisuals", \n'
    '    "name":"Set Track Visuals", "params":\n'
    '      [ \n'
    '        { "key":"Height", "type":"int", "default":"unchanged" },\n'
    '        { "key":"Display", "type":"enum", "default":"unchanged", '
    '"enum":\n'
    '            [ "Waveform", "Spectrogram" ] },\n'
    '        { "key":"Scale", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Linear", "dB" ] },\n'
    '        { "key":"Color", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Color0", "Color1", "Color2", "Color3" ] },\n'
    '        { "key":"VZoom", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Reset", "Times2", "HalfWave" ] },\n'
    '        { "key":"VZoomHigh", "type":"double", "default":"unchanged" },\n'
    '        { "key":"VZoomLow", "type":"double", "default":"unchanged" },\n'
    '        { "key":"SpecPrefs", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"SpectralSel", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"GrayScale", "type":"bool", "default":"unchanged" } '
    '], \n'
    '    "url":"Extra_Menu:_Scriptables_I#set_track_visuals", \n'
    '    "tip":"Sets various values for a track." },\n'
    '  { "id":"SetTrack", "name":"Set Track", "params":\n'
    '      [ \n'
    '        { "key":"Name", "type":"string", "default":"unchanged" },\n'
    '        { "key":"Selected", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"Focused", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"Mute", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"Solo", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"Gain", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Pan", "type":"double", "default":"unchanged" },\n'
    '        { "key":"Height", "type":"int", "default":"unchanged" },\n'
    '        { "key":"Display", "type":"enum", "default":"unchanged", '
    '"enum":\n'
    '            [ "Waveform", "Spectrogram" ] },\n'
    '        { "key":"Scale", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Linear", "dB" ] },\n'
    '        { "key":"Color", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Color0", "Color1", "Color2", "Color3" ] },\n'
    '        { "key":"VZoom", "type":"enum", "default":"unchanged", "enum":\n'
    '            [ "Reset", "Times2", "HalfWave" ] },\n'
    '        { "key":"VZoomHigh", "type":"double", "default":"unchanged" },\n'
    '        { "key":"VZoomLow", "type":"double", "default":"unchanged" },\n'
    '        { "key":"SpecPrefs", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"SpectralSel", "type":"bool", "default":"unchanged" },\n'
    '        { "key":"GrayScale", "type":"bool", "default":"unchanged" } '
    '], \n'
    '    "url":"Extra_Menu:_Scriptables_II#set_track", \n'
    '    "tip":"Sets various values for a track." } ]\n')

# Sample return data for 'GetInfo: Type=Menus'
getinfo_menus_str = (
    '[ \n'
    '  { "depth":0, "flags":0, "label":"File", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"New", "accel":"Ctrl+N", "id":"New" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"Open...", "accel":"Ctrl+O", '
    '"id":"Open" },\n'
    '  { "depth":1, "flags":1, "label":"Recent Files", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Jams\\Jam 20190301\\Jam 20190301.aup", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Jams\\Jam 20200306\\Jam 20200306.aup", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Highball 20200216.aup", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK18.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK17.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK16.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK15.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK14.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK13.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK12.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK11.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Users\\athomas\\Documents\\Audacity\\Spoken '
    'Tones\\Gigs\\Highball\\2020-02-16\\Raw Tracks\\TRK10.WAV", "accel":"" '
    '},\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Clear", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Close", "accel":"Ctrl+W", '
    '"id":"Close" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Save Project", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Save Project", "accel":"Ctrl+S", '
    '"id":"Save" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Save Project As...", "accel":"", "id":"SaveAs" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Save Lossless Copy of Project...", "accel":"", '
    '"id":"SaveCopy" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Save Compressed Copy of Project...", "accel":"", '
    '"id":"SaveCompressed" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Export", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Export as MP3", "accel":"", '
    '"id":"ExportMp3" },\n'
    '  { "depth":2, "flags":0, "label":"Export as WAV", "accel":"", '
    '"id":"ExportWav" },\n'
    '  { "depth":2, "flags":0, "label":"Export as OGG", "accel":"", '
    '"id":"ExportOgg" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Export Audio...", "accel":"Ctrl+Shift+E", "id":"Export" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Export Selected Audio...", "accel":"", "id":"ExportSel" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Export Labels...", "accel":"", "id":"ExportLabels" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Export Multiple...", "accel":"Ctrl+Shift+L", '
    '"id":"ExportMultiple" },\n'
    '  { "depth":2, "flags":0, "label":"Export MIDI...", "accel":"", '
    '"id":"ExportMIDI" },\n'
    '  { "depth":1, "flags":1, "label":"Import", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Audio...", "accel":"Ctrl+Shift+I", '
    '"id":"ImportAudio" },\n'
    '  { "depth":2, "flags":0, "label":"Labels...", "accel":"", '
    '"id":"ImportLabels" },\n'
    '  { "depth":2, "flags":0, "label":"MIDI...", "accel":"", '
    '"id":"ImportMIDI" },\n'
    '  { "depth":2, "flags":0, "label":"Raw Data...", "accel":"", '
    '"id":"ImportRaw" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Page Setup...", "accel":"", '
    '"id":"PageSetup" },\n'
    '  { "depth":1, "flags":0, "label":"Print...", "accel":"", "id":"Print" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Exit", "accel":"Ctrl+Q", "id":"Exit" '
    '},\n'
    '  { "depth":0, "flags":0, "label":"Edit", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Undo", "accel":"Ctrl+Z", "id":"Undo" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"Redo", "accel":"Ctrl+Y", "id":"Redo" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Cut", "accel":"Ctrl+X", "id":"Cut" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"Delete", "accel":"Ctrl+K", '
    '"id":"Delete" },\n'
    '  { "depth":1, "flags":0, "label":"Copy", "accel":"Ctrl+C", "id":"Copy" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"Paste", "accel":"Ctrl+V", '
    '"id":"Paste" },\n'
    '  { "depth":1, "flags":0, "label":"Duplicate", "accel":"Ctrl+D", '
    '"id":"Duplicate" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Remove Special", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Split Cut", "accel":"Ctrl+Alt+X", '
    '"id":"SplitCut" },\n'
    '  { "depth":2, "flags":0, "label":"Split Delete", "accel":"Ctrl+Alt+K", '
    '"id":"SplitDelete" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Silence Audio", "accel":"Ctrl+L", '
    '"id":"Silence" },\n'
    '  { "depth":2, "flags":0, "label":"Trim Audio", "accel":"Ctrl+T", '
    '"id":"Trim" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Clip Boundaries", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Split", "accel":"Ctrl+I", '
    '"id":"Split" },\n'
    '  { "depth":2, "flags":0, "label":"Split New", "accel":"", '
    '"id":"SplitNew" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Join", "accel":"", "id":"Join" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Detach at Silences", "accel":"", "id":"Disjoin" },\n'
    '  { "depth":1, "flags":1, "label":"Labels", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Edit Labels...", "accel":"", '
    '"id":"EditLabels" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Add Label at Selection", "accel":"Ctrl+B", "id":"AddLabel" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Add Label at Playback Position", "accel":"Ctrl+M", \n'
    '    "id":"AddLabelPlaying" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Paste Text to New Label", "accel":"", "id":"PasteNewLabel" '
    '},\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":2, \n'
    '    "label":"Type to Create a Label (on/off)", "accel":"", \n'
    '    "id":"TypeToCreateLabel" },\n'
    '  { "depth":1, "flags":1, "label":"Labeled Audio", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Cut", "accel":"", "id":"CutLabels" '
    '},\n'
    '  { "depth":2, "flags":0, "label":"Delete", "accel":"", '
    '"id":"DeleteLabels" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Split Cut", "accel":"Alt+Shift+X", '
    '"id":"SplitCutLabels" },\n'
    '  { "depth":2, "flags":0, "label":"Split Delete", '
    '"accel":"Alt+Shift+K", \n'
    '    "id":"SplitDeleteLabels" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Silence Audio", "accel":"", '
    '"id":"SilenceLabels" },\n'
    '  { "depth":2, "flags":0, "label":"Copy", "accel":"Alt+Shift+C", '
    '"id":"CopyLabels" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Split", "accel":"", '
    '"id":"SplitLabels" },\n'
    '  { "depth":2, "flags":0, "label":"Join", "accel":"", "id":"JoinLabels" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Detach at Silences", "accel":"Alt+Shift+J", '
    '"id":"DisjoinLabels" },\n'
    '  { "depth":1, "flags":0, "label":"Metadata...", "accel":"", '
    '"id":"EditMetaData" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Preferences...", "accel":"Ctrl+P", '
    '"id":"Preferences" },\n'
    '  { "depth":0, "flags":0, "label":"Select", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"All", "accel":"Ctrl+A", '
    '"id":"SelectAll" },\n'
    '  { "depth":1, "flags":0, "label":"None", "accel":"", "id":"SelectNone" '
    '},\n'
    '  { "depth":1, "flags":1, "label":"Tracks", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"In All Tracks", '
    '"accel":"Ctrl+Shift+K", "id":"SelAllTracks" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"In All Sync-Locked Tracks", "accel":"Ctrl+Shift+Y", \n'
    '    "id":"SelSyncLockTracks" },\n'
    '  { "depth":1, "flags":1, "label":"Region", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Left at Playback Position", "accel":"[", \n'
    '    "id":"SetLeftSelection" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Right at Playback Position", "accel":"]", \n'
    '    "id":"SetRightSelection" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Track Start to Cursor", "accel":"Shift+J", \n'
    '    "id":"SelTrackStartToCursor" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Cursor to Track End", "accel":"Shift+K", \n'
    '    "id":"SelCursorToTrackEnd" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Track Start to End", "accel":"", \n'
    '    "id":"SelTrackStartToEnd" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Store Selection", "accel":"", "id":"SelSave" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Retrieve Selection", "accel":"", "id":"SelRestore" },\n'
    '  { "depth":1, "flags":1, "label":"Spectral", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Toggle Spectral Selection", "accel":"Q", \n'
    '    "id":"ToggleSpectralSelection" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Next Higher Peak Frequency", "accel":"", \n'
    '    "id":"NextHigherPeakFrequency" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Next Lower Peak Frequency", "accel":"", \n'
    '    "id":"NextLowerPeakFrequency" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Clip Boundaries", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Previous Clip Boundary to Cursor", "accel":"", \n'
    '    "id":"SelPrevClipBoundaryToCursor" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Cursor to Next Clip Boundary", "accel":"", \n'
    '    "id":"SelCursorToNextClipBoundary" },\n'
    '  { "depth":2, "flags":0, "label":"Previous Clip", "accel":"Alt+,", '
    '"id":"SelPrevClip" },\n'
    '  { "depth":2, "flags":0, "label":"Next Clip", "accel":"Alt+.", '
    '"id":"SelNextClip" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Cursor to Stored Cursor Position", "accel":"", \n'
    '    "id":"SelCursorStoredCursor" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Store Cursor Position", "accel":"", \n'
    '    "id":"StoreCursorPosition" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"At Zero Crossings", "accel":"Z", "id":"ZeroCross" },\n'
    '  { "depth":0, "flags":0, "label":"View", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Zoom", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Zoom In", "accel":"Ctrl+1", '
    '"id":"ZoomIn" },\n'
    '  { "depth":2, "flags":0, "label":"Zoom Normal", "accel":"Ctrl+2", '
    '"id":"ZoomNormal" },\n'
    '  { "depth":2, "flags":0, "label":"Zoom Out", "accel":"Ctrl+3", '
    '"id":"ZoomOut" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Zoom to Selection", "accel":"Ctrl+E", "id":"ZoomSel" },\n'
    '  { "depth":2, "flags":0, "label":"Zoom Toggle", "accel":"Shift+Z", '
    '"id":"ZoomToggle" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Advanced Vertical Zooming", "accel":"", '
    '"id":"AdvancedVZoom" },\n'
    '  { "depth":1, "flags":1, "label":"Track Size", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Fit to Width", "accel":"Ctrl+F", '
    '"id":"FitInWindow" },\n'
    '  { "depth":2, "flags":0, "label":"Fit to Height", '
    '"accel":"Ctrl+Shift+F", "id":"FitV" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Collapse All Tracks", "accel":"Ctrl+Shift+C", \n'
    '    "id":"CollapseAllTracks" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Expand Collapsed Tracks", "accel":"Ctrl+Shift+X", \n'
    '    "id":"ExpandAllTracks" },\n'
    '  { "depth":1, "flags":1, "label":"Skip to", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Selection Start", "accel":"", "id":"SkipSelStart" },\n'
    '  { "depth":2, "flags":0, "label":"Selection End", "accel":"", '
    '"id":"SkipSelEnd" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"History...", "accel":"", '
    '"id":"UndoHistory" },\n'
    '  { "depth":1, "flags":0, "label":"Karaoke...", "accel":"", '
    '"id":"Karaoke" },\n'
    '  { "depth":1, "flags":0, "label":"Mixer Board...", "accel":"", '
    '"id":"MixerBoard" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Toolbars", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Reset Toolbars", "accel":"", '
    '"id":"ResetToolbars" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":2, \n'
    '    "label":"Transport Toolbar", "accel":"", \n'
    '    "id":"ShowTransportTB" },\n'
    '  { "depth":2, "flags":2, "label":"Tools Toolbar", "accel":"", '
    '"id":"ShowToolsTB" },\n'
    '  { "depth":2, "flags":2, \n'
    '    "label":"Recording Meter Toolbar", "accel":"", \n'
    '    "id":"ShowRecordMeterTB" },\n'
    '  { "depth":2, "flags":2, \n'
    '    "label":"Playback Meter Toolbar", "accel":"", \n'
    '    "id":"ShowPlayMeterTB" },\n'
    '  { "depth":2, "flags":2, "label":"Mixer Toolbar", "accel":"", '
    '"id":"ShowMixerTB" },\n'
    '  { "depth":2, "flags":2, "label":"Edit Toolbar", "accel":"", '
    '"id":"ShowEditTB" },\n'
    '  { "depth":2, "flags":2, \n'
    '    "label":"Play-at-Speed Toolbar", "accel":"", \n'
    '    "id":"ShowTranscriptionTB" },\n'
    '  { "depth":2, "flags":0, "label":"Scrub Toolbar", "accel":"", \n'
    '    "id":"ShowScrubbingTB" },\n'
    '  { "depth":2, "flags":2, "label":"Device Toolbar", "accel":"", '
    '"id":"ShowDeviceTB" },\n'
    '  { "depth":2, "flags":2, \n'
    '    "label":"Selection Toolbar", "accel":"", \n'
    '    "id":"ShowSelectionTB" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Spectral Selection Toolbar", "accel":"", \n'
    '    "id":"ShowSpectralSelectionTB" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Extra Menus (on/off)", "accel":"", "id":"ShowExtraMenus" '
    '},\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Show Clipping (on/off)", "accel":"", "id":"ShowClipping" '
    '},\n'
    '  { "depth":0, "flags":0, "label":"Transport", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Playing", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Play/Stop", "accel":"Space", '
    '"id":"PlayStop" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Play/Stop and Set Cursor", "accel":"X", '
    '"id":"PlayStopSelect" },\n'
    '  { "depth":2, "flags":0, "label":"Loop Play", "accel":"Shift+Space", '
    '"id":"PlayLooped" },\n'
    '  { "depth":2, "flags":0, "label":"Pause", "accel":"P", "id":"Pause" '
    '},\n'
    '  { "depth":1, "flags":1, "label":"Recording", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Record", "accel":"R", \n'
    '    "id":"Record1stChoice" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Record New Track", "accel":"Shift+R", \n'
    '    "id":"Record2ndChoice" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Timer Record...", "accel":"Shift+T", "id":"TimerRecord" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Punch and Roll Record", "accel":"Shift+D", '
    '"id":"PunchAndRoll" },\n'
    '  { "depth":2, "flags":0, "label":"Pause", "accel":"P", "id":"Pause" '
    '},\n'
    '  { "depth":1, "flags":1, "label":"Scrubbing", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Scrub", "accel":"", "id":"Scrub" },\n'
    '  { "depth":2, "flags":0, "label":"Seek", "accel":"", "id":"Seek" },\n'
    '  { "depth":2, "flags":0, "label":"Scrub Ruler", "accel":"", \n'
    '    "id":"ToggleScrubRuler" },\n'
    '  { "depth":1, "flags":1, "label":"Cursor to", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Selection Start", "accel":"", "id":"CursSelStart" },\n'
    '  { "depth":2, "flags":0, "label":"Selection End", "accel":"", '
    '"id":"CursSelEnd" },\n'
    '  { "depth":2, "flags":0, "label":"Track Start", "accel":"J", '
    '"id":"CursTrackStart" },\n'
    '  { "depth":2, "flags":0, "label":"Track End", "accel":"K", '
    '"id":"CursTrackEnd" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Previous Clip Boundary", "accel":"", \n'
    '    "id":"CursPrevClipBoundary" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Next Clip Boundary", "accel":"", \n'
    '    "id":"CursNextClipBoundary" },\n'
    '  { "depth":2, "flags":0, "label":"Project Start", "accel":"Home", \n'
    '    "id":"CursProjectStart" },\n'
    '  { "depth":2, "flags":0, "label":"Project End", "accel":"End", '
    '"id":"CursProjectEnd" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Play Region", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Lock", "accel":"", '
    '"id":"LockPlayRegion" },\n'
    '  { "depth":2, "flags":0, "label":"Unlock", "accel":"", \n'
    '    "id":"UnlockPlayRegion" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Rescan Audio Devices", "accel":"", "id":"RescanDevices" '
    '},\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Transport Options", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Sound Activation Level...", "accel":"", \n'
    '    "id":"SoundActivationLevel" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Sound Activated Recording (on/off)", "accel":"", \n'
    '    "id":"SoundActivation" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Pinned Play/Record Head (on/off)", "accel":"", '
    '"id":"PinnedHead" },\n'
    '  { "depth":2, "flags":2, \n'
    '    "label":"Overdub (on/off)", "accel":"", "id":"Overdub" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Software Playthrough (on/off)", "accel":"", '
    '"id":"SWPlaythrough" },\n'
    '  { "depth":0, "flags":0, "label":"Tracks", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Add New", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Mono Track", "accel":"", '
    '"id":"NewMonoTrack" },\n'
    '  { "depth":2, "flags":0, "label":"Stereo Track", "accel":"", '
    '"id":"NewStereoTrack" },\n'
    '  { "depth":2, "flags":0, "label":"Label Track", "accel":"", '
    '"id":"NewLabelTrack" },\n'
    '  { "depth":2, "flags":0, "label":"Time Track", "accel":"", '
    '"id":"NewTimeTrack" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Mix", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Mix Stereo Down to Mono", "accel":"", "id":"Stereo to '
    'Mono" },\n'
    '  { "depth":2, "flags":0, "label":"Mix and Render", "accel":"", '
    '"id":"MixAndRender" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Mix and Render to New Track", "accel":"", \n'
    '    "id":"MixAndRenderToNewTrack" },\n'
    '  { "depth":1, "flags":0, "label":"Resample...", "accel":"", '
    '"id":"Resample" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Remove Tracks", "accel":"", '
    '"id":"RemoveTracks" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Mute/Unmute", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Mute All Tracks", "accel":"Ctrl+U", "id":"MuteAllTracks" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Unmute All Tracks", "accel":"Ctrl+Shift+U", \n'
    '    "id":"UnmuteAllTracks" },\n'
    '  { "depth":1, "flags":1, "label":"Pan", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Left", "accel":"", "id":"PanLeft" '
    '},\n'
    '  { "depth":2, "flags":0, "label":"Right", "accel":"", "id":"PanRight" '
    '},\n'
    '  { "depth":2, "flags":0, "label":"Center", "accel":"", '
    '"id":"PanCenter" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Align Tracks", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Align End to End", "accel":"", "id":"Align_EndToEnd" },\n'
    '  { "depth":2, "flags":0, "label":"Align Together", "accel":"", '
    '"id":"Align_Together" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Start to Zero", "accel":"", \n'
    '    "id":"Align_StartToZero" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Start to Cursor/Selection Start", "accel":"", \n'
    '    "id":"Align_StartToSelStart" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Start to Selection End", "accel":"", \n'
    '    "id":"Align_StartToSelEnd" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"End to Cursor/Selection Start", "accel":"", \n'
    '    "id":"Align_EndToSelStart" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"End to Selection End", "accel":"", \n'
    '    "id":"Align_EndToSelEnd" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Move Selection with Tracks (on/off)", "accel":"", \n'
    '    "id":"MoveSelectionWithTracks" },\n'
    '  { "depth":1, "flags":1, "label":"Sort Tracks", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"By Start Time", "accel":"", '
    '"id":"SortByTime" },\n'
    '  { "depth":2, "flags":0, "label":"By Name", "accel":"", '
    '"id":"SortByName" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":2, \n'
    '    "label":"Sync-Lock Tracks (on/off)", "accel":"", "id":"SyncLock" '
    '},\n'
    '  { "depth":0, "flags":0, "label":"Generate", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Add / Remove Plug-ins...", "accel":"", \n'
    '    "id":"ManageGenerators" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Chirp...", "accel":"", '
    '"id":"Chirp..." },\n'
    '  { "depth":1, "flags":0, "label":"DTMF Tones...", "accel":"", '
    '"id":"DTMF Tones..." },\n'
    '  { "depth":1, "flags":0, "label":"Noise...", "accel":"", '
    '"id":"Noise..." },\n'
    '  { "depth":1, "flags":0, "label":"Silence...", "accel":"", '
    '"id":"Silence..." },\n'
    '  { "depth":1, "flags":0, "label":"Tone...", "accel":"", "id":"Tone..." '
    '},\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Pluck...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\pluck.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\pluck.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity\\plug-ins\\pluck.ny", '
    '"accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\pluck.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Rhythm Track...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\rhythmtrack.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\rhythmtrack.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\rhythmtrack.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\rhythmtrack.ny" '
    '},\n'
    '  { "depth":1, "flags":1, "label":"Risset Drum...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\rissetdrum.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\rissetdrum.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\rissetdrum.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\rissetdrum.ny" '
    '},\n'
    '  { "depth":0, "flags":0, "label":"Effect", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Add / Remove Plug-ins...", "accel":"", '
    '"id":"ManageEffects" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Repeat Last Effect", "accel":"Ctrl+R", \n'
    '    "id":"RepeatLastEffect" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Amplify...", "accel":"", '
    '"id":"Amplify..." },\n'
    '  { "depth":1, "flags":0, "label":"Auto Duck...", "accel":"", '
    '"id":"Auto Duck..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Bass and Treble...", "accel":"", \n'
    '    "id":"Bass and Treble..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Change Pitch...", "accel":"", \n'
    '    "id":"Change Pitch..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Change Speed...", "accel":"", \n'
    '    "id":"Change Speed..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Change Tempo...", "accel":"", \n'
    '    "id":"Change Tempo..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Click Removal...", "accel":"", \n'
    '    "id":"Click Removal..." },\n'
    '  { "depth":1, "flags":0, "label":"Compressor...", "accel":"Shift+C", '
    '"id":"Compressor..." },\n'
    '  { "depth":1, "flags":0, "label":"Distortion...", "accel":"", '
    '"id":"Distortion..." },\n'
    '  { "depth":1, "flags":0, "label":"Echo...", "accel":"", "id":"Echo..." '
    '},\n'
    '  { "depth":1, "flags":0, "label":"Fade In", "accel":"", "id":"Fade In" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"Fade Out", "accel":"", "id":"Fade '
    'Out" },\n'
    '  { "depth":1, "flags":0, "label":"Invert", "accel":"", "id":"Invert" '
    '},\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Noise Reduction...", "accel":"", \n'
    '    "id":"Noise Reduction..." },\n'
    '  { "depth":1, "flags":0, "label":"Normalize...", "accel":"Shift+N", '
    '"id":"Normalize..." },\n'
    '  { "depth":1, "flags":0, "label":"Paulstretch...", "accel":"", '
    '"id":"Paulstretch..." },\n'
    '  { "depth":1, "flags":0, "label":"Phaser...", "accel":"", '
    '"id":"Phaser..." },\n'
    '  { "depth":1, "flags":0, "label":"Repair", "accel":"", "id":"Repair" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"Repeat...", "accel":"", '
    '"id":"Repeat..." },\n'
    '  { "depth":1, "flags":0, "label":"Reverb...", "accel":"", '
    '"id":"Reverb..." },\n'
    '  { "depth":1, "flags":0, "label":"Reverse", "accel":"", "id":"Reverse" '
    '},\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Sliding Stretch...", "accel":"", \n'
    '    "id":"Sliding Stretch..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Truncate Silence...", "accel":"", \n'
    '    "id":"Truncate Silence..." },\n'
    '  { "depth":1, "flags":0, "label":"Wahwah...", "accel":"", '
    '"id":"Wahwah..." },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Adjustable Fade...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\adjustable-fade.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\adjustable-fade.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\adjustable-fade.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\adjustable-fade.ny" },\n'
    '  { "depth":1, "flags":1, "label":"Clip Fix...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\clipfix.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\clipfix.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity\\plug-ins\\clipfix.ny", '
    '"accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\clipfix.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Crossfade Clips", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\crossfadeclips.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\crossfadeclips.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\crossfadeclips.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\crossfadeclips.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Crossfade Tracks...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\crossfadetracks.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\crossfadetracks.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\crossfadetracks.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\crossfadetracks.ny" },\n'
    '  { "depth":1, "flags":1, "label":"Delay...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\delay.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\delay.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity\\plug-ins\\delay.ny", '
    '"accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\delay.ny" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"High Pass Filter...", "accel":"", \n'
    '    "id":"High Pass Filter..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"High-Pass Filter...", "accel":"", \n'
    '    "id":"High-Pass Filter..." },\n'
    '  { "depth":1, "flags":1, "label":"Limiter...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\limiter.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\limiter.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity\\plug-ins\\limiter.ny", '
    '"accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\limiter.ny" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Low Pass Filter...", "accel":"", \n'
    '    "id":"Low Pass Filter..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Low-Pass Filter...", "accel":"", \n'
    '    "id":"Low-Pass Filter..." },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Notch Filter...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\notch.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\notch.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity\\plug-ins\\notch.ny", '
    '"accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\notch.ny" },\n'
    '  { "depth":1, "flags":0, "label":"SC4...", "accel":"", "id":"SC4..." '
    '},\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Spectral edit multi tool", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SpectralEditMulti.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SpectralEditMulti.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SpectralEditMulti.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SpectralEditMulti.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Spectral edit parametric EQ...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SpectralEditParametricEQ.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SpectralEditParametricEQ.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SpectralEditParametricEQ.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SpectralEditParametricEQ.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Spectral edit shelves...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SpectralEditShelves.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SpectralEditShelves.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SpectralEditShelves.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SpectralEditShelves.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Studio Fade Out", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\StudioFadeOut.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\StudioFadeOut.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\StudioFadeOut.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\StudioFadeOut.ny" },\n'
    '  { "depth":1, "flags":1, "label":"Tremolo...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\tremolo.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\tremolo.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity\\plug-ins\\tremolo.ny", '
    '"accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\tremolo.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Vocal Reduction and Isolation...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\vocalrediso.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\vocalrediso.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\vocalrediso.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\vocalrediso.ny" '
    '},\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Vocal Remover...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\vocalremover.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\vocalremover.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\vocalremover.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\vocalremover.ny" '
    '},\n'
    '  { "depth":1, "flags":1, "label":"Vocoder...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\vocoder.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\vocoder.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity\\plug-ins\\vocoder.ny", '
    '"accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\vocoder.ny" },\n'
    '  { "depth":0, "flags":0, "label":"Analyze", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Add / Remove Plug-ins...", "accel":"", \n'
    '    "id":"ManageAnalyzers" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Contrast...", "accel":"", \n'
    '    "id":"ContrastAnalyser" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Plot Spectrum...", "accel":"", "id":"PlotSpectrum" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Find Clipping...", "accel":"", \n'
    '    "id":"Find Clipping..." },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Beat Finder...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\beat.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\beat.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity\\plug-ins\\beat.ny", '
    '"accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\beat.ny" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Regular Interval Labels...", "accel":"", \n'
    '    "id":"Regular Interval Labels..." },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Silence Finder...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SilenceMarker.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SilenceMarker.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SilenceMarker.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SilenceMarker.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Sound Finder...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SoundFinder.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\SoundFinder.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\SoundFinder.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity\\plug-ins\\SoundFinder.ny" '
    '},\n'
    '  { "depth":0, "flags":0, "label":"Tools", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Add / Remove Plug-ins...", "accel":"", "id":"ManageTools" '
    '},\n'
    '  { "depth":1, "flags":0, "label":"Macros...", "accel":"", '
    '"id":"ManageMacros" },\n'
    '  { "depth":1, "flags":1, "label":"Apply Macro", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Palette...", "accel":"", \n'
    '    "id":"ApplyMacrosPalette" },\n'
    '  { "depth":2, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":2, "flags":0, "label":"Fade Ends", "accel":"", '
    '"id":"Macro_FadeEnds" },\n'
    '  { "depth":2, "flags":0, "label":"MP3 Conversion", "accel":"", \n'
    '    "id":"Macro_MP3Conversion" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Screenshot...", "accel":"", \n'
    '    "id":"FancyScreenshot" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Run Benchmark...", "accel":"", "id":"Benchmark" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Nyquist Prompt...", "accel":"", \n'
    '    "id":"Nyquist Prompt..." },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Nyquist Plug-in Installer...", "accel":"", \n'
    '    "id":"Nyquist Plug-in Installer..." },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Regular Interval Labels...", "accel":"", \n'
    '    "id":"Regular Interval Labels..." },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Sample Data Export...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\sample-data-export.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\sample-data-export.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\sample-data-export.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\sample-data-export.ny" },\n'
    '  { "depth":1, "flags":1, \n'
    '    "label":"Sample Data Import...", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\sample-data-import.ny", "accel":"", \n'
    '    "id":"C:\\Program Files (x86)\\Audacity (Local '
    'Build)\\plug-ins\\sample-data-import.ny" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\sample-data-import.ny", "accel":"", \n'
    '    "id":"C:\\Program Files '
    '(x86)\\Audacity\\plug-ins\\sample-data-import.ny" },\n'
    '  { "depth":0, "flags":0, "label":"Help", "accel":"" },\n'
    '  { "depth":1, "flags":0, "label":"Quick Help...", "accel":"", '
    '"id":"QuickHelp" },\n'
    '  { "depth":1, "flags":0, "label":"Manual...", "accel":"", '
    '"id":"Manual" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":1, "label":"Diagnostics", "accel":"" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Audio Device Info...", "accel":"", "id":"DeviceInfo" },\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"MIDI Device Info...", "accel":"", "id":"MidiDeviceInfo" '
    '},\n'
    '  { "depth":2, "flags":0, "label":"Show Log...", "accel":"", "id":"Log" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Generate Support Data...", "accel":"", "id":"CrashReport" '
    '},\n'
    '  { "depth":2, "flags":0, \n'
    '    "label":"Check Dependencies...", "accel":"", "id":"CheckDeps" },\n'
    '  { "depth":1, "flags":0, "label":"----", "accel":"" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"Check for Updates...", "accel":"", "id":"Updates" },\n'
    '  { "depth":1, "flags":0, \n'
    '    "label":"About Audacity...", "accel":"", "id":"About" } ]\n')

# Sample return data for 'GetInfo: Type=Preferences'
getinfo_preferences_str = (
    '[ \n'
    '  { "id":"/AudioIO/Host", "prompt":"&Host:", "type":"enum", '
    '"default":"", "enum":\n'
    '      [ "MME", \n'
    '        "Windows DirectSound", "Windows WASAPI" ] },\n'
    '  { "id":"/AudioIO/LatencyDuration", \n'
    '    "prompt":"&Buffer length:", "type":"number", "default":100 },\n'
    '  { "id":"/AudioIO/LatencyCorrection", \n'
    '    "prompt":"&Latency compensation:", "type":"number", "default":-130 '
    '},\n'
    '  { "id":"/AudioIO/EffectsPreviewLen", "prompt":"&Length:", '
    '"type":"number", "default":6 },\n'
    '  { "id":"/AudioIO/CutPreviewBeforeLen", \n'
    '    "prompt":"&Before cut region:", "type":"number", "default":2 },\n'
    '  { "id":"/AudioIO/CutPreviewAfterLen", \n'
    '    "prompt":"&After cut region:", "type":"number", "default":1 },\n'
    '  { "id":"/AudioIO/SeekShortPeriod", "prompt":"&Short period:", '
    '"type":"number", "default":1 },\n'
    '  { "id":"/AudioIO/SeekLongPeriod", "prompt":"Lo&ng period:", '
    '"type":"number", "default":15 },\n'
    '  { "id":"/AudioIO/VariSpeedPlay", \n'
    '    "prompt":"&Vari-Speed Play", "type":"bool", "default":"true" },\n'
    '  { "id":"/AudioIO/Microfades", "prompt":"&Micro-fades", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/AudioIO/UnpinnedScrubbing", \n'
    '    "prompt":"Always scrub un&pinned", "type":"bool", "default":"true" '
    '},\n'
    '  { "id":"/AudioIO/Duplex", \n'
    '    "prompt":"Play &other tracks while recording (overdub)", '
    '"type":"bool", "default":"true" },\n'
    '  { "id":"/AudioIO/SWPlaythrough", \n'
    '    "prompt":"&Software playthrough of input", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/PreferNewTrackRecord", \n'
    '    "prompt":"Record on a new track", "type":"bool", "default":"false" '
    '},\n'
    '  { "id":"/Warnings/DropoutDetected", \n'
    '    "prompt":"Detect dropouts", "type":"bool", "default":"true" },\n'
    '  { "id":"/AudioIO/SoundActivatedRecord", "prompt":"&Enable", '
    '"type":"bool", "default":"false" },\n'
    '  { "id":"/AudioIO/SilenceLevel", "prompt":"Le&vel (dB):", '
    '"type":"number", "default":-50 },\n'
    '  { "id":"/GUI/TrackNames/RecordingNameCustom", \n'
    '    "prompt":"Custom Track &Name", "type":"bool", "default":"false" },\n'
    '  { "id":"/GUI/TrackNames/RecodingTrackName", "prompt":"", '
    '"type":"string", "default":"Recorded_Audio" },\n'
    '  { "id":"/GUI/TrackNames/TrackNumber", "prompt":"&Track Number", '
    '"type":"bool", "default":"false" },\n'
    '  { "id":"/GUI/TrackNames/DateStamp", "prompt":"System &Date", '
    '"type":"bool", "default":"false" },\n'
    '  { "id":"/GUI/TrackNames/TimeStamp", "prompt":"System T&ime", '
    '"type":"bool", "default":"false" },\n'
    '  { "id":"/AudioIO/PreRoll", "prompt":"Pre-ro&ll:", "type":"number", '
    '"default":5 },\n'
    '  { "id":"/AudioIO/Crossfade", "prompt":"Cross&fade:", "type":"number", '
    '"default":10 },\n'
    '  { "id":"/MidiIO/Host", "prompt":"&Host:", "type":"enum", '
    '"default":"", "enum":\n'
    '      [ "MMSystem" ] },\n'
    '  { "id":"/MidiIO/SynthLatency", \n'
    '    "prompt":"MIDI Synth L&atency (ms):", "type":"number", "default":5 '
    '},\n'
    '  { "id":"/SamplingRate/DefaultProjectSampleRate", "prompt":"", '
    '"type":"number", "default":44100 },\n'
    '  { "id":"/SamplingRate/DefaultProjectSampleFormatChoice", \n'
    '    "prompt":"Default Sample &Format:", "type":"enum", \n'
    '    "default":"Format32BitFloat", "enum":\n'
    '      [ "Format16Bit", "Format24Bit", \n'
    '        "Format32BitFloat" ] },\n'
    '  { "id":"/Quality/LibsoxrSampleRateConverterChoice", \n'
    '    "prompt":"Sample Rate Con&verter:", "type":"enum", '
    '"default":"MediumQuality", "enum":\n'
    '      [ "LowQuality", "MediumQuality", "HighQuality", "BestQuality" ] '
    '},\n'
    '  { "id":"Quality/DitherAlgorithmChoice", "prompt":"&Dither:", '
    '"type":"enum", "default":"None", "enum":\n'
    '      [ "None", "Rectangle", "Triangle", "Shaped" ] },\n'
    '  { "id":"/Quality/LibsoxrHQSampleRateConverterChoice", \n'
    '    "prompt":"Sample Rate Conver&ter:", "type":"enum", '
    '"default":"BestQuality", "enum":\n'
    '      [ "LowQuality", "MediumQuality", "HighQuality", "BestQuality" ] '
    '},\n'
    '  { "id":"Quality/HQDitherAlgorithmChoice", "prompt":"Dit&her:", '
    '"type":"enum", "default":"Shaped", "enum":\n'
    '      [ "None", "Rectangle", "Triangle", "Shaped" ] },\n'
    '  { "id":"/Locale/Language", "prompt":"&Language:", "type":"enum", '
    '"default":"", "enum":\n'
    '      [ "", "af", "id", "bs", "ca", "cy", "da", "de", "en", "es", "eu", '
    '"eu_ES", "fr", "ga", "gl", "hr", "it", "lt", "hu", "nl", "nb", "oc", '
    '"pl", "pt_PT", "pt_BR", "ro", "sk", "sl", "sr_RS@latin", "fi", "sv", '
    '"vi", "tr", "ca_ES@valencia", "cs", "el", "be", "bg", "mk", "ru", '
    '"sr_RS", "tg", "uk", "hy", "he", "ar", "fa", "hi", "bn", "ta", "my", '
    '"ka", "km", "zh_CN", "zh_TW", "ja", "ko" ] },\n'
    '  { "id":"/GUI/Help", \n'
    '    "prompt":"Location of &Manual:", "type":"enum", "default":"Local", '
    '"enum":\n'
    '      [ "Local", "FromInternet" ] },\n'
    '  { "id":"/GUI/Theme", "prompt":"Th&eme:", "type":"enum", '
    '"default":"light", "enum":\n'
    '      [ "classic", "light", "dark", "high-contrast", "custom" ] },\n'
    '  { "id":"/GUI/EnvdBRange", \n'
    '    "prompt":"Meter dB &range:", "type":"enum", "default":"60", '
    '"enum":\n'
    '      [ "36", "48", "60", "72", "84", "96", "120", "145" ] },\n'
    '  { "id":"/GUI/ShowSplashScreen", \n'
    '    "prompt":"Show \'How to Get &Help\' at launch", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/GUI/ShowExtraMenus", \n'
    '    "prompt":"Show e&xtra menus", "type":"bool", "default":"false" },\n'
    '  { "id":"/GUI/BeepOnCompletion", \n'
    '    "prompt":"&Beep on completion of longer activities", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/RetainLabels", \n'
    '    "prompt":"Re&tain labels if selection snaps to a label", '
    '"type":"bool", "default":"false" },\n'
    '  { "id":"/GUI/BlendThemes", \n'
    '    "prompt":"B&lend system and Audacity theme", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/GUI/RtlWorkaround", \n'
    '    "prompt":"Use mostly Left-to-Right layouts in RTL languages", '
    '"type":"bool", "default":"true" },\n'
    '  { "id":"/GUI/TracksFitVerticallyZoomed", \n'
    '    "prompt":"Auto-&fit track height", "type":"bool", "default":"false" '
    '},\n'
    '  { "id":"/GUI/ShowTrackNameInWaveform", \n'
    '    "prompt":"Sho&w audio track name as overlay", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/CollapseToHalfWave", \n'
    '    "prompt":"Use &half-wave display when collapsed", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/AutoScroll", \n'
    '    "prompt":"A&uto-scroll if head unpinned", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/GUI/DefaultViewModeChoice", \n'
    '    "prompt":"Default &view mode:", "type":"enum", '
    '"default":"Waveform", "enum":\n'
    '      [ "Waveform", "WaveformDB", "Spectrogram" ] },\n'
    '  { "id":"/GUI/SampleViewChoice", \n'
    '    "prompt":"Display &samples:", "type":"enum", "default":"StemPlot", '
    '"enum":\n'
    '      [ "ConnectDots", "StemPlot" ] },\n'
    '  { "id":"/GUI/TrackNames/DefaultTrackName", \n'
    '    "prompt":"Default audio track &name:", "type":"string", '
    '"default":"Audio Track" },\n'
    '  { "id":"/GUI/ZoomPreset1Choice", "prompt":"Preset 1:", "type":"enum", '
    '"default":"ZoomDefault", "enum":\n'
    '      [ "FitToWidth", \n'
    '        "ZoomToSelection", "ZoomDefault", "Minutes", "Seconds", \n'
    '        "FifthsOfSeconds", \n'
    '        "TenthsOfSeconds", \n'
    '        "TwentiethsOfSeconds", \n'
    '        "FiftiethsOfSeconds", \n'
    '        "HundredthsOfSeconds", \n'
    '        "FiveHundredthsOfSeconds", "MilliSeconds", "Samples", \n'
    '        "FourPixelsPerSample", "MaxZoom" ] },\n'
    '  { "id":"/GUI/ZoomPreset2Choice", "prompt":"Preset 2:", '
    '"type":"enum", \n'
    '    "default":"FourPixelsPerSample", "enum":\n'
    '      [ "FitToWidth", \n'
    '        "ZoomToSelection", "ZoomDefault", "Minutes", "Seconds", \n'
    '        "FifthsOfSeconds", \n'
    '        "TenthsOfSeconds", \n'
    '        "TwentiethsOfSeconds", \n'
    '        "FiftiethsOfSeconds", \n'
    '        "HundredthsOfSeconds", \n'
    '        "FiveHundredthsOfSeconds", "MilliSeconds", "Samples", \n'
    '        "FourPixelsPerSample", "MaxZoom" ] },\n'
    '  { "id":"/GUI/SelectAllOnNone", \n'
    '    "prompt":"&Select all audio, if selection required", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/EnableCutLines", \n'
    '    "prompt":"Enable cut &lines", "type":"bool", "default":"false" },\n'
    '  { "id":"/GUI/AdjustSelectionEdges", \n'
    '    "prompt":"Enable &dragging selection edges", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/GUI/EditClipCanMove", \n'
    '    "prompt":"Editing a clip can &move other clips", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/GUI/CircularTrackNavigation", \n'
    '    "prompt":"\\"Move track focus\\" c&ycles repeatedly through '
    'tracks", "type":"bool", "default":"false" },\n'
    '  { "id":"/GUI/TypeToCreateLabel", \n'
    '    "prompt":"&Type to create a label", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/DialogForNameNewLabel", \n'
    '    "prompt":"Use dialog for the &name of a new label", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/ScrollBeyondZero", \n'
    '    "prompt":"Enable scrolling left of &zero", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/VerticalZooming", \n'
    '    "prompt":"Advanced &vertical zooming", "type":"bool", '
    '"default":"false" },\n'
    '  { "id":"/GUI/Solo", "prompt":"Solo &Button:", "type":"enum", '
    '"default":"Standard", "enum":\n'
    '      [ "Simple", "Multi", "None" ] },\n'
    '  { "id":"/AudioFiles/ShowId3Dialog", \n'
    '    "prompt":"S&how Metadata Tags editor before export", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/AudioFiles/SkipSilenceAtBeginning", \n'
    '    "prompt":"&Ignore blank space at the beginning", "type":"bool", '
    '"default":"false" },\n'
    '  { '
    '"id":"/ExtendedImport/OverrideExtendedImportByOpenFileDialogChoice", \n'
    '    "prompt":"A&ttempt to use filter in OpenFile dialog first", '
    '"type":"bool", "default":"true" },\n'
    '  { "id":"/Directories/TempDir", "prompt":"&Location:", '
    '"type":"string", "default":"" },\n'
    '  { "id":"/Warnings/FirstProjectSave", \n'
    '    "prompt":"Saving &projects", "type":"bool", "default":"true" },\n'
    '  { "id":"/GUI/EmptyCanBeDirty", \n'
    '    "prompt":"Saving &empty project", "type":"bool", "default":"true" '
    '},\n'
    '  { "id":"/Warnings/DiskSpaceWarning", \n'
    '    "prompt":"&Low disk space at launch or new project", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/Warnings/MixMono", \n'
    '    "prompt":"Mixing down to &mono during export", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/Warnings/MixStereo", \n'
    '    "prompt":"Mixing down to &stereo during export", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/Warnings/MixUnknownChannels", \n'
    '    "prompt":"Mixing down on export (&Custom FFmpeg or external '
    'program)", "type":"bool", "default":"true" },\n'
    '  { "id":"/LADSPA/Enable", "prompt":"&LADSPA", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/LV2/Enable", "prompt":"LV&2", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/Nyquist/Enable", "prompt":"N&yquist", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/Vamp/Enable", "prompt":"&Vamp", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/VST/Enable", "prompt":"V&ST", "type":"bool", '
    '"default":"true" },\n'
    '  { "id":"/Effects/GroupBy", \n'
    '    "prompt":"S&ort or Group:", "type":"enum", "default":"sortby:name", '
    '"enum":\n'
    '      [ "sortby:name", \n'
    '        "sortby:publisher:name", \n'
    '        "sortby:type:name", \n'
    '        "groupby:publisher", "groupby:type" ] },\n'
    '  { "id":"/Effects/MaxPerGroup", \n'
    '    "prompt":"&Maximum effects per group (0 to disable):", '
    '"type":"number", "default":0 } ]\n')

# Sample return data for 'GetInfo: Type=Tracks'
getinfo_tracks_str = (
    '[ \n'
    '  { "name":"L - AT2050", "focused":1, "selected":0, "kind":"wave", '
    '"start":0, "end":10603.5, "pan":0, "gain":3.16228, "channels":1, '
    '"solo":0, "mute":0, "VZoomMin":-1, "VZoomMax":1 },\n'
    '  { "name":"R - SM57", "focused":0, "selected":0, "kind":"wave", '
    '"start":0, "end":10603.5, "pan":0, "gain":3.16228, "channels":1, '
    '"solo":0, "mute":0, "VZoomMin":-1, "VZoomMax":1 },\n'
    '  { "name":"Label Track", "focused":0, "selected":0, "kind":"label" } '
    ']\n')

# Sample return data for 'GetInfo: Type=Clips'
getinfo_clips_str = (
    '[ \n'
    '  { "track":0, "start":0, "end":8328.9, "color":0 },\n'
    '  { "track":0, "start":8328.9, "end":10603.5, "color":0 },\n'
    '  { "track":1, "start":0, "end":8328.9, "color":0 },\n'
    '  { "track":1, "start":8328.9, "end":10603.5, "color":0 } ]\n')

# Sample return data for 'GetInfo: Type=Envelopes'
getinfo_envelopes_str = (
    '[ \n'
    '  { "track":0, "clip":0, "start":0, "points":\n'
    '      [  ], "end":8328.9 },\n'
    '  { "track":0, "clip":1, "start":8328.9, "points":\n'
    '      [  ], "end":10603.5 },\n'
    '  { "track":0, "clip":2, "start":0, "points":\n'
    '      [  ], "end":8328.9 },\n'
    '  { "track":0, "clip":3, "start":8328.9, "points":\n'
    '      [  ], "end":10603.5 } ]\n')

# Sample return data for 'GetInfo: Type=Labels'
getinfo_labels_str = (
    '[ \n'
    '  [ 2,\n'
    '    [ \n'
    '      [ 134.861, 134.861, \n'
    '        "Just Don\'t Touch It" ],\n'
    '      [ 526.071, 526.071, "Blues Riff" ],\n'
    '      [ 2489.18, 2489.18, "Next" ],\n'
    '      [ 4419.59, 4419.59, "CCR" ],\n'
    '      [ 5248.82, 5248.82, "Magazine Drive" ],\n'
    '      [ 5700.59, 5700.59, "Crooked Folk" ],\n'
    '      [ 6008.21, 6008.21, "Holdfast" ],\n'
    '      [ 8328.9, 8328.9, "Post Food" ] ] ] ]\n')

# Sample return data for 'GetInfo: Type=Boxes'
getinfo_boxes_str = (
    '[ \n'
    '  { "depth":0, \n'
    '    "name":"Audacity Window", "box":\n'
    '      [ -8, -8, 1927, 1167 ] },\n'
    '  { "depth":1, "label":"MenuBar", "box":\n'
    '      [ 2, 32, 1921, 53 ] },\n'
    '  { "depth":1, "label":"Panel", "id":-31990, "box":\n'
    '      [ 2, 166, 1921, 1088 ] },\n'
    '  { "depth":2, \n'
    '    "label":"Horizontal Scrollbar", "id":1001, "box":\n'
    '      [ 138, 1072, 1904, 1088 ] },\n'
    '  { "depth":2, \n'
    '    "label":"Vertical Scrollbar", "id":1002, "box":\n'
    '      [ 1905, 166, 1921, 1071 ] },\n'
    '  { "depth":2, "label":"Track Panel", "id":1003, "box":\n'
    '      [ 2, 166, 1904, 1071 ] },\n'
    '  { "depth":3, "label":"VRuler", "box":\n'
    '      [ 102, 171, 137, 313 ] },\n'
    '  { "depth":3, "label":"VRuler", "box":\n'
    '      [ 102, 321, 137, 463 ] },\n'
    '  { "depth":3, "label":"VRuler", "box":\n'
    '      [ 102, 471, 137, 536 ] },\n'
    '  { "depth":1, "label":"Panel", "id":-31991, "box":\n'
    '      [ 2, 52, 1921, 165 ] },\n'
    '  { "depth":2, "label":"ToolDock", "id":1, "box":\n'
    '      [ 2, 52, 1921, 136 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Audacity Transport Toolbar", "id":0, "box":\n'
    '      [ 3, 53, 329, 107 ] },\n'
    '  { "depth":4, "label":"Grabber", "id":0, "box":\n'
    '      [ 3, 53, 12, 107 ] },\n'
    '  { "depth":4, "label":"*Pause (P)", "id":11000, "box":\n'
    '      [ 19, 56, 66, 103 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Play (Space) / Loop Play (Shift+Space)", "id":11001, '
    '"box":\n'
    '      [ 69, 56, 116, 103 ] },\n'
    '  { "depth":4, "label":"*Stop", "id":11002, "box":\n'
    '      [ 119, 56, 166, 103 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Skip to Start (Home) / Select to Start (Shift+Home)", '
    '"id":11004, "box":\n'
    '      [ 169, 56, 216, 103 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Skip to End (End) / Select to End (Shift+End)", '
    '"id":11003, "box":\n'
    '      [ 219, 56, 266, 103 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Record (R) / Record New Track (Shift+R)", "id":11005, '
    '"box":\n'
    '      [ 277, 56, 324, 103 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Audacity Tools Toolbar", "id":1, "box":\n'
    '      [ 331, 53, 424, 107 ] },\n'
    '  { "depth":4, "label":"Grabber", "id":1, "box":\n'
    '      [ 331, 53, 340, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Selection Tool (F1)", "id":11200, "box":\n'
    '      [ 342, 53, 368, 79 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Envelope Tool (F2)", "id":11201, "box":\n'
    '      [ 370, 53, 396, 79 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Draw Tool (F3)", "id":11202, "box":\n'
    '      [ 398, 53, 424, 79 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Zoom Tool (F4)", "id":11203, "box":\n'
    '      [ 342, 81, 368, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Time Shift Tool (F5)", "id":11204, "box":\n'
    '      [ 370, 81, 396, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Multi Tool (F6)", "id":11205, "box":\n'
    '      [ 398, 81, 424, 107 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Audacity Recording Meter Toolbar", "id":3, "box":\n'
    '      [ 426, 53, 885, 79 ] },\n'
    '  { "depth":4, "label":"Grabber", "id":3, "box":\n'
    '      [ 426, 53, 435, 79 ] },\n'
    '  { "depth":4, "label":"Record Meter", "id":-31984, "box":\n'
    '      [ 437, 53, 880, 79 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Audacity Playback Meter Toolbar", "id":4, "box":\n'
    '      [ 887, 53, 1345, 79 ] },\n'
    '  { "depth":4, "label":"Grabber", "id":4, "box":\n'
    '      [ 887, 53, 896, 79 ] },\n'
    '  { "depth":4, "label":"Play Meter", "id":-31982, "box":\n'
    '      [ 898, 53, 1340, 79 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Audacity Mixer Toolbar", "id":5, "box":\n'
    '      [ 1347, 53, 1673, 79 ] },\n'
    '  { "depth":4, "label":"Grabber", "id":5, "box":\n'
    '      [ 1347, 53, 1356, 79 ] },\n'
    '  { "depth":4, \n'
    '    "label":"Recording Volume", "id":-31979, "box":\n'
    '      [ 1383, 54, 1511, 78 ] },\n'
    '  { "depth":4, \n'
    '    "label":"Playback Volume", "id":-31977, "box":\n'
    '      [ 1537, 54, 1666, 78 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Audacity Edit Toolbar", "id":6, "box":\n'
    '      [ 426, 81, 788, 107 ] },\n'
    '  { "depth":4, "label":"Grabber", "id":6, "box":\n'
    '      [ 426, 81, 435, 107 ] },\n'
    '  { "depth":4, "label":"*Cut (Ctrl+X)", "id":11300, "box":\n'
    '      [ 437, 81, 463, 107 ] },\n'
    '  { "depth":4, "label":"*Copy (Ctrl+C)", "id":11301, "box":\n'
    '      [ 464, 81, 490, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Paste (Ctrl+V)", "id":11302, "box":\n'
    '      [ 491, 81, 517, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Trim audio outside selection (Ctrl+T)", "id":11303, '
    '"box":\n'
    '      [ 518, 81, 544, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Silence audio selection (Ctrl+L)", "id":11304, "box":\n'
    '      [ 545, 81, 571, 107 ] },\n'
    '  { "depth":4, "label":"*Undo (Ctrl+Z)", "id":11305, "box":\n'
    '      [ 586, 81, 612, 107 ] },\n'
    '  { "depth":4, "label":"*Redo (Ctrl+Y)", "id":11306, "box":\n'
    '      [ 613, 81, 639, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Zoom In (Ctrl+1)", "id":11307, "box":\n'
    '      [ 654, 81, 680, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Zoom Out (Ctrl+3)", "id":11308, "box":\n'
    '      [ 681, 81, 707, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Fit selection to width (Ctrl+E)", "id":11310, "box":\n'
    '      [ 708, 81, 734, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Fit project to width (Ctrl+F)", "id":11311, "box":\n'
    '      [ 735, 81, 761, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Zoom Toggle (Shift+Z)", "id":11309, "box":\n'
    '      [ 762, 81, 788, 107 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Audacity Play-at-Speed Toolbar", "id":7, "box":\n'
    '      [ 790, 81, 980, 107 ] },\n'
    '  { "depth":4, "label":"Grabber", "id":7, "box":\n'
    '      [ 790, 81, 799, 107 ] },\n'
    '  { "depth":4, \n'
    '    "label":"*Play-at-Speed / Looped-Play-at-Speed", "id":0, "box":\n'
    '      [ 801, 81, 827, 107 ] },\n'
    '  { "depth":4, "label":"Playback Speed", "id":1, "box":\n'
    '      [ 828, 82, 973, 106 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Audacity Device Toolbar", "id":9, "box":\n'
    '      [ 3, 109, 885, 135 ] },\n'
    '  { "depth":4, "label":"Grabber", "id":9, "box":\n'
    '      [ 3, 109, 12, 135 ] },\n'
    '  { "depth":4, "label":"Audio Host", "id":-31974, "box":\n'
    '      [ 14, 111, 166, 133 ] },\n'
    '  { "depth":4, \n'
    '    "label":"Recording Device", "id":-31972, "box":\n'
    '      [ 192, 111, 446, 133 ] },\n'
    '  { "depth":4, \n'
    '    "label":"Recording Channels", "id":-31971, "box":\n'
    '      [ 447, 111, 603, 133 ] },\n'
    '  { "depth":4, \n'
    '    "label":"Playback Device", "id":-31969, "box":\n'
    '      [ 629, 111, 880, 133 ] },\n'
    '  { "depth":2, "label":"Timeline", "id":-31989, "box":\n'
    '      [ 2, 137, 1921, 165 ] },\n'
    '  { "depth":3, "label":"Grabber", "id":-31989, "box":\n'
    '      [ 3, 137, 13, 163 ] },\n'
    '  { "depth":3, "label":"*Click to pin", "id":7006, "box":\n'
    '      [ 14, 137, 40, 163 ] },\n'
    '  { "depth":1, "label":"ToolDock", "id":2, "box":\n'
    '      [ 2, 1089, 1921, 1145 ] },\n'
    '  { "depth":2, \n'
    '    "label":"Audacity Selection Toolbar", "id":10, "box":\n'
    '      [ 3, 1090, 676, 1144 ] },\n'
    '  { "depth":3, "label":"Grabber", "id":10, "box":\n'
    '      [ 3, 1090, 12, 1144 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Project Rate (Hz)", "id":-31958, "box":\n'
    '      [ 19, 1099, 110, 1113 ] },\n'
    '  { "depth":3, "label":"Snap-To", "id":-31956, "box":\n'
    '      [ 124, 1099, 170, 1113 ] },\n'
    '  { "depth":3, "label":"Audio Position", "id":-31954, "box":\n'
    '      [ 210, 1099, 288, 1113 ] },\n'
    '  { "depth":3, \n'
    '    "label":"Project Rate (Hz)", "id":2701, "box":\n'
    '      [ 19, 1119, 98, 1141 ] },\n'
    '  { "depth":3, "label":"Snap To", "id":2702, "box":\n'
    '      [ 124, 1119, 196, 1141 ] },\n'
    '  { "depth":3, "label":"Audio Position", "id":2709, "box":\n'
    '      [ 212, 1121, 359, 1142 ] },\n'
    '  { "depth":3, "label":"Show", "id":2704, "box":\n'
    '      [ 371, 1095, 670, 1117 ] },\n'
    '  { "depth":3, "label":"Start", "id":2705, "box":\n'
    '      [ 373, 1121, 520, 1142 ] },\n'
    '  { "depth":3, "label":"End", "id":2708, "box":\n'
    '      [ 526, 1121, 673, 1142 ] },\n'
    '  { "depth":1, "label":"status_line", "id":0, "box":\n'
    '      [ 2, 1146, 1921, 1168 ] },\n'
    '  { "depth":1, "label":"Get Info", "id":-31575, "box":\n'
    '      [ 850, 490, 1072, 687 ] },\n'
    '  { "depth":2, \n'
    '    "label":"Applying Get Info...", "id":-31574, "box":\n'
    '      [ 873, 536, 1049, 551 ] },\n'
    '  { "depth":2, "label":"gauge", "id":-31573, "box":\n'
    '      [ 868, 567, 1054, 581 ] },\n'
    '  { "depth":2, "label":"Elapsed Time:", "id":-31572, "box":\n'
    '      [ 908, 592, 979, 607 ] },\n'
    '  { "depth":2, "label":"00:00:00", "id":-31571, "box":\n'
    '      [ 990, 592, 1031, 607 ] },\n'
    '  { "depth":2, \n'
    '    "label":"Remaining Time:", "id":-31570, "box":\n'
    '      [ 891, 618, 979, 633 ] },\n'
    '  { "depth":2, "label":"00:00:00", "id":-31569, "box":\n'
    '      [ 990, 618, 1031, 633 ] },\n'
    '  { "depth":2, "label":"button", "id":5101, "box":\n'
    '      [ 957, 644, 1044, 669 ] } ]\n')
