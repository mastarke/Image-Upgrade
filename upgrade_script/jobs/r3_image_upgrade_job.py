from ats.easypy import run
import os

class ScriptArgs(object):
    """SCRIPT RELATED ARGUMENTS"""
    testbed_file = ('/ws/mastarke-sjc/my_local_git/merit/my_yaml.yaml')
    rtr = 'R3'
    base_image_repo = '/auto/prod_weekly_archive1/bin/'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '223.255.254.245'
    image_available_date = 'Sep 26' # 632 12I IMAGE AVAILABLE DATE
    load_image = '6.3.2'

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = 'meritData'

    ### PSAT ARGS ###
    psat_unzip_output_folder = '/auto/tftp-sjc-users2/mastarke/psat/r3'
    psat_job_file = '/auto/nest/ats5.3.0/mastarke/jobs/R3-repeat-trigger-psat.job'


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/merit/auto_merit.py'))
