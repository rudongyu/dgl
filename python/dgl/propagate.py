"""Module for message propagation."""
from __future__ import absolute_import

from . import backend as F
from . import traversal as trv
from .heterograph import DGLHeteroGraph

__all__ = [
    "prop_nodes",
    "prop_nodes_bfs",
    "prop_nodes_topo",
    "prop_edges",
    "prop_edges_dfs",
]


def prop_nodes(
    graph,
    nodes_generator,
    message_func="default",
    reduce_func="default",
    apply_node_func="default",
):
    """Functional method for :func:`dgl.DGLGraph.prop_nodes`.

    Parameters
    ----------
    node_generators : generator
        The generator of node frontiers.
    message_func : callable, optional
        The message function.
    reduce_func : callable, optional
        The reduce function.
    apply_node_func : callable, optional
        The update function.

    See Also
    --------
    dgl.DGLGraph.prop_nodes
    """
    graph.prop_nodes(
        nodes_generator, message_func, reduce_func, apply_node_func
    )


def prop_edges(
    graph,
    edges_generator,
    message_func="default",
    reduce_func="default",
    apply_node_func="default",
):
    """Functional method for :func:`dgl.DGLGraph.prop_edges`.

    Parameters
    ----------
    edges_generator : generator
        The generator of edge frontiers.
    message_func : callable, optional
        The message function.
    reduce_func : callable, optional
        The reduce function.
    apply_node_func : callable, optional
        The update function.

    See Also
    --------
    dgl.DGLGraph.prop_edges
    """
    graph.prop_edges(
        edges_generator, message_func, reduce_func, apply_node_func
    )


def prop_nodes_bfs(
    graph,
    source,
    message_func,
    reduce_func,
    reverse=False,
    apply_node_func=None,
):
    """Message propagation using node frontiers generated by BFS.

    Parameters
    ----------
    graph : DGLHeteroGraph
        The graph object.
    source : list, tensor of nodes
        Source nodes.
    message_func : callable
        The message function.
    reduce_func : callable
        The reduce function.
    reverse : bool, optional
        If true, traverse following the in-edge direction.
    apply_node_func : callable, optional
        The update function.

    See Also
    --------
    dgl.traversal.bfs_nodes_generator
    """
    assert isinstance(
        graph, DGLHeteroGraph
    ), "DGLGraph is deprecated, Please use DGLHeteroGraph"
    assert (
        len(graph.canonical_etypes) == 1
    ), "prop_nodes_bfs only support homogeneous graph"
    # TODO(murphy): Graph traversal currently is only supported on
    # CPP graphs. Move graph to CPU as a workaround,
    # which should be fixed in the future.
    nodes_gen = trv.bfs_nodes_generator(graph.cpu(), source, reverse)
    nodes_gen = [F.copy_to(frontier, graph.device) for frontier in nodes_gen]
    prop_nodes(graph, nodes_gen, message_func, reduce_func, apply_node_func)


def prop_nodes_topo(
    graph, message_func, reduce_func, reverse=False, apply_node_func=None
):
    """Message propagation using node frontiers generated by topological order.

    Parameters
    ----------
    graph : DGLHeteroGraph
        The graph object.
    message_func : callable
        The message function.
    reduce_func : callable
        The reduce function.
    reverse : bool, optional
        If true, traverse following the in-edge direction.
    apply_node_func : callable, optional
        The update function.

    See Also
    --------
    dgl.traversal.topological_nodes_generator
    """
    assert isinstance(
        graph, DGLHeteroGraph
    ), "DGLGraph is deprecated, Please use DGLHeteroGraph"
    assert (
        len(graph.canonical_etypes) == 1
    ), "prop_nodes_topo only support homogeneous graph"
    # TODO(murphy): Graph traversal currently is only supported on
    # CPP graphs. Move graph to CPU as a workaround,
    # which should be fixed in the future.
    nodes_gen = trv.topological_nodes_generator(graph.cpu(), reverse)
    nodes_gen = [F.copy_to(frontier, graph.device) for frontier in nodes_gen]
    prop_nodes(graph, nodes_gen, message_func, reduce_func, apply_node_func)


def prop_edges_dfs(
    graph,
    source,
    message_func,
    reduce_func,
    reverse=False,
    has_reverse_edge=False,
    has_nontree_edge=False,
    apply_node_func=None,
):
    """Message propagation using edge frontiers generated by labeled DFS.

    Parameters
    ----------
    graph : DGLHeteroGraph
        The graph object.
    source : list, tensor of nodes
        Source nodes.
    message_func : callable, optional
        The message function.
    reduce_func : callable, optional
        The reduce function.
    reverse : bool, optional
        If true, traverse following the in-edge direction.
    has_reverse_edge : bool, optional
        If true, REVERSE edges are included.
    has_nontree_edge : bool, optional
        If true, NONTREE edges are included.
    apply_node_func : callable, optional
        The update function.

    See Also
    --------
    dgl.traversal.dfs_labeled_edges_generator
    """
    assert isinstance(
        graph, DGLHeteroGraph
    ), "DGLGraph is deprecated, Please use DGLHeteroGraph"
    assert (
        len(graph.canonical_etypes) == 1
    ), "prop_edges_dfs only support homogeneous graph"
    # TODO(murphy): Graph traversal currently is only supported on
    # CPP graphs. Move graph to CPU as a workaround,
    # which should be fixed in the future.
    edges_gen = trv.dfs_labeled_edges_generator(
        graph.cpu(),
        source,
        reverse,
        has_reverse_edge,
        has_nontree_edge,
        return_labels=False,
    )
    edges_gen = [F.copy_to(frontier, graph.device) for frontier in edges_gen]
    prop_edges(graph, edges_gen, message_func, reduce_func, apply_node_func)
