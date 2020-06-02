
# Make sure Audacity is running first and that mod-script-pipe is enabled
# before running this script.

# Audacity Scripting Reference:
# https://manual.audacityteam.org/man/scripting_reference.html

from audacity_scripting.core.base import AudacityScriptingBase
from math import log10

# TODO(adthomas811): Raise exception if any return type besides json is
#                    requested in the GetInfo command.


class AudacityScriptingUtils(AudacityScriptingBase):
    """
    A class to extend the base Audacity scripting class and add functionality
    to execute commands and process the results.

    Methods
    -------
    get_commands_info()
        Returns a JSON object containing the Commands info.
    get_menus_info()
        Returns a JSON object containing the Menus info.
    get_preferences_info()
        Returns a JSON object containing the Preferences info.
    get_tracks_info()
        Returns a JSON object containing the Tracks info.
    get_clips_info()
        Returns a JSON object containing the Clips info.
    get_envelopes_info()
        Returns a JSON object containing the Envelopes info.
    get_labels_info()
        Returns a JSON object containing the Labels info.
    get_boxes_info()
        Returns a JSON object containing the Boxes info.
    get_audio_tracks_info(track_name_filter_list=None)
        Returns a list containing useful audio track information.
    get_scripting_id_list()
        Returns a unique list of scripting ids from the Commands and Menus
        info.
    join_all_clips()
        Joins all clips in the project.
    split_all_audio_on_labels()
        Split all audio based on the labels.
    rename_track_by_num(track_name, track_num)
        Rename a track based on its ordered track number.
    export_multiple_prompt()
        Open the export multiple prompt.
    close_project_prompt()
        Open the close project prompt.
    normalize_tracks_by_label(track_name_list, peak_level=float(-1),
                              apply_gain=True, rem_dc_offset=True,
                              stereo_ind=False)
        Used to normalize one or more tracks using the labels as boundaries
        between regions.
    compress_tracks_by_label(track_name_list, threshold=float(-12),
                             noise_floor=float(-40), ratio=float(2),
                             attack_time=float(0.2),
                             release_time=float(1), normalize=True,
                             use_peak=False)
        Used to compress one or more tracks using the labels as boundaries
        between regions.
    get_track_gain(track_name)
        Returns the gain for one track by track name.
    set_track_gain(track_name, gain)
        Sets the gain for one track by track name.
    mix_and_render_to_new_track(track_name_list)
        Used to mix and render multiple tracks to a new track.
    """

    def __init__(self):
        """
        Call parent class init.
        """

        super(AudacityScriptingUtils, self).__init__()

    def __enter__(self):
        """
        Returns self when entering with statement.
        """

        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        """
        Closes self when exiting with statement.
        """

        self.close()

    def get_commands_info(self):
        """
        Returns a JSON object containing the Commands info.
        """

        result = self.run_command('GetInfo: Type=Commands')
        return self.get_json(result)

    def get_menus_info(self):
        """
        Returns a JSON object containing the Menus info.
        """

        result = self.run_command('GetInfo: Type=Menus')
        return self.get_json(result)

    def get_preferences_info(self):
        """
        Returns a JSON object containing the Preferences info.
        """

        result = self.run_command('GetInfo: Type=Preferences')
        return self.get_json(result)

    def get_tracks_info(self):
        """
        Returns a JSON object containing the Tracks info.
        """

        result = self.run_command('GetInfo: Type=Tracks')
        return self.get_json(result)

    def get_clips_info(self):
        """
        Returns a JSON object containing the Clips info.
        """

        result = self.run_command('GetInfo: Type=Clips')
        return self.get_json(result)

    def get_envelopes_info(self):
        """
        Returns a JSON object containing the Envelopes info.
        """

        result = self.run_command('GetInfo: Type=Envelopes')
        return self.get_json(result)

    def get_labels_info(self):
        """
        Returns a JSON object containing the Labels info.
        """

        result = self.run_command('GetInfo: Type=Labels')
        return self.get_json(result)

    def get_boxes_info(self):
        """
        Returns a JSON object containing the Boxes info.
        """

        result = self.run_command('GetInfo: Type=Boxes')
        return self.get_json(result)

    # TODO(adthomas811): Handle zero or more than one label tracks.
    def get_audio_tracks_info(self, track_name_filter_list=None):
        """
        Returns a list containing useful audio track information.

        Parameters
        ----------
        track_name_filter_list : list, optional
            A list of track names for filtering the audio track information.
            Track information is returned if the track name is present in the
            list. Information for all audio tracks is returned if the value of
            the list is None (Default is None).
        """

        tracks_info = self.get_tracks_info()
        labels_info = self.get_labels_info()
        tracks_list = []

        for track_num in range(len(tracks_info)):
            if tracks_info[track_num]['kind'] == 'wave':
                if (track_name_filter_list is None or
                        tracks_info[track_num]['name']
                        in track_name_filter_list):
                    track_dict = {}
                    track_dict['track_num'] = track_num
                    track_dict['name'] = tracks_info[track_num]['name']

                    voltage_ratio_gain = tracks_info[track_num]['gain']
                    track_dict['gain'] = round(20 * log10(voltage_ratio_gain),
                                               4)

                    boundary_timestamps = []
                    boundary_timestamps.append(tracks_info[track_num]['start'])
                    for label_info in labels_info[0][1]:
                        boundary_timestamps.append((label_info[0] +
                                                    label_info[1])/2)
                    boundary_timestamps.append(tracks_info[track_num]['end'])

                    track_dict['labels'] = []
                    for i in range(len(boundary_timestamps)-1):
                        label_dict = {}
                        label_dict['start'] = boundary_timestamps[i]
                        label_dict['end'] = boundary_timestamps[i+1]
                        track_dict['labels'].append(label_dict)
                    tracks_list.append(track_dict)
        return tracks_list

    def get_scripting_id_list(self):
        """
        Returns a unique list of scripting ids from the Commands and Menus
        info.
        """

        commands_info = self.get_commands_info()
        menus_info = self.get_menus_info()
        raw_scripting_id_list = []

        for command_info in commands_info:
            raw_scripting_id_list.append(command_info['id'])

        for menu_info in menus_info:
            if 'id' in menu_info.keys():
                raw_scripting_id_list.append(menu_info['id'])

        raw_scripting_id_list = list(set(raw_scripting_id_list))

        scripting_id_list = []
        for scripting_id in raw_scripting_id_list:
            if '\\' not in scripting_id:
                scripting_id_list.append(scripting_id)

        return scripting_id_list

    def join_all_clips(self):
        """
        Joins all clips in the project.
        """

        self.run_command('SelectNone:')
        self.run_command('SelectAll:')
        self.run_command('Join:')
        self.run_command('SelectNone:')

    def split_all_audio_on_labels(self):
        """
        Split all audio based on the labels.
        """

        self.run_command('SelectNone:')
        self.run_command('SelectAll:')
        self.run_command('SplitLabels:')
        self.run_command('SelectNone:')

    def rename_track_by_num(self, track_name, track_num):
        """
        Rename a track based on its ordered track number.

        Parameters
        ----------
        track_name : str
            New track name.
        track_num : int
            Track number based on track order in the project.
        """

        self.run_command('SelectNone:')
        self.run_command('SelectTracks: Mode=Set Track={}'.format(track_num))
        self.run_command('SetTrackStatus: Name="{}"'.format(track_name))
        self.run_command('SelectNone:')

    def export_multiple_prompt(self):
        """
        Open the export multiple prompt.
        """

        self.run_command('SelectNone:')
        self.run_command('ExportMultiple:')

    def close_project_prompt(self):
        """
        Open the close project prompt.
        """

        self.run_command('SelectNone:')
        self.run_command('Close:')

    # TODO(adthomas811): Rename to normalize_tracks_by_labels.
    def normalize_tracks_by_label(self, track_name_list, peak_level=float(-1),
                                  apply_gain=True, rem_dc_offset=True,
                                  stereo_ind=False):
        """
        Used to normalize one or more tracks using the labels as boundaries
        between regions.

        Parameters
        ----------
        track_name_list : list
            The track names of the tracks to be normalized.
        peak_level : float, optional
            Value passed to the PeakLevel parameter of the Normalize command
            in Audacity. (Default is float(-1)).
        apply_gain : bool, optional
            Value passed to the ApplyGain parameter of the Normalize command
            in Audacity. (Default is True).
        rem_dc_offset : bool, optional
            Value passed to the RemoveDcOffset parameter of the Normalize
            command in Audacity. (Default is True).
        stereo_ind : bool, optional
            Value passed to the StereoIndependent parameter of the Normalize
            command in Audacity. (Default is False).
        """

        self.run_command('SelectNone:')
        audio_tracks_info = self.get_audio_tracks_info(track_name_list)

        for audio_track_info in audio_tracks_info:
            track_num = audio_track_info['track_num']
            for label in audio_track_info['labels']:
                self.run_command('Select: Mode=Set Track={} '
                                 'Start={} End={}'.format(track_num,
                                                          label['start'],
                                                          label['end']))
                self.run_command('Normalize: PeakLevel={} ApplyGain={} '
                                 'RemoveDcOffset={} '
                                 'StereoIndependent={}'.format(peak_level,
                                                               apply_gain,
                                                               rem_dc_offset,
                                                               stereo_ind))

        self.run_command('SelectNone:')

    # TODO(adthomas811): Rename to compress_tracks_by_labels.
    def compress_tracks_by_label(self, track_name_list, threshold=float(-12),
                                 noise_floor=float(-40), ratio=float(2),
                                 attack_time=float(0.2),
                                 release_time=float(1), normalize=True,
                                 use_peak=False):
        """
        Used to compress one or more tracks using the labels as boundaries
        between regions.

        Parameters
        ----------
        track_name_list : list
            The track names of the tracks to be compressed.
        threshold : float, optional
            Value passed to the Threshold parameter of the Compressor command
            in Audacity. (Default is float(-12)).
        noise_floor : float, optional
            Value passed to the NoiseFloor parameter of the Compressor command
            in Audacity. (Default is float(-40)).
        ratio : float, optional
            Value passed to the Ratio parameter of the Compressor command in
            Audacity. (Default is float(2)).
        attack_time : float, optional
            Value passed to the AttackTime parameter of the Compressor command
            in Audacity. (Default is float(0.2)).
        release_time : float, optional
            Value passed to the ReleaseTime parameter of the Compressor command
            in Audacity. (Default is float(1)).
        normalize : bool, optional
            Value passed to the Normalize parameter of the Compressor command
            in Audacity. (Default is True).
        use_peak : bool, optional
            Value passed to the UsePeak parameter of the Compressor command
            in Audacity. (Default is False).
        """

        self.run_command('SelectNone:')
        audio_tracks_info = self.get_audio_tracks_info(track_name_list)

        for audio_track_info in audio_tracks_info:
            track_num = audio_track_info['track_num']
            for label in audio_track_info['labels']:
                self.run_command('Select: Mode=Set Track={} '
                                 'Start={} End={}'.format(track_num,
                                                          label['start'],
                                                          label['end']))
                self.run_command('Compressor: Threshold={} NoiseFloor={} '
                                 'Ratio={} AttackTime={} ReleaseTime={} '
                                 'Normalize={} '
                                 'UsePeak={}'.format(threshold, noise_floor,
                                                     ratio, attack_time,
                                                     release_time, normalize,
                                                     use_peak))

        self.run_command('SelectNone:')

    # TODO(adthomas811): Check that only one track is returned.
    def get_track_gain(self, track_name):
        """
        Returns the gain for one track by track name.

        Parameters
        ----------
        track_name : str
            Name of the track to return the gain of.
        """

        audio_tracks_info = self.get_audio_tracks_info([track_name])

        return audio_tracks_info[0]['gain']

    # TODO(adthomas811): Check that only one track is returned.
    def set_track_gain(self, track_name, gain):
        """
        Sets the gain for one track by track name.

        Parameters
        ----------
        track_name : str
            Name of the track to set the gain of.
        gain : float
            Gain to be set on the track.
        """

        self.run_command('SelectNone:')
        audio_tracks_info = self.get_audio_tracks_info([track_name])

        track_num = audio_tracks_info[0]['track_num']

        self.run_command('SelectTracks: '
                         'Mode=Set Track={}'.format(track_num))
        self.run_command('SetTrackAudio: Gain={}'.format(gain))

        self.run_command('SelectNone:')

    def mix_and_render_to_new_track(self, track_name_list):
        """
        Used to mix and render multiple tracks to a new track.

        Parameters
        ----------
        track_name_list : list
            The track names of the tracks to be mixed and rendered.
        """

        self.run_command('SelectNone:')
        audio_tracks_info = self.get_audio_tracks_info(track_name_list)

        for audio_track_info in audio_tracks_info:
            self.run_command('SelectTracks: Mode=Add '
                             'Track={}'.format(audio_track_info['track_num']))
        self.run_command('MixAndRenderToNewTrack:')

        self.run_command('SelectNone:')
