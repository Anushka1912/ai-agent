import logging
import os
import uuid
import pandas as pd
import numpy as np
import google.generativeai as genai
import hnswlib
from rdflib import Graph, Namespace, Literal, URIRef
from google.cloud import bigquery
from google.cloud import storage
from requests.exceptions import ReadTimeout
import time
import io
import tempfile

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(_name_)

# Namespaces
RDF = Namespace("http://www.w3.org/1999/02/22-rdf-syntax-ns#")
CUSTOM = Namespace("http://example.org/ontology/")
XSD = Namespace("http://www.w3.org/2001/XMLSchema#")

# GCS bucket details
BUCKET_NAME = "safety-bot"

# Custom function to serialize HNSW index to bytes
def serialize_hnsw_to_bytes(index):
    buffer = io.BytesIO()
    with tempfile.NamedTemporaryFile(delete=False) as temp_file:
        index.save_index(temp_file.name)
        with open(temp_file.name, 'rb') as f:
            buffer.write(f.read())
    os.unlink(temp_file.name)
    buffer.seek(0)
    return buffer

def create_hnsw_index():
    try:
        # Initialize clients
        bigquery_client = bigquery.Client()
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)

        # RDF graph setup
        g = Graph()
        g.bind("rdf", RDF)
        g.bind("custom", CUSTOM)
        g.bind("xsd", XSD)

        # Function to add BigQuery data to graph
        def add_bigquery_data_to_graph(graph, table_name, row):
            record_uri = URIRef(f"http://example.org/bigquery/{table_name}/{row.get('id', uuid.uuid4())}")
            for field, value in row.items():
                predicate_uri = URIRef(f"http://example.org/ontology/{field}")
                if isinstance(value, (int, float)):
                    graph.add((record_uri, predicate_uri, Literal(value, datatype=XSD.decimal if isinstance(value, float) else XSD.integer)))
                else:
                    graph.add((record_uri, predicate_uri, Literal(value)))

        # Fetch BigQuery data
        PROJECT_ID = "atomic-affinity-452318-k7"  # Replace with your project ID
        DATASET_ID = "SafetyBot"  # Replace with your dataset ID
        tables = list(bigquery_client.list_tables(f"{PROJECT_ID}.{DATASET_ID}"))
        
        for table in tables:
            table_ref = f"{PROJECT_ID}.{DATASET_ID}.{table.table_id}"
            query = f"SELECT * FROM {table_ref}"
            query_job = bigquery_client.query(query)
            df = query_job.to_dataframe()
            for _, row in df.iterrows():
                add_bigquery_data_to_graph(g, table.table_id, row)

        logger.info(f"Graph constructed with {len(g)} triples")

        # Convert triples to strings
        triples = [f"{s} {p} {o}" for s, p, o in g]

        # Generate embeddings
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        embedding_model = "models/embedding-001"
        chunk_size = 50
        embeddings = []
        max_retries = 3

        for i in range(0, len(triples), chunk_size):
            chunk = triples[i:i + chunk_size]
            for attempt in range(max_retries):
                try:
                    embeddings.extend(genai.embed_content(
                        model=embedding_model,
                        content=chunk,
                        task_type="retrieval_document"
                    )["embedding"])
                    break
                except (ReadTimeout, Exception) as e:
                    if attempt < max_retries - 1:
                        time.sleep(5)
                    else:
                        embeddings.extend([None] * len(chunk))

        embeddings = [emb for emb in embeddings if emb is not None]
        embeddings_np = np.array(embeddings, dtype=np.float32)

        # Save embeddings to GCS
        embeddings_blob = bucket.blob("triple_embeddings.npy")
        with io.BytesIO() as f:
            np.save(f, embeddings_np)
            f.seek(0)
            embeddings_blob.upload_from_file(f, content_type='application/octet-stream')

        # Save triples to GCS
        triples_blob = bucket.blob("triples.npy")
        with io.BytesIO() as f:
            np.save(f, np.array(triples))
            f.seek(0)
            triples_blob.upload_from_file(f, content_type='application/octet-stream')

        # Create HNSW index
        dim = embeddings_np.shape[1]
        num_elements = embeddings_np.shape[0]
        index = hnswlib.Index(space='cosine', dim=dim)
        index.init_index(max_elements=num_elements, ef_construction=200, M=16)
        index.add_items(embeddings_np, list(range(num_elements)))

        # Save HNSW index to GCS
        index_blob = bucket.blob("hnsw_index.bin")
        index_buffer = serialize_hnsw_to_bytes(index)
        index_blob.upload_from_file(index_buffer, content_type='application/octet-stream')

        # Save knowledge graph to GCS
        graph_blob = bucket.blob("knowledge_graph.ttl")
        with io.BytesIO() as f:
            g.serialize(f, format="turtle")
            f.seek(0)
            graph_blob.upload_from_file(f, content_type='text/turtle')

        logger.info("Successfully created and uploaded HNSW index and files to GCS")
        return {"status": "success", "triples": len(g), "embeddings": len(embeddings_np)}

    except Exception as e:
        logger.error(f"Error in creating index: {str(e)}")
        return {"status": "error", "message": str(e)}

if _name_ == "_main_":
    result = create_hnsw_index()
    print(result)