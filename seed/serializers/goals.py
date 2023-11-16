"""
SEED Platform (TM), Copyright (c) Alliance for Sustainable Energy, LLC, and other contributors.
See also https://github.com/seed-platform/seed/main/LICENSE.md
"""
from rest_framework import serializers
from django.core.exceptions import ValidationError

from seed.models import Goal


class GoalSerializer(serializers.ModelSerializer):

    class Meta:
        model = Goal
        fields = '__all__'

    def validate(self, data):
        # cycles must be unique 
        if data.get('baseline_cycle') == data.get('current_cycle'):
            message = 'Cycles must be unique.'
            raise ValidationError(message)
        
        # non Null columns must be uniuqe
        columns = [data.get('column1'), data.get('column2'), data.get('column3')]   
        unique_columns = set(columns)
        if len(unique_columns) < len([col for col in columns if col is not None]):
            message = 'Columns must be unique.'
            raise ValidationError(message)
        
        return data