# Swagger/OpenAPI Import Feature

## Overview

This feature allows users to automatically generate API requirements from existing Swagger 2.0 or OpenAPI 3.0 specifications. The system parses API documentation and creates corresponding API requirement records with extracted endpoint, method, payload, and response information.

## Features

- **Dual Format Support**: Supports both Swagger 2.0 and OpenAPI 3.0 specifications
- **Multiple Import Methods**: Upload files (JSON/YAML) or fetch from URL
- **Schema Extraction**: Automatically extracts and formats request/response schemas
- **Reference Resolution**: Resolves `$ref` references within specifications
- **Batch Import**: Import multiple endpoints in a single transaction
- **Conflict Resolution**: Skip duplicates or update existing records
- **Preview Before Import**: Review all endpoints before importing
- **Selective Import**: Choose which endpoints to import

## Backend Components

### 1. Swagger Parser Service (`swagger_parser.py`)

The parser service handles:
- Version detection (Swagger 2.0 vs OpenAPI 3.0)
- Schema extraction and transformation
- Reference resolution (`$ref`)
- Schema-to-text conversion for human-readable format

**Key Methods:**
- `parse_from_file(file_content, file_type)`: Parse from file content
- `parse_from_url(url)`: Fetch and parse from URL
- `_resolve_schema_swagger_2()`: Resolve references in Swagger 2.0
- `_resolve_schema_openapi_3()`: Resolve references in OpenAPI 3.0
- `_schema_to_text()`: Convert schema to readable text

### 2. Database Models (`models.py`)

**APIRequirement Model:**
- `id`: Primary key
- `method`: HTTP method (GET, POST, PUT, DELETE, etc.)
- `endpoint`: API endpoint path
- `summary`: Endpoint summary
- `description`: Detailed description
- `payload_schema`: Request body schema (text format)
- `response_schema`: Response schema (text format)
- `tags`: Comma-separated tags
- `created_at`, `updated_at`: Timestamps

**Unique Constraint:** `(method, endpoint)` - prevents duplicate endpoints

### 3. Import Controller (`swagger_import_controller.py`)

**Endpoints:**

1. **POST `/api/swagger-import/parse-file`**
   - Upload and parse Swagger/OpenAPI file
   - Accepts: Multipart file upload (JSON/YAML)
   - Returns: Preview of all endpoints

2. **POST `/api/swagger-import/parse-url`**
   - Fetch and parse from URL
   - Accepts: Query parameter `url`
   - Returns: Preview of all endpoints

3. **POST `/api/swagger-import/import`**
   - Import selected endpoints
   - Accepts: List of endpoints, `skip_duplicates` flag
   - Returns: Import summary (imported, skipped, failed counts)

## Frontend Components

### Swagger Import Component (`swagger-import.component.ts`)

**Features:**
- Modal-based import interface
- Two tabs: File Upload and URL Import
- Preview table with endpoint selection
- Schema viewer modal
- Import progress and results display

**Key Methods:**
- `openImportModal()`: Open import dialog
- `parseFile()`: Parse uploaded file
- `parseUrl()`: Parse from URL
- `importSelected()`: Import selected endpoints
- `viewSchema()`: View request/response schema

## Usage Flow

### File Upload Flow

1. User clicks "Import from Swagger" button
2. Modal opens with "Upload File" tab active
3. User selects JSON/YAML file
4. User clicks "Parse" button
5. System displays preview table with all endpoints
6. User selects/deselects endpoints
7. User toggles "Skip Duplicates" if needed
8. User clicks "Import Selected"
9. System shows import summary
10. User is redirected to API Requirements list

### URL Import Flow

1. User clicks "Import from Swagger" button
2. User switches to "From URL" tab
3. User enters Swagger URL
4. User clicks "Fetch & Parse" button
5. (Same preview and import flow as file upload)

## Technical Details

### Schema Formatting

Schemas are converted to human-readable text format:
- Objects: Nested structure with properties
- Arrays: Array type with item schema
- Required fields: Marked as "(required)"
- Optional fields: Marked as "(optional)"
- Nested objects: Indented hierarchy

### Reference Resolution

The parser resolves `$ref` references:
- **Swagger 2.0**: `#/definitions/ModelName`
- **OpenAPI 3.0**: `#/components/schemas/ModelName`
- Recursively resolves nested references

### Error Handling

- Invalid file format: Returns 400 with error message
- Invalid URL: Returns 400 with error message
- Network errors: Returns 500 with error details
- Individual endpoint failures: Continues processing, reports in summary

### Database Transactions

- Each import operation uses database transactions
- Failed endpoints don't prevent successful imports
- Rollback on critical errors
- Commit after successful batch import

## Installation

1. Install additional dependencies:
```bash
pip install -r requirements_swagger.txt
```

2. Initialize database:
```python
from database import init_db
init_db()
```

3. Ensure database connection is configured in `database.py`

## API Examples

### Parse File
```bash
curl -X POST "http://localhost:8000/api/swagger-import/parse-file" \
  -F "file=@swagger.json"
```

### Parse URL
```bash
curl -X POST "http://localhost:8000/api/swagger-import/parse-url?url=https://api.example.com/swagger.json"
```

### Import Endpoints
```bash
curl -X POST "http://localhost:8000/api/swagger-import/import" \
  -H "Content-Type: application/json" \
  -d '{
    "endpoints": [
      {
        "method": "GET",
        "endpoint": "/api/users",
        "summary": "Get users",
        "payload_schema": null,
        "response_schema": "..."
      }
    ],
    "skip_duplicates": true
  }'
```

## Configuration

### Database
Update `DATABASE_URL` in `database.py`:
```python
DATABASE_URL = "postgresql://user:password@localhost/dbname"
```

### CORS
Configure CORS in `main.py` for production:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Limitations

- Maximum file size: Limited by server memory (consider streaming for very large files)
- Nested reference depth: Limited by recursion depth
- Complex schemas: Some edge cases may not format perfectly

## Future Enhancements

- Support for OpenAPI 3.1
- Streaming parser for large files
- Schema validation
- Export to Swagger/OpenAPI format
- Bulk update existing requirements
- Import from multiple sources
