"""
This script demonstrates node classification with GraphSAGE on large graphs, 
merging GraphBolt (GB) and PyTorch Geometric (PyG). GraphBolt efficiently manages 
data loading for large datasets, crucial for mini-batch processing. Post data 
loading, PyG's user-friendly framework takes over for training, showcasing seamless 
integration with GraphBolt. This combination offers an efficient alternative to 
traditional Deep Graph Library (DGL) methods, highlighting adaptability and 
scalability in handling large-scale graph data for diverse real-world applications.



Key Features:
- Implements the GraphSAGE model, a scalable GNN, for node classification on large graphs.
- Utilizes GraphBolt, an efficient framework for large-scale graph data processing.
- Integrates with PyTorch Geometric for building and training the GraphSAGE model.
- The script is well-documented, providing clear explanations at each step.

This flowchart describes the main functional sequence of the provided example.
main: 

main
│
├───> Load and preprocess dataset (GraphBolt)
│     │
│     └───> Utilize GraphBolt's BuiltinDataset for dataset handling
│
├───> Instantiate the SAGE model (PyTorch Geometric)
│     │
│     └───> Define the GraphSAGE model architecture
│
├───> Train the model
│     │
│     ├───> Mini-Batch Processing with GraphBolt
│     │     │
│     │     └───> Efficient handling of mini-batches using GraphBolt's utilities
│     │
│     └───> Training Loop
│           │
│           ├───> Forward and backward passes
│           │
│           └───> Parameters optimization
│
└───> Evaluate the model
      │
      └───> Performance assessment on validation and test datasets
            │
            └───> Accuracy and other relevant metrics calculation


"""

import argparse

import dgl.graphbolt as gb
import torch
import torch.nn.functional as F
import torchmetrics.functional as MF
from torch_geometric.nn import SAGEConv


class GraphSAGE(torch.nn.Module):
    #####################################################################
    # (HIGHLIGHT) Define the GraphSAGE model architecture.
    #
    # - This class inherits from `torch.nn.Module`.
    # - Two convolutional layers are created using the SAGEConv class from PyG.
    # - 'in_size', 'hidden_size', 'out_size' are the sizes of
    #   the input, hidden, and output features, respectively.
    # - The forward method defines the computation performed at every call.
    #####################################################################
    def __init__(self, in_size, hidden_size, out_size):
        super(GraphSAGE, self).__init__()
        self.layers = torch.nn.ModuleList()
        self.layers.append(SAGEConv(in_size, hidden_size))
        self.layers.append(SAGEConv(hidden_size, hidden_size))
        self.layers.append(SAGEConv(hidden_size, out_size))

    def forward(self, blocks, x, device):
        h = x
        for i, (layer, block) in enumerate(zip(self.layers, blocks)):
            src, dst = block.edges()
            edge_index = torch.stack([src, dst], dim=0)
            h_src, h_dst = h, h[: block.number_of_dst_nodes()]
            h = layer((h_src, h_dst), edge_index)
            if i != len(blocks) - 1:
                h = F.relu(h)
        return h


def create_dataloader(dataset_set, graph, feature, device, is_train):
    #####################################################################
    # (HIGHLIGHT) Create a data loader for efficiently loading graph data.
    #
    # - 'ItemSampler' samples mini-batches of node IDs from the dataset.
    # - 'sample_neighbor' performs neighbor sampling on the graph.
    # - 'FeatureFetcher' fetches node features based on the sampled subgraph.
    # - 'CopyTo' copies the fetched data to the specified device.

    #####################################################################
    # Create a datapipe for mini-batch sampling with a specific neighbor fanout.
    # Here, [10, 10, 10] specifies the number of neighbors sampled for each node at each layer.
    # We're using `sample_neighbor` for consistency with DGL's sampling API.
    # Note: GraphBolt offers additional sampling methods, such as `sample_layer_neighbor`,
    # which could provide further optimization and efficiency for GNN training.
    # Users are encouraged to explore these advanced features for potentially improved performance.

    # Initialize an ItemSampler to sample mini-batches from the dataset.
    datapipe = gb.ItemSampler(
        dataset_set, batch_size=1024, shuffle=is_train, drop_last=is_train
    )
    # Sample neighbors for each node in the mini-batch.
    datapipe = datapipe.sample_neighbor(graph, [10, 10, 10])
    # Fetch node features for the sampled subgraph.
    datapipe = datapipe.fetch_feature(feature, node_feature_keys=["feat"])
    # Copy the data to the specified device.
    datapipe = datapipe.copy_to(device=device)
    # Create and return a DataLoader to handle data loading.
    dataloader = gb.DataLoader(datapipe, num_workers=0)

    return dataloader


def train(model, dataloader, optimizer, criterion, device, num_classes):
    #####################################################################
    # (HIGHLIGHT) Train the model for one epoch.
    #
    # - Iterates over the data loader, fetching mini-batches of graph data.
    # - For each mini-batch, it performs a forward pass, computes loss, and
    #   updates the model parameters.
    # - The function returns the average loss and accuracy for the epoch.
    #
    # Parameters:
    #   model: The GraphSAGE model.
    #   dataloader: DataLoader that provides mini-batches of graph data.
    #   optimizer: Optimizer used for updating model parameters.
    #   criterion: Loss function used for training.
    #   device: The device (CPU/GPU) to run the training on.
    #####################################################################

    model.train()  # Set the model to training mode
    total_loss = 0  # Accumulator for the total loss
    total_correct = 0  # Accumulator for the total number of correct predictions
    total_samples = 0  # Accumulator for the total number of samples processed
    num_batches = 0  # Counter for the number of mini-batches processed

    for minibatch in dataloader:
        node_features = minibatch.node_features["feat"]
        labels = minibatch.labels
        optimizer.zero_grad()
        out = model(minibatch.blocks, node_features, device)
        loss = criterion(out, labels)
        total_loss += loss.item()
        total_correct += MF.accuracy(
            out, labels, task="multiclass", num_classes=num_classes
        ) * labels.size(0)
        total_samples += labels.size(0)
        loss.backward()
        optimizer.step()
        num_batches += 1
    avg_loss = total_loss / num_batches
    avg_accuracy = total_correct / total_samples
    return avg_loss, avg_accuracy


@torch.no_grad()
def evaluate(model, dataloader, device, num_classes):
    model.eval()
    y_hats = []
    ys = []
    for minibatch in dataloader:
        node_features = minibatch.node_features["feat"]
        labels = minibatch.labels
        out = model(minibatch.blocks, node_features, device)
        y_hats.append(out)
        ys.append(labels)

    return MF.accuracy(
        torch.cat(y_hats),
        torch.cat(ys),
        task="multiclass",
        num_classes=num_classes,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Which dataset are you going to use?"
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="ogbn-arxiv",
        help='Name of the dataset to use (e.g., "ogbn-products", "ogbn-arxiv")',
    )
    args = parser.parse_args()
    dataset_name = args.dataset
    dataset = gb.BuiltinDataset(dataset_name).load()
    graph = dataset.graph
    feature = dataset.feature
    train_set = dataset.tasks[0].train_set
    valid_set = dataset.tasks[0].validation_set
    test_set = dataset.tasks[0].test_set
    num_classes = dataset.tasks[0].metadata["num_classes"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    train_dataloader = create_dataloader(
        train_set, graph, feature, device, is_train=True
    )
    valid_dataloader = create_dataloader(
        valid_set, graph, feature, device, is_train=False
    )
    test_dataloader = create_dataloader(
        test_set, graph, feature, device, is_train=False
    )
    in_channels = feature.size("node", None, "feat")[0]
    hidden_channels = 128
    model = GraphSAGE(in_channels, hidden_channels, num_classes).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01, weight_decay=5e-4)
    criterion = torch.nn.CrossEntropyLoss()
    for epoch in range(10):
        train_loss, train_accuracy = train(
            model, train_dataloader, optimizer, criterion, device, num_classes
        )

        valid_accuracy = evaluate(model, valid_dataloader, device, num_classes)
        print(
            f"Epoch {epoch}, Train Loss: {train_loss:.4f}, Train Accuracy: {train_accuracy:.4f}, "
            f"Valid Accuracy: {valid_accuracy:.4f}"
        )
    test_accuracy = evaluate(model, test_dataloader, device, num_classes)
    print(f"Test Accuracy: {test_accuracy:.4f}")


if __name__ == "__main__":
    main()
