"""
Contract-Request Association & Validation - Task 6
Enables association of API requests with OpenAPI contracts and validates method/endpoint existence
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from models import OpenAPIEndpoint, APIRequirement
from sqlalchemy import and_


class ContractValidator:
    """
    Contract Validator - Task 6
    Handles association and validation of API requests with OpenAPI contracts
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def associate_request_with_endpoint(
        self,
        api_requirement_id: int,
        endpoint_id: int
    ) -> Dict[str, Any]:
        """
        Associate an API requirement with an OpenAPI endpoint
        
        Args:
            api_requirement_id: ID of the API requirement
            endpoint_id: ID of the OpenAPI endpoint
            
        Returns:
            Dictionary with association result
        """
        # Validate API requirement exists
        api_req = self.db.query(APIRequirement).filter(
            APIRequirement.id == api_requirement_id
        ).first()
        
        if not api_req:
            return {
                'success': False,
                'error': f'API requirement {api_requirement_id} not found'
            }
        
        # Validate endpoint exists
        endpoint = self.db.query(OpenAPIEndpoint).filter(
            OpenAPIEndpoint.id == endpoint_id
        ).first()
        
        if not endpoint:
            return {
                'success': False,
                'error': f'OpenAPI endpoint {endpoint_id} not found'
            }
        
        # Validate method matches
        if api_req.method.upper() != endpoint.method.upper():
            return {
                'success': False,
                'warning': f'Method mismatch: API requirement uses {api_req.method}, endpoint expects {endpoint.method}'
            }
        
        # Validate endpoint path matches (fuzzy matching for path parameters)
        if not self._paths_match(api_req.endpoint, endpoint.path):
            return {
                'success': False,
                'warning': f'Endpoint path mismatch: API requirement uses {api_req.endpoint}, endpoint expects {endpoint.path}'
            }
        
        # Store association (you might want to add an endpoint_id field to APIRequirement)
        # For now, we'll return success with validation results
        
        return {
            'success': True,
            'api_requirement_id': api_requirement_id,
            'endpoint_id': endpoint_id,
            'method': endpoint.method,
            'path': endpoint.path,
            'validation_passed': True
        }
    
    def validate_endpoint_exists(
        self,
        method: str,
        path: str,
        spec_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate that an endpoint exists in the specification
        
        Args:
            method: HTTP method
            path: Endpoint path
            spec_id: Optional specification ID to limit search
            
        Returns:
            Dictionary with validation result
        """
        query = self.db.query(OpenAPIEndpoint).filter(
            and_(
                OpenAPIEndpoint.method == method.upper(),
                OpenAPIEndpoint.path == path
            )
        )
        
        if spec_id:
            query = query.filter(OpenAPIEndpoint.spec_id == spec_id)
        
        endpoint = query.first()
        
        if endpoint:
            return {
                'exists': True,
                'endpoint_id': endpoint.id,
                'method': endpoint.method,
                'path': endpoint.path,
                'operation_id': endpoint.operation_id,
                'summary': endpoint.summary
            }
        else:
            # Try fuzzy matching for path parameters
            fuzzy_match = self._find_fuzzy_match(method, path, spec_id)
            
            if fuzzy_match:
                return {
                    'exists': False,
                    'warning': f'Exact match not found. Possible match: {fuzzy_match.method} {fuzzy_match.path}',
                    'suggested_endpoint_id': fuzzy_match.id
                }
            
            return {
                'exists': False,
                'error': f'Endpoint {method} {path} not found in specification'
            }
    
    def validate_method_exists(
        self,
        path: str,
        method: str,
        spec_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Validate that HTTP method exists for the given endpoint path
        
        Args:
            path: Endpoint path
            method: HTTP method to validate
            spec_id: Optional specification ID
            
        Returns:
            Dictionary with validation result
        """
        query = self.db.query(OpenAPIEndpoint).filter(
            OpenAPIEndpoint.path == path
        )
        
        if spec_id:
            query = query.filter(OpenAPIEndpoint.spec_id == spec_id)
        
        endpoints = query.all()
        
        if not endpoints:
            return {
                'exists': False,
                'error': f'No endpoints found for path {path}'
            }
        
        available_methods = [ep.method for ep in endpoints]
        
        if method.upper() in available_methods:
            matching_endpoint = next(ep for ep in endpoints if ep.method.upper() == method.upper())
            return {
                'exists': True,
                'method': method.upper(),
                'path': path,
                'endpoint_id': matching_endpoint.id
            }
        else:
            return {
                'exists': False,
                'error': f'Method {method} not found for path {path}',
                'available_methods': available_methods
            }
    
    def get_endpoint_for_request(
        self,
        method: str,
        path: str,
        spec_id: Optional[int] = None
    ) -> Optional[OpenAPIEndpoint]:
        """
        Get OpenAPI endpoint for a given method and path
        
        Args:
            method: HTTP method
            path: Endpoint path
            spec_id: Optional specification ID
            
        Returns:
            OpenAPIEndpoint object or None
        """
        query = self.db.query(OpenAPIEndpoint).filter(
            and_(
                OpenAPIEndpoint.method == method.upper(),
                OpenAPIEndpoint.path == path
            )
        )
        
        if spec_id:
            query = query.filter(OpenAPIEndpoint.spec_id == spec_id)
        
        endpoint = query.first()
        
        if endpoint:
            return endpoint
        
        # Try fuzzy matching
        return self._find_fuzzy_match(method, path, spec_id)
    
    def _paths_match(self, path1: str, path2: str) -> bool:
        """
        Check if two paths match (handles path parameters)
        
        Args:
            path1: First path
            path2: Second path
            
        Returns:
            True if paths match
        """
        # Exact match
        if path1 == path2:
            return True
        
        # Normalize paths
        p1_parts = path1.split('/')
        p2_parts = path2.split('/')
        
        if len(p1_parts) != len(p2_parts):
            return False
        
        # Compare parts (treat {param} as matching any)
        for part1, part2 in zip(p1_parts, p2_parts):
            if part1 != part2:
                # Check if one is a path parameter
                if not ((part1.startswith('{') and part1.endswith('}')) or
                        (part2.startswith('{') and part2.endswith('}'))):
                    return False
        
        return True
    
    def _find_fuzzy_match(
        self,
        method: str,
        path: str,
        spec_id: Optional[int] = None
    ) -> Optional[OpenAPIEndpoint]:
        """Find endpoint with fuzzy path matching"""
        query = self.db.query(OpenAPIEndpoint).filter(
            OpenAPIEndpoint.method == method.upper()
        )
        
        if spec_id:
            query = query.filter(OpenAPIEndpoint.spec_id == spec_id)
        
        endpoints = query.all()
        
        for endpoint in endpoints:
            if self._paths_match(path, endpoint.path):
                return endpoint
        
        return None
