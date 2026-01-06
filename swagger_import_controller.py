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
    """
    try:
        # Determine file type
        file_type = "json"
        if file.filename:
            if file.filename.endswith(('.yaml', '.yml')):
                file_type = "yaml"
        
        # Read file content
        content = await file.read()
        file_content = content.decode('utf-8')
        
        # Parse specification
        parser = SwaggerParser()
        result = parser.parse_from_file(file_content, file_type)
        
        return JSONResponse(content={
            "success": True,
            "spec_info": {
                "title": result.get('title', 'Unknown API'),
                "version": result.get('api_version', '1.0.0'),
                "spec_version": result.get('spec_version', '2.0')
            },
            "endpoints": result.get('endpoints', [])
        })
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing file: {str(e)}")


@router.post("/parse-url")
async def parse_swagger_url(
    url: str = Query(..., description="Swagger/OpenAPI specification URL"),
    db: Session = Depends(get_db)
):
    """
    Fetch and parse Swagger/OpenAPI specification from URL
    """
    try:
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        
        # Parse specification
        parser = SwaggerParser()
        result = parser.parse_from_url(url)
        
        return JSONResponse(content={
            "success": True,
            "spec_info": {
                "title": result.get('title', 'Unknown API'),
                "version": result.get('api_version', '1.0.0'),
                "spec_version": result.get('spec_version', '2.0')
            },
            "endpoints": result.get('endpoints', [])
        })
    
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error parsing URL: {str(e)}")


@router.post("/import")
async def import_endpoints(
    request: ImportPreviewRequest,
    db: Session = Depends(get_db)
):
    """
    Import selected endpoints as API requirements
    """
    imported_count = 0
    skipped_count = 0
    failed_count = 0
    errors = []
    
    for endpoint_data in request.endpoints:
        try:
            method = endpoint_data.get('method')
            endpoint = endpoint_data.get('endpoint')
            
            if not method or not endpoint:
                failed_count += 1
                errors.append(f"Missing method or endpoint for: {endpoint_data}")
                continue
            
            # Check for existing endpoint
            existing = db.query(APIRequirement).filter(
                and_(
                    APIRequirement.method == method,
                    APIRequirement.endpoint == endpoint
                )
            ).first()
            
            if existing:
                if request.skip_duplicates:
                    skipped_count += 1
                    continue
                else:
                    # Update existing record
                    existing.summary = endpoint_data.get('summary', existing.summary)
                    existing.description = endpoint_data.get('description', existing.description)
                    existing.payload_schema = endpoint_data.get('payload_schema', existing.payload_schema)
                    existing.response_schema = endpoint_data.get('response_schema', existing.response_schema)
                    existing.tags = ','.join(endpoint_data.get('tags', [])) if endpoint_data.get('tags') else existing.tags
                    db.commit()
                    imported_count += 1
            else:
                # Create new record
                tags_str = ','.join(endpoint_data.get('tags', [])) if endpoint_data.get('tags') else None
                new_requirement = APIRequirement(
                    method=method,
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
            errors.append(f"Error importing {endpoint_data.get('endpoint', 'unknown')}: {str(e)}")
            db.rollback()
    
    return ImportResponse(
        imported=imported_count,
        skipped=skipped_count,
        failed=failed_count,
        errors=errors
    )
