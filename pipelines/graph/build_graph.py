import os
from neo4j import GraphDatabase
import pandas as pd
from pipelines.features.generation import ELEMENTAL_DATA

class AlloyKnowledgeGraphBuilder:
    def __init__(self, uri=None, user=None, password=None):
        self.uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.user = user or os.getenv("NEO4J_USER", "neo4j")
        self.password = password or os.getenv("NEO4J_PASSWORD", "alloy_graph_password")
        self.driver = None
        
    def connect(self):
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # Test connection
            self.driver.verify_connectivity()
            print("Successfully connected to Neo4j database.")
        except Exception as e:
            print(f"Failed to connect to Neo4j at {self.uri}: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def run_query(self, query, parameters=None):
        if not self.driver:
            return None
        with self.driver.session() as session:
            return session.run(query, parameters).data()

    def setup_constraints(self):
        print("Setting up unique constraints...")
        # Neo4j 5 syntax for constraints
        self.run_query("CREATE CONSTRAINT IF NOT EXISTS FOR (e:Element) REQUIRE e.symbol IS UNIQUE")
        self.run_query("CREATE CONSTRAINT IF NOT EXISTS FOR (a:Alloy) REQUIRE a.name IS UNIQUE")
        self.run_query("CREATE CONSTRAINT IF NOT EXISTS FOR (p:Paper) REQUIRE p.doi IS UNIQUE")
        self.run_query("CREATE CONSTRAINT IF NOT EXISTS FOR (ph:Phase) REQUIRE ph.name IS UNIQUE")

    def seed_elements(self):
        print("Seeding Element nodes...")
        query = """
        UNWIND $elements AS el
        MERGE (e:Element {symbol: el.symbol})
        SET e.atomic_number = el.atomic_number,
            e.electronegativity = el.electronegativity,
            e.radius = el.radius,
            e.vec = el.vec,
            e.biocompatibility = el.biocompatibility
        """
        elements_list = []
        for symbol, data in ELEMENTAL_DATA.items():
            # Add atomic number mock-up if missing
            atomic_numbers = {"Ti": 22, "Nb": 41, "Zr": 40, "Ta": 73, "Mo": 42, "Fe": 26, "Al": 13, "V": 23, "Cr": 24, "Ni": 28}
            elements_list.append({
                "symbol": symbol,
                "atomic_number": atomic_numbers.get(symbol, 0),
                "electronegativity": data["electronegativity"],
                "radius": data["radius"],
                "vec": data["vec"],
                "biocompatibility": data["biocompatibility"]
            })
        self.run_query(query, {"elements": elements_list})

    def build_graph_from_dataset(self, data_path: str):
        if not self.driver:
            print("Driver not connected. Seeding graph in dry run or skipping.")
            return
            
        df = pd.read_parquet(data_path)
        print(f"Seeding knowledge graph from {len(df)} alloys...")
        
        # 1. Setup phases
        phases = df["phase"].dropna().unique()
        for phase in phases:
            self.run_query("MERGE (:Phase {name: $name})", {"name": phase})
            
        # 2. Seed dummy literature papers
        papers = [
            {"doi": "10.1016/j.msea.2007.09.053", "title": "Recent research and development in titanium alloys for biomedical applications and healthcare goods", "journal": "Materials Science and Engineering: A", "year": 2008},
            {"doi": "10.1016/j.matdes.2016.12.011", "title": "Review on low modulus beta-type titanium alloys for implant materials", "journal": "Materials & Design", "year": 2017},
            {"doi": "10.1002/adem.200500122", "title": "Classification of Bulk Metallic Glasses by Enthalpy of Mixing", "journal": "Advanced Engineering Materials", "year": 2005}
        ]
        query_paper = """
        UNWIND $papers AS p
        MERGE (paper:Paper {doi: p.doi})
        SET paper.title = p.title,
            paper.journal = p.journal,
            paper.year = p.year
        """
        self.run_query(query_paper, {"papers": papers})
        
        # 3. Seed Alloys, contains links, and phase links
        for _, row in df.iterrows():
            # Create Alloy
            self.run_query(
                "MERGE (a:Alloy {name: $name}) SET a.phase = $phase, a.aus_score = $aus",
                {"name": row["name"], "phase": str(row["phase"]), "aus": float(row.get("biocompatibility_score", 0.8))}
            )
            
            # Link to phase
            if pd.notna(row["phase"]):
                self.run_query("""
                MATCH (a:Alloy {name: $name})
                MATCH (ph:Phase {name: $phase})
                MERGE (a)-[:HAS_PHASE]->(ph)
                """, {"name": row["name"], "phase": row["phase"]})
                
            # Elements contains links
            for el in ELEMENTAL_DATA.keys():
                wt = float(row[el])
                if wt > 0:
                    self.run_query("""
                    MATCH (a:Alloy {name: $name})
                    MATCH (e:Element {symbol: $symbol})
                    MERGE (a)-[r:CONTAINS]->(e)
                    SET r.fraction = $wt
                    """, {"name": row["name"], "symbol": el, "wt": wt})
                    
            # Link a few alloys to research papers randomly to simulate references
            if "beta" in str(row["phase"]):
                self.run_query("""
                MATCH (a:Alloy {name: $name})
                MATCH (p:Paper {doi: '10.1016/j.matdes.2016.12.011'})
                MERGE (a)-[:REPORTED_IN]->(p)
                """, {"name": row["name"]})
            elif "alpha" in str(row["phase"]):
                self.run_query("""
                MATCH (a:Alloy {name: $name})
                MATCH (p:Paper {doi: '10.1016/j.msea.2007.09.053'})
                MERGE (a)-[:REPORTED_IN]->(p)
                """, {"name": row["name"]})

        # 4. Link similar alloys (e.g. if they share 2 major elements)
        # We can run a cypher query to link alloys that share dominant elements
        similarity_query = """
        MATCH (a1:Alloy)-[c1:CONTAINS]->(e:Element)<-[c2:CONTAINS]->(a2:Alloy)
        WHERE a1.name < a2.name AND c1.fraction > 0.15 AND c2.fraction > 0.15
        WITH a1, a2, count(e) as shared_elements
        WHERE shared_elements >= 2
        MERGE (a1)-[:SIMILAR_TO {score: shared_elements * 0.25}]->(a2)
        """
        self.run_query(similarity_query)
        print("Knowledge Graph successfully populated.")

if __name__ == "__main__":
    builder = AlloyKnowledgeGraphBuilder()
    builder.connect()
    if builder.driver:
        builder.setup_constraints()
        builder.seed_elements()
        builder.build_graph_from_dataset("data/raw/alloy_dataset.parquet")
        builder.close()
    else:
        print("Neo4j not running or unreachable. Skipping graph populator database seeding.")
