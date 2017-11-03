
from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    # MATTHEW CELERY JOB FILE

    testbed_file = ('testbed-e50a0c91-58c6-441a-b3bb-a937e8d6586e.yaml')
    rtr = 'R3'
    image_repo = '/auto/prod_weekly_archive1/bin/6.3.2.16I.DT_IMAGE/asr9k-px'
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


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/image_picker_site/basic_telnet_script.py'))
