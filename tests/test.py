__author__ = 'shekarnh'

from nose.tools import *
import cloudWhip
import os

def setup():
    print "SETUP!"

def teardown():
    print "TEAR DOWN!"

def test_basic():
    print "I RAN!"