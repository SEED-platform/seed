from graphviz import Digraph


def c_node_name(bs):
    status = 'active' if bs.canonical_building.active else 'inactive'
    return "C-{bs.custom_id_1} ({bs.canonical_building_id} - {status})".format(
        bs=bs,
        status=status,
    )


def bs_node_name(bs):
    return "{bs.custom_id_1} ({bs.pk})".format(bs=bs)


def c_node_id(bs):
    return "C-{bs.canonical_building_id}".format(bs=bs)


def bs_node_id(bs):
    return str(bs.pk)


def s_node_id(c):
    return "S-{c.canonical_snapshot.pk}".format(c=c)


def s_node_name(c):
    return "S-{c.canonical_snapshot.custom_id_1} ({c.canonical_snapshot_id})".format(c=c)


def create_tree(queryset):
    """
    Given a queryset of BuildingSnapshots, construct a graphviz dot graph of
    the tree structure.  This can be useful for visually inspecting the tree.
    """
    seen_nodes = set()

    dot = Digraph(comment="Building Snapshot Visualization")
    for bs in queryset:
        if bs.canonical_building_id is None:
            continue
        bs_id, bs_name = bs_node_id(bs), bs_node_name(bs)
        c_id, c_name = c_node_id(bs), c_node_name(bs)
        dot.node(c_id, c_name)
        dot.node(bs_id, bs_name)
        dot.edge(c_id, bs_id)
        seen_nodes.add(bs_id)
        seen_nodes.add((c_id, bs_id))

        if bs.canonical_building.canonical_snapshot_id is not None:
            s_id, s_name = s_node_id(bs.canonical_building), s_node_name(bs.canonical_building)
            dot.node(s_id, s_name)
            dot.edge(s_id, c_id)

        create_bs_tree(bs, dot, seen_nodes)

    return dot


def create_bs_tree(bs, dot, seen_nodes):
    """
    Recursively crawl down the tree and add the nodes and edges.
    """
    parent_id = bs_node_id(bs)

    for child in bs.children.all():
        child_id, child_name = bs_node_id(child), bs_node_name(child)
        if child_id not in seen_nodes:
            dot.node(child_id, child_name)
            seen_nodes.add(child_id)

        if (parent_id, child_id) not in seen_nodes:
            dot.edge(parent_id, child_id)
            seen_nodes.add((parent_id, child_id))

        create_bs_tree(child, dot, seen_nodes)
