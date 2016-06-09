import os
import pdb

def get_core_organizations():
    # IDs of the 12 organizations defined by robin 6/6/16.
    # Google Doc for file describing this:
    # https://docs.google.com/document/u/4/d/1z1FScU-lysmgkCNGa9-hH0PCQudpzV_IG2IKcxYzyfM/edit
    GOOD_ORGS = [124,21,117,69,6,20,7,156,10,49,105,126]
    return GOOD_ORGS


def projection_onto_index(n):
    """Return function that returns the nth value for a vector."""
    def projection_func(vect): return vect[n]
    return projection_func


def get_static_building_snapshot_tree_file():
    management_file_directory = os.path.split(__file__)[0]
    tree_file = os.path.join(management_file_directory, "tree_file.csv")
    return tree_file

def read_building_snapshot_tree_structure(input_file):
    with open(input_file) as tree_file:
        l = tree_file.readline() # Header
        assert l.startswith("id")

        z = lambda line: map(int, line.split(',')[1:])
        m2m = map(z, tree_file.readlines())
    return m2m



def find_matching_values_linear(array, val):
    results = []
    for (ndx, array_val) in enumerate(array):
        if array_val == val: results.append(ndx)
    return set(results)



def get_node_sinks(tree_label, labelarray, parent_adj_dict, child_adj_dict):
    label_nodes = find_matching_values_linear(labelarray, tree_label)

    import_nodes = filter(lambda node_ndx: len(parent_adj_dict[node_ndx]) == 0, label_nodes)
    leaf_nodes = filter(lambda node_ndx: len(child_adj_dict[node_ndx]) == 0, label_nodes)
    other_nodes = [x for x in label_nodes if x not in import_nodes and x not in leaf_nodes]

    # print "import_nodes({}): {}".format(len(import_nodes), import_nodes)
    # print "leaf_nodes({}): {}".format(len(leaf_nodes), leaf_nodes)
    # print "other_nodes({}): {}".format(len(other_nodes), other_nodes)
    return import_nodes, leaf_nodes, other_nodes
