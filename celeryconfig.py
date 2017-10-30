CELERY_RESULT_BACKEND = "mongodb"
CELERY_MONGODB_BACKEND_SETTINGS = {
    "host": "127.0.0.1",
    "port": 27017,
    "database": "meritDB", 
    "taskmeta_collection": "flask_app_job_results",
}


# CELERY_RESULT_BACKEND = 'mongodb'
# CELERY_MONGODB_BACKEND_SETTINGS = {
#     "host": "mastarke-lnx-v2",
#     "port": 27017,
#     "database": "meritDB", 
#     "taskmeta_collection": "flask_app_job_results",
# }

CELERY_TASK_SERIALIZER = 'json'

