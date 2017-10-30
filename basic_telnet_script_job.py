from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    # MATTHEW CELERY JOB FILE
    testbed_file = ('/ws/mastarke-sjc/my_local_git/merit/my_yaml.yaml')
    rtr = 'R6'
    base_image_repo = '/auto/prod_weekly_archive1/bin/'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '223.255.254.245'
    load_image = '6.3.2'

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = 'meritData'

    ### PSAT ARGS ###
    psat_unzip_output_folder = '/auto/tftp-sjc-users2/mastarke/psat/r6'
    psat_job_file = '/auto/nest/ats5.3.0/mastarke/jobs/R6-repeat-trigger-psat.job'


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/image_picker_site/basic_telnet_script.py'))
