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


    def to_representation(self, obj):
        result = super().to_representation(obj)
        result['level_name_index'] = obj.access_level_instance.depth - 1
        return result

    def validate(self, data):
        baseline_cycle = data.get('baseline_cycle')
        current_cycle = data.get('current_cycle')

        if baseline_cycle and current_cycle:
            if baseline_cycle == current_cycle:
                raise ValidationError('Cycles must be unique.')
            
            if baseline_cycle.end > current_cycle.end:
                raise ValidationError('Baseline Cycle must preceed Current Cycle')

        
        # non Null columns must be uniuqe
        columns = [data.get('column1'), data.get('column2'), data.get('column3')]   
        unique_columns = {column for column in columns if column is not None}
        if len(unique_columns) < len([col for col in columns if col is not None]):
            message = 'Columns must be unique.'
            raise ValidationError(message)
        
        return data