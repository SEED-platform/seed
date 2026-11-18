"""
SEED Platform (TM), Copyright (c) Alliance for Energy Innovation, LLC, and other contributors.
See also https://github.com/SEED-platform/seed/blob/main/LICENSE.md
"""

import argparse
from collections import Counter

from django.db import connections
from django.test.runner import DiscoverRunner
from django.test.utils import iter_test_cases


def parse_shard(value):
    index, _, count = value.partition("/")
    if not (index.isdigit() and count.isdigit() and 1 <= int(index) <= int(count)):
        raise argparse.ArgumentTypeError(f"expected INDEX/COUNT with 1 <= INDEX <= COUNT, got {value!r}")
    return int(index), int(count)


class ParallelTestRunner(DiscoverRunner):
    def __init__(self, shard=None, **kwargs):
        super().__init__(**kwargs)
        self.shard = shard

    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--shard",
            type=parse_shard,
            metavar="INDEX/COUNT",
            help="Run only one of COUNT groups of test modules with similar test counts, e.g. 2/6, to split the suite across CI jobs.",
        )

    def load_tests_for_label(self, label, discover_kwargs):
        tests = super().load_tests_for_label(label, discover_kwargs)
        if self.shard is None:
            return tests

        # Assign whole modules, largest first, to the shard with the fewest tests so far. Every shard
        # discovers the same tests, so the shards agree on the split without a shared list of modules.
        index, count = self.shard
        tests = list(iter_test_cases(tests))
        loads = [0] * count
        modules = set()
        for module, size in sorted(Counter(type(test).__module__ for test in tests).items(), key=lambda item: (-item[1], item[0])):
            shard = loads.index(min(loads))
            loads[shard] += size
            if shard == index - 1:
                modules.add(module)

        # Parallel workers take one class at a time in this order, so start the largest classes first
        # to keep a long class from finishing after the others. The sort is stable, so classes stay intact.
        class_sizes = Counter(type(test) for test in tests)
        tests = sorted((test for test in tests if type(test).__module__ in modules), key=lambda test: -class_sizes[type(test)])
        self.log(f"Shard {index}/{count}: {len(tests)} of {sum(loads)} tests from {len(modules)} modules.")
        return self.test_suite(tests)

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
