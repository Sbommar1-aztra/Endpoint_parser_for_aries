"""
Check database structure and prerequisites
"""
from database import SessionLocal
from models import *
from sqlalchemy import inspect
import json

db = SessionLocal()

print("=" * 70)
print("DATABASE STRUCTURE CHECK")
print("=" * 70)

# Check tables
inspector = inspect(db.bind)
tables = inspector.get_table_names()

for table in tables:
    print(f"\nTable: {table}")
    print("-" * 70)
    columns = inspector.get_columns(table)
    for col in columns:
        nullable = "NULL" if col['nullable'] else "NOT NULL"
        print(f"  • {col['name']:30s} {str(col['type']):20s} {nullable}")

print("\n" + "=" * 70)
print("PREREQUISITE DATA CHECK")
print("=" * 70)

# Check PrerequisiteSuggestion table
prereq_count = db.query(PrerequisiteSuggestion).count()
print(f"\n[STATS] Prerequisite Suggestions: {prereq_count}")

if prereq_count > 0:
    prereqs = db.query(PrerequisiteSuggestion).limit(5).all()
    for i, prereq in enumerate(prereqs, 1):
        print(f"\n  Prerequisite {i}:")
        print(f"    ID: {prereq.id}")
        print(f"    API Requirement ID: {prereq.api_requirement_id}")
        print(f"    Endpoint ID: {prereq.endpoint_id}")
        print(f"    Execution Order: {prereq.execution_order}")
        print(f"    Confidence: {prereq.confidence_score}")
        
        # Parse prerequisites
        prereq_list = prereq.get_prerequisites()
        print(f"    Prerequisites Count: {len(prereq_list)}")
        if prereq_list:
            print("    Prerequisites:")
            for p in prereq_list[:3]:  # Show first 3
                print(f"      - {p.get('method')} {p.get('endpoint')}")
        
        # Parse field mappings
        mappings = prereq.get_field_mappings()
        print(f"    Field Mappings Count: {len(mappings)}")
        if mappings:
            print("    Sample Field Mappings:")
            for field, mapping in list(mappings.items())[:3]:  # Show first 3
                print(f"      - {field}: {mapping.get('source_type', 'N/A')}")

# Check OpenAPIFieldDependency table
dep_count = db.query(OpenAPIFieldDependency).count()
print(f"\n[STATS] Field Dependencies: {dep_count}")

if dep_count > 0:
    deps = db.query(OpenAPIFieldDependency).limit(5).all()
    for i, dep in enumerate(deps, 1):
        print(f"\n  Dependency {i}:")
        print(f"    Source Endpoint ID: {dep.source_endpoint_id}")
        print(f"    Target Endpoint ID: {dep.target_endpoint_id}")
        print(f"    Source Field: {dep.source_field_name}")
        print(f"    Target Field: {dep.target_field_name}")
        print(f"    Method: {dep.detection_method}")
        print(f"    Confidence: {dep.confidence_score}")
        print(f"    Response Path: {dep.response_path}")

# Check OpenAPIEndpoint table
endpoint_count = db.query(OpenAPIEndpoint).count()
print(f"\n[STATS] OpenAPI Endpoints: {endpoint_count}")

if endpoint_count > 0:
    endpoints = db.query(OpenAPIEndpoint).limit(5).all()
    for i, ep in enumerate(endpoints, 1):
        print(f"\n  Endpoint {i}:")
        print(f"    ID: {ep.id}")
        print(f"    Method: {ep.method}")
        print(f"    Path: {ep.path}")
        print(f"    Has Request Schema: {bool(ep.request_schema_json)}")
        print(f"    Has Response Schema: {bool(ep.response_schema_json)}")
        
        # Check schema structure
        if ep.request_schema_json:
            try:
                req_schema = json.loads(ep.request_schema_json)
                props = req_schema.get('properties', {})
                required = req_schema.get('required', [])
                print(f"    Request Schema Fields: {len(props)}")
                print(f"    Required Fields: {len(required)}")
            except:
                print(f"    Request Schema: Invalid JSON")
        
        if ep.response_schema_json:
            try:
                resp_schema = json.loads(ep.response_schema_json)
                if isinstance(resp_schema, dict):
                    status_codes = list(resp_schema.keys())
                    print(f"    Response Status Codes: {status_codes}")
            except:
                print(f"    Response Schema: Invalid JSON")

# Check OpenAPISpecification table
spec_count = db.query(OpenAPISpecification).count()
print(f"\n[STATS] OpenAPI Specifications: {spec_count}")

if spec_count > 0:
    specs = db.query(OpenAPISpecification).all()
    for spec in specs:
        print(f"\n  Specification:")
        print(f"    ID: {spec.id}")
        print(f"    Title: {spec.title}")
        print(f"    Version: {spec.version}")
        print(f"    Spec Version: {spec.spec_version}")
        print(f"    Endpoints: {len(spec.endpoints)}")

print("\n" + "=" * 70)
print("SCHEMA PARSING STRUCTURE CHECK")
print("=" * 70)

# Check a sample endpoint's schema structure
sample_endpoint = db.query(OpenAPIEndpoint).first()
if sample_endpoint:
    print(f"\n[SAMPLE] Endpoint Schema Structure:")
    print(f"  Endpoint: {sample_endpoint.method} {sample_endpoint.path}")
    
    if sample_endpoint.request_schema_json:
        try:
            req_schema = json.loads(sample_endpoint.request_schema_json)
            print(f"\n  Request Schema Structure:")
            print(f"    Type: {req_schema.get('type', 'N/A')}")
            print(f"    Properties: {list(req_schema.get('properties', {}).keys())}")
            print(f"    Required: {req_schema.get('required', [])}")
            
            # Show sample property structure
            props = req_schema.get('properties', {})
            if props:
                first_prop = list(props.items())[0]
                print(f"\n    Sample Property '{first_prop[0]}':")
                for key, value in first_prop[1].items():
                    print(f"      {key}: {value}")
        except Exception as e:
            print(f"    Error parsing request schema: {e}")
    
    if sample_endpoint.response_schema_json:
        try:
            resp_schema = json.loads(sample_endpoint.response_schema_json)
            print(f"\n  Response Schema Structure:")
            if isinstance(resp_schema, dict):
                for status, schema in list(resp_schema.items())[:2]:  # Show first 2
                    print(f"    Status {status}:")
                    if isinstance(schema, dict):
                        print(f"      Type: {schema.get('type', 'N/A')}")
                        props = schema.get('properties', {})
                        if props:
                            print(f"      Properties: {list(props.keys())[:5]}")  # First 5
        except Exception as e:
            print(f"    Error parsing response schema: {e}")

db.close()
print("\n" + "=" * 70)
print("CHECK COMPLETE")
print("=" * 70)

