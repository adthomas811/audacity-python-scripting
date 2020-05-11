# audacity-python-scripting

## Description

This Python package is designed to automate tasks in Audacity. It does not include an exhaustive implementation of all of the possible commands (listed in 'Scriptable Audacity' below), but instead includes console scripts for common commands I use and wished to automate (listed in 'Installation and Use' below). That being said, it would be straightforward to add more commands to the package and console scripts to expose them. At this time, the scripts have only been tested on Windows, and the module is only available for Python 3.x.

## Scriptable Audacity

The mod-script-pipe plug-in is used to drive Audacity from an external scripting language. It is now shipped with Audacity, and just needs to be enabled in the preferences.

Here is general information on the plug-in: https://alphamanual.audacityteam.org/man/Mod-script-pipe

More detailed information on scripting: https://alphamanual.audacityteam.org/man/Scripting

Reference of all possible commands: https://alphamanual.audacityteam.org/man/Scripting_Reference

## Installation and Use

To install the latest version of the package, run the following pip command:

pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple audacity-scripting

The following console scripts are accessible once the package is installed (the --help flag can be used to get information on each script):

norm_tracks

join_clips

mix_and_render
