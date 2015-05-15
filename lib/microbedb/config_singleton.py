from config import Config
import os.path

'''
Module for loading a config file, acts like
a singleton.

@author: Matthew Laird
@created: April 30, 2015
'''

local_config = None

def initConfig(file=None):
    
    if not file:
        raise Exception("No config file given")

    if not os.path.isfile(file):
        raise Exception("Config file {} doesn't exist!".format(file));

    global local_config
    local_config = Config(file)

    return local_config

def getConfig():
    global local_config

    if not local_config:
        raise Exception("Config file not initialized");

    return local_config

def configLoaded():
    global local_config

    return local_config != None
