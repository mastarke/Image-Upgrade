
from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    # CELERY JOB FILE

    get_score = False

    testbed_file = ('testbed-75a7b554-a610-4c3e-9537-8fc749199991.yaml')
    rtr = 'R6'
    image_repo = '/auto/prod_weekly_archive1/bin/6.3.2.17I.SIT_IMAGE/asr9k-x64'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '223.255.254.245'
    platform = 'asr9k-x64'

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = 'None'

    ### PSAT ARGS ###
    psat_unzip_output_folder = 'None'
    psat_job_file = 'None'

    # IXIA_CHASSIS
    ixia_chassis_ip = None


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/image_picker_site/basic_telnet_script.py'))
