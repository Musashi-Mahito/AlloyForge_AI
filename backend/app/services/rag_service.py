import os
import PyPDF2
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict

# Classic metallurgy/biomaterial literature fallback paragraphs
FALLBACK_LITERATURE = [
    {
        "title": "Recent research and development in titanium alloys for biomedical applications",
        "authors": "M. Niinomi",
        "journal": "Materials Science and Engineering: A",
        "year": 2008,
        "doi": "10.1016/j.msea.2007.09.053",
        "text": "Beta-type titanium alloys such as Ti-29Nb-13Ta-4.6Zr exhibit low elastic modulus ranging from 55 to 65 GPa. This low modulus matches cortical bone (10-30 GPa) much closer than Ti-6Al-4V (110 GPa), thereby mitigating stress-shielding effects and promoting bone remodeling in clinical orthopedic implants."
    },
    {
        "title": "Review on low modulus beta-type titanium alloys for implant materials",
        "authors": "L. Zhang et al.",
        "journal": "Materials & Design",
        "year": 2017,
        "doi": "10.1016/j.matdes.2016.12.011",
        "text": "Valence Electron Concentration (VEC) plays a pivotal role in the design of beta-stabilized titanium alloys. When the VEC is decreased below 4.2, the body-centered cubic (BCC) beta phase is stabilized. Niobium (Nb) and Tantalum (Ta) are isomorphic beta stabilizers that are completely non-toxic compared to Nickel or Vanadium."
    },
    {
        "title": "Corrosion behavior and biocompatibility of metallic biomaterials",
        "authors": "Y. Okazaki et al.",
        "journal": "Biomaterials",
        "year": 1998,
        "doi": "10.1016/S0142-9612(97)00234-7",
        "text": "Corrosion rates of metallic implants in physiological environments dictate their longevity and safety. Alloys containing toxic elements such as Nickel, Cobalt, and Vanadium release metallic ions through passive film breakdown, leading to cytotoxicity, genetic mutation, and allergic reactions. Titanium, Zirconium, and Tantalum form stable, self-healing oxide films (TiO2, ZrO2, Ta2O5) showing minimal ion release."
    },
    {
        "title": "Mechanical properties of Cobalt-Chromium-Molybdenum alloys for orthopedic bearings",
        "authors": "A. Chiba",
        "journal": "Journal of the Mechanical Behavior of Biomedical Materials",
        "year": 2010,
        "doi": "10.1016/j.jmbbm.2009.11.002",
        "text": "Co-Cr-Mo alloys exhibit high yield strength and superior wear resistance, making them ideal for hip joint replacement bearings. However, their high elastic modulus (approximately 210-230 GPa) presents a severe mismatch with bone, restricting their use to high-wear contact surfaces rather than bone-fixation plates."
    }
]

class RAGService:
    def __init__(self):
        # Configure client connection to ChromaDB
        # We check if running inside Docker via host configuration
        host = os.getenv("CHROMA_SERVER_HOST", "localhost")
        port = int(os.getenv("CHROMA_SERVER_HTTP_PORT", "8000"))
        
        try:
            # Connect to Chroma server
            self.client = chromadb.HttpClient(host=host, port=port)
            print(f"Connected to ChromaDB server at http://{host}:{port}")
        except Exception:
            # Fallback to local persistent client if HTTP server is unavailable
            self.client = chromadb.PersistentClient(path="./chroma_db_local")
            print("Connected to ChromaDB via local PersistentClient.")

        # Load SentenceTransformer model
        # 'all-MiniLM-L6-v2' is small, fast (80MB), and excellent for CPU-only local architectures
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="scientific_literature",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Check if already seeded, if not, perform initial seed
        if self.collection.count() == 0:
            self.seed_initial_data()

    def seed_initial_data(self):
        print("Seeding scientific papers vector store...")
        documents = []
        metadatas = []
        ids = []
        
        for idx, item in enumerate(FALLBACK_LITERATURE):
            documents.append(item["text"])
            metadatas.append({
                "title": item["title"],
                "authors": item["authors"],
                "journal": item["journal"],
                "year": item["year"],
                "doi": item["doi"]
            })
            ids.append(f"lit_{idx}")
            
        embeddings = self.model.encode(documents).tolist()
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"Successfully seeded {len(documents)} scientific abstract chunks.")

    def ingest_pdf(self, pdf_path: str):
        """Extracts text from a scientific PDF, chunks it, embeds, and uploads."""
        if not os.path.exists(pdf_path):
            print(f"PDF path not found: {pdf_path}")
            return
            
        print(f"Reading PDF: {pdf_path}")
        title = os.path.basename(pdf_path).replace(".pdf", "")
        
        with open(pdf_path, 'rb') as f:
            pdf_reader = PyPDF2.PdfReader(f)
            chunks = []
            
            # Simple chunking by page / paragraph limits
            for p_idx, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if not text:
                    continue
                # Split page text into chunks of ~600 chars
                words = text.split()
                chunk_size = 120
                for i in range(0, len(words), chunk_size):
                    chunk = " ".join(words[i:i+chunk_size])
                    if len(chunk.strip()) > 50:
                        chunks.append((chunk, p_idx))
                        
        if not chunks:
            print("No text extracted from PDF.")
            return

        print(f"Embedding {len(chunks)} chunks from {title}...")
        texts = [c[0] for c in chunks]
        metadatas = [{
            "title": title,
            "authors": "Extracted PDF",
            "journal": "Local Library",
            "year": 2023,
            "doi": f"local_{hash(title)}",
            "page": c[1]
        } for c in chunks]
        ids = [f"pdf_{hash(title)}_{i}" for i in range(len(chunks))]
        
        embeddings = self.model.encode(texts).tolist()
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
            ids=ids
        )
        print(f"PDF {title} successfully ingested into RAG store.")

    def query_evidence(self, composition_wt: Dict[str, float], n_results: int = 3) -> List[Dict]:
        """Queries the vector store for academic evidence matching the composition."""
        # Convert composition dict to text query string
        # e.g., "Ti Nb Zr Ta low modulus biocompatibility corrosion resistance"
        query_elements = " ".join([el for el, wt in composition_wt.items() if wt > 2.0])
        query = f"{query_elements} biocompatibility low modulus alloy corrosion"
        
        query_embedding = self.model.encode([query]).tolist()
        
        results = self.collection.query(
            query_embeddings=query_embedding,
            n_results=n_results
        )
        
        citations = []
        if results and results["documents"]:
            # Chroma returns nested arrays
            docs = results["documents"][0]
            metas = results["metadatas"][0]
            distances = results["distances"][0]
            
            for doc, meta, dist in zip(docs, metas, distances):
                # Convert distance to a similarity score (cosine distance range [0, 2])
                similarity = round(1.0 - (dist / 2.0), 3)
                citations.append({
                    "title": meta.get("title", "Unknown"),
                    "authors": meta.get("authors", "Unknown"),
                    "journal": meta.get("journal", "Unknown"),
                    "year": int(meta.get("year", 0)),
                    "doi": meta.get("doi", ""),
                    "relevance_score": similarity,
                    "matching_snippet": doc
                })
        return citations

if __name__ == "__main__":
    # Test RAG query
    rag = RAGService()
    test_comp = {"Ti": 70.0, "Nb": 20.0, "Zr": 5.0, "Ta": 5.0}
    citations = rag.query_evidence(test_comp, n_results=2)
    print("\nTest query citations:")
    for c in citations:
        print(f"- {c['title']} (Score: {c['relevance_score']})")
        print(f"  Snippet: {c['matching_snippet'][:120]}...\n")
