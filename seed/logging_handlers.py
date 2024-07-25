import atexit
from logging.handlers import HTTPHandler, QueueHandler, QueueListener
from queue import Queue


class APIHandler(HTTPHandler):
    """
    Subclass of HTTPHandler to reduce the amount of information that is sent to the logger
    """
    def mapLogRecord(self, record):
        if record.name == 'django.db.backends':
            return {
                'duration': record.duration,
                'sql': record.sql,
                'timestamp': round(record.created * 1000),
            }
        # elif record.name == 'django.request':
        #     result = {
        #         'error': record.args[0],
        #         'path': record.args[1],
        #         'statusCode': record.status_code,
        #     }
        # elif record.name == 'django.server':
        #     m = re.match('^([^ ]+) (.+) HTTP/1.1$', record.args[0])
        #     result = {
        #         'method': m.group(1),
        #         'path': m.group(2),
        #         'statusCode': record.status_code,
        #     }

        # return {
        #     # 'name': record.name,
        #     'timestamp': round(record.created * 1000),
        #     # 'message': record.msg % record.args,
        #     **result,
        # }
        return {}


class QueueListenerHandler(QueueHandler):
    def __init__(self):
        queue = Queue(-1)
        super().__init__(queue)
        self._listener = QueueListener(
            self.queue,
            APIHandler(host='127.0.0.1:3000', url='/', method='POST')
        )
        self.start()
        atexit.register(self.stop)

    def start(self):
        self._listener.start()

    def stop(self):
        self._listener.stop()
