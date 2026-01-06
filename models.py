"""
Database models for API Requirements
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime

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
