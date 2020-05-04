from setuptools import setup, find_packages

with open("README.md", "r") as fh:
   long_description = fh.read()

setup(name='audacity-scripting',
      version="0.0.1",
      author="Alex Thomas",
      author_email="adthomas811@gmail.com",
      description='A program to call commands in Audacity from python.',
      long_description=long_description,
      url='https://github.com/adthomas811/audacity-python-scripting',
      packages=setuptools.find_packages()
)