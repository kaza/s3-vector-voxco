# S3 Vectors Web Demo

A Streamlit web application demonstrating semantic search using OpenAI embeddings and AWS S3 Vectors.

## Features

- **Document Management**: Add, view, and delete documents
- **Semantic Search**: Natural language search with OpenAI embeddings
- **Cosine Similarity**: Shows similarity scores for search results
- **Real-time Updates**: Instant feedback for all operations

## Setup

1. **Install Dependencies**
   ```bash
   cd webdemo
   pip install -r requirements.txt
   ```

2. **Configure Environment Variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials:
   # - OPENAI_API_KEY (required)
   # - AWS credentials (if not already configured)
   ```

3. **Ensure S3 Vectors Resources Exist**
   ```bash
   # The bucket and index should already exist from the main project
   # If not, run the integration tests first:
   cd ..
   pytest tests/test_s3_vectors_integration.py::test_create_bucket_and_index
   ```

## Running the Demo

```bash
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Usage

1. **Add Documents**: Use the sidebar form to add new documents
2. **Search**: Enter queries in the main search box
3. **View Results**: See results ranked by cosine similarity (0-100%)
4. **Manage**: Delete individual documents or clear all

## How It Works

1. **Embeddings**: Uses OpenAI's `text-embedding-3-small` model (128 dimensions)
2. **Storage**: Documents stored in AWS S3 Vectors with metadata
3. **Search**: Query embeddings compared using cosine similarity
4. **Ranking**: Results sorted by similarity score

## Architecture

```
webdemo/
├── app.py              # Main Streamlit application
├── utils/
│   ├── embeddings.py   # OpenAI embedding generation
│   └── similarity.py   # Cosine similarity calculations
├── requirements.txt    # Python dependencies
└── .env               # Configuration (create from .env.example)
```

## Notes

- OpenAI API calls are rate-limited on free tier
- S3 Vectors may have slight indexing delays
- Cosine similarity shows how similar documents are (100% = identical)