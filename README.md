# AI-AGENT - SafetyBot: Women’s Safety Assistance Platform

## Overview
SafetyBot is a project aimed at enhancing women's safety in India by providing users with real-time information about helplines, police stations, shelters, legal resources, and safety tips. The system integrates Retrieval-Augmented Generation (RAG) using RDF-based knowledge graphs, embeddings, and an HNSW index for efficient retrieval.

## Approach and Design Philosophy
1. **Retrieval-Augmented Generation (RAG)**: The project employs an RDF-based knowledge graph combined with vector embeddings and an HNSW index for efficient data retrieval.
2. **Contextual AI Assistance**: Using Google Gemini models, SafetyBot generates personalized and scenario-specific responses.
3. **Scalability & Performance**: The architecture leverages Google Cloud (BigQuery, Storage) for handling large-scale structured data and efficient querying.
4. **User Experience**: The chatbot is designed with a friendly, character-driven interaction model, making it engaging and intuitive.
5. **Open-Source & Free Libraries**: We have used open-source tools wherever possible to keep costs minimal and ensure accessibility.

## Key Technical Decisions and Justifications
1. **RDF Knowledge Graph**: We structured information in RDF format to allow flexible data representation and efficient querying.
2. **Google Cloud Services**: Used BigQuery for structured data storage and retrieval, and Google Cloud Storage for storing serialized graph, embeddings, and HNSW index.
3. **Embeddings & HNSW Index**:
   - **Google Gemini embeddings** for converting textual data into numerical representations.
   - **HNSWlib for Approximate Nearest Neighbors (ANN)** to quickly find relevant triples for retrieval.
4. **Flask Backend**:
   - Exposes REST API endpoints for chatbot interaction.
   - Handles query processing and response generation using RAG.
5. **React Frontend**:
   - Provides an interactive UI for users to chat with SafetyBot.
   - Handles user queries and displays responses dynamically.

## Deployment Instructions

### 1. Backend Deployment (Flask API)
#### Prerequisites
- Python 3.8+
- Google Cloud SDK installed and authenticated
- Google Cloud Storage and BigQuery setup
- Service account key (JSON) for authentication

#### Steps
1. **Clone the repository**:
   ```sh
   git clone https://github.com/Anushka1912/ai-agent.git
   cd ai-agent/backend
   ```
2. **Set up a virtual environment**:
   ```sh
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install dependencies**:
   ```sh
   pip install -r requirements.txt
   ```
4. **Set environment variables**:
   ```sh
   export GEMINI_API_KEY="your-api-key"
   export GOOGLE_APPLICATION_CREDENTIALS="path-to-service-account.json"
   ```
5. **Run the Flask server**:
   ```sh
   python graph-embed-index.py (run it once to create and save the graph, embeddings, indexing of the bigquery database - required only once until and unless there are changes in the dataset)
   python main.py
   ```

### 2. Frontend Deployment (React App)
#### Prerequisites
- Node.js (v16+)
- NPM or Yarn

#### Steps
1. **Navigate to the frontend directory**:
   ```sh
   cd ai-agent/frontend
   ```
2. **Install dependencies**:
   ```sh
   npm install  # or yarn install
   ```
3. **Set environment variables**:
   Create a `.env` file and add:
   ```sh
   REACT_APP_API_URL=http://localhost:8080/ai-agent
   ```
4. **Start the development server**:
   ```sh
   npm start  # or yarn start
   ```

### 3. Deployment on Google Cloud Run
1. **Build the Docker image**:
   ```sh
   docker build -t gcr.io/your-project-id/ai-agent.
   ```
2. **Push to Google Container Registry**:
   ```sh
   docker push gcr.io/your-project-id/ai-agent
   ```
3. **Deploy to Cloud Run**:
   ```sh
   gcloud run deploy safety-bot --image gcr.io/your-project-id/ai-agent --platform managed --region us-central1 --allow-unauthenticated
   ```
4. **Update the frontend `.env` file** with the deployed API URL and redeploy the frontend.

## Conclusion
SafetyBot is designed as a robust, scalable, and interactive AI assistant for women's safety, leveraging state-of-the-art retrieval and generation techniques. Future improvements include expanding data sources, improving multilingual support, and enhancing real-time event tracking capabilities.

## Frontend
![Screenshot 2025-03-17 100617](https://github.com/user-attachments/assets/085e0e8e-24b0-4044-b428-36c339e2b913)

