# Compliance Document Review — Data Engineering

## Overview

This repository contains the Data Engineering components I developed for a compliance document review platform. The system processes uploaded compliance documents, protects sensitive information through PII masking, converts document content into vector embeddings, and provides semantic retrieval of compliance rules, required disclosures, and historical precedents.

The Data Engineering layer is designed to support a backend/API and AI-assisted compliance review workflow.

---

## Architecture

```text
                         Document Upload
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Document Extraction │
                    │  PDF / DOCX / XLSX  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │     PII Masking     │
                    │ Names, emails, etc. │
                    └──────────┬──────────┘
                               │
                     ┌─────────┴─────────┐
                     │                   │
                     ▼                   ▼
              PII Mapping          Masked Text
              PostgreSQL                 │
                                        ▼
                              ┌─────────────────┐
                              │     Chunking    │
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │    Embeddings   │
                              │ Gemini Embedding│
                              └────────┬────────┘
                                       │
                                       ▼
                              ┌─────────────────┐
                              │ PostgreSQL +    │
                              │    pgvector     │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
                    ▼                  ▼                  ▼
             Rule Retrieval    Disclosure Retrieval   Precedent
                                                        Retrieval
                    │                  │                  │
                    └──────────────────┼──────────────────┘
                                       ▼
                              AI-Assisted Review
                                       │
                                       ▼
                              Compliance Officer
```

---

## My Contribution

I was responsible for the Data Engineering layer of the project, including:

- Designed and implemented the document ingestion pipeline covering extraction, PII masking, chunking, embedding generation, and database persistence.
- Built document extraction support for PDF, DOCX and XLSX files and implemented a routing layer to select the appropriate extractor.
- Developed PII detection and masking functionality so sensitive information is removed before text is embedded and stored for semantic retrieval.
- Implemented text chunking and Gemini embedding generation, using 768-dimensional vectors for similarity search.
- Designed PostgreSQL/pgvector storage and implemented semantic retrieval for compliance rules, mandatory disclosures and historical precedents.
- Built seed-data pipelines for compliance rules, disclosures and precedent documents and added automated tests for core Data Engineering components.
- Exposed the Data Engineering functionality through a reusable Python package interface for integration with the backend application.

---

## Data Engineering Pipeline

### 1. Document Extraction

Uploaded documents are passed through an extraction router that identifies the file type and uses the appropriate extractor.

Supported formats:

- PDF
- DOCX
- XLSX

### 2. PII Masking

Before embedding, sensitive information is detected and replaced with placeholders.

Example:

```text
Original:

John Smith submitted an investment application for £50,000.

Masked:

[CLIENT_1] submitted an investment application for [AMOUNT_1].
```

The original values are stored separately in the PII mapping table rather than being included in the text used for embeddings.

### 3. Chunking

Masked document text is divided into smaller overlapping chunks.

Each chunk contains metadata such as:

- Document ID
- Chunk index
- Character start/end positions
- Token count
- Masked text

### 4. Embeddings

The masked chunks are converted into vector embeddings using Google's Gemini embedding model.

The configured embedding dimension is:

```text
768
```

Embeddings are stored in PostgreSQL using the `pgvector` extension.

### 5. Semantic Retrieval

The vector database supports three main retrieval workflows:

#### Compliance Rules

Retrieves relevant compliance rules based on semantic similarity to the uploaded document.

#### Mandatory Disclosures

Checks document content against the required disclosure corpus to identify relevant disclosure requirements.

#### Historical Precedents

Retrieves similar previously reviewed documents and their compliance decisions.

---

## Database

The project uses:

- PostgreSQL
- pgvector

The main data areas include:

```text
documents
    │
    ├── document_chunks
    │
    └── pii_mappings

compliance_rules

disclosures

precedent_index
```

These tables support document storage, PII mappings, chunk storage, and vector-based retrieval.

---

## Backend Integration

The Data Engineering layer exposes a simple Python interface:

```python
from data_engineering import (
    ingest_document,
    RuleRetriever,
    DisclosureRetriever,
    PrecedentRetriever,
    unmask_text,
)
```

### Document ingestion

The backend creates the document record and then calls:

```python
result = ingest_document(
    document_id=document_id,
    file_bytes=file_bytes,
    filename=filename,
)
```

The pipeline performs:

```text
Extract
   ↓
Mask PII
   ↓
Store PII mapping
   ↓
Chunk
   ↓
Generate embeddings
   ↓
Store chunks + vectors
```

### Retrieval

The backend/AI layer can access:

```python
RuleRetriever
DisclosureRetriever
PrecedentRetriever
```

for the respective semantic retrieval workflows.

---

## Seed Data

Synthetic data is provided for development and retrieval testing.

The Data Engineering layer includes seed pipelines for:

- Compliance rules
- Required disclosures
- Historical precedents

Current development seed data includes:

```text
40 compliance rules
8 disclosures
100 historical precedents
```

---

## Testing

Core Data Engineering components have been tested, including:

- Document extraction
- PII masking
- Text chunking
- Embedding generation
- Database functionality
- Unmasking functionality
- Retrieval components

Example embedding validation:

```text
Embedding dimension: 768
```

The ingestion pipeline has also been tested against a sample PDF to verify extraction and PII detection.

---

## Project Structure

```text
data_engineering/
│
├── chunking/
│   └── chunker.py
│
├── embedding/
│   └── embedder.py
│
├── extraction/
│   ├── router.py
│   └── ...
│
├── masking/
│   ├── masker.py
│   ├── patterns.py
│   ├── entity_types.py
│   └── unmasker.py
│
├── pipeline/
│   └── ingest.py
│
├── retrieval/
│   ├── rule_retrieval.py
│   ├── disclosure_retrieval.py
│   └── precedent_retrieval.py
│
├── seeding/
│   ├── seed_rules.py
│   ├── seed_disclosures.py
│   ├── seed_precedents.py
│   └── data/
│
├── tests/
│
├── config.py
└── db.py
```

---

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python |
| Database | PostgreSQL |
| Vector Search | pgvector |
| Embeddings | Google Gemini |
| Document Processing | PDF / DOCX / XLSX |
| Database Access | SQLAlchemy |
| Testing | Pytest |
| Configuration | Environment variables |
| Containerisation | Docker / Docker Compose |
| Logging | Structlog |

---

## Key Engineering Considerations

### Privacy

PII is masked before embedding. Original PII values are maintained separately through the PII mapping layer.

### Idempotency

The ingestion pipeline is designed to be safely retried. Existing document chunks and PII mappings can be replaced when ingestion is rerun.

### Modularity

Extraction, masking, chunking, embedding, retrieval and ingestion are separated into independent modules.

### Backend Integration

The Data Engineering layer exposes a small Python API so the backend does not need to depend on internal implementation details.

---

## Running the Data Engineering Components

Create and configure the required environment variables.

Example:

```env
GEMINI_API_KEY=your_api_key_here
EMBEDDING_MODEL=models/gemini-embedding-001
EMBEDDING_DIMENSION=768
```

Install dependencies:

```bash
pip install -r data_engineering/requirements.txt
```

Run the seed pipelines:

```bash
python -m data_engineering.seeding.seed_rules
python -m data_engineering.seeding.seed_disclosures
python -m data_engineering.seeding.seed_precedents
```

Run tests:

```bash
pytest data_engineering/tests
```

---

## Project Context

This Data Engineering layer was developed as part of a wider compliance document review application.

The wider application combines:

```text
Frontend
   ↓
Backend/API
   ↓
Data Engineering
   ↓
PostgreSQL + pgvector
   ↓
AI-assisted compliance review
```

This repository focuses specifically on the **Data Engineering components I developed**.
