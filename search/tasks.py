from services.celery import app
from django.apps import apps


@app.task
def update_index_for_model(app_label, model_name, instance_id):
    model_class = apps.get_model(app_label, model_name)
    try:
        instance = model_class.objects.get(pk=instance_id)
    except model_class.DoesNotExist:
        # XXX log some warning here
        print 'something bad happened'
