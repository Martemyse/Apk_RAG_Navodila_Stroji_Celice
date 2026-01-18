# Fused Text-Image Ingestion Pipeline

## Overview

This pipeline implements the **text-image fused content unit** architecture where text and images are treated as unified semantic units.

## Key Components

### 1. Layout Parser (`processing/layout_parser.py`)
- Extracts text blocks with bounding boxes
- Identifies headings and sections
- Provides page-level layout information

### 2. Image Extractor (`processing/image_extractor.py`)
- Extracts images from PDFs
- Saves cropped images to filesystem
- Identifies nearby text (captions, paragraphs)

### 3. Content Unit Builder (`processing/content_unit_builder.py`)
- Creates `IMAGE_WITH_CONTEXT` units (image + surrounding text)
- Creates `TEXT_ONLY` units (text chunks without images)
- Builds hierarchical section paths

### 4. Multimodal Embedder (`embeddings/multimodal_embeddings.py`)
- Generates embeddings for content units
- Currently: text-only embeddings (future: true multimodal)

### 5. PostgreSQL Client (`storage/postgres_client.py`)
- Stores documents, image_assets, content_units
- Maintains relationships between entities

### 6. Weaviate Client (`storage/weaviate_fused_client.py`)
- Stores ContentUnits with embeddings
- Enables hybrid search (BM25 + vector)

## Usage

```bash
# Run fused ingestion
python ingestion/main_fused.py
```

## Data Flow

```
PDF → Layout Parser → PageLayout
                    ↓
              Image Extractor → ImageBlocks
                    ↓
         Content Unit Builder → ContentUnits + ImageAssets
                    ↓
         Multimodal Embedder → Embeddings
                    ↓
         PostgreSQL + Weaviate → Stored
```

## Configuration

Set in `.env`:
```bash
OPENAI_API_KEY=sk-your-key
POSTGRES_HOST=postgres
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=postgres
```

## Output

- **PostgreSQL**: `documents`, `image_assets`, `content_units` tables
- **Weaviate**: `ContentUnit` collection with embeddings
- **Filesystem**: Extracted images in `data_processed/images/{doc_id}/`

