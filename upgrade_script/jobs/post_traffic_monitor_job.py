from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    testbed_file = ('/ws/mastarke-sjc/my_local_git/merit/my_yaml.yaml')
    rtr = 'F1'
    traffic_state = 'post_traffic'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'

def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/merit/traffic_monitor.py'))
