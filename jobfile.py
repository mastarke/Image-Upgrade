
from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    # CELERY JOB FILE

    get_score = False

    testbed_file = ('testbed-f04fa384-8758-45cb-9a68-a4284a9a8118.yaml')
    rtr = 'SS'
    image_repo = '/auto/prod_weekly_archive1/bin/6.4.1.29I.SIT_IMAGE/asr9k-x64'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '233.255.254.253'
    platform = 'asr9k-x64'

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = 'None'

    ### PSAT ARGS ###
    psat_unzip_output_folder = 'None'
    psat_job_file = 'None'

    # IXIA_CHASSIS
    ixia_chassis_ip = 'None'


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/image_picker_site/basic_telnet_script.py'))
