# Compliance Data Engineering Pipeline

A data engineering pipeline developed as part of a compliance document review application.

This repository contains my authorized data engineering contribution to the wider application.

## Overview

The pipeline provides functionality for:

- Document extraction from PDF, DOCX, and XLSX files
- Document chunking
- Text embedding
- PII/entity masking and unmasking
- Document ingestion
- Vector/database integration
- Compliance rule retrieval
- Disclosure retrieval
- Precedent retrieval
- Data seeding
- Automated testing

## Architecture

```text
Documents
    |
    v
Document Extraction
    |
    v
Chunking
    |
    v
PII / Entity Masking
    |
    v
Embeddings
    |
    v
Database / Vector Storage
    |
    v
Retrieval
    |
    +--> Rules
    +--> Disclosures
    +--> Precedents

Project Structure

    data_engineering/
├── chunking/
├── embedding/
├── extraction/
├── masking/
├── migrations/
├── pipeline/
├── retrieval/
├── seeding/
└── tests/


Testing
The project includes automated tests covering:
- Chunking
- Database operations
- Embedding
- Document extraction
- Masking
- Retrieval
- Unmasking