from celery.task import task
from celery.utils.log import get_task_logger
from models import Cleansing

logger = get_task_logger(__name__)


@task
def cleanse_data_chunk(chunk, file_pk, source_type, prog_key, increment, *args, **kwargs):
    c = Cleansing()
    c.cleanse(chunk)
