# Text-Image Fused RAG Architecture

## 🎯 Core Concept

**"The unit of meaning is text+image together, not one or the other."**

This architecture explicitly models text-image relationships and treats them as fused semantic units.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   4-Layer Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Raw Storage                                               │
│     ├── Original PDFs                                         │
│     └── Extracted Images (cropped from PDFs)                 │
│                                                               │
│  2. Metadata + Relationships (PostgreSQL)                    │
│     ├── documents                                             │
│     ├── image_assets                                         │
│     └── content_units (with image_id references)             │
│                                                               │
│  3. Vector Store (Weaviate)                                   │
│     └── ContentUnit (with fused embeddings)                  │
│                                                               │
│  4. MCP Tools + API                                          │
│     ├── search_content_units(query)                          │
│     ├── get_image(image_id)                                   │
│     └── get_pdf_section(unit_id)                              │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Model

### 1. Document
- One PDF file
- Fields: `id`, `doc_id`, `title`, `file_path`, `domain`, `total_pages`

### 2. ImageAsset
- One cropped image from PDF
- Fields: `id`, `document_id`, `page_number`, `bbox`, `image_path`, `auto_caption`

### 3. ContentUnit (The Key Entity)
- **Fused text+image semantic unit**
- Can be:
  - `TEXT_ONLY`: Text chunk without image
  - `IMAGE_WITH_CONTEXT`: Image + surrounding text (caption + nearby paragraphs)
- Fields:
  - `id`, `document_id`, `doc_id`, `page_number`
  - `section_title`, `section_path`
  - `text` (chunk or fused text)
  - `unit_type` (`TEXT_ONLY` or `IMAGE_WITH_CONTEXT`)
  - `image_id` (nullable, links to ImageAsset)
  - `embedding_vector` (stored in Weaviate)
  - `tags` (domain, machine_type, safety_level, etc.)

**Key Point:** Agents reason over ContentUnits, not bare images or text.

---

## 🔄 Ingestion Pipeline

### Step 1: Parse PDF Layout
- Extract text blocks with bounding boxes
- Extract headings
- Identify images and their positions

### Step 2: Extract Images
- Crop images from PDF
- Save to filesystem
- Create `ImageAsset` records

### Step 3: Build ContentUnits

**For Images:**
1. Find nearby text (caption + 1-2 paragraphs)
2. Create fused text: `"Figure 4: Hydraulic circuit layout. This diagram shows..."`
3. Create `ContentUnit`:
   - `text`: fused text
   - `image_id`: link to ImageAsset
   - `unit_type`: `IMAGE_WITH_CONTEXT`

**For Text-Only Sections:**
1. Chunk by headings (~200-300 tokens)
2. Create `ContentUnit`:
   - `text`: chunk text
   - `image_id`: null
   - `unit_type`: `TEXT_ONLY`

### Step 4: Generate Embeddings
- For each ContentUnit:
  - If `IMAGE_WITH_CONTEXT`: Embed fused text (future: multimodal embedding)
  - If `TEXT_ONLY`: Embed text
- Store in Weaviate

### Step 5: Store
- **PostgreSQL**: Documents, ImageAssets, ContentUnits (with relationships)
- **Weaviate**: ContentUnits with embeddings

---

## 🔍 Retrieval Flow

### User Query: "Show me the emergency valve diagram"

1. **Agent calls**: `search_content_units("emergency valve diagram")`
   - Weaviate hybrid search returns ContentUnits
   - Results include `image_id` if unit has image

2. **Agent sees**: ContentUnit with `image_id` not null
   - Knows there's a relevant image

3. **Agent calls**: `get_image(image_id)`
   - Returns image path and metadata

4. **UI displays**: Text + Image together

---

## 🛠️ MCP Tools

### 1. `search_content_units(query, top_k)`
- Searches ContentUnit collection
- Returns units with `has_image` flag
- Agent can identify which results have images

### 2. `get_image(image_id)`
- Returns image path, bbox, caption
- Used when agent needs to display image

### 3. `get_pdf_section(unit_id)`
- Returns PDF section info (doc_id, page, section)
- For deep linking to original PDF

---

## 📁 File Structure

```
2_Apk_RAG_Navodila_Stroji_Celice/
├── postgres/
│   └── schema.sql              # PostgreSQL schema
├── ingestion/
│   ├── models.py               # Document, ImageAsset, ContentUnit
│   ├── layout_parser.py        # Parse PDF layout
│   ├── image_extractor.py      # Extract images
│   ├── content_unit_builder.py # Build fused units
│   ├── multimodal_embeddings.py # Generate embeddings
│   ├── postgres_client.py      # PostgreSQL operations
│   ├── weaviate_fused_client.py # Weaviate operations
│   └── main_fused.py           # Main ingestion pipeline
├── retrieval/
│   ├── weaviate_fused_client.py # ContentUnit retrieval
│   ├── mcp_tools.py            # MCP tool implementations
│   ├── mcp_server_fused.py     # MCP server
│   └── main_fused.py           # FastAPI for ContentUnits
└── data_processed/
    └── images/                 # Extracted images
        └── {doc_id}/
            └── {doc_id}_p{page}_i{idx}.png
```

---

## 🚀 Usage

### Ingestion
```bash
# Run fused ingestion pipeline
python ingestion/main_fused.py
```

### Retrieval API
```bash
# Query content units
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "emergency valve procedure",
    "top_k": 5
  }'

# Get image
curl http://localhost:8001/image/{image_id}

# Get PDF section
curl http://localhost:8001/pdf_section/{unit_id}
```

### MCP (Agents)
```python
# Agent calls
results = await search_content_units("valve diagram", top_k=5)
for unit in results:
    if unit['has_image']:
        image = await get_image(unit['image_id'])
        # Display text + image
```

---

## ✅ Benefits

1. **Explicit Relationships**: Text-image links stored in PostgreSQL
2. **Semantic Fusion**: ContentUnits represent meaning, not just text
3. **Agent-Friendly**: Simple MCP tools hide complexity
4. **Scalable**: Can add vision models later for true multimodal embeddings
5. **Deep Linking**: Can link back to exact PDF page/region

---

## 🔮 Future Enhancements

1. **True Multimodal Embeddings**: Use OpenAI Vision API or CLIP
2. **Image Captioning**: Auto-generate captions with Florence-2/BLIP-2
3. **Table Extraction**: Add Table content units
4. **Visual Search**: Search images by visual similarity

---

**This architecture ensures text and images are always retrieved together as meaningful units!** 🎯

