"""Diagram data for Streamlit's native Graphviz renderer."""

TASK_GRAPH = '''digraph workflow {
  graph [rankdir=LR, bgcolor="transparent", pad="0.25", nodesep="0.15", ranksep="0.8", splines=ortho];
  node [shape=box, style="rounded,filled", color="#e5eeff", fillcolor="#eff4ff",
        fontname="Inter", fontsize=12, fontcolor="#0b1c30", margin="0.2,0.18", penwidth=1];
  edge [color="#cbd5e1", arrowsize=0.55, penwidth=1.3];
  claim [label="TS_CLAIM\\l\\nIntake & Authorization\\l\\n120ms   Succeeded\\l"];
  identity [label="TS_IDENTITY   GATE\\l\\nOfficial Registry Gate\\l\\n480ms   Succeeded\\l", color="#c4b5fd"];
  sanctions [label="TS_SANCTIONS     310ms\\lOFAC / EU / UN Check\\l", fontcolor="#059669"];
  ownership [label="TS_OWNERSHIP     620ms\\lUBO Graph Traversal · Partial Gap\\l"];
  news [label="TS_NEWS          890ms\\lAdverse Media · Flagged Conflict\\l", fillcolor="#fff1f2", color="#fecdd3", fontcolor="#dc2626"];
  legal [label="TS_LEGAL         420ms\\lHigh Court & Gazette\\l", fontcolor="#059669"];
  aggregate [label="TS_AGGREGATE\\l\\nDiscrepancy Matrix & Provenance\\l\\n210ms   Succeeded\\l"];
  assess [label="TS_ASSESS\\l\\nRisk Engine & Scorer\\l\\nReview (68/100)\\l", fillcolor="#f5f3ff", color="#c4b5fd", fontcolor="#4f46e5"];
  claim -> identity;
  identity -> sanctions; identity -> ownership; identity -> news; identity -> legal;
  sanctions -> aggregate; ownership -> aggregate; news -> aggregate; legal -> aggregate;
  aggregate -> assess;
  { rank=same; sanctions; ownership; news; legal; }
}'''
