import os
import logging
import random
import numpy as np
import google.generativeai as genai
import hnswlib
from rdflib import Graph, URIRef
from google.cloud import storage
from google.oauth2 import service_account  # For service account credentials
from flask import Flask, request, jsonify
import tempfile

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(_name_)

# Flask app
app = Flask(_name_)

# Gemini API setup
API_KEY = os.environ.get("GEMINI_API_KEY")
genai.configure(api_key=API_KEY)
EMBEDDING_MODEL = "models/embedding-001"
GENERATIVE_MODEL = "gemini-1.5-flash"

# GCS bucket details
BUCKET_NAME = "safety-bot"
EMBEDDINGS_FILE = "triple_embeddings.npy"
INDEX_FILE = "hnsw_index.bin"
TRIPLES_FILE = "triples.npy"
RDF_FILE = "knowledge_graph.ttl"

# Path to your service account credentials file
CREDENTIALS_PATH = "atomic-affinity-452318-k7-a6c0ca9c983e.json"  # Update with the correct path if needed

# Load credentials once at startup
CREDENTIALS = service_account.Credentials.from_service_account_file(
    CREDENTIALS_PATH,
    scopes=["https://www.googleapis.com/auth/cloud-platform"]
)

# SafetyBot context
SAFETYBOT_CONTEXT = """
SafetyBot is a project focused on women’s safety in India, providing information on helplines, police stations, shelters, legal resources, and safety tips. It aims to assist users in emergencies or unsafe situations by offering location-specific and scenario-based guidance.
"""

# Fictional characters
CHARACTERS = [
    {"name": "Dory", "intro": "Hiya, pal! I’m Dory, here to help!", "style": "Cheerful, scatterbrained", "exit": "Bye-bye, pal!"},
    {"name": "Po", "intro": "Hey, awesome human! I’m Po!", "style": "Warm, goofy", "exit": "See ya, awesome friend!"},
    {"name": "Mrs. Potts", "intro": "Oh, my dear! I’m Mrs. Potts!", "style": "Kind, maternal", "exit": "Farewell, dearie!"}
]

# Global variables
g = None
triples = None
embeddings_np = None
index = None
character = random.choice(CHARACTERS)
conversation_history = []

def download_from_gcs(bucket_name, source_blob_name):
    # Use the globally loaded credentials
    storage_client = storage.Client(credentials=CREDENTIALS)
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(source_blob_name)
    temp_file = tempfile.NamedTemporaryFile(delete=False)
    blob.download_to_file(temp_file)
    temp_file.close()
    return temp_file.name

def initialize_bot():
    global g, triples, embeddings_np, index
    logger.info("Initializing SafetyBot...")

    rdf_temp_path = download_from_gcs(BUCKET_NAME, RDF_FILE)
    g = Graph()
    g.parse(rdf_temp_path, format="turtle")
    logger.info(f"Loaded {len(g)} triples from {RDF_FILE}")
    os.unlink(rdf_temp_path)

    triples_temp_path = download_from_gcs(BUCKET_NAME, TRIPLES_FILE)
    triples = np.load(triples_temp_path, allow_pickle=True).tolist()
    logger.info(f"Loaded {len(triples)} triples from {TRIPLES_FILE}")
    os.unlink(triples_temp_path)

    embeddings_temp_path = download_from_gcs(BUCKET_NAME, EMBEDDINGS_FILE)
    embeddings_np = np.load(embeddings_temp_path)
    logger.info(f"Loaded {len(embeddings_np)} embeddings from {EMBEDDINGS_FILE}")
    os.unlink(embeddings_temp_path)

    index_temp_path = download_from_gcs(BUCKET_NAME, INDEX_FILE)
    dim = embeddings_np.shape[1]
    index = hnswlib.Index(space='cosine', dim=dim)
    index.load_index(index_temp_path, max_elements=len(embeddings_np))
    logger.info(f"Loaded HNSW index from {INDEX_FILE}")
    os.unlink(index_temp_path)

# Initialize bot
if g is None:
    initialize_bot()

def get_response(user_query):
    global conversation_history
    try:
        query_embedding = genai.embed_content(
            model=EMBEDDING_MODEL,
            content=user_query,
            task_type="retrieval_query"
        )["embedding"]
        query_embedding_np = np.array([query_embedding], dtype=np.float32)

        labels, distances = index.knn_query(query_embedding_np, k=15)
        matching_triples = [triples[idx] for idx in labels[0]]

        subjects = set(triple.split()[0] for triple in matching_triples)
        expanded_subjects = set(subjects)
        for subj in subjects:
            for s, p, o in g.triples((None, None, URIRef(subj))):
                if p.split("/")[-1].lower() in ["influencedby", "partof"]:
                    expanded_subjects.add(str(s))
            for s, p, o in g.triples((URIRef(subj), None, None)):
                if p.split("/")[-1].lower() in ["influencedby", "partof"]:
                    expanded_subjects.add(str(o))

        entity_data = {}
        for subj in expanded_subjects:
            entity_data[subj] = {}
            for s, p, o in g.triples((URIRef(subj), None, None)):
                prop_name = str(p).split("/")[-1].lower()
                entity_data[subj][prop_name] = float(o) if isinstance(o, str) and o.replace(".", "").isdigit() else str(o)

        data_str = "\n".join(
            f"Entity: {subj}\n" + "\n".join(
                f"  {k}: {v}" for k, v in sorted(data.items())
            ) for subj, data in entity_data.items()
        )

        history_str = "\n".join([f"User: {q}\n{character['name']}: {r}" for q, r in conversation_history[-3:]])

        input_text = f"""
        {SAFETYBOT_CONTEXT}
        You are {character['name']}, style: {character['style']}.
        Previous conversation:
        {history_str}
        User query: '{user_query}'.
        Data:
        {data_str}
        Instructions:
        1. Answer only if related to women’s safety in India.
        2. Interpret intent, use data, respond in {character['name']}’s style.
        3. If data is insufficient, suggest calling 1091.
        """
        response = genai.GenerativeModel(GENERATIVE_MODEL).generate_content(input_text)
        return response.text

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return f"Oops, something went wrong: {e}. Try again?"

@app.route('/safety_bot', methods=['POST', 'OPTIONS'])
def safety_bot():
    global conversation_history

    if request.method == "OPTIONS":
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600"
        }
        return "", 204, headers

    request_json = request.get_json(silent=True)
    if not request_json or "query" not in request_json:
        return jsonify({"response": f"{character['name']}: Oh, hi! Did you forget to ask something?"}), 200

    user_query = request_json["query"].strip()
    if not user_query:
        return jsonify({"response": f"{character['name']}: Take your time, I’m here!"}), 200

    if user_query.lower() == "exit":
        response = f"{character['name']}: {character['exit']}"
        conversation_history = []
        return jsonify({"response": response, "intro": False}), 200

    response = get_response(user_query)
    conversation_history.append((user_query, response))

    headers = {"Access-Control-Allow-Origin": "*"}
    if len(conversation_history) == 1:
        return jsonify({
            "response": response,
            "intro": character["intro"],
            "hint": "Ask about helplines, police stations, shelters, legal resources, or safety tips."
        }), 200, headers

    return jsonify({"response": response, "intro": False}), 200, headers

if _name_ == "_main_":
    app.run(debug=True, host="0.0.0.0", port=8080)