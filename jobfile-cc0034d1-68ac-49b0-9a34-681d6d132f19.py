
from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    # CELERY JOB FILE

    get_score = True

    testbed_file = ('testbed-cc0034d1-68ac-49b0-9a34-681d6d132f19.yaml')
    rtr = 'R6'
    image_repo = '/auto/prod_weekly_archive1/bin/6.3.2.17I.SIT_IMAGE/asr9k-x64'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '223.255.254.245'
    platform = 'asr9k-x64'

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = 'meritData'

    ### PSAT ARGS ###
    psat_unzip_output_folder = '/auto/tftp-sjc-users2/mastarke/psat/r6'
    psat_job_file = '/auto/nest/ats5.3.0/mastarke/jobs/R6-repeat-trigger-psat.job'

    # IXIA_CHASSIS
    ixia_chassis_ip = '172.27.211.87'


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/image_picker_site/basic_telnet_script.py'))
