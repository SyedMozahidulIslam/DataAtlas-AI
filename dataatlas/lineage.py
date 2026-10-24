"""Bounded workspace-scoped traversal of persisted dataset lineage edges."""
from __future__ import annotations


MAX_GRAPH_NODES = 200
MAX_GRAPH_EDGES = 5_000
MAX_DEPTH = 8


def build_lineage_graph(db, workspace_id: str, focus_dataset_id: str,
                        direction: str = "both", depth: int = 4) -> dict:
    if direction not in {"upstream", "downstream", "both"}:
        raise ValueError("Direction must be upstream, downstream, or both.")
    if not isinstance(depth, int) or not 1 <= depth <= MAX_DEPTH:
        raise ValueError(f"Depth must be between 1 and {MAX_DEPTH}.")
    focus = db.execute("SELECT id FROM datasets WHERE id=? AND workspace_id=?",
                       (focus_dataset_id, workspace_id)).fetchone()
    if not focus:
        raise LookupError("Dataset not found in the active workspace.")
    stored_edges = db.execute("""SELECT e.source_dataset_id,e.target_dataset_id,e.lineage_id,
        l.event_type,l.created_at FROM dataset_edges e JOIN lineage l ON l.id=e.lineage_id
        WHERE e.workspace_id=? ORDER BY e.created_at DESC LIMIT ?""",
                              (workspace_id, MAX_GRAPH_EDGES)).fetchall()
    all_edges = [dict(edge) for edge in stored_edges]
    truncated = len(stored_edges) == MAX_GRAPH_EDGES
    levels = {focus_dataset_id: 0}
    frontier = {focus_dataset_id}
    for step in range(1, depth + 1):
        candidates: dict[str, int] = {}
        for edge in all_edges:
            source, target = edge["source_dataset_id"], edge["target_dataset_id"]
            if direction in ("downstream", "both") and source in frontier and target not in levels:
                candidates.setdefault(target, step)
            if direction in ("upstream", "both") and target in frontier and source not in levels:
                candidates.setdefault(source, -step)
        capacity = MAX_GRAPH_NODES - len(levels)
        if len(candidates) > capacity:
            truncated = True
            candidates = dict(list(candidates.items())[:max(0, capacity)])
        levels.update(candidates)
        frontier = set(candidates)
        if not frontier:
            break
        if step == depth:
            if any((edge["source_dataset_id"] in frontier and direction in ("downstream", "both")
                    and edge["target_dataset_id"] not in levels)
                   or (edge["target_dataset_id"] in frontier and direction in ("upstream", "both")
                       and edge["source_dataset_id"] not in levels) for edge in all_edges):
                truncated = True

    dataset_ids = list(levels)
    placeholders = ",".join("?" for _ in dataset_ids)
    nodes = db.execute(f"""SELECT id,name,layer,row_count,schema_version,source_name
        FROM datasets WHERE workspace_id=? AND id IN ({placeholders})""",
                       [workspace_id, *dataset_ids]).fetchall()
    node_values = [{**dict(node), "level": levels[node["id"]], "focused": node["id"] == focus_dataset_id}
                   for node in nodes]
    edges = [edge for edge in all_edges if edge["source_dataset_id"] in levels
             and edge["target_dataset_id"] in levels]
    return {"focus_dataset_id": focus_dataset_id, "direction": direction, "depth": depth,
            "nodes": node_values, "edges": edges, "truncated": truncated,
            "limits": {"max_nodes": MAX_GRAPH_NODES, "max_depth": MAX_DEPTH}}
