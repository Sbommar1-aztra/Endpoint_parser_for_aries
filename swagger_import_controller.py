"""
Swagger/OpenAPI Import Controller
Handles file upload and URL-based imports
"""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
import tempfile
import os

from swagger_parser import SwaggerParser
from models import (
    APIRequirement, Base, OpenAPISpecification, OpenAPIEndpoint,
    OpenAPIFieldDependency, PrerequisiteSuggestion
)
from database import get_db
from openapi_parser import OpenAPIParser
from field_dependency_detector import FieldDependencyDetector
from prerequisite_suggestion_engine import PrerequisiteSuggestionEngine
from dependency_analyzer import DependencyAnalyzer
from suggestion_generator import SuggestionGenerator
from contract_validator import ContractValidator
from schema_validator import SchemaValidator
from contract_change_detector import ContractChangeDetector
from prerequisite_regeneration import PrerequisiteRegeneration
from test_generation_integration import TestGenerationIntegration
import json

# Configuration constants
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB maximum file size
ALLOWED_EXTENSIONS = {'.json', '.yaml', '.yml'}
ALLOWED_CONTENT_TYPES = {
    'application/json',
    'application/x-yaml',
    'text/yaml',
    'text/x-yaml',
    'application/octet-stream'  # Some servers send this for YAML
}


router = APIRouter(prefix="/api/swagger-import", tags=["swagger-import"])


class ImportPreviewRequest(BaseModel):
    """Request model for importing selected endpoints"""
    endpoints: List[Dict[str, Any]]  # List of endpoint objects to import
    skip_duplicates: bool = True  # Whether to skip existing endpoints


class ImportResponse(BaseModel):
    """Response model for import operation"""
    imported: int
    skipped: int
    failed: int
    errors: List[str] = []


@router.post("/parse-file")
async def parse_swagger_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Parse Swagger/OpenAPI file and return preview of endpoints
    
    Supports:
    - Swagger 2.0 and OpenAPI 3.0 specifications
    - JSON and YAML file formats
    - Maximum file size: 10 MB
    """
    try:
        # Validate file name
        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail="File name is required. Please provide a valid Swagger/OpenAPI file."
            )
        
        # Validate file extension
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}. "
                       f"Received: {file_ext or 'no extension'}"
            )
        
        # Determine file type
        file_type = "json"
        if file_ext in ('.yaml', '.yml'):
            file_type = "yaml"
        
        # Validate content type (if provided)
        if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
            # Warning only, not blocking - some servers don't set content-type correctly
            pass
        
        # Read file content with size validation
        content = await file.read()
        
        # Check file size
        file_size = len(content)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size ({file_size / 1024 / 1024:.2f} MB) exceeds maximum allowed size "
                       f"({MAX_FILE_SIZE / 1024 / 1024} MB). Please use a smaller file or split the specification."
            )
        
        if file_size == 0:
            raise HTTPException(
                status_code=400,
                detail="File is empty. Please provide a valid Swagger/OpenAPI specification file."
            )
        
        # Decode file content
        try:
            file_content = content.decode('utf-8')
        except UnicodeDecodeError as e:
            raise HTTPException(
                status_code=400,
                detail=f"File encoding error: {str(e)}. Please ensure the file is UTF-8 encoded."
            )
        
        # Parse specification
        parser = SwaggerParser()
        result = parser.parse_from_file(file_content, file_type)
        
        # Validate that endpoints were found
        endpoints = result.get('endpoints', [])
        if not endpoints:
            raise HTTPException(
                status_code=400,
                detail="No endpoints found in the specification. Please ensure the file contains valid API endpoints."
            )
        
        # Phase 0C: Analyze Dependencies
        dependency_analyzer = DependencyAnalyzer()
        dependencies = dependency_analyzer.analyze(endpoints)
        
        # Phase 0D: Generate Suggestions
        suggestion_generator = SuggestionGenerator()
        suggestions = suggestion_generator.generate_suggestions(endpoints)
        
        return JSONResponse(content={
            "success": True,
            "spec_info": {
                "title": result.get('title', 'Unknown API'),
                "version": result.get('api_version', '1.0.0'),
                "spec_version": result.get('spec_version', '2.0')
            },
            "endpoints": endpoints,
            "endpoint_count": len(endpoints),
            "dependencies": dependencies,
            "suggestions": {
                "prerequisite_configs": suggestions.get('prerequisite_configs', []),
                "field_mappings": suggestions.get('field_mappings', []),
                "execution_order": suggestions.get('execution_order', [])
            }
        })
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Swagger/OpenAPI specification: {str(e)}. "
                   "Please ensure the file is a valid Swagger 2.0 or OpenAPI 3.0 specification."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error parsing file: {str(e)}. Please check the file format and try again."
        )


@router.post("/parse-url")
async def parse_swagger_url(
    url: str = Query(..., description="Swagger/OpenAPI specification URL"),
    db: Session = Depends(get_db)
):
    """
    Fetch and parse Swagger/OpenAPI specification from URL
    
    Supports:
    - Swagger 2.0 and OpenAPI 3.0 specifications
    - JSON and YAML formats
    - HTTP and HTTPS URLs
    """
    try:
        # Validate URL format
        if not url or not isinstance(url, str):
            raise HTTPException(
                status_code=400,
                detail="URL is required. Please provide a valid Swagger/OpenAPI specification URL."
            )
        
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid URL format: '{url}'. URL must start with http:// or https://"
            )
        
        # Basic URL validation
        if len(url) > 2048:  # Reasonable URL length limit
            raise HTTPException(
                status_code=400,
                detail="URL is too long. Maximum length is 2048 characters."
            )
        
        # Parse specification
        parser = SwaggerParser()
        result = parser.parse_from_url(url)
        
        # Validate that endpoints were found
        endpoints = result.get('endpoints', [])
        if not endpoints:
            raise HTTPException(
                status_code=400,
                detail="No endpoints found in the specification at the provided URL. "
                       "Please ensure the URL points to a valid Swagger/OpenAPI specification."
            )
        
        # Phase 0C: Analyze Dependencies
        dependency_analyzer = DependencyAnalyzer()
        dependencies = dependency_analyzer.analyze(endpoints)
        
        # Phase 0D: Generate Suggestions
        suggestion_generator = SuggestionGenerator()
        suggestions = suggestion_generator.generate_suggestions(endpoints)
        
        return JSONResponse(content={
            "success": True,
            "spec_info": {
                "title": result.get('title', 'Unknown API'),
                "version": result.get('api_version', '1.0.0'),
                "spec_version": result.get('spec_version', '2.0')
            },
            "endpoints": endpoints,
            "endpoint_count": len(endpoints),
            "dependencies": dependencies,
            "suggestions": {
                "prerequisite_configs": suggestions.get('prerequisite_configs', []),
                "field_mappings": suggestions.get('field_mappings', []),
                "execution_order": suggestions.get('execution_order', [])
            }
        })
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except ValueError as e:
        error_msg = str(e)
        if "Failed to fetch" in error_msg:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to fetch specification from URL: {error_msg}. "
                       "Please check the URL is accessible and points to a valid Swagger/OpenAPI file."
            )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid Swagger/OpenAPI specification: {error_msg}. "
                   "Please ensure the URL points to a valid Swagger 2.0 or OpenAPI 3.0 specification."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error parsing URL: {str(e)}. Please check the URL and try again."
        )


@router.post("/import")
async def import_endpoints(
    request: ImportPreviewRequest,
    db: Session = Depends(get_db)
):
    """
    Import selected endpoints as API requirements
    
    Parameters:
    - endpoints: List of endpoint objects to import
    - skip_duplicates: If True, skip existing endpoints. If False, update existing endpoints.
    
    Returns:
    - imported: Number of successfully imported endpoints
    - skipped: Number of skipped endpoints (duplicates)
    - failed: Number of failed imports
    - errors: List of error messages for failed imports
    """
    # Validate request
    if not request.endpoints:
        raise HTTPException(
            status_code=400,
            detail="No endpoints provided. Please select at least one endpoint to import."
        )
    
    if len(request.endpoints) > 1000:  # Reasonable batch limit
        raise HTTPException(
            status_code=400,
            detail=f"Too many endpoints ({len(request.endpoints)}). Maximum batch size is 1000 endpoints. "
                   "Please split into smaller batches."
        )
    
    imported_count = 0
    skipped_count = 0
    failed_count = 0
    errors = []
    
    # Validate HTTP methods
    valid_methods = {'GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS'}
    
    for endpoint_data in request.endpoints:
        try:
            method = endpoint_data.get('method')
            endpoint = endpoint_data.get('endpoint')
            
            # Validate required fields
            if not method:
                failed_count += 1
                errors.append(f"Missing HTTP method for endpoint: {endpoint_data.get('endpoint', 'unknown')}")
                continue
            
            if not endpoint:
                failed_count += 1
                errors.append(f"Missing endpoint path for method: {method}")
                continue
            
            # Validate HTTP method
            method_upper = method.upper()
            if method_upper not in valid_methods:
                failed_count += 1
                errors.append(f"Invalid HTTP method '{method}' for endpoint '{endpoint}'. "
                             f"Valid methods: {', '.join(valid_methods)}")
                continue
            
            # Validate endpoint path
            if not isinstance(endpoint, str) or not endpoint.startswith('/'):
                failed_count += 1
                errors.append(f"Invalid endpoint path '{endpoint}'. Endpoint must be a string starting with '/'")
                continue
            
            # Check for existing endpoint
            existing = db.query(APIRequirement).filter(
                and_(
                    APIRequirement.method == method_upper,
                    APIRequirement.endpoint == endpoint
                )
            ).first()
            
            if existing:
                if request.skip_duplicates:
                    skipped_count += 1
                    continue
                else:
                    # Update existing record
                    # BUG FIX: Use explicit key presence check instead of 'or' operator
                    # The 'or' operator treats empty strings ('') as falsy, preventing field clearing
                    # Using 'in' check allows distinguishing:
                    #   - Key not provided: skip update (preserve existing value)
                    #   - Key with empty string: clear field (set to '')
                    #   - Key with value: update field (set to new value)
                    if 'summary' in endpoint_data:
                        existing.summary = endpoint_data['summary']
                    if 'description' in endpoint_data:
                        existing.description = endpoint_data['description']
                    if 'payload_schema' in endpoint_data:
                        existing.payload_schema = endpoint_data['payload_schema']
                    if 'response_schema' in endpoint_data:
                        existing.response_schema = endpoint_data['response_schema']
                    if 'tags' in endpoint_data:
                        tags = endpoint_data['tags']
                        existing.tags = ','.join(tags) if isinstance(tags, list) and tags else (str(tags) if tags else None)
                    db.commit()
                    imported_count += 1
            else:
                # Create new record
                tags = endpoint_data.get('tags', [])
                tags_str = ','.join(tags) if isinstance(tags, list) and tags else (str(tags) if tags else None)
                
                new_requirement = APIRequirement(
                    method=method_upper,
                    endpoint=endpoint,
                    summary=endpoint_data.get('summary'),
                    description=endpoint_data.get('description'),
                    payload_schema=endpoint_data.get('payload_schema'),
                    response_schema=endpoint_data.get('response_schema'),
                    tags=tags_str
                )
                db.add(new_requirement)
                db.commit()
                imported_count += 1
        
        except Exception as e:
            failed_count += 1
            endpoint_info = f"{endpoint_data.get('method', 'unknown')} {endpoint_data.get('endpoint', 'unknown')}"
            errors.append(f"Error importing {endpoint_info}: {str(e)}")
            db.rollback()
    
    return ImportResponse(
        imported=imported_count,
        skipped=skipped_count,
        failed=failed_count,
        errors=errors
    )


@router.post("/import-specification")
async def import_specification_to_db(
    file: UploadFile = File(None),
    url: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Enhanced import endpoint - Task 2, 3, 4
    Imports OpenAPI specification and stores in proper database tables:
    - OPENAPI_SPECIFICATIONS
    - OPENAPI_ENDPOINTS
    - OPENAPI_FIELD_DEPENDENCIES
    - PREREQUISITE_SUGGESTIONS
    """
    try:
        # Parse specification
        parser = OpenAPIParser()
        
        if file:
            file_content = await file.read()
            file_type = "json"
            if file.filename:
                ext = os.path.splitext(file.filename)[1].lower()
                if ext in ['.yaml', '.yml']:
                    file_type = "yaml"
            
            result = parser.parse_specification(
                file_content=file_content.decode('utf-8'),
                file_type=file_type
            )
        elif url:
            result = parser.parse_specification(url=url)
        else:
            raise HTTPException(
                status_code=400,
                detail="Either file or url must be provided"
            )
        
        # Create or get specification record
        spec = OpenAPISpecification(
            title=result.get('title', 'Unknown API'),
            version=result.get('api_version', '1.0.0'),
            spec_version=result.get('spec_version', '2.0'),
            spec_json=json.dumps(parser.spec)
        )
        db.add(spec)
        db.flush()  # Get spec.id
        
        # Parse endpoints using enhanced parser
        endpoints_data = parser.parse_endpoints()
        
        # Store endpoints
        endpoint_objects = []
        for ep_data in endpoints_data:
            endpoint = OpenAPIEndpoint(
                spec_id=spec.id,
                path=ep_data['path'],
                method=ep_data['method'],
                operation_id=ep_data.get('operation_id'),
                summary=ep_data.get('summary'),
                request_schema_ref=ep_data.get('request_schema_ref'),
                response_schema_ref=ep_data.get('response_schema_ref'),
                request_schema_json=ep_data.get('request_schema_json'),
                response_schema_json=ep_data.get('response_schema_json'),
                tags=ep_data.get('tags')
            )
            db.add(endpoint)
            endpoint_objects.append(endpoint)
        
        db.flush()  # Get endpoint IDs
        
        # Task 3: Detect field dependencies
        detector = FieldDependencyDetector()
        dependencies_data = detector.detect_dependencies(
            endpoints_data, endpoint_objects
        )
        
        # Store dependencies
        dependency_objects = []
        for dep_data in dependencies_data:
            dependency = OpenAPIFieldDependency(
                source_endpoint_id=dep_data['source_endpoint_id'],
                target_endpoint_id=dep_data['target_endpoint_id'],
                source_field_name=dep_data['source_field_name'],
                target_field_name=dep_data['target_field_name'],
                dependency_type=dep_data['dependency_type'],
                confidence_score=dep_data['confidence_score'],
                detection_method=dep_data['detection_method'],
                response_path=dep_data['response_path'],
                is_mandatory=dep_data['is_mandatory']
            )
            db.add(dependency)
            dependency_objects.append(dependency)
        
        db.flush()  # Get dependency IDs
        
        # Task 4: Generate prerequisite suggestions
        suggestion_engine = PrerequisiteSuggestionEngine()
        suggestions_data = suggestion_engine.generate_suggestions(
            endpoint_objects, dependencies_data
        )
        
        # Store suggestions
        for sugg_data in suggestions_data:
            suggestion = PrerequisiteSuggestion(
                api_requirement_id=sugg_data.get('api_requirement_id'),
                endpoint_id=sugg_data['endpoint_id'],
                suggested_prerequisites=sugg_data['suggested_prerequisites'],
                suggested_field_mappings=sugg_data['suggested_field_mappings'],
                execution_order=sugg_data['execution_order'],
                confidence_score=sugg_data['confidence_score'],
                user_reviewed=sugg_data['user_reviewed'],
                user_approved=sugg_data['user_approved']
            )
            db.add(suggestion)
        
        db.commit()
        
        return JSONResponse(content={
            "success": True,
            "specification_id": spec.id,
            "endpoints_count": len(endpoint_objects),
            "dependencies_count": len(dependency_objects),
            "suggestions_count": len(suggestions_data),
            "message": "Specification imported successfully"
        })
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error importing specification: {str(e)}"
        )


@router.post("/associate-request")
async def associate_request_with_endpoint(
    api_requirement_id: int = Query(..., description="API Requirement ID"),
    endpoint_id: int = Query(..., description="OpenAPI Endpoint ID"),
    db: Session = Depends(get_db)
):
    """
    Task 6: Associate API request with OpenAPI endpoint
    """
    validator = ContractValidator(db)
    result = validator.associate_request_with_endpoint(api_requirement_id, endpoint_id)
    
    if not result.get('success'):
        return JSONResponse(
            status_code=400 if 'error' in result else 200,
            content=result
        )
    
    return JSONResponse(content=result)


@router.get("/validate-endpoint")
async def validate_endpoint(
    method: str = Query(..., description="HTTP Method"),
    path: str = Query(..., description="Endpoint Path"),
    spec_id: int = Query(None, description="Optional Specification ID"),
    db: Session = Depends(get_db)
):
    """
    Task 6: Validate endpoint exists in specification
    """
    validator = ContractValidator(db)
    result = validator.validate_endpoint_exists(method, path, spec_id)
    
    status_code = 200 if result.get('exists') else 404
    return JSONResponse(status_code=status_code, content=result)


class ValidateRequestPayload(BaseModel):
    """Request model for payload validation"""
    payload: Dict[str, Any]
    endpoint_id: int


class ValidateResponsePayload(BaseModel):
    """Request model for response validation"""
    response_body: Dict[str, Any]
    status_code: str
    endpoint_id: int


@router.post("/validate-request")
async def validate_request(
    request: ValidateRequestPayload,
    db: Session = Depends(get_db)
):
    """
    Task 7: Validate request payload against schema
    """
    endpoint = db.query(OpenAPIEndpoint).filter(
        OpenAPIEndpoint.id == request.endpoint_id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=404,
            detail=f"Endpoint {request.endpoint_id} not found"
        )
    
    validator = SchemaValidator()
    result = validator.validate_request_payload(request.payload, endpoint)
    
    return JSONResponse(content=result)


@router.post("/validate-response")
async def validate_response(
    request: ValidateResponsePayload,
    db: Session = Depends(get_db)
):
    """
    Task 7: Validate response against schema
    """
    endpoint = db.query(OpenAPIEndpoint).filter(
        OpenAPIEndpoint.id == request.endpoint_id
    ).first()
    
    if not endpoint:
        raise HTTPException(
            status_code=404,
            detail=f"Endpoint {request.endpoint_id} not found"
        )
    
    validator = SchemaValidator()
    result = validator.validate_response(
        request.response_body,
        request.status_code,
        endpoint
    )
    
    return JSONResponse(content=result)


@router.post("/detect-changes/{spec_id}")
async def detect_specification_changes(
    spec_id: int,
    file: UploadFile = File(None),
    url: str = Query(None),
    db: Session = Depends(get_db)
):
    """
    Task 8: Detect changes in specification
    """
    # Parse new specification
    parser = OpenAPIParser()
    
    if file:
        file_content = await file.read()
        file_type = "json"
        if file.filename:
            ext = os.path.splitext(file.filename)[1].lower()
            if ext in ['.yaml', '.yml']:
                file_type = "yaml"
        
        result = parser.parse_specification(
            file_content=file_content.decode('utf-8'),
            file_type=file_type
        )
    elif url:
        result = parser.parse_specification(url=url)
    else:
        raise HTTPException(
            status_code=400,
            detail="Either file or url must be provided"
        )
    
    # Detect changes
    detector = ContractChangeDetector(db)
    changes = detector.detect_changes(spec_id, parser.spec)
    
    return JSONResponse(content=changes)


@router.post("/regenerate-prerequisites")
async def regenerate_prerequisites(
    endpoint_ids: List[int] = Query(..., description="List of endpoint IDs to regenerate"),
    api_requirement_id: int = Query(None, description="Optional API requirement ID"),
    db: Session = Depends(get_db)
):
    """
    Task 9: Regenerate prerequisites for endpoints
    """
    regenerator = PrerequisiteRegeneration(db)
    result = regenerator.regenerate_for_endpoints(endpoint_ids, api_requirement_id)
    
    return JSONResponse(content=result)


@router.get("/test-config/{api_requirement_id}/{endpoint_id}")
async def get_test_config(
    api_requirement_id: int,
    endpoint_id: int,
    db: Session = Depends(get_db)
):
    """
    Task 10: Generate test configuration with prerequisites and field mappings
    """
    test_gen = TestGenerationIntegration(db)
    config = test_gen.generate_test_config(api_requirement_id, endpoint_id)
    
    return JSONResponse(content=config)
