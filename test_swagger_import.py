"""
Complete test script for Swagger Import Feature
Run this after starting the FastAPI server
"""
import requests
import json
import os

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

def test_parse_file():
    """Test 1: Parse Swagger file"""
    print_section("TEST 1: Parse Swagger File")
    
    # Create a sample Swagger 2.0 file
    swagger_data = {
        "swagger": "2.0",
        "info": {
            "title": "Test Pet Store API",
            "version": "1.0.0",
            "description": "A sample API for testing"
        },
        "host": "petstore.swagger.io",
        "basePath": "/v2",
        "paths": {
            "/pets": {
                "get": {
                    "summary": "List all pets",
                    "description": "Returns a list of all pets in the store",
                    "tags": ["pets"],
                    "responses": {
                        "200": {
                            "description": "Successful response",
                            "schema": {
                                "type": "array",
                                "items": {
                                    "$ref": "#/definitions/Pet"
                                }
                            }
                        }
                    }
                },
                "post": {
                    "summary": "Create a new pet",
                    "description": "Adds a new pet to the store",
                    "tags": ["pets"],
                    "parameters": [
                        {
                            "name": "body",
                            "in": "body",
                            "required": True,
                            "schema": {
                                "$ref": "#/definitions/Pet"
                            }
                        }
                    ],
                    "responses": {
                        "201": {
                            "description": "Pet created successfully",
                            "schema": {
                                "$ref": "#/definitions/Pet"
                            }
                        }
                    }
                }
            },
            "/pets/{petId}": {
                "get": {
                    "summary": "Get pet by ID",
                    "tags": ["pets"],
                    "parameters": [
                        {
                            "name": "petId",
                            "in": "path",
                            "required": True,
                            "type": "integer"
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Pet found",
                            "schema": {
                                "$ref": "#/definitions/Pet"
                            }
                        },
                        "404": {
                            "description": "Pet not found"
                        }
                    }
                }
            }
        },
        "definitions": {
            "Pet": {
                "type": "object",
                "required": ["name"],
                "properties": {
                    "id": {
                        "type": "integer",
                        "format": "int64"
                    },
                    "name": {
                        "type": "string",
                        "example": "doggie"
                    },
                    "status": {
                        "type": "string",
                        "enum": ["available", "pending", "sold"],
                        "description": "Pet status in the store"
                    }
                }
            }
        }
    }
    
    # Save to file
    test_file = "test_swagger.json"
    with open(test_file, 'w') as f:
        json.dump(swagger_data, f, indent=2)
    
    print(f"Created test file: {test_file}")
    
    # Test the endpoint
    url = f"{BASE_URL}/api/swagger-import/parse-file"
    
    try:
        with open(test_file, 'rb') as f:
            files = {'file': (test_file, f, 'application/json')}
            response = requests.post(url, files=files)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: {data.get('success')}")
            print(f"✓ API Title: {data['spec_info']['title']}")
            print(f"✓ API Version: {data['spec_info']['version']}")
            print(f"✓ Spec Version: {data['spec_info']['spec_version']}")
            print(f"✓ Endpoints Found: {len(data['endpoints'])}")
            
            # Display endpoints
            print("\nEndpoints:")
            for i, ep in enumerate(data['endpoints'], 1):
                print(f"  {i}. {ep['method']} {ep['endpoint']}")
                print(f"     Summary: {ep.get('summary', 'N/A')}")
            
            return data['endpoints']
        else:
            print(f"✗ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        return None
    finally:
        # Clean up
        if os.path.exists(test_file):
            os.remove(test_file)

def test_parse_yaml_file():
    """Test 2: Parse Swagger YAML file"""
    print_section("TEST 2: Parse Swagger YAML File")
    
    yaml_file = "sample_swagger.yaml"
    
    if not os.path.exists(yaml_file):
        print(f"✗ YAML file not found: {yaml_file}")
        print("  Please make sure sample_swagger.yaml exists in the current directory")
        return None
    
    url = f"{BASE_URL}/api/swagger-import/parse-file"
    
    try:
        print(f"Parsing YAML file: {yaml_file}")
        with open(yaml_file, 'rb') as f:
            files = {'file': (yaml_file, f, 'application/x-yaml')}
            response = requests.post(url, files=files)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: {data.get('success')}")
            print(f"✓ API Title: {data['spec_info']['title']}")
            print(f"✓ API Version: {data['spec_info']['version']}")
            print(f"✓ Spec Version: {data['spec_info']['spec_version']}")
            print(f"✓ Endpoints Found: {len(data['endpoints'])}")
            
            # Display endpoints grouped by method
            methods = {}
            for ep in data['endpoints']:
                method = ep['method']
                if method not in methods:
                    methods[method] = []
                methods[method].append(ep['endpoint'])
            
            print("\nEndpoints by method:")
            for method in sorted(methods.keys()):
                print(f"  {method}: {len(methods[method])} endpoint(s)")
                for endpoint in methods[method][:3]:  # Show first 3
                    print(f"    - {endpoint}")
                if len(methods[method]) > 3:
                    print(f"    ... and {len(methods[method]) - 3} more")
            
            # Show sample endpoint details
            if data['endpoints']:
                print("\nSample endpoint details:")
                sample = data['endpoints'][0]
                print(f"  Method: {sample['method']}")
                print(f"  Endpoint: {sample['endpoint']}")
                print(f"  Summary: {sample.get('summary', 'N/A')}")
                if sample.get('payload_schema'):
                    print(f"  Has Request Schema: Yes")
                if sample.get('response_schema'):
                    print(f"  Has Response Schema: Yes")
            
            return data['endpoints']
        else:
            print(f"✗ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return None

def test_parse_url():
    """Test 3: Parse Swagger from URL"""
    print_section("TEST 3: Parse Swagger from URL")
    
    url = f"{BASE_URL}/api/swagger-import/parse-url"
    params = {"url": "https://petstore.swagger.io/v2/swagger.json"}
    
    try:
        print(f"Fetching from: {params['url']}")
        response = requests.post(url, params=params, timeout=30)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Success: {data.get('success')}")
            print(f"✓ API Title: {data['spec_info']['title']}")
            print(f"✓ Endpoints Found: {len(data['endpoints'])}")
            
            # Show first 5 endpoints
            print("\nFirst 5 endpoints:")
            for i, ep in enumerate(data['endpoints'][:5], 1):
                print(f"  {i}. {ep['method']} {ep['endpoint']}")
            
            if len(data['endpoints']) > 5:
                print(f"  ... and {len(data['endpoints']) - 5} more")
            
            return data['endpoints']
        else:
            print(f"✗ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        return None

def test_import_endpoints(endpoints):
    """Test 4: Import endpoints"""
    print_section("TEST 4: Import Endpoints")
    
    if not endpoints:
        print("No endpoints to import. Skipping test.")
        return
    
    # Take first 2 endpoints for testing
    test_endpoints = endpoints[:2]
    
    print(f"Importing {len(test_endpoints)} endpoints...")
    for ep in test_endpoints:
        print(f"  - {ep['method']} {ep['endpoint']}")
    
    url = f"{BASE_URL}/api/swagger-import/import"
    data = {
        "endpoints": test_endpoints,
        "skip_duplicates": True
    }
    
    try:
        response = requests.post(url, json=data)
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Imported: {result['imported']}")
            print(f"✓ Skipped: {result['skipped']}")
            print(f"✓ Failed: {result['failed']}")
            
            if result['errors']:
                print(f"\nErrors:")
                for error in result['errors']:
                    print(f"  - {error}")
            
            return result
        else:
            print(f"✗ Error: {response.text}")
            return None
            
    except Exception as e:
        print(f"✗ Exception: {str(e)}")
        return None

def test_duplicate_handling():
    """Test 5: Test duplicate handling"""
    print_section("TEST 5: Duplicate Handling")
    
    endpoint = {
        "method": "GET",
        "endpoint": "/test/duplicate",
        "summary": "Test duplicate endpoint",
        "description": "This endpoint is used to test duplicate handling",
        "payload_schema": None,
        "response_schema": "Status 200:\nObject:\n  - message (optional): string",
        "tags": ["test"]
    }
    
    url = f"{BASE_URL}/api/swagger-import/import"
    
    # First import
    print("1. First import (skip_duplicates=True)...")
    response1 = requests.post(url, json={
        "endpoints": [endpoint],
        "skip_duplicates": True
    })
    result1 = response1.json()
    print(f"   Result: Imported={result1['imported']}, Skipped={result1['skipped']}")
    
    # Second import (should skip)
    print("\n2. Second import (skip_duplicates=True) - should skip...")
    response2 = requests.post(url, json={
        "endpoints": [endpoint],
        "skip_duplicates": True
    })
    result2 = response2.json()
    print(f"   Result: Imported={result2['imported']}, Skipped={result2['skipped']}")
    
    # Third import (should update)
    endpoint["summary"] = "Updated test duplicate endpoint"
    print("\n3. Third import (skip_duplicates=False) - should update...")
    response3 = requests.post(url, json={
        "endpoints": [endpoint],
        "skip_duplicates": False
    })
    result3 = response3.json()
    print(f"   Result: Imported={result3['imported']}, Skipped={result3['skipped']}")
    
    print("\n✓ Duplicate handling test completed")

def test_database_verification():
    """Test 6: Verify data in database"""
    print_section("TEST 6: Database Verification")
    
    try:
        from database import SessionLocal
        from models import APIRequirement
        
        db = SessionLocal()
        requirements = db.query(APIRequirement).all()
        
        print(f"Total API Requirements in database: {len(requirements)}")
        
        if requirements:
            print("\nRecent requirements:")
            for req in requirements[-5:]:  # Show last 5
                print(f"  - {req.method} {req.endpoint}")
                print(f"    Summary: {req.summary}")
                print(f"    Created: {req.created_at}")
                print()
        else:
            print("No requirements found in database.")
        
        db.close()
        
    except Exception as e:
        print(f"✗ Error accessing database: {str(e)}")
        print("  (This is normal if database is not set up)")

def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("  SWAGGER IMPORT FEATURE - TEST SUITE")
    print("=" * 60)
    print(f"\nTesting against: {BASE_URL}")
    print("Make sure the FastAPI server is running!")
    
    # Check if server is running
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        if response.status_code != 200:
            print(f"\n⚠ Warning: Server might not be running properly")
    except:
        print(f"\n✗ ERROR: Cannot connect to {BASE_URL}")
        print("   Please start the server with: uvicorn main:app --reload")
        return
    
    # Run tests
    endpoints1 = test_parse_file()
    endpoints2 = test_parse_yaml_file()  # Test YAML file
    endpoints3 = test_parse_url()
    
    # Import endpoints from YAML file test (most comprehensive)
    if endpoints2:
        test_import_endpoints(endpoints2)
    elif endpoints1:
        test_import_endpoints(endpoints1)
    
    # Test duplicate handling
    test_duplicate_handling()
    
    # Verify database
    test_database_verification()
    
    print_section("ALL TESTS COMPLETED")
    print("✓ Check the results above for any errors")

if __name__ == "__main__":
    main()