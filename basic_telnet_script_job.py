from ats.easypy import run
import os

class ScriptArgs(object):
    """script related arguments"""
    # MATTHEW CELERY JOB FILE

    testbed_file = ('testbed-aab0c630-d58d-4923-bc0a-9d9ffcff1d40.yaml')
    rtr = 'R6'
    image_repo = '/auto/prod_weekly_archive1/bin/6.3.2.16I.DT_IMAGE/asr9k-px'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '223.255.254.245'
    load_image = '6.3.2'
    install_cmd = 'admin install add source tftp://223.255.254.245/auto/tftp-merit/mastarke/ asr9k-mini-px.pie-6.3.2.16I asr9k-mpls-px.pie-6.3.2.16I synchronous activate prompt-level none'
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
