
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

import os
import sys
import win32pipe
import win32file


class AudacityMock(object):
    def __init__(self):
        if sys.platform == 'win32':
            self._init_mock_win()
        else:
            # Linux and Mac not Implemented
            toname = '/tmp/audacity_script_pipe.to.' + str(os.getuid())
            fromname = '/tmp/audacity_script_pipe.from.' + str(os.getuid())

    def _init_mock_win(self):
        PIPE_REJECT_REMOTE_CLIENTS = 0x00000008
        open_mode = win32pipe.PIPE_ACCESS_DUPLEX
        pipe_mode = (win32pipe.PIPE_TYPE_MESSAGE |
                     win32pipe.PIPE_READMODE_MESSAGE |
                     win32pipe.PIPE_WAIT |
                     PIPE_REJECT_REMOTE_CLIENTS)
        max_instances = win32pipe.PIPE_UNLIMITED_INSTANCES
        self.buffer_size = 1024

        self.tofile = win32pipe.CreateNamedPipe(r'\\.\pipe\ToSrvPipe',
                                                open_mode,
                                                pipe_mode,
                                                max_instances,
                                                self.buffer_size,
                                                self.buffer_size,
                                                50,
                                                None)
        if self.tofile == win32file.INVALID_HANDLE_VALUE:
            # raise exception
            print('self.tofile not valid')

        self.fromfile = win32pipe.CreateNamedPipe(r'\\.\pipe\FromSrvPipe',
                                                  open_mode,
                                                  pipe_mode,
                                                  max_instances,
                                                  self.buffer_size,
                                                  self.buffer_size,
                                                  50,
                                                  None)
        if self.fromfile == win32file.INVALID_HANDLE_VALUE:
            # raise exception
            print('self.fromfile not valid')

    def run_pipe_server(self):
        if sys.platform == 'win32':
            self._run_pipe_server_win()
        else:
            # Linux and Mac not Implemented
            pass

    def _run_pipe_server_win(self):
        tofile_conn_res = win32pipe.ConnectNamedPipe(self.tofile, None)
        fromfile_conn_res = win32pipe.ConnectNamedPipe(self.fromfile, None)

        if tofile_conn_res == 0 and fromfile_conn_res == 0:
            try:
                while(True):
                    success, data = win32file.ReadFile(self.tofile,
                                                       self.buffer_size,
                                                       None)
                    if success != 0:
                        # Raise Exception
                        print('Read Failed!')
                        break

                    command = data.decode().split('\r')[0]
                    response = self.evaluate_command(command)

                    success = win32file.WriteFile(self.fromfile,
                                                  (response +
                                                  '\n').encode())[0]
                    if success != 0:
                        # Raise Exception
                        print('Write Failed!')
                        break
            finally:
                win32file.FlushFileBuffers(self.tofile)
                win32pipe.DisconnectNamedPipe(self.tofile)
                win32file.CloseHandle(self.tofile)

                win32file.FlushFileBuffers(self.fromfile)
                win32pipe.DisconnectNamedPipe(self.fromfile)
                win32file.CloseHandle(self.fromfile)

    def evaluate_command(self, command):
        scripting_id_and_args_list = command.split(':')

        if len(scripting_id_and_args_list) == 1:
            pass
        elif len(scripting_id_and_args_list) == 2:
            pass
        elif len(scripting_id_and_args_list) > 2:
            pass
        else:
            pass

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
