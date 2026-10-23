"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

from django.db import connections
from django.test.runner import DiscoverRunner


class ParallelTestRunner(DiscoverRunner):
    def setup_databases(self, **kwargs):
        # DiscoverRunner.build_suite() reduces --parallel to the number of
        # parallelizable TestCase groups. For example, --parallel=32 with five
        # groups creates only five database clones. Pass that effective count to
        # the backend so it knows when the final clone is complete and can
        # re-enable connections to the source test database.
        for alias in kwargs.get("aliases") or connections:
            set_parallel_processes = getattr(connections[alias].creation, "set_parallel_processes", None)
            if set_parallel_processes is not None:
                set_parallel_processes(self.parallel)

        return super().setup_databases(**kwargs)
