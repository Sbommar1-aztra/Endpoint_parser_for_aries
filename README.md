# Endpoint Parser for Aries - OpenAPI Integration System

A comprehensive backend system for importing, parsing, analyzing, and validating OpenAPI/Swagger specifications. The system automatically detects dependencies, generates prerequisite suggestions, and integrates with test generation workflows.

## Features

### Core Functionality

- **OpenAPI Specification Parsing** (Task 2)
  - Supports Swagger 2.0 and OpenAPI 3.0 specifications
  - Automatic version detection
  - Full schema extraction with field-level details
  - Reference resolution ($ref)
  - Field constraint extraction (min/max, pattern, enum, etc.)

- **Field Dependency Analysis** (Task 3)
  - Three detection methods:
    - Explicit: x-foreign-key extension parsing (100% confidence)
    - Naming: {entity}_id pattern detection (85% confidence)
    - Description: Natural language analysis (80% confidence)
  - JSONPath expression generation for response extraction
  - Mandatory field detection

- **Prerequisite Suggestion Generation** (Task 4)
  - Automatic prerequisite configuration
  - Smart caching strategy (cache static data, don't cache user-specific)
  - Field mapping generation (FK, timestamp, LLM-generated)
  - Execution order calculation
  - User review and approval workflow

- **Contract-Request Association & Validation** (Task 6)
  - Associate API requests with OpenAPI endpoints
  - Validate endpoint existence
  - Validate HTTP method matches
  - Fuzzy path matching for path parameters

- **Request & Response Schema Validation** (Task 7)
  - Request payload validation
  - Response validation
  - Field-level constraint validation
  - Coverage percentage calculation
  - Validation suggestions

- **Contract Change Detection** (Task 8)
  - Breaking change detection
  - Non-breaking change identification
  - Affected endpoint tracking
  - Version comparison

- **Prerequisite Regeneration Workflow** (Task 9)
  - Automatic detection of affected dependencies
  - Regeneration prompts
  - Comparison of old vs new suggestions

- **Test Generation Integration** (Task 10)
  - Test configuration generation
  - Prerequisite execution with caching
  - Field mapping application
  - Test variation generation

## Installation

### Prerequisites

- Python 3.8+
- SQLite (default) or PostgreSQL
- FastAPI
- SQLAlchemy

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd Endpoint_parser_for_aries-1
```

2. Install dependencies:
```bash
pip install -r requirements_swagger.txt
```

3. Initialize the database:
```bash
python -c "from database import init_db; init_db()"
```

4. Run the application:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Specification Import

#### Import OpenAPI Specification
```
POST /api/swagger-import/import-specification
```
Import a complete OpenAPI specification with full database storage.

**File Upload:**
```bash
curl -X POST "http://localhost:8000/api/swagger-import/import-specification" \
  -F "file=@specification.yaml"
```

**URL Import:**
```bash
curl -X POST "http://localhost:8000/api/swagger-import/import-specification?url=https://api.example.com/openapi.json"
```

**Response:**
```json
{
  "success": true,
  "specification_id": 1,
  "endpoints_count": 25,
  "dependencies_count": 12,
  "suggestions_count": 8,
  "message": "Specification imported successfully"
}
```

#### Parse File (Preview)
```
POST /api/swagger-import/parse-file
```
Parse and preview endpoints before import.

#### Parse URL
```
POST /api/swagger-import/parse-url?url=<swagger-url>
```
Parse specification from URL.

### Contract Validation

#### Associate Request with Endpoint
```
POST /api/swagger-import/associate-request?api_requirement_id=1&endpoint_id=5
```
Associate an API requirement with an OpenAPI endpoint.

#### Validate Endpoint Exists
```
GET /api/swagger-import/validate-endpoint?method=POST&path=/users
```
Validate that an endpoint exists in the specification.

### Schema Validation

#### Validate Request Payload
```
POST /api/swagger-import/validate-request
```
```json
{
  "payload": {
    "name": "John Doe",
    "email": "john@example.com"
  },
  "endpoint_id": 5
}
```

#### Validate Response
```
POST /api/swagger-import/validate-response
```
```json
{
  "response_body": {
    "id": 123,
    "name": "John Doe"
  },
  "status_code": "200",
  "endpoint_id": 5
}
```

### Change Detection

#### Detect Specification Changes
```
POST /api/swagger-import/detect-changes/{spec_id}
```
Detect changes between existing and new specification versions.

**Request:**
```bash
curl -X POST "http://localhost:8000/api/swagger-import/detect-changes/1" \
  -F "file=@updated_specification.yaml"
```

**Response:**
```json
{
  "has_changes": true,
  "breaking_changes": [...],
  "non_breaking_changes": [...],
  "removed_endpoints": [...],
  "added_endpoints": [...],
  "modified_endpoints": [...]
}
```

### Prerequisite Management

#### Regenerate Prerequisites
```
POST /api/swagger-import/regenerate-prerequisites?endpoint_ids=1,2,3
```
Regenerate prerequisites for affected endpoints after specification changes.

### Test Generation

#### Get Test Configuration
```
GET /api/swagger-import/test-config/{api_requirement_id}/{endpoint_id}
```
Generate test configuration with prerequisites and field mappings.

## Database Schema

### Tables

#### `openapi_specifications`
Stores imported OpenAPI specifications.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| title | String | API title |
| version | String | API version |
| spec_version | String | OpenAPI/Swagger version (2.0 or 3.0) |
| spec_json | Text | Full specification JSON |
| imported_at | DateTime | Import timestamp |
| imported_by | String | User identifier |

#### `openapi_endpoints`
Stores parsed endpoints from specifications.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| spec_id | Integer | Foreign key to specifications |
| path | String | Endpoint path |
| method | String | HTTP method |
| operation_id | String | Operation ID |
| summary | Text | Endpoint summary |
| request_schema_ref | String | Request schema $ref |
| response_schema_ref | String | Response schema $ref |
| request_schema_json | Text | Resolved request schema JSON |
| response_schema_json | Text | Resolved response schemas JSON |
| tags | String | Comma-separated tags |

**Unique Constraint:** `(spec_id, path, method)`

#### `openapi_field_dependencies`
Stores detected field dependencies between endpoints.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| source_endpoint_id | Integer | Source endpoint ID |
| target_endpoint_id | Integer | Target endpoint ID |
| source_field_name | String | Source field name |
| target_field_name | String | Target field name |
| dependency_type | String | Type of dependency |
| confidence_score | Float | Confidence score (0.0-1.0) |
| detection_method | String | Detection method used |
| response_path | String | JSONPath expression |
| is_mandatory | Boolean | Whether dependency is mandatory |

#### `prerequisite_suggestions`
Stores auto-generated prerequisite suggestions.

| Column | Type | Description |
|--------|------|-------------|
| id | Integer | Primary key |
| api_requirement_id | Integer | Associated API requirement |
| endpoint_id | Integer | Associated endpoint |
| suggested_prerequisites | Text | JSON array of prerequisites |
| suggested_field_mappings | Text | JSON object of field mappings |
| execution_order | Integer | Execution order |
| confidence_score | Float | Overall confidence |
| user_reviewed | Boolean | User review status |
| user_approved | Boolean | User approval status |
| created_at | DateTime | Creation timestamp |
| updated_at | DateTime | Update timestamp |

## Architecture

### Component Overview

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Application                    │
│                    (main.py)                            │
└─────────────────────────────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
┌───────▼──────┐  ┌────────▼────────┐  ┌─────▼──────┐
│   Import     │  │   Validation    │  │    Test    │
│  Controller  │  │   Services      │  │ Generation │
└───────┬──────┘  └────────┬────────┘  └─────┬──────┘
        │                  │                  │
┌───────▼──────────────────▼──────────────────▼───────┐
│              Core Processing Layer                   │
├──────────────────────────────────────────────────────┤
│ • OpenAPIParser          • ContractValidator        │
│ • FieldDependencyDetector • SchemaValidator          │
│ • PrerequisiteEngine     • ChangeDetector           │
│ • TestIntegration        • Regeneration             │
└──────────────────────────────────────────────────────┘
                           │
                  ┌────────▼────────┐
                  │  Database Layer │
                  │   (SQLAlchemy)  │
                  └─────────────────┘
```

### Processing Flow

1. **Import Phase**
   - Parse OpenAPI specification
   - Extract endpoints and schemas
   - Store in database

2. **Analysis Phase**
   - Detect field dependencies
   - Generate prerequisite suggestions
   - Calculate execution order

3. **Validation Phase**
   - Validate contract associations
   - Validate request/response schemas
   - Detect specification changes

4. **Integration Phase**
   - Generate test configurations
   - Execute prerequisites
   - Apply field mappings

## Usage Examples

### Example 1: Import and Analyze Specification

```python
import requests

# Import specification
response = requests.post(
    'http://localhost:8000/api/swagger-import/import-specification',
    files={'file': open('api-spec.yaml', 'rb')}
)

result = response.json()
spec_id = result['specification_id']

# The system automatically:
# - Parses all endpoints
# - Detects field dependencies
# - Generates prerequisite suggestions
```

### Example 2: Validate Request Payload

```python
import requests

validation = requests.post(
    'http://localhost:8000/api/swagger-import/validate-request',
    json={
        'payload': {
            'name': 'John Doe',
            'email': 'john@example.com'
        },
        'endpoint_id': 5
    }
)

result = validation.json()
print(f"Valid: {result['valid']}")
print(f"Coverage: {result['coverage_percentage']}%")
print(f"Errors: {result['errors']}")
```

### Example 3: Detect Changes and Regenerate

```python
import requests

# Detect changes
changes = requests.post(
    'http://localhost:8000/api/swagger-import/detect-changes/1',
    files={'file': open('updated-spec.yaml', 'rb')}
)

result = changes.json()

# Regenerate if needed
if result['has_changes']:
    affected_endpoints = [ep['endpoint_id'] for ep in result['modified_endpoints']]
    
    regenerate = requests.post(
        'http://localhost:8000/api/swagger-import/regenerate-prerequisites',
        params={'endpoint_ids': ','.join(map(str, affected_endpoints))}
    )
```

## Configuration

### Database Configuration

Edit `database.py` to configure database connection:

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./api_requirements.db")
```

For PostgreSQL:
```python
DATABASE_URL = "postgresql://user:password@localhost/dbname"
```

### CORS Configuration

Edit `main.py` to configure CORS:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Testing

Run the test suite:

```bash
python test_swagger_import.py
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Project Structure

```
.
├── main.py                          # FastAPI application entry point
├── database.py                      # Database connection and session management
├── models.py                        # SQLAlchemy database models
├── swagger_parser.py                # Basic Swagger/OpenAPI parser
├── openapi_parser.py                # Enhanced OpenAPI parser (Task 2)
├── field_dependency_detector.py     # Dependency detection (Task 3)
├── prerequisite_suggestion_engine.py # Suggestion generation (Task 4)
├── contract_validator.py            # Contract validation (Task 6)
├── schema_validator.py              # Schema validation (Task 7)
├── contract_change_detector.py      # Change detection (Task 8)
├── prerequisite_regeneration.py     # Regeneration workflow (Task 9)
├── test_generation_integration.py   # Test integration (Task 10)
├── swagger_import_controller.py     # API endpoints
├── dependency_analyzer.py           # Legacy dependency analyzer
├── suggestion_generator.py          # Legacy suggestion generator
└── requirements_swagger.txt         # Python dependencies
```

## Tasks Completed

✅ **Task 2**: OpenAPI Specification Parsing
✅ **Task 3**: Field Dependency Analysis
✅ **Task 4**: Prerequisite Suggestion Generation
⏭️ **Task 5**: User Review & Approval Interface (Frontend - Skipped)
✅ **Task 6**: Contract-Request Association & Validation
✅ **Task 7**: Request & Response Schema Validation
✅ **Task 8**: Contract Change Detection
✅ **Task 9**: Prerequisite Regeneration Workflow
✅ **Task 10**: Test Generation Integration
⏭️ **Task 1**: Model Serving Infrastructure Setup (Ollama - Not Implemented)

## License

[Specify your license here]

## Contributing

[Contributing guidelines]

## Support

[Support information]

---

**Note:** This is a backend-only implementation. Frontend components are not included per project requirements.