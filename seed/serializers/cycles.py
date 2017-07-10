# !/usr/bin/env python
# encoding: utf-8
"""
:copyright (c) 2014 - 2017, The Regents of the University of California, through Lawrence Berkeley National Laboratory (subject to receipt of any required approvals from the U.S. Department of Energy) and contributors. All rights reserved.  # NOQA
:author
"""
from rest_framework import serializers

from seed.models import Cycle


class CycleSerializer(serializers.ModelSerializer):

    class Meta:
        model = Cycle
        fields = ('name', 'start', 'end',
                  'organization', 'user', 'id', )
        extra_kwargs = {
            'user': {'read_only': True},
            'organization': {'read_only': True}
        }
