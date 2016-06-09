from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management.base import BaseCommand
from django.apps import apps
import collections
import os

# DEBUG - HOHO
from seed.bluesky.models import *
from seed.models import *



import numpy as np
from scipy.sparse import dok_matrix
from scipy.sparse.csgraph import connected_components

from _localtools import projection_onto_index

class Command(BaseCommand):
    def handle(self, *args, **options):
        print "Calculating Statistics"





        all_nodes = set(map(projection_onto_index(0), m2m)).union(set(map(projection_onto_index(1), m2m)))
        child_dictionary = collections.defaultdict(lambda : set())
        parent_dictionary = collections.defaultdict(lambda : set())

        adj_dim = max(all_nodes) + 1
        adj_matrix = dok_matrix((adj_dim, adj_dim), dtype=np.bool)

        for (from_node, to_node) in m2m:
            adj_matrix[from_node, to_node] = 1
            child_dictionary[from_node].add(to_node)
            parent_dictionary[to_node].add(from_node)

        # We don't care about the total number because
        _, labelarray = connected_components(adj_matrix)

        counts = collections.Counter()
        for label in labelarray: counts[label] += 1
        nontrivial_tree_labels = set(map(projection_onto_index(0), filter(lambda (x,y): y > 1, counts.items())))

        # complex_tree_bs_nodes = [node for (node,label) in enumerate(labelarray) if label in nontrivial_tree_labels]
        # print "There are non-trivial {} trees in the building snapshots table containing {} nodes.".format(len(nontrivial_tree_labels), len(complex_tree_bs_nodes))

        # for label in nontrivial_tree_labels:
        label = nontrivial_tree_labels.pop()
        printTreeStatistics(label, labelarray, parent_dictionary, child_dictionary, counts[label])
        return

def findOccurenceIndexesLinear(array, val):
    results = []
    for (ndx, array_val) in enumerate(array):
        if array_val == val: results.append(ndx)
    return set(results)

def getNodeSinks(tree_label, labelarray, parent_adj_dict, child_adj_dict):
    label_nodes = findOccurenceIndexesLinear(labelarray, tree_label)

    import_nodes = filter(lambda node_ndx: len(parent_adj_dict[node_ndx]) == 0, label_nodes)
    leaf_nodes = filter(lambda node_ndx: len(child_adj_dict[node_ndx]) == 0, label_nodes)
    other_nodes = [x for x in label_nodes if x not in import_nodes and x not in leaf_nodes]

    # print "import_nodes({}): {}".format(len(import_nodes), import_nodes)
    # print "leaf_nodes({}): {}".format(len(leaf_nodes), leaf_nodes)
    # print "other_nodes({}): {}".format(len(other_nodes), other_nodes)
    return import_nodes, leaf_nodes, other_nodes

def printTreeStatistics(tree_label, labelarray, parent_adj_matrix, child_adj_matrix, count):
    print "Tree: {}, Size: {}".format(tree_label, count)
    # Double check there is exactly one FINAL node
    a,b,c = getNodeSinks(tree_label, labelarray, parent_adj_matrix, child_adj_matrix)
    print a,b,c
    return

def processLabel(label, labelarray, parent_dictionary, child_dictionary):
    import_nodes, leaf_nodes, other_nodes  = getNodeSinks(label, labelarray, parent_dictionary, child_dictionary)

    import_buildingsnapshots = seed.models.BuildingSnapshot.objects.filter(pk__in=import_nodes).all()
    leaf_buildingsnapshots= seed.models.BuildingSnapshot.objects.filter(pk__in=leaf_nodes).all()
    other_buildingsnapshots= seed.models.BuildingSnapshot.objects.filter(pk__in=other_nodes).all()
