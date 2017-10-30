from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    testbed_file = ('/ws/mastarke-sjc/my_local_git/merit/rjil.yaml')
    rtr = 'AG2_2'
    base_image_repo = '/auto/prod_weekly_archive1/bin/'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '223.255.254.245'
    load_image = '6.3.2'

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = 'RJIL'

    ### PSAT ARGS ###
    psat_unzip_output_folder = '/auto/tftp-sjc-users2/mastarke/psat/r6'
    psat_job_file = '/ws/mastarke-sjc/my_local_git/merit/RJIL_AG2_2_nest.job'


def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/merit/auto_merit.py'))
