from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management.base import BaseCommand
from django.apps import apps
import collections
import os

# DEBUG - HOHO
from seed.models import *
from seed.models import *

from django.db import models, migrations
from django.core.management.base import BaseCommand
from django.apps import apps
import collections
import os
# import networkx as nx
# import matplotlib.pyplot as plt
# import pygraphviz
import logging
from IPython import embed
# from networkx.drawing.nx_agraph import graphviz_layout
import seed.models
# import numpy as np
# from scipy.sparse import dok_matrix
# from scipy.sparse.csgraph import connected_components
from _localtools import *

import numpy as np
from scipy.sparse import dok_matrix
from scipy.sparse.csgraph import connected_components

from _localtools import projection_onto_index

class Command(BaseCommand):
    def handle(self, *args, **options):
        embed()
        return
