from celery import shared_task
from celery.utils.log import get_task_logger
from models import Cleansing
from seed.decorators import get_prog_key
from django.core.cache import cache

logger = get_task_logger(__name__)


@shared_task
def cleanse_data_chunk(chunk, file_pk, increment):
    c = Cleansing()
    c.cleanse(chunk)
    c.save_to_cache(file_pk)


@shared_task
def finish_cleansing(results, file_pk):
    # import_file = ImportFile.objects.get(pk=file_pk)
    # import_file.mapping_done = True
    # import_file.save()
    # finish_import_record(import_file.import_record.pk)
    prog_key = get_prog_key('cleanse_data', file_pk)
    cache.set(prog_key, 100)
    data = cache.get(Cleansing.cache_key(file_pk))
