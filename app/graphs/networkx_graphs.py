"""NetworkX-based process graph analysis: builds a directed graph of the
process, computes bottleneck/critical-path analysis, and renders a Plotly
network view (the "Process Bottleneck Map").
"""
from __future__ import annotations

import networkx as nx
import plotly.graph_objects as go

from app.schemas.process import ProcessStepDiagnostic


def build_process_graph(steps: list[ProcessStepDiagnostic]) -> nx.DiGraph:
    graph = nx.DiGraph()
    for s in steps:
        graph.add_node(
            s.step_number,
            label=s.step_name,
            cycle_time=s.cycle_time_minutes,
            wait_time=s.wait_time_minutes,
            value_class=s.value_classification.value,
            automation_score=s.automation_score,
        )
    for a, b in zip(steps, steps[1:]):
        graph.add_edge(a.step_number, b.step_number, weight=max(a.cycle_time_minutes, 0.01))
    return graph


def find_bottlenecks(steps: list[ProcessStepDiagnostic], top_n: int = 3) -> list[ProcessStepDiagnostic]:
    """The Theory-of-Constraints view: the steps with the highest total
    (cycle + wait) time are the process bottleneck(s) constraining throughput.
    """
    ranked = sorted(steps, key=lambda s: (s.cycle_time_minutes + s.wait_time_minutes), reverse=True)
    return ranked[:top_n]


def critical_path_minutes(steps: list[ProcessStepDiagnostic]) -> float:
    return sum(s.cycle_time_minutes for s in steps)


def render_bottleneck_map(steps: list[ProcessStepDiagnostic]) -> go.Figure:
    graph = build_process_graph(steps)
    if len(graph.nodes) == 0:
        return go.Figure()

    pos = nx.spring_layout(graph, seed=42, k=1.2)
    bottlenecks = {s.step_number for s in find_bottlenecks(steps)}

    edge_x, edge_y = [], []
    for u, v in graph.edges():
        edge_x += [pos[u][0], pos[v][0], None]
        edge_y += [pos[u][1], pos[v][1], None]
    edge_trace = go.Scatter(x=edge_x, y=edge_y, mode="lines", line=dict(width=1.5, color="#94A3B8"), hoverinfo="none")

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    for n, data in graph.nodes(data=True):
        node_x.append(pos[n][0])
        node_y.append(pos[n][1])
        total_time = data["cycle_time"] + data["wait_time"]
        node_text.append(
            f"Step {n}: {data['label']}<br>Cycle: {data['cycle_time']}m | Wait: {data['wait_time']}m<br>"
            f"Automation potential: {data['automation_score']}"
        )
        node_color.append("#DC2626" if n in bottlenecks else "#2563EB")
        node_size.append(24 + min(total_time, 60) * 0.6)

    node_trace = go.Scatter(
        x=node_x, y=node_y, mode="markers+text",
        text=[str(n) for n in graph.nodes()], textposition="middle center",
        textfont=dict(color="white", size=11, family="Arial Black"),
        hovertext=node_text, hoverinfo="text",
        marker=dict(size=node_size, color=node_color, line=dict(width=2, color="white")),
    )

    fig = go.Figure(data=[edge_trace, node_trace])
    fig.update_layout(
        title="Process Bottleneck Map (red = top time-constrained steps)",
        showlegend=False, hovermode="closest",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        plot_bgcolor="white", margin=dict(l=10, r=10, t=50, b=10),
    )
    return fig
