import os
from setuptools import setup
# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

setup(
    name = "cloudWhip",
    version = "0.0.1",
    author = "Shekar N H",
    author_email = "",
    description = "",
    license = "",
    keywords = "",
    url = "",
    install_requires=['nose', 'boto', 'awscli'],
    packages=['cloudWhip', 'tests'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: ",
        "Topic :: Utilities",
        "License :: ",
    ],
)