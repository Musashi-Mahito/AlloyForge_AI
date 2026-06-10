import os
from neo4j import GraphDatabase
from typing import Dict, List, Tuple

class GraphService:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "alloy_graph_password")
        self.driver = None
        self.connect()

    def connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
        except Exception as e:
            print(f"GraphService failed to connect to Neo4j at {self.uri}: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def get_alloy_neighborhood(self, name: str) -> Dict:
        """
        Queries Neo4j for elements, papers, phases, and similar alloys connected to a given alloy.
        Returns a D3.js-ready graph format containing lists of 'nodes' and 'links'.
        """
        if not self.driver:
            # Mock graph data fallback if Neo4j is not connected/running
            return self._get_mock_neighborhood(name)

        query = """
        MATCH (a:Alloy {name: $name})
        OPTIONAL MATCH (a)-[r:CONTAINS]->(e:Element)
        OPTIONAL MATCH (a)-[:HAS_PHASE]->(ph:Phase)
        OPTIONAL MATCH (a)-[:REPORTED_IN]->(pa:Paper)
        OPTIONAL MATCH (a)-[s:SIMILAR_TO]-(sim:Alloy)
        RETURN a, collect(distinct {node: e, fraction: r.fraction}) as elements, 
               ph as phase, collect(distinct pa) as papers, collect(distinct {node: sim, score: s.score}) as similar_alloys
        """
        
        nodes = []
        links = []
        node_ids = set()

        def add_node(id_, label, type_, properties=None):
            if id_ not in node_ids:
                nodes.append({
                    "id": id_,
                    "label": label,
                    "type": type_,
                    "properties": properties or {}
                })
                node_ids.add(id_)

        with self.driver.session() as session:
            result = session.run(query, {"name": name}).data()
            if not result:
                return {"nodes": [], "links": []}
                
            row = result[0]
            alloy_node = row["a"]
            if not alloy_node:
                return {"nodes": [], "links": []}
                
            # Add self
            add_node(name, name, "Alloy", {"phase": alloy_node.get("phase"), "aus_score": alloy_node.get("aus_score")})
            
            # Add phase
            phase_node = row["phase"]
            if phase_node:
                p_name = phase_node.get("name")
                add_node(p_name, p_name, "Phase")
                links.append({"source": name, "target": p_name, "type": "HAS_PHASE"})
                
            # Add elements
            for el_entry in row["elements"]:
                el_node = el_entry["node"]
                if el_node:
                    symbol = el_node.get("symbol")
                    fraction = el_entry["fraction"]
                    add_node(symbol, symbol, "Element", {"vec": el_node.get("vec")})
                    links.append({"source": name, "target": symbol, "type": "CONTAINS", "value": fraction})
                    
            # Add papers
            for paper in row["papers"]:
                if paper:
                    doi = paper.get("doi")
                    title = paper.get("title")
                    add_node(doi, title[:30] + "...", "Paper", {"doi": doi, "year": paper.get("year")})
                    links.append({"source": name, "target": doi, "type": "REPORTED_IN"})
                    
            # Add similar alloys
            for sim_entry in row["similar_alloys"]:
                sim_node = sim_entry["node"]
                if sim_node:
                    s_name = sim_node.get("name")
                    score = sim_entry["score"]
                    add_node(s_name, s_name, "Alloy", {"aus_score": sim_node.get("aus_score")})
                    links.append({"source": name, "target": s_name, "type": "SIMILAR_TO", "value": score})
                    
        return {"nodes": nodes, "links": links}

    def _get_mock_neighborhood(self, name: str) -> Dict:
        """Returns mock neighborhood when Neo4j database is unreachable."""
        # Split composition from name if fits standard pattern e.g. Ti-35Nb-7Zr-5Ta
        elements = ["Ti", "Nb", "Zr", "Ta"]
        nodes = [
            {"id": name, "label": name, "type": "Alloy", "properties": {"phase": "beta", "aus_score": 0.942}},
            {"id": "beta", "label": "beta", "type": "Phase", "properties": {}},
            {"id": "10.1016/j.matdes.2016.12.011", "label": "Review on low modulus beta...", "type": "Paper", "properties": {"doi": "10.1016/j.matdes.2016.12.011"}}
        ]
        links = [
            {"source": name, "target": "beta", "type": "HAS_PHASE"},
            {"source": name, "target": "10.1016/j.matdes.2016.12.011", "type": "REPORTED_IN"}
        ]
        
        # Add basic elements
        for el in elements:
            nodes.append({"id": el, "label": el, "type": "Element", "properties": {}})
            links.append({"source": name, "target": el, "type": "CONTAINS", "value": 0.15})
            
        # Add one similar alloy
        nodes.append({"id": "Ti-29Nb-13Ta-4.6Zr", "label": "Ti-29Nb-13Ta-4.6Zr", "type": "Alloy", "properties": {"aus_score": 0.912}})
        links.append({"source": name, "target": "Ti-29Nb-13Ta-4.6Zr", "type": "SIMILAR_TO", "value": 0.75})
        
        return {"nodes": nodes, "links": links}
