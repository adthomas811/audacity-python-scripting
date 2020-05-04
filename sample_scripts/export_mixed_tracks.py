
from audacity_scripting.utils import AudacityScriptingUtils

def main():
   left_track = 'L - AT2050'
   right_track = 'R - SM57'
   track_settings_list =   [
                              { left_track  : {'Gain': '0'},
                                right_track : {'Gain': '-6'}},

                              { left_track  : {'Gain': '-3'},
                                right_track : {'Gain': '-3'}},

                              { left_track  : {'Gain': '-6'},
                                right_track : {'Gain': '0'}},
                           ]

   command_runner = AudacityScriptingUtils()

   command_runner.join_all_clips()

   raw_track_name_list = track_settings_list[0].keys()

   command_runner.normalize_tracks_by_clip(raw_track_name_list)

   new_track_name_list = []
   for track_settings in track_settings_list:
      command_runner.set_track_gain(raw_track_name_list, track_settings)
      track_name = 'AT {} SM {}'.format(track_settings[left_track]['Gain'], track_settings[right_track]['Gain'])
      new_track_name_list.append(track_name)
      command_runner.mix_and_render_to_new_track(raw_track_name_list)
      new_track_num = len(command_runner.get_tracks_info()) - 1
      command_runner.rename_track_by_num(track_name, new_track_num)

   command_runner.normalize_tracks_by_clip(new_track_name_list)

   command_runner.close()

if __name__ == '__main__':
   main()