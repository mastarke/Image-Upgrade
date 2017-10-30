from ats.easypy import run


class ScriptArgs(object):
    """script related arguments"""
    testbed_file = ('/ws/mastarke-sjc/my_local_git/merit/my_yaml.yaml')
    rtr = 'F1'
    base_image_repo = '/auto/prod_weekly_archive1/bin/'
    user_tftp_dir = '/auto/tftp-merit/mastarke/'
    tftp_ip = '223.255.254.245'
    load_image = '6.3.2'
    image_available_date = 'Oct  5' # 632 13I IMAGE AVAILABLE DATE

    ### DATABASE ARGS ###
    db_host = 'mastarke-lnx-v2'
    db_name = 'meritDB'
    db_collection = 'meritData'

    ### PSAT ARGS ###
    psat_unzip_output_folder = '/auto/tftp-sjc-users2/mastarke/psat/f1'
    psat_job_file = '/auto/nest/ats5.3.0/mastarke/jobs/F1-repeat-trigger-psat.job'



def main():
    run(testscript=('/ws/mastarke-sjc/my_local_git/merit/auto_merit.py'))
