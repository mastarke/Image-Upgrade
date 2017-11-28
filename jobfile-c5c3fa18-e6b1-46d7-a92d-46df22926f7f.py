
from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    # CELERY JOB FILE

    get_score = False

    testbed_file = ('testbed-c5c3fa18-e6b1-46d7-a92d-46df22926f7f.yaml')
    rtr = 'AG1-4'
    image_repo = '/auto/prod_weekly_archive1/bin/6.3.2.18I.SIT_IMAGE/asr9k-px'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '223.255.254.245'
    platform = 'asr9k-px'

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = 'meritData'

    ### PSAT ARGS ###
    psat_unzip_output_folder = '/auto/tftp-sjc-users2/mastarke/psat/r6'
    psat_job_file = '/auto/nest/ats5.3.0/mastarke/jobs/R6-repeat-trigger-psat.job'

    # IXIA_CHASSIS
    ixia_chassis_ip = '172.27.211.88'


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/image_picker_site/basic_telnet_script.py'))
