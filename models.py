"""
Database models for API Requirements
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, UniqueConstraint, ForeignKey, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import json

Base = declarative_base()


class APIRequirement(Base):
    """API Requirement model"""
    __tablename__ = 'api_requirements'
    
    id = Column(Integer, primary_key=True, index=True)
    method = Column(String(10), nullable=False, index=True)  # GET, POST, PUT, DELETE, etc.
    endpoint = Column(String(500), nullable=False, index=True)
    summary = Column(String(500))
    description = Column(Text)
    payload_schema = Column(Text)
    response_schema = Column(Text)
    tags = Column(String(500))  # Comma-separated tags
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Unique constraint on method + endpoint
    __table_args__ = (
        UniqueConstraint('method', 'endpoint', name='uq_method_endpoint'),
    )
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'method': self.method,
            'endpoint': self.endpoint,
            'summary': self.summary,
            'description': self.description,
            'payload_schema': self.payload_schema,
            'response_schema': self.response_schema,
            'tags': self.tags,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class OpenAPISpecification(Base):
    """OpenAPI Specification model"""
    __tablename__ = 'openapi_specifications'
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500))
    version = Column(String(50))
    spec_version = Column(String(10))  # '2.0' or '3.0'
    spec_json = Column(Text)  # Full specification JSON
    imported_at = Column(DateTime, default=func.now())
    imported_by = Column(String(100))  # User identifier
    
    # Relationships
    endpoints = relationship("OpenAPIEndpoint", back_populates="specification", cascade="all, delete-orphan")
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'title': self.title,
            'version': self.version,
            'spec_version': self.spec_version,
            'imported_at': self.imported_at.isoformat() if self.imported_at else None,
            'imported_by': self.imported_by
        }


class OpenAPIEndpoint(Base):
    """OpenAPI Endpoint model - Task 2"""
    __tablename__ = 'openapi_endpoints'
    
    id = Column(Integer, primary_key=True, index=True)
    spec_id = Column(Integer, ForeignKey('openapi_specifications.id'), nullable=False, index=True)
    path = Column(String(500), nullable=False)
    method = Column(String(10), nullable=False)  # GET, POST, PUT, DELETE, etc.
    operation_id = Column(String(200))
    summary = Column(Text)
    request_schema_ref = Column(String(500))  # $ref path
    response_schema_ref = Column(String(500))  # $ref path
    request_schema_json = Column(Text)  # Resolved schema as JSON string
    response_schema_json = Column(Text)  # Resolved schemas as JSON string (object with status codes as keys)
    tags = Column(String(500))  # Comma-separated tags
    
    # Relationships
    specification = relationship("OpenAPISpecification", back_populates="endpoints")
    field_dependencies = relationship("OpenAPIFieldDependency", foreign_keys="[OpenAPIFieldDependency.source_endpoint_id]", back_populates="source_endpoint")
    
    # Unique constraint on (spec_id, path, method)
    __table_args__ = (
        UniqueConstraint('spec_id', 'path', 'method', name='uq_spec_path_method'),
    )
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'spec_id': self.spec_id,
            'path': self.path,
            'method': self.method,
            'operation_id': self.operation_id,
            'summary': self.summary,
            'request_schema_ref': self.request_schema_ref,
            'response_schema_ref': self.response_schema_ref,
            'request_schema_json': self.request_schema_json,
            'response_schema_json': self.response_schema_json,
            'tags': self.tags
        }
    
    def get_request_schema(self):
        """Get request schema as dict"""
        if self.request_schema_json:
            return json.loads(self.request_schema_json)
        return None
    
    def get_response_schema(self, status_code: str = '200'):
        """Get response schema for a specific status code"""
        if self.response_schema_json:
            schemas = json.loads(self.response_schema_json)
            return schemas.get(status_code)
        return None


class OpenAPIFieldDependency(Base):
    """OpenAPI Field Dependency model - Task 3"""
    __tablename__ = 'openapi_field_dependencies'
    
    id = Column(Integer, primary_key=True, index=True)
    source_endpoint_id = Column(Integer, ForeignKey('openapi_endpoints.id'), nullable=False, index=True)
    target_endpoint_id = Column(Integer, ForeignKey('openapi_endpoints.id'), nullable=False, index=True)
    source_field_name = Column(String(200), nullable=False)
    target_field_name = Column(String(200), nullable=False)
    dependency_type = Column(String(50))  # 'explicit', 'naming', 'description'
    confidence_score = Column(Float, default=0.0)  # 0.0 to 1.0
    detection_method = Column(String(50))  # 'explicit', 'naming', 'description'
    response_path = Column(String(500))  # JSONPath expression (e.g., $.id, $.user_id)
    is_mandatory = Column(Boolean, default=False)
    
    # Relationships
    source_endpoint = relationship("OpenAPIEndpoint", foreign_keys=[source_endpoint_id], back_populates="field_dependencies")
    target_endpoint = relationship("OpenAPIEndpoint", foreign_keys=[target_endpoint_id])
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'source_endpoint_id': self.source_endpoint_id,
            'target_endpoint_id': self.target_endpoint_id,
            'source_field_name': self.source_field_name,
            'target_field_name': self.target_field_name,
            'dependency_type': self.dependency_type,
            'confidence_score': self.confidence_score,
            'detection_method': self.detection_method,
            'response_path': self.response_path,
            'is_mandatory': self.is_mandatory
        }


class PrerequisiteSuggestion(Base):
    """Prerequisite Suggestion model - Task 4"""
    __tablename__ = 'prerequisite_suggestions'
    
    id = Column(Integer, primary_key=True, index=True)
    api_requirement_id = Column(Integer, ForeignKey('api_requirements.id'), nullable=False, index=True)
    endpoint_id = Column(Integer, ForeignKey('openapi_endpoints.id'), nullable=False, index=True)
    suggested_prerequisites = Column(Text)  # JSON array of prerequisite configs
    suggested_field_mappings = Column(Text)  # JSON object of field mappings
    execution_order = Column(Integer)
    confidence_score = Column(Float, default=0.0)  # 0.0 to 1.0
    user_reviewed = Column(Boolean, default=False)
    user_approved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'api_requirement_id': self.api_requirement_id,
            'endpoint_id': self.endpoint_id,
            'suggested_prerequisites': self.suggested_prerequisites,
            'suggested_field_mappings': self.suggested_field_mappings,
            'execution_order': self.execution_order,
            'confidence_score': self.confidence_score,
            'user_reviewed': self.user_reviewed,
            'user_approved': self.user_approved,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def get_prerequisites(self):
        """Get prerequisites as list"""
        if self.suggested_prerequisites:
            return json.loads(self.suggested_prerequisites)
        return []
    
    def get_field_mappings(self):
        """Get field mappings as dict"""
        if self.suggested_field_mappings:
            return json.loads(self.suggested_field_mappings)
        return {}
