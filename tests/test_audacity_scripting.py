
from datetime import datetime
import logging
import os
from os import mkdir
from os.path import abspath, dirname, isdir, isfile, join
import stat
import sys
from time import sleep
import unittest
from unittest.mock import Mock
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
log_file = join(log_dir_path, current_time + '.log')

if isfile(log_file):
    sleep(1)
    current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = join(log_dir_path, current_time + '.log')

# Create the Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create the Handler for logging data to a file
logger_handler = logging.FileHandler(log_file)
logger_handler.setLevel(logging.DEBUG)

# Create a Formatter for formatting the log messages
logger_formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - '
                                     '%(message)s')

# Add the Formatter to the Handler
logger_handler.setFormatter(logger_formatter)

# Add the Handler to the Logger
logger.addHandler(logger_handler)


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
# https://codereview.stackexchange.com/questions/ \
#                                      88672/python-wrapper-for-windows-pipes
# https://www.python-course.eu/pipes.php

# Create pipes for testing
# https://github.com/audacity/audacity/blob/master/lib-src/mod-script-pipe/PipeServer.cpp
# http://timgolden.me.uk/pywin32-docs/win32pipe.html


class AudacityMock(object):
    def __init__(self):
        if sys.platform == 'win32':
            self._init_mock_win()
        else:
            self._init_mock_unix()

    def _init_mock_win(self):
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
            # raise exception
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
            # raise exception
            logger.info('fromfile not valid')
        else:
            logger.info('fromfile is valid')

    def _init_mock_unix(self):
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
            raise

    def run_pipe_server(self):
        if sys.platform == 'win32':
            self._run_pipe_server_win()
        else:
            self._run_pipe_server_unix()

    def _run_pipe_server_win(self):
        tofile_conn_res = win32pipe.ConnectNamedPipe(self.tofile, None)
        fromfile_conn_res = win32pipe.ConnectNamedPipe(self.fromfile, None)

        logger.info('tofile connected: {}'.format(str(tofile_conn_res == 0)))
        logger.info('fromfile connected: '
                    '{}'.format(str(fromfile_conn_res == 0)))

        if tofile_conn_res == 0 and fromfile_conn_res == 0:
            try:
                while(True):
                    success, data = win32file.ReadFile(self.tofile,
                                                       self.buffer_size,
                                                       None)
                    if success != 0:
                        # Raise Exception
                        logger.info('Read Failed!')
                        break
                    else:
                        logger.info('Read succeeded!')

                    command = data.decode().split('\r')[0]
                    response = self.evaluate_command(command)

                    success = win32file.WriteFile(self.fromfile,
                                                  response.encode())[0]
                    if success != 0:
                        # Raise Exception
                        logger.info('Write Failed!')
                        break
                    else:
                        logger.info('Write succeeded!')
            except pywintypes.error as err:
                logger.info(err)
            finally:
                win32file.FlushFileBuffers(self.tofile)
                win32pipe.DisconnectNamedPipe(self.tofile)
                win32file.CloseHandle(self.tofile)

                win32file.FlushFileBuffers(self.fromfile)
                win32pipe.DisconnectNamedPipe(self.fromfile)
                win32file.CloseHandle(self.fromfile)

    def _run_pipe_server_unix(self):
        try:
            tofile = open(self.toname, 'r')
            fromfile = open(self.fromname, 'w')

            while(True):
                command = tofile.readline()
                if len(command) == 0:
                    break

                response = self.evaluate_command(command)

                fromfile.write(response)
                fromfile.flush()
        except IOError as err:
            logger.info(err)
            raise
        except BrokenPipeError as err:
            logger.info(err)
        finally:
            tofile.close()
            fromfile.close()
            os.unlink(self.toname)
            os.unlink(self.fromname)

    def evaluate_command(self, command):
        command_list = command.split(':')
        scripting_id = command_list[0]
        logger.info('scripting_id: {}'.format(scripting_id))

        response = ''
        if len(command_list) == 1:
            response = 'No colon. Not yet implemented.\n'
        elif len(command_list) == 2:
            if scripting_id in scripting_id_list:
                response = 'BatchCommand finished: OK\n'
            else:
                response = ('Your batch command of {} was not recognized.\n'
                            'BatchCommand finished: '
                            'Failed!\n'.format(scripting_id))
        elif len(command_list) > 2:
            response = 'Multiple colons. Not yet implemented.\n'
        else:
            response = 'Something went terribly wrong.\n'

        return response + '\n'

scripting_id_list = [
    'CursNextClipBoundary', 'SilenceFinder', 'Repeat', 'Align_StartToSelStart',
    'DTMF Tones...', 'FindClipping', 'SelPrevClip', 'CutLabels', 'Wahwah',
    'SelCursorToNextClipBoundary', 'Scrub', 'SetPreference', 'UndoHistory',
    'MixAndRender', 'ManageTools', 'TruncateSilence', 'ShowExtraMenus',
    'ClipFix', 'CursSelEnd', 'Repeat...', 'ShowScrubbingTB', 'ExportMIDI',
    'JoinLabels', 'Record2ndChoice', 'Fade Out', 'ImportAudio',
    'SelTrackStartToCursor', 'New', 'SetRightSelection', 'Export2',
    'CursProjectEnd', 'DisjoinLabels', 'VocalRemover', 'NewStereoTrack',
    'EditLabels', 'Reverb', 'SetLeftSelection', 'NyquistPrompt',
    'NextLowerPeakFrequency', 'Seek', 'AddLabel', 'ShowClipping',
    'ShowTranscriptionTB', 'AutoDuck', 'FitInWindow', 'Join', 'DeleteLabels',
    'ShowEditTB', 'Record1stChoice', 'Align_EndToEnd', 'Vocoder', 'Paste',
    'NewMonoTrack', 'TypeToCreateLabel', 'Silence...', 'Sliding Stretch...',
    'SplitLabels', 'SelAllTracks', 'SelSave', 'NextHigherPeakFrequency',
    'Align_StartToZero', 'BeatFinder', 'PageSetup', 'SelectTracks',
    'VocalReductionAndIsolation', 'HighPassFilter', 'ShowToolsTB', 'Help',
    'PlotSpectrum', 'MuteAllTracks', 'SelRestore', 'Overdub',
    'NyquistPlug-inInstaller', 'ZoomOut', 'SoundFinder', 'Select',
    'SortByName', 'Export', 'Compressor...', 'TimerRecord', 'GetPreference',
    'Duplicate', 'SaveCopy', 'RepeatLastEffect', 'QuickHelp', 'CopyLabels',
    'PanLeft', 'Reverb...', 'Repair', 'Print', 'RemoveTracks',
    'Noise Reduction...', 'Copy', 'CursTrackStart', 'ImportMIDI',
    'ShowDeviceTB', 'Delay', 'Import2', 'MoveSelectionWithTracks', 'Log',
    'Normalize', 'FancyScreenshot', 'MixAndRenderToNewTrack', 'CrossfadeClips',
    'EditMetaData', 'SetEnvelope', 'BassAndTreble', 'RissetDrum',
    'Low Pass Filter...', 'ShowPlayMeterTB', 'PanCenter', 'Distortion',
    'SelectNone', 'Save', 'ZoomNormal', 'ManageGenerators', 'SC4...',
    'ExportOgg', 'High Pass Filter...', 'Open', 'RescanDevices', 'SetProject',
    'UnmuteAllTracks', 'ExportWav', 'SetTrack', 'ZeroCross', 'Screenshot',
    'AddLabelPlaying', 'SampleDataExport', 'Click Removal...', 'RhythmTrack',
    'ManageMacros', 'PasteNewLabel', 'CursTrackEnd', 'SaveProject2',
    'ContrastAnalyser', 'SaveCompressed', 'ManageEffects', 'Cut',
    'Macro_MP3Conversion', 'Undo', 'SplitCutLabels', 'Bass and Treble...',
    'AdvancedVZoom', 'CursPrevClipBoundary', 'Amplify', 'Noise', 'SkipSelEnd',
    'SelPrevClipBoundaryToCursor', 'Low-passFilter', 'SortByTime',
    'LockPlayRegion', 'Preferences', 'Echo', 'SpectralEditParametricEq',
    'CrashReport', 'SetLabel', 'Paulstretch', 'CheckDeps',
    'Regular Interval Labels...', 'SampleDataImport', 'About', 'ClickRemoval',
    'ExportMp3', 'SelSyncLockTracks', 'Nyquist Plug-in Installer...',
    'PlayStop', 'Tone', 'CursProjectStart', 'PlayStopSelect', 'Delete',
    'CollapseAllTracks', 'CursSelStart', 'StudioFadeOut', 'ZoomSel',
    'AdjustableFade', 'ResetToolbars', 'Manual', 'ShowMixerTB',
    'Low-Pass Filter...', 'SelCursorStoredCursor', 'Truncate Silence...',
    'Change Pitch...', 'SetTrackVisuals', 'Auto Duck...', 'ZoomToggle',
    'Normalize...', 'Tone...', 'Tremolo', 'SilenceLabels', 'Echo...',
    'CrossfadeTracks', 'Align_EndToSelEnd', 'Message', 'SlidingStretch',
    'SplitNew', 'SyncLock', 'Compressor', 'Phaser', 'Wahwah...',
    'SplitDeleteLabels', 'Demo', 'Disjoin', 'ChangeTempo', 'Change Tempo...',
    'NewLabelTrack', 'StoreCursorPosition', 'High-Pass Filter...',
    'SpectralEditMultiTool', 'SoundActivation', 'ExportSel', 'MixerBoard',
    'Pluck', 'OpenProject2', 'SplitCut', 'MidiDeviceInfo', 'Phaser...', 'Exit',
    'Benchmark', 'PanRight', 'Updates', 'ExportMultiple', 'Distortion...',
    'ExpandAllTracks', 'Split', 'ChangePitch', 'LowPassFilter', 'Amplify...',
    'NotchFilter', 'Drag', 'Macro_FadeEnds', 'ImportLabels', 'Chirp', 'Trim',
    'SplitDelete', 'SkipSelStart', 'GetInfo', 'Pause', 'Nyquist Prompt...',
    'SpectralEditShelves', 'DeviceInfo', 'UnlockPlayRegion', 'SelectTime',
    'PlayLooped', 'Stereo to Mono', 'SetTrackStatus', 'SelectFrequencies',
    'High-passFilter', 'ChangeSpeed', 'Redo', 'ShowRecordMeterTB',
    'NewTimeTrack', 'Paulstretch...', 'Resample', 'SWPlaythrough', 'Chirp...',
    'Change Speed...', 'ZoomIn', 'ToggleScrubRuler', 'Close',
    'Align_StartToSelEnd', 'Fade In', 'Invert', 'ExportLabels', 'ImportRaw',
    'DtmfTones', 'Reverse', 'Align_EndToSelStart', 'ToggleSpectralSelection',
    'Find Clipping...', 'SetClip', 'Limiter', 'Karaoke', 'CompareAudio',
    'SetTrackAudio', 'SelNextClip', 'PinnedHead', 'Noise...',
    'ShowSpectralSelectionTB', 'RegularIntervalLabels', 'SelectAll', 'SaveAs',
    'PunchAndRoll', 'Silence', 'SelTrackStartToEnd', 'SoundActivationLevel',
    'Align_Together', 'ShowSelectionTB', 'ManageAnalyzers', 'ShowTransportTB',
    'ApplyMacrosPalette', 'SelCursorToTrackEnd', 'FitV']

