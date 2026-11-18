"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as BaseBackend
from django.core.mail.utils import DNS_NAME


class EmailBackend(BaseBackend):
    def __init__(self, *, verify_tls=None, **kwargs):
        super().__init__(**kwargs)
        self.verify_tls = settings.EMAIL_VERIFY_TLS if verify_tls is None else verify_tls

    def open(self):
        if self.connection:
            # Nothing to do if the connection is already open.
            return False

        # If local_hostname is not specified, socket.getfqdn() gets used.
        # For performance, we use the cached FQDN for local_hostname.
        connection_params = {"local_hostname": DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params["timeout"] = self.timeout
        if self.use_ssl:
            connection_params["context"] = self.ssl_context
        try:
            self.connection = self.connection_class(self.host, self.port, **connection_params)

            # TLS/SSL are mutually exclusive, so only attempt TLS over
            # non-secure connections.
            if not self.use_ssl and self.use_tls:
                if self.verify_tls:
                    self.connection.starttls(context=self.ssl_context)
                else:
                    self.connection.starttls()
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise
