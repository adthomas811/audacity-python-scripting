
# Make sure Audacity is running first and that mod-script-pipe is enabled
# before running this script.

# Audacity Scripting Reference: https://manual.audacityteam.org/man/scripting_reference.html

from audacity_scripting.base import AudacityScriptingBase


class AudacityScriptingUtils(AudacityScriptingBase):
   def __init__(self):
      super(AudacityScriptingUtils, self).__init__()

   def get_tracks_info(self):
      result = self.run_command('GetInfo: Type=Tracks')
      return self.get_json(result)

   def get_labels_info(self):
      result = self.run_command('GetInfo: Type=Labels')
      return self.get_json(result)

   def get_clips_info(self):
      result = self.run_command('GetInfo: Type=Clips')
      return self.get_json(result)

   def get_audio_tracks_info(self, track_name_filter_list=None):
      tracks_info = self.get_tracks_info()
      labels_info = self.get_labels_info()
      tracks_list = []

      for track_num in range(len(tracks_info)):
         if tracks_info[track_num]['kind'] == 'wave':
            if track_name_filter_list is None or tracks_info[track_num]['name'] in track_name_filter_list:
               track_dict = {}
               track_dict['name'] = tracks_info[track_num]['name']
               track_dict['track_num'] = track_num

               boundary_timestamps = []
               boundary_timestamps.append(tracks_info[track_num]['start'])
               for label_info in labels_info[0][1]:
                  boundary_timestamps.append((label_info[0]+label_info[1])/2)
               boundary_timestamps.append(tracks_info[track_num]['end'])

               track_dict['clips'] = []
               for i in range(len(boundary_timestamps)-1):
                  clip_dict = {}
                  clip_dict['start'] = boundary_timestamps[i]
                  clip_dict['end'] = boundary_timestamps[i+1]
                  track_dict['clips'].append(clip_dict)
               tracks_list.append(track_dict)
      return tracks_list

   def join_all_clips(self):
      self.run_command('SelectNone:')
      self.run_command('SelectAll:')
      self.run_command('Join:')
      self.run_command('SelectNone:')

   def split_all_audio_on_labels(self):
      self.run_command('SelectNone:')
      self.run_command('SelectAll:')
      self.run_command('SplitLabels:')
      self.run_command('SelectNone:')

   def rename_track_by_num(self, track_name, track_num):
      self.run_command('SelectNone:')
      self.run_command('SelectTracks: Mode=Set Track={}'.format(track_num))
      self.run_command('SetTrackStatus: Name="{}"'.format(track_name))
      self.run_command('SelectNone:')

   def export_multiple_prompt(self):
      self.run_command('SelectNone:')
      self.run_command('ExportMultiple:')

   def close_project_prompt(self):
      self.run_command('SelectNone:')
      self.run_command('Close:')

   def normalize_tracks_by_clip(self, track_name_list):
      self.run_command('SelectNone:')
      audio_tracks_info = self.get_audio_tracks_info(track_name_list)

      for audio_track_info in audio_tracks_info:
         track_num = audio_track_info['track_num']
         for clip in audio_track_info['clips']:
            self.run_command('Select: Mode=Set Track={} Start={} End={}'.format(track_num, clip['start'], clip['end']))
            self.run_command('Normalize:')

      self.run_command('SelectNone:')

   def compress_tracks_by_clip(self, track_name_list):
      self.run_command('SelectNone:')
      audio_tracks_info = self.get_audio_tracks_info(track_name_list)

      for audio_track_info in audio_tracks_info:
         track_num = audio_track_info['track_num']
         for clip in audio_track_info['clips']:
            self.run_command('Select: Mode=Set Track={} Start={} End={}'.format(track_num, clip['start'], clip['end']))
            self.run_command('Compressor: Ratio=4 UsePeak=True')

      self.run_command('SelectNone:')

   def set_track_gain(self, track_name_list, track_settings):
      self.run_command('SelectNone:')
      audio_tracks_info = self.get_audio_tracks_info(track_name_list)

      for audio_track_info in audio_tracks_info:
         track_num = audio_track_info['track_num']
         track_name = audio_track_info['name']
         track_dict = track_settings[track_name]
         self.run_command('SelectTracks: Mode=Set Track={}'.format(track_num))
         self.run_command('SetTrackAudio: Gain={}'.format(track_dict['Gain']))

      self.run_command('SelectNone:')

   def mix_and_render_to_new_track(self, track_name_list):
      self.run_command('SelectNone:')
      audio_tracks_info = self.get_audio_tracks_info(track_name_list)

      for audio_track_info in audio_tracks_info:
         self.run_command('SelectTracks: Mode=Add Track={}'.format(audio_track_info['track_num']))
      self.run_command('MixAndRenderToNewTrack:')

      self.run_command('SelectNone:')
