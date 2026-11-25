
import pandas as pd
import pytest
import networkx as nx

from app.services.graph_intelligence_engine import (
    build_transaction_graph,
    get_account_connections,
    calculate_account_graph_metrics,
    find_suspicious_accounts,
    find_suspicious_transaction_paths,
    calculate_graph_risk,
)


@pytest.fixture
def sample_transactions():
    return pd.DataFrame([
        {
            "transaction_id": "TX001",
            "nameOrig": "A",
            "nameDest": "B",
            "amount": 100,
            "step": 1,
            "type": "TRANSFER",
        },
        {
            "transaction_id": "TX002",
            "nameOrig": "A",
            "nameDest": "B",
            "amount": 200,
            "step": 2,
            "type": "TRANSFER",
        },
        {
            "transaction_id": "TX003",
            "nameOrig": "B",
            "nameDest": "C",
            "amount": 150,
            "step": 3,
            "type": "PAYMENT",
        },
        {
            "transaction_id": "TX004",
            "nameOrig": "D",
            "nameDest": "C",
            "amount": 300,
            "step": 4,
            "type": "PAYMENT",
        },
        {
            "transaction_id": "TX005",
            "nameOrig": "C",
            "nameDest": "E",
            "amount": 250,
            "step": 5,
            "type": "TRANSFER",
        },
    ])


def test_build_transaction_graph(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    assert isinstance(graph, nx.MultiDiGraph)
    assert graph.number_of_nodes() == 5
    assert graph.number_of_edges() == 5
    assert graph.has_edge("A", "B")


def test_parallel_transactions_are_preserved(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    # A sends two separate transactions to B.
    assert graph.number_of_edges("A", "B") == 2


def test_get_account_connections(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    connections = get_account_connections(graph, "B")

    assert connections["account_id"] == "B"
    assert connections["incoming_accounts"] == ["A"]
    assert connections["outgoing_accounts"] == ["C"]
    assert connections["incoming_transaction_count"] == 2
    assert connections["outgoing_transaction_count"] == 1


def test_calculate_account_graph_metrics(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    metrics = calculate_account_graph_metrics(graph, "C")

    assert metrics["account_id"] == "C"
    assert metrics["incoming_transaction_count"] == 2
    assert metrics["outgoing_transaction_count"] == 1
    assert metrics["unique_incoming_accounts"] == 2
    assert "B" in metrics["connected_accounts"]
    assert "D" in metrics["connected_accounts"]


def test_find_suspicious_accounts(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    results = find_suspicious_accounts(
        graph,
        flagged_transaction_ids=["TX003"],
        min_transaction_count=10,
        shared_receiver_threshold=2,
    )

    account_ids = {item["account_id"] for item in results}

    # TX003 connects B and C, and C receives from B and D.
    assert "B" in account_ids
    assert "C" in account_ids


def test_find_transaction_paths(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    paths = find_suspicious_transaction_paths(
        graph,
        source_account="A",
        target_account="E",
        max_hops=3,
        suspicious_transaction_ids=["TX003"],
    )

    assert len(paths) == 1
    assert paths[0]["account_path"] == ["A", "B", "C", "E"]
    assert paths[0]["hop_count"] == 3
    assert paths[0]["suspicious_path_detected"] is True
    assert "TX003" in paths[0]["matched_suspicious_transaction_ids"]


def test_graph_risk_output(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    result = calculate_graph_risk(
        graph,
        transaction_id="TX003",
        suspicious_transaction_ids=["TX003"],
        activity_threshold=2,
        shared_receiver_threshold=2,
    )

    assert result["transaction_id"] == "TX003"
    assert result["sender_account"] == "B"
    assert result["receiver_account"] == "C"
    assert 0.0 <= result["graph_risk"] <= 1.0
    assert result["graph_risk_level"] in {"low", "medium", "high"}
    assert isinstance(result["connected_accounts"], list)
    assert result["suspicious_path_detected"] is True
    assert len(result["evidence"]) > 0


def test_missing_account_raises_error(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    with pytest.raises(ValueError):
        get_account_connections(graph, "UNKNOWN")


def test_missing_transaction_raises_error(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    with pytest.raises(ValueError):
        calculate_graph_risk(graph, "UNKNOWN-TX")


def test_missing_account_columns_raises_error():
    invalid_data = pd.DataFrame({
        "transaction_id": ["TX001"],
        "amount": [100],
    })

    with pytest.raises(ValueError):
        build_transaction_graph(invalid_data)


def test_empty_data_raises_error():
    with pytest.raises(ValueError):
        build_transaction_graph(pd.DataFrame())


def test_invalid_path_limits_raise_error(sample_transactions):
    graph = build_transaction_graph(sample_transactions)

    with pytest.raises(ValueError):
        find_suspicious_transaction_paths(
            graph,
            source_account="A",
            max_hops=0,
        )
