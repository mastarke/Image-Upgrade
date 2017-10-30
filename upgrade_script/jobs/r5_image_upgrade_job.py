from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    testbed_file = ('/ws/mastarke-sjc/my_local_git/merit/my_yaml.yaml')
    rtr = 'R5'
    base_image_repo = '/auto/prod_weekly_archive1/bin/'
    tftp_dir = '/tftpboot/mastarke/'
    tftp_ip = '223.255.254.245'
    #load_image = '6.3.1'


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/merit/auto_merit.py'))
