from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='audacity-scripting',
      version="0.0.29",
      author="Alex Thomas",
      author_email="adthomas811@gmail.com",
      description='A program to call commands in Audacity from python.',
      long_description=long_description,
      url='https://github.com/adthomas811/audacity-python-scripting',
      packages=find_packages(),
      entry_points={
        'console_scripts': ['norm_tracks=audacity_scripting.scripts.'
                            'normalize_tracks:main',

                            'join_clips=audacity_scripting.scripts.'
                            'join_all_clips:main',

                            'mix_and_render=audacity_scripting.scripts.'
                            'mix_and_render_tracks:main']
      }
      )
