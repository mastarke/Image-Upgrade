import sys
import os

# THIS WILL BE THE FINAL LIST WHEN READY
job_files = ['easypy pre_traffic_monitor_job.py', 
             'easypy f1_image_upgrade_job.py',
             'easypy post_traffic_monitor_job.py', 
             'python psat_final_score_calc.py']


for job in job_files:
    print('Matthew job file {} is running'.format(job))
    os.system(job)
