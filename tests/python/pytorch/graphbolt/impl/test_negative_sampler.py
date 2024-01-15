import dgl.graphbolt as gb
import pytest
import torch

from .. import gb_test_utils


def test_NegativeSampler_invoke():
    # Instantiate graph and required datapipes.
    num_seeds = 30
    item_set = gb.ItemSet(
        torch.arange(0, 2 * num_seeds).reshape(-1, 2), names="node_pairs"
    )
    batch_size = 10
    item_sampler = gb.ItemSampler(item_set, batch_size=batch_size)
    negative_ratio = 2

    # Invoke NegativeSampler via class constructor.
    negative_sampler = gb.NegativeSampler(
        item_sampler,
        negative_ratio,
    )
    with pytest.raises(NotImplementedError):
        next(iter(negative_sampler))

    # Invoke NegativeSampler via functional form.
    negative_sampler = item_sampler.sample_negative(
        negative_ratio,
    )
    with pytest.raises(NotImplementedError):
        next(iter(negative_sampler))


def test_UniformNegativeSampler_invoke():
    # Instantiate graph and required datapipes.
    graph = gb_test_utils.rand_csc_graph(100, 0.05, bidirection_edge=True)
    num_seeds = 30
    item_set = gb.ItemSet(
        torch.arange(0, 2 * num_seeds).reshape(-1, 2), names="node_pairs"
    )
    batch_size = 10
    item_sampler = gb.ItemSampler(item_set, batch_size=batch_size)
    negative_ratio = 2

    # Verify iteration over UniformNegativeSampler.
    def _verify(negative_sampler):
        for data in negative_sampler:
            # Assertation
            assert data.negative_srcs is None
            assert data.negative_dsts.size(0) == batch_size
            assert data.negative_dsts.size(1) == negative_ratio

    # Invoke UniformNegativeSampler via class constructor.
    negative_sampler = gb.UniformNegativeSampler(
        item_sampler,
        graph,
        negative_ratio,
    )
    _verify(negative_sampler)

    # Invoke UniformNegativeSampler via functional form.
    negative_sampler = item_sampler.sample_uniform_negative(
        graph,
        negative_ratio,
    )
    _verify(negative_sampler)


@pytest.mark.parametrize("negative_ratio", [1, 5, 10, 20])
def test_Uniform_NegativeSampler(negative_ratio):
    # Construct FusedCSCSamplingGraph.
    graph = gb_test_utils.rand_csc_graph(100, 0.05, bidirection_edge=True)
    num_seeds = 30
    item_set = gb.ItemSet(
        torch.arange(0, num_seeds * 2).reshape(-1, 2), names="node_pairs"
    )
    batch_size = 10
    item_sampler = gb.ItemSampler(item_set, batch_size=batch_size)
    # Construct NegativeSampler.
    negative_sampler = gb.UniformNegativeSampler(
        item_sampler,
        graph,
        negative_ratio,
    )
    # Perform Negative sampling.
    for data in negative_sampler:
        pos_src, pos_dst = data.node_pairs
        neg_src, neg_dst = data.negative_srcs, data.negative_dsts
        # Assertation
        assert len(pos_src) == batch_size
        assert len(pos_dst) == batch_size
        assert len(neg_dst) == batch_size
        assert neg_src is None
        assert neg_dst.numel() == batch_size * negative_ratio


def get_hetero_graph():
    # COO graph:
    # [0, 0, 1, 1, 2, 2, 3, 3, 4, 4]
    # [2, 4, 2, 3, 0, 1, 1, 0, 0, 1]
    # [1, 1, 1, 1, 0, 0, 0, 0, 0] - > edge type.
    # num_nodes = 5, num_n1 = 2, num_n2 = 3
    ntypes = {"n1": 0, "n2": 1}
    etypes = {"n1:e1:n2": 0, "n2:e2:n1": 1}
    indptr = torch.LongTensor([0, 2, 4, 6, 8, 10])
    indices = torch.LongTensor([2, 4, 2, 3, 0, 1, 1, 0, 0, 1])
    type_per_edge = torch.LongTensor([1, 1, 1, 1, 0, 0, 0, 0, 0, 0])
    node_type_offset = torch.LongTensor([0, 2, 5])
    return gb.fused_csc_sampling_graph(
        indptr,
        indices,
        node_type_offset=node_type_offset,
        type_per_edge=type_per_edge,
        node_type_to_id=ntypes,
        edge_type_to_id=etypes,
    )


def test_NegativeSampler_Hetero_Data():
    graph = get_hetero_graph()
    itemset = gb.ItemSetDict(
        {
            "n1:e1:n2": gb.ItemSet(
                torch.LongTensor([[0, 0, 1, 1], [0, 2, 0, 1]]).T,
                names="node_pairs",
            ),
            "n2:e2:n1": gb.ItemSet(
                torch.LongTensor([[0, 0, 1, 1, 2, 2], [0, 1, 1, 0, 0, 1]]).T,
                names="node_pairs",
            ),
        }
    )

    item_sampler = gb.ItemSampler(itemset, batch_size=2)
    negative_dp = gb.UniformNegativeSampler(item_sampler, graph, 1)
    assert len(list(negative_dp)) == 5
