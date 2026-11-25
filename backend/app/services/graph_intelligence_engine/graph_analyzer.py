
from __future__ import annotations

from itertools import product
from typing import Any

import networkx as nx
import pandas as pd


def _records_to_dataframe(transactions: Any) -> pd.DataFrame:
    """Convert supported transaction inputs into a normalized DataFrame."""
    if isinstance(transactions, pd.DataFrame):
        df = transactions.copy()
    elif isinstance(transactions, dict):
        df = pd.DataFrame([transactions])
    elif isinstance(transactions, (list, tuple)):
        df = pd.DataFrame(list(transactions))
    else:
        raise TypeError(
            "transactions must be a DataFrame, dictionary, or list of dictionaries"
        )

    if df.empty:
        raise ValueError("Transaction data cannot be empty")

    aliases = {
        "nameOrig": "sender_account",
        "nameDest": "receiver_account",
        "type": "transaction_type",
    }

    for source, target in aliases.items():
        if target not in df.columns and source in df.columns:
            df[target] = df[source]

    required = {"sender_account", "receiver_account"}
    missing = required.difference(df.columns)

    if missing:
        raise ValueError(
            f"Missing required transaction columns: {sorted(missing)}"
        )

    if "transaction_id" not in df.columns:
        df["transaction_id"] = [
            f"TX-{index + 1:06d}" for index in range(len(df))
        ]

    if "amount" not in df.columns:
        df["amount"] = 0.0

    if "step" not in df.columns:
        df["step"] = None

    if "transaction_type" not in df.columns:
        df["transaction_type"] = "UNKNOWN"

    df["sender_account"] = df["sender_account"].astype("string").str.strip()
    df["receiver_account"] = df["receiver_account"].astype("string").str.strip()
    df["transaction_id"] = df["transaction_id"].astype("string").str.strip()

    invalid_accounts = (
        df["sender_account"].isna()
        | df["receiver_account"].isna()
        | df["sender_account"].eq("")
        | df["receiver_account"].eq("")
    )

    if invalid_accounts.any():
        raise ValueError("Every transaction must have sender and receiver accounts")

    if df["transaction_id"].isna().any() or df["transaction_id"].eq("").any():
        raise ValueError("Transaction IDs cannot be empty")

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0.0)

    if (df["amount"] < 0).any():
        raise ValueError("Transaction amounts cannot be negative")

    return df


def build_transaction_graph(transactions: Any) -> nx.MultiDiGraph:
    """
    Build a directed multigraph.

    Accounts are nodes. Each transaction is a directed edge from sender
    to receiver. MultiDiGraph preserves multiple transactions between
    the same pair of accounts.
    """
    df = _records_to_dataframe(transactions)
    graph = nx.MultiDiGraph()

    for row_number, row in enumerate(df.to_dict(orient="records")):
        sender = str(row["sender_account"])
        receiver = str(row["receiver_account"])
        transaction_id = str(row["transaction_id"])

        graph.add_node(sender, account_id=sender)
        graph.add_node(receiver, account_id=receiver)

        # Use a unique edge key so repeated transaction IDs do not
        # accidentally overwrite another edge.
        edge_key = f"{transaction_id}::{row_number}"

        graph.add_edge(
            sender,
            receiver,
            key=edge_key,
            transaction_id=transaction_id,
            amount=float(row["amount"]),
            step=row["step"],
            transaction_type=str(row["transaction_type"]),
        )

    graph.graph["transaction_count"] = len(df)
    graph.graph["account_count"] = graph.number_of_nodes()

    return graph


def get_account_connections(
    graph: nx.MultiDiGraph,
    account_id: str,
) -> dict[str, Any]:
    """Return the incoming and outgoing account connections."""
    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("graph must be a NetworkX MultiDiGraph")

    account_id = str(account_id)

    if account_id not in graph:
        raise ValueError(f"Account not found in graph: {account_id}")

    incoming_accounts = sorted(str(node) for node in graph.predecessors(account_id))
    outgoing_accounts = sorted(str(node) for node in graph.successors(account_id))

    return {
        "account_id": account_id,
        "incoming_accounts": incoming_accounts,
        "outgoing_accounts": outgoing_accounts,
        "incoming_transaction_count": int(graph.in_degree(account_id)),
        "outgoing_transaction_count": int(graph.out_degree(account_id)),
        "connected_accounts": sorted(
            set(incoming_accounts).union(outgoing_accounts)
        ),
    }


def calculate_account_graph_metrics(
    graph: nx.MultiDiGraph,
    account_id: str,
) -> dict[str, Any]:
    """Calculate transaction activity and connectivity metrics for an account."""
    connections = get_account_connections(graph, account_id)

    return {
        "account_id": connections["account_id"],
        "in_degree": int(graph.in_degree(account_id)),
        "out_degree": int(graph.out_degree(account_id)),
        "total_degree": int(graph.degree(account_id)),
        "incoming_transaction_count": connections[
            "incoming_transaction_count"
        ],
        "outgoing_transaction_count": connections[
            "outgoing_transaction_count"
        ],
        "unique_incoming_accounts": len(connections["incoming_accounts"]),
        "unique_outgoing_accounts": len(connections["outgoing_accounts"]),
        "connected_accounts": connections["connected_accounts"],
    }


def _transaction_edge_records(graph: nx.MultiDiGraph) -> list[dict[str, Any]]:
    """Return all graph edges with their transaction attributes."""
    records = []

    for sender, receiver, key, data in graph.edges(keys=True, data=True):
        records.append({
            "sender_account": str(sender),
            "receiver_account": str(receiver),
            "edge_key": str(key),
            "transaction_id": str(data.get("transaction_id", key)),
            "amount": float(data.get("amount", 0.0)),
            "step": data.get("step"),
            "transaction_type": str(data.get("transaction_type", "UNKNOWN")),
        })

    return records


def find_suspicious_accounts(
    graph: nx.MultiDiGraph,
    flagged_transaction_ids: set[str] | list[str] | tuple[str, ...] | None = None,
    min_transaction_count: int = 10,
    shared_receiver_threshold: int = 3,
) -> list[dict[str, Any]]:
    """
    Identify accounts with notable graph evidence.

    Evidence includes:
    - An endpoint of a transaction flagged by another detection component.
    - High incoming or outgoing transaction activity.
    - Receiving transactions from multiple distinct senders.

    These indicators are for investigation, not proof of fraud.
    """
    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("graph must be a NetworkX MultiDiGraph")

    if min_transaction_count < 1 or shared_receiver_threshold < 2:
        raise ValueError("Thresholds must be positive and meaningful")

    flagged_ids = {str(value) for value in (flagged_transaction_ids or [])}
    evidence_by_account: dict[str, list[str]] = {
        str(node): [] for node in graph.nodes
    }

    for sender, receiver, data in graph.edges(data=True):
        transaction_id = str(data.get("transaction_id", ""))

        if transaction_id in flagged_ids:
            evidence_by_account[str(sender)].append(
                f"Sender is connected to flagged transaction {transaction_id}"
            )
            evidence_by_account[str(receiver)].append(
                f"Receiver is connected to flagged transaction {transaction_id}"
            )

    # Detect receivers shared by multiple distinct sender accounts.
    for receiver in graph.nodes:
        distinct_senders = {
            str(sender)
            for sender in graph.predecessors(receiver)
        }

        if len(distinct_senders) >= shared_receiver_threshold:
            evidence_by_account[str(receiver)].append(
                f"Receives transactions from {len(distinct_senders)} "
                "different sender accounts"
            )

    results = []

    for account_id in graph.nodes:
        account_id = str(account_id)
        incoming_count = int(graph.in_degree(account_id))
        outgoing_count = int(graph.out_degree(account_id))

        if outgoing_count >= min_transaction_count:
            evidence_by_account[account_id].append(
                f"High outgoing transaction activity: {outgoing_count}"
            )

        if incoming_count >= min_transaction_count:
            evidence_by_account[account_id].append(
                f"High incoming transaction activity: {incoming_count}"
            )

        evidence = sorted(set(evidence_by_account[account_id]))

        if evidence:
            results.append({
                "account_id": account_id,
                "incoming_transaction_count": incoming_count,
                "outgoing_transaction_count": outgoing_count,
                "evidence": evidence,
            })

    return sorted(results, key=lambda item: item["account_id"])


def find_suspicious_transaction_paths(
    graph: nx.MultiDiGraph,
    source_account: str,
    target_account: str | None = None,
    max_hops: int = 3,
    max_paths: int = 20,
    suspicious_transaction_ids: set[str] | list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """
    Find directed account-to-account paths.

    A returned path is marked suspicious only when at least one of its
    transactions appears in suspicious_transaction_ids.
    """
    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("graph must be a NetworkX MultiDiGraph")

    if max_hops < 1 or max_paths < 1:
        raise ValueError("max_hops and max_paths must be at least 1")

    source_account = str(source_account)

    if source_account not in graph:
        raise ValueError(f"Source account not found: {source_account}")

    if target_account is not None:
        target_account = str(target_account)

        if target_account not in graph:
            raise ValueError(f"Target account not found: {target_account}")

    suspicious_ids = {
        str(value) for value in (suspicious_transaction_ids or [])
    }

    if target_account is not None:
        candidate_paths = nx.all_simple_paths(
            graph,
            source=source_account,
            target=target_account,
            cutoff=max_hops,
        )
    else:
        candidate_paths = (
            path
            for target in graph.nodes
            if target != source_account
            for path in nx.all_simple_paths(
                graph,
                source=source_account,
                target=target,
                cutoff=max_hops,
            )
        )

    results = []
    seen_paths = set()

    for account_path in candidate_paths:
        path_key = tuple(account_path)

        if path_key in seen_paths:
            continue

        seen_paths.add(path_key)

        if len(results) >= max_paths:
            break

        hops = []
        path_transaction_ids = []

        for sender, receiver in zip(account_path, account_path[1:]):
            edge_data = graph.get_edge_data(sender, receiver) or {}

            transactions_on_hop = []

            for edge in edge_data.values():
                transaction_id = str(edge.get("transaction_id", ""))
                path_transaction_ids.append(transaction_id)

                transactions_on_hop.append({
                    "transaction_id": transaction_id,
                    "amount": float(edge.get("amount", 0.0)),
                    "transaction_type": str(
                        edge.get("transaction_type", "UNKNOWN")
                    ),
                })

            hops.append({
                "sender_account": str(sender),
                "receiver_account": str(receiver),
                "transactions": transactions_on_hop,
            })

        matched_ids = sorted(set(path_transaction_ids).intersection(suspicious_ids))

        results.append({
            "account_path": [str(account) for account in account_path],
            "hop_count": len(account_path) - 1,
            "hops": hops,
            "suspicious_path_detected": bool(matched_ids),
            "matched_suspicious_transaction_ids": matched_ids,
        })

    return results


def calculate_graph_risk(
    graph: nx.MultiDiGraph,
    transaction_id: str,
    suspicious_transaction_ids: set[str] | list[str] | tuple[str, ...] | None = None,
    activity_threshold: int = 10,
    shared_receiver_threshold: int = 3,
) -> dict[str, Any]:
    """
    Calculate an explainable graph risk indicator for one transaction.

    This is a graph-based investigation score, not a calibrated fraud
    probability. It uses only transaction relationships and graph evidence.
    """
    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError("graph must be a NetworkX MultiDiGraph")

    if activity_threshold < 1 or shared_receiver_threshold < 2:
        raise ValueError("Risk thresholds must be positive and meaningful")

    transaction_id = str(transaction_id)
    suspicious_ids = {
        str(value) for value in (suspicious_transaction_ids or [])
    }

    matching_edges = []

    for sender, receiver, data in graph.edges(data=True):
        if str(data.get("transaction_id", "")) == transaction_id:
            matching_edges.append((str(sender), str(receiver), data))

    if not matching_edges:
        raise ValueError(f"Transaction not found in graph: {transaction_id}")

    # The transaction ID is expected to identify one transaction. If it
    # occurs more than once, evaluate the first matching edge consistently.
    sender, receiver, transaction_data = matching_edges[0]

    sender_metrics = calculate_account_graph_metrics(graph, sender)
    receiver_metrics = calculate_account_graph_metrics(graph, receiver)

    shared_senders = {
        str(node) for node in graph.predecessors(receiver)
    }

    evidence = []
    risk_score = 0.0

    # Activity contributes up to 0.25.
    activity_count = max(
        sender_metrics["outgoing_transaction_count"],
        receiver_metrics["incoming_transaction_count"],
    )
    activity_component = min(activity_count / activity_threshold, 1.0) * 0.25
    risk_score += activity_component

    if activity_count >= activity_threshold:
        evidence.append(
            f"High account activity observed: {activity_count} transactions"
        )

    # Shared receiver pattern contributes up to 0.30.
    shared_component = min(
        len(shared_senders) / shared_receiver_threshold, 1.0
    ) * 0.30
    risk_score += shared_component

    if len(shared_senders) >= shared_receiver_threshold:
        evidence.append(
            f"Receiver is connected to {len(shared_senders)} distinct senders"
        )

    # Known suspicious transactions connected to either endpoint contribute
    # up to 0.35. The input should come from another validated component.
    adjacent_flagged_ids = set()

    for node in (sender, receiver):
        for _, _, edge_data in graph.in_edges(node, data=True):
            edge_id = str(edge_data.get("transaction_id", ""))
            if edge_id in suspicious_ids:
                adjacent_flagged_ids.add(edge_id)

        for _, _, edge_data in graph.out_edges(node, data=True):
            edge_id = str(edge_data.get("transaction_id", ""))
            if edge_id in suspicious_ids:
                adjacent_flagged_ids.add(edge_id)

    if transaction_id in suspicious_ids:
        adjacent_flagged_ids.add(transaction_id)

    if adjacent_flagged_ids:
        risk_score += 0.35
        evidence.append(
            "Connected to known suspicious transaction(s): "
            + ", ".join(sorted(adjacent_flagged_ids))
        )

    risk_score = round(min(risk_score, 1.0), 4)

    if risk_score >= 0.60:
        risk_level = "high"
    elif risk_score >= 0.30:
        risk_level = "medium"
    else:
        risk_level = "low"

    connected_accounts = sorted(
        set(sender_metrics["connected_accounts"])
        .union(receiver_metrics["connected_accounts"])
        .difference({sender, receiver})
    )

    return {
        "transaction_id": transaction_id,
        "sender_account": sender,
        "receiver_account": receiver,
        "graph_risk": risk_score,
        "graph_risk_level": risk_level,
        "connected_accounts": connected_accounts,
        "suspicious_path_detected": bool(adjacent_flagged_ids),
        "evidence": evidence or [
            "No configured graph-risk indicators were triggered"
        ],
    }
