# Endpoint_parser_for_aries


Step 1: Install dependencies
# Install required packagespip install PyYAML requests sqlalchemy fastapi uvicorn# Or install from requirements filepip install -r requirements_swagger.txt
Verify installation:
python -c "import yaml, requests, sqlalchemy; print('All packages installed!')"
Step 2: Set up files
Ensure these files are in your project directory:
swagger_parser.py
swagger_import_controller.py
models.py
database.py
main.py (with router integration)
Verify main.py includes:
from database import init_dbfrom swagger_import_controller import router as swagger_import_routerapp.include_router(swagger_import_router)init_db()
Step 3: Start the FastAPI server
# Navigate to your project directorycd "path/to/your/project"# Start the serveruvicorn main:app --reload --port 8000
Expected output:
INFO:     Uvicorn running on http://127.0.0.1:8000INFO:     Application startup complete.
Keep this terminal open.
Step 4: Verify server is running
Open in browser:
http://localhost:8000/docs
You should see:
FastAPI interactive documentation
A section called "swagger-import" with 3 endpoints:
POST /api/swagger-import/parse-file
POST /api/swagger-import/parse-url
POST /api/swagger-import/import
Step 5: Test method 1 — using FastAPI docs (easiest)
Test 5a: Parse a file
In the browser at http://localhost:8000/docs
Find POST /api/swagger-import/parse-file
Click "Try it out"
Click "Choose File" and select sample_swagger.yaml (or any Swagger JSON/YAML file)
Click "Execute"
Expected: Status 200 with a JSON response showing endpoints
Example response:
{  "success": true,  "spec_info": {    "title": "Sample API for Testing",    "version": "1.0.0",    "spec_version": "2.0"  },  "endpoints": [    {      "method": "GET",      "endpoint": "/users",      "summary": "List all users",      ...    }  ]}
Test 5b: Parse from URL
Find POST /api/swagger-import/parse-url
Click "Try it out"
Enter URL: https://petstore.swagger.io/v2/swagger.json
Click "Execute"
Expected: Status 200 with parsed endpoints
Test 5c: Import endpoints
After parsing (5a or 5b), copy the endpoints array from the response
Find POST /api/swagger-import/import
Click "Try it out"
Paste this JSON (replace with your endpoints):
{  "endpoints": [    {      "method": "GET",      "endpoint": "/users",      "summary": "List all users",      "description": "Retrieve a list of all users",      "payload_schema": null,      "response_schema": "Status 200:\nArray of User...",      "tags": ["users"]    }  ],  "skip_duplicates": true}
Click "Execute"
Expected: Status 200 with import summary:
{  "imported": 1,  "skipped": 0,  "failed": 0,  "errors": []}
Step 6: Test method 2 — using the test script
Option A: Run the full test script
# Make sure server is running in another terminalpython test_swagger_import.py
This runs:
Test 1: Parse Swagger file (creates test file automatically)
Test 2: Parse YAML file (uses sample_swagger.yaml)
Test 3: Parse from URL
Test 4: Import endpoints
Test 5: Duplicate handling
Test 6: Database verification

