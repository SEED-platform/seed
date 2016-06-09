"""Take an organization pk and produce a graph of its BuildingSnapshot
View.
"""

from __future__ import unicode_literals

from django.db import models, migrations
from django.core.management.base import BaseCommand
from seed.lib.superperms.orgs.models import Organization
from django.apps import apps
import pdb
import collections
import os
import networkx as nx
import matplotlib.pyplot as plt
import pygraphviz
import logging
import itertools
from IPython import embed
from networkx.drawing.nx_agraph import graphviz_layout
import seed.bluesky.models
import numpy as np
from scipy.sparse import dok_matrix
from scipy.sparse.csgraph import connected_components
from _localtools import projection_onto_index
from _localtools import get_static_building_snapshot_tree_file
from _localtools import read_building_snapshot_tree_structure
from _localtools import get_core_organizations
from _localtools import get_node_sinks

logging.basicConfig(level=logging.DEBUG)

class Command(BaseCommand):
    def add_arguments(self, parser):
        # Positional arguments
        # parser.add_argument('building_snapshot_pk', type=int)
        return

    def handle(self, *args, **options):
        """Do something."""

        tree_file = get_static_building_snapshot_tree_file()
        m2m = read_building_snapshot_tree_structure(tree_file)

        all_nodes = set(map(projection_onto_index(0), m2m)).union(set(map(projection_onto_index(1), m2m)))
        child_dictionary = collections.defaultdict(lambda : set())
        parent_dictionary = collections.defaultdict(lambda : set())

        adj_dim = max(all_nodes) + 1
        adj_matrix = dok_matrix((adj_dim, adj_dim), dtype=np.bool)

        for (from_node, to_node) in m2m:
            adj_matrix[from_node, to_node] = 1
            child_dictionary[from_node].add(to_node)
            parent_dictionary[to_node].add(from_node)

        # Core data struct, possible refactor point.
        all_nodes, child_dictionary, parent_dictionary, adj_matrix

        # We don't care about the total number because
        _, labelarray = connected_components(adj_matrix)

        counts = collections.Counter()
        for label in labelarray: counts[label] += 1

        core_organization = get_core_organizations()
        for org_id in core_organization:
            # Writing loop over organizations

            org = Organization.objects.filter(pk=org_id).first()
            assert org, "Should get something back here."

            org_canonical_buildings = seed.models.CanonicalBuilding.objects.filter(canonical_snapshot__super_organization=org_id).all()
            org_canonical_snapshots = [cb.canonical_snapshot for cb in org_canonical_buildings]

            tree_sizes = [counts[labelarray[bs.id]] for bs in org_canonical_snapshots]

            ## For each of those trees find the tip
            ## For each of those trees find the import records
            ## For each of those trees find the cycles associated with it

            for bs in org_canonical_snapshots:
                bs_label = labelarray[bs.id]
                import_nodes, leaf_nodes, other_nodes  = get_node_sinks(label, labelarray, parent_dictionary, child_dictionary)


                # Load all those building snapshots
                tree_nodes = itertools.chain(import_nodes, leaf_nodes, other_nodes)
                building_dict = {bs.id: bs for bs in seed.models.BuildingSnapshot.objects.filter(pk__in=tree_nodes).all()}
                missing_buildings = [node for node in itertools.chain(import_nodes, leaf_nodes, other_nodes) if node not in building_dict]

                import_buildingsnapshots = [building_dict[bs_id] for bs_id in import_nodes]
                leaf_buildingsnapshots = [building_dict[bs_id] for bs_id in leaf_nodes]
                other_buildingsnapshots = [building_dict[bs_id] for bs_id in other_nodes]

                create_associated_blue_sky_structure(org, import_buildingsnapshots, leaf_buildingsnapshots, other_buildingsnapshots, child_dictionary, parent_dictionary, adj_matrix)
        # counts = collections.Counter()
        # for label in labelarray: counts[label] += 1
        # nontrivial_tree_labels = set(map(projection_onto_index(0), filter(lambda (x,y): y > 1, counts.items())))


        # nontrivial_tree_labels = set(map(projection_onto_index(0), filter(lambda (x,y): y > 1, counts.items())))

        # label = nontrivial_tree_labels.pop()
        # embed()

        return


def create_associated_blue_sky_structure(org, import_buildingsnapshots, leaf_buildingsnapshots, other_buildingsnapshots, child_dictionary, parent_dictionary, adj_matrix):
    """Take tree structure describing a single Property/TaxLot over time and create the entities."""
    logging.info("Creating a new entity thing-a-majig!")
    embed()
    return
