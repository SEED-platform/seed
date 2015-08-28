from celery import shared_task
from celery.utils.log import get_task_logger
from models import Cleansing

logger = get_task_logger(__name__)


@shared_task
def cleanse_data_chunk(chunk, file_pk, source_type, increment):
    c = Cleansing()
    c.cleanse(chunk)
    c.save_to_cache(file_pk)
