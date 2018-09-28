from __future__ import unicode_literals

# import networkx as nx
# import matplotlib.pyplot as plt
# import pygraphviz
from IPython import embed
from django.core.management.base import BaseCommand


# DEBUG - HOHO
# from networkx.drawing.nx_agraph import graphviz_layout
# import numpy as np
# from scipy.sparse import dok_matrix
# from scipy.sparse.csgraph import connected_components


class Command(BaseCommand):
    def handle(self, *args, **options):
        embed()
        return
