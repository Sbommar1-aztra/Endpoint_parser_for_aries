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
from models import APIRequirement, Base
from database import get_db  # Assuming database connection module

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
        
        return JSONResponse(content={
            "success": True,
            "spec_info": {
                "title": result.get('title', 'Unknown API'),
                "version": result.get('api_version', '1.0.0'),
                "spec_version": result.get('spec_version', '2.0')
            },
            "endpoints": endpoints,
            "endpoint_count": len(endpoints)
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
        
        return JSONResponse(content={
            "success": True,
            "spec_info": {
                "title": result.get('title', 'Unknown API'),
                "version": result.get('api_version', '1.0.0'),
                "spec_version": result.get('spec_version', '2.0')
            },
            "endpoints": endpoints,
            "endpoint_count": len(endpoints)
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
                    existing.summary = endpoint_data.get('summary') or existing.summary
                    existing.description = endpoint_data.get('description') or existing.description
                    existing.payload_schema = endpoint_data.get('payload_schema') or existing.payload_schema
                    existing.response_schema = endpoint_data.get('response_schema') or existing.response_schema
                    tags = endpoint_data.get('tags', [])
                    if tags:
                        existing.tags = ','.join(tags) if isinstance(tags, list) else str(tags)
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
