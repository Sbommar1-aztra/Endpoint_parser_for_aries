"""
Field Dependency Detector - Task 3
Automatically detects foreign key relationships between endpoints using multiple detection methods
"""
import json
import re
from typing import Dict, List, Optional, Any, Tuple


class FieldDependencyDetector:
    """
    Field Dependency Detector - Task 3
    Detects foreign key relationships between endpoints using:
    1. Explicit x-foreign-key extensions
    2. Naming conventions ({entity}_id pattern)
    3. Description analysis
    """
    
    def __init__(self):
        self.endpoints = []
        self.dependencies = []
    
    def detect_dependencies(
        self, 
        endpoints: List[Dict[str, Any]], 
        endpoint_objects: List[Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Detect all dependencies between endpoints
        
        Args:
            endpoints: List of parsed endpoint dictionaries
            endpoint_objects: Optional list of OpenAPIEndpoint database objects
            
        Returns:
            List of dependency dictionaries
        """
        self.endpoints = endpoints
        self.endpoint_objects = endpoint_objects or {}
        self.dependencies = []
        
        # Build endpoint lookup by ID
        if endpoint_objects:
            self.endpoint_by_id = {ep.id: ep for ep in endpoint_objects}
        else:
            self.endpoint_by_id = {}
        
        # Analyze each endpoint
        for idx, endpoint in enumerate(endpoints):
            endpoint_id = endpoint.get('id') if isinstance(endpoint, dict) else None
            if not endpoint_id and endpoint_objects and idx < len(endpoint_objects):
                endpoint_id = endpoint_objects[idx].id
            
            deps = self._detect_endpoint_dependencies(endpoint, endpoint_id)
            if deps:
                self.dependencies.extend(deps)
        
        return self.dependencies
    
    def _detect_endpoint_dependencies(
        self, 
        endpoint: Dict[str, Any], 
        endpoint_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Detect dependencies for a single endpoint"""
        dependencies = []
        
        # Get request schema
        request_schema_json = endpoint.get('request_schema_json')
        if request_schema_json:
            if isinstance(request_schema_json, str):
                request_schema = json.loads(request_schema_json)
            else:
                request_schema = request_schema_json
        else:
            request_schema = None
        
        if not request_schema:
            return dependencies
        
        # Extract fields from request schema
        fields = self._extract_fields_from_schema(request_schema)
        
        # Method 1: Detect explicit x-foreign-key extensions
        explicit_deps = self._detect_explicit_fk(
            endpoint, endpoint_id, fields, request_schema
        )
        dependencies.extend(explicit_deps)
        
        # Method 2: Detect by naming convention
        naming_deps = self._detect_by_naming(
            endpoint, endpoint_id, fields, request_schema
        )
        dependencies.extend(naming_deps)
        
        # Method 3: Detect by description
        desc_deps = self._detect_by_description(
            endpoint, endpoint_id, fields, request_schema
        )
        dependencies.extend(desc_deps)
        
        return dependencies
    
    def _detect_explicit_fk(
        self,
        endpoint: Dict[str, Any],
        endpoint_id: Optional[int],
        fields: List[Dict],
        request_schema: Dict
    ) -> List[Dict[str, Any]]:
        """
        Method 1: Detect explicit x-foreign-key extensions
        Confidence: 1.00
        """
        dependencies = []
        
        properties = request_schema.get('properties', {})
        
        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue
            
            # Check for x-foreign-key extension
            fk_extension = field_schema.get('x-foreign-key')
            if not fk_extension:
                continue
            
            # Parse x-foreign-key format
            # Expected format: {"endpoint": "POST /users", "method": "POST", "column": "id"}
            if isinstance(fk_extension, dict):
                target_endpoint_path = fk_extension.get('endpoint', '')
                target_method = fk_extension.get('method', '')
                target_column = fk_extension.get('column', 'id')
                
                # Find target endpoint
                target_endpoint = self._find_endpoint_by_path_and_method(
                    target_endpoint_path, target_method
                )
                
                if target_endpoint:
                    target_endpoint_id = target_endpoint.get('id')
                    
                    # Generate JSONPath expression for response
                    response_path = f"$.{target_column}"
                    
                    # Check if field is required
                    required_fields = request_schema.get('required', [])
                    is_mandatory = field_name in required_fields
                    
                    dependencies.append({
                        'source_endpoint_id': endpoint_id,
                        'target_endpoint_id': target_endpoint_id,
                        'source_field_name': field_name,
                        'target_field_name': target_column,
                        'dependency_type': 'foreign_key',
                        'confidence_score': 1.00,
                        'detection_method': 'explicit',
                        'response_path': response_path,
                        'is_mandatory': is_mandatory
                    })
        
        return dependencies
    
    def _detect_by_naming(
        self,
        endpoint: Dict[str, Any],
        endpoint_id: Optional[int],
        fields: List[Dict],
        request_schema: Dict
    ) -> List[Dict[str, Any]]:
        """
        Method 2: Detect by naming convention ({entity}_id pattern)
        Confidence: 0.85
        """
        dependencies = []
        
        # Pattern to match {entity}_id (e.g., user_id, product_id, order_id)
        id_pattern = re.compile(r'^(\w+)_id$', re.IGNORECASE)
        
        properties = request_schema.get('required', []) + list(request_schema.get('properties', {}).keys())
        required_fields = request_schema.get('required', [])
        
        for field_name in properties:
            match = id_pattern.match(field_name)
            if not match:
                continue
            
            entity_name = match.group(1).lower()
            
            # Find entity creation endpoints (POST endpoints)
            # Priority: POST endpoints that likely create the entity
            target_endpoints = self._find_entity_creation_endpoints(entity_name)
            
            for target_endpoint in target_endpoints:
                target_endpoint_id = target_endpoint.get('id')
                
                # Common response field names
                possible_id_fields = ['id', f'{entity_name}_id', f'{entity_name}Id']
                
                # Try to find the actual response field
                response_field = self._find_response_id_field(
                    target_endpoint, possible_id_fields
                )
                
                response_path = f"$.{response_field}" if response_field else "$.id"
                
                is_mandatory = field_name in required_fields
                
                dependencies.append({
                    'source_endpoint_id': endpoint_id,
                    'target_endpoint_id': target_endpoint_id,
                    'source_field_name': field_name,
                    'target_field_name': response_field or 'id',
                    'dependency_type': 'foreign_key',
                    'confidence_score': 0.85,
                    'detection_method': 'naming',
                    'response_path': response_path,
                    'is_mandatory': is_mandatory
                })
                
                # Only use first matching endpoint for each field
                break
        
        return dependencies
    
    def _detect_by_description(
        self,
        endpoint: Dict[str, Any],
        endpoint_id: Optional[int],
        fields: List[Dict],
        request_schema: Dict
    ) -> List[Dict[str, Any]]:
        """
        Method 3: Detect by description (field descriptions containing "foreign key to {entity}")
        Confidence: 0.80
        """
        dependencies = []
        
        # Pattern to match "foreign key to {entity}" or similar
        fk_patterns = [
            re.compile(r'foreign\s+key\s+to\s+(\w+)', re.IGNORECASE),
            re.compile(r'reference\s+to\s+(\w+)', re.IGNORECASE),
            re.compile(r'links?\s+to\s+(\w+)', re.IGNORECASE),
            re.compile(r'refers?\s+to\s+(\w+)', re.IGNORECASE),
        ]
        
        properties = request_schema.get('properties', {})
        required_fields = request_schema.get('required', [])
        
        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue
            
            description = field_schema.get('description', '')
            if not description:
                continue
            
            # Check each pattern
            for pattern in fk_patterns:
                match = pattern.search(description)
                if match:
                    entity_name = match.group(1).lower()
                    
                    # Find entity creation endpoints
                    target_endpoints = self._find_entity_creation_endpoints(entity_name)
                    
                    for target_endpoint in target_endpoints:
                        target_endpoint_id = target_endpoint.get('id')
                        
                        response_field = self._find_response_id_field(
                            target_endpoint, ['id', f'{entity_name}_id']
                        )
                        
                        response_path = f"$.{response_field}" if response_field else "$.id"
                        
                        is_mandatory = field_name in required_fields
                        
                        dependencies.append({
                            'source_endpoint_id': endpoint_id,
                            'target_endpoint_id': target_endpoint_id,
                            'source_field_name': field_name,
                            'target_field_name': response_field or 'id',
                            'dependency_type': 'foreign_key',
                            'confidence_score': 0.80,
                            'detection_method': 'description',
                            'response_path': response_path,
                            'is_mandatory': is_mandatory
                        })
                        
                        break
                    
                    # Only process first match
                    break
        
        return dependencies
    
    def _extract_fields_from_schema(self, schema: Dict) -> List[Dict]:
        """Extract field information from schema"""
        fields = []
        properties = schema.get('properties', {})
        required_fields = schema.get('required', [])
        
        for field_name, field_schema in properties.items():
            if isinstance(field_schema, dict):
                fields.append({
                    'name': field_name,
                    'type': field_schema.get('type'),
                    'required': field_name in required_fields,
                    'description': field_schema.get('description', ''),
                    'schema': field_schema
                })
        
        return fields
    
    def _find_endpoint_by_path_and_method(
        self, path: str, method: str
    ) -> Optional[Dict[str, Any]]:
        """Find endpoint by path and method"""
        for endpoint in self.endpoints:
            if isinstance(endpoint, dict):
                if endpoint.get('path') == path and endpoint.get('method') == method:
                    return endpoint
            else:
                # Database object
                if endpoint.path == path and endpoint.method == method:
                    return {'id': endpoint.id, 'path': endpoint.path, 'method': endpoint.method}
        return None
    
    def _find_entity_creation_endpoints(self, entity_name: str) -> List[Dict[str, Any]]:
        """Find POST endpoints that likely create the entity"""
        candidates = []
        
        for endpoint in self.endpoints:
            if isinstance(endpoint, dict):
                method = endpoint.get('method', '').upper()
                path = endpoint.get('path', '').lower()
                summary = endpoint.get('summary', '').lower()
                operation_id = endpoint.get('operation_id', '').lower()
            else:
                method = endpoint.method.upper()
                path = endpoint.path.lower()
                summary = (endpoint.summary or '').lower()
                operation_id = (endpoint.operation_id or '').lower()
            
            # Look for POST endpoints related to the entity
            if method == 'POST':
                # Check if path, summary, or operation_id contains entity name
                if (entity_name in path or 
                    entity_name in summary or 
                    entity_name in operation_id or
                    'create' in summary or
                    'create' in operation_id):
                    
                    if isinstance(endpoint, dict):
                        candidates.append(endpoint)
                    else:
                        candidates.append({
                            'id': endpoint.id,
                            'path': endpoint.path,
                            'method': endpoint.method,
                            'operation_id': endpoint.operation_id
                        })
        
        return candidates
    
    def _find_response_id_field(
        self, endpoint: Dict[str, Any], possible_fields: List[str]
    ) -> Optional[str]:
        """Find the ID field in endpoint response schema"""
        response_schema_json = endpoint.get('response_schema_json')
        if not response_schema_json:
            return 'id'  # Default
        
        try:
            if isinstance(response_schema_json, str):
                response_schemas = json.loads(response_schema_json)
            else:
                response_schemas = response_schema_json
            
            # Check 200 response first
            schema_200 = response_schemas.get('200') or response_schemas.get(200)
            if schema_200:
                properties = schema_200.get('properties', {})
                for field in possible_fields:
                    if field in properties:
                        return field
            
            # Check other responses
            for status_code, schema in response_schemas.items():
                if isinstance(schema, dict):
                    properties = schema.get('properties', {})
                    for field in possible_fields:
                        if field in properties:
                            return field
        except Exception:
            pass
        
        return 'id'  # Default fallback
