"""
Enhanced OpenAPI Parser - Task 2
Implements OpenAPIParser class with proper schema extraction and field parsing
"""
import json
from typing import Dict, List, Optional, Any, Tuple
from swagger_parser import SwaggerParser


class OpenAPIParser:
    """
    Enhanced OpenAPI Parser - Task 2
    Parses OpenAPI specifications to extract endpoints, schemas, and field definitions
    """
    
    def __init__(self):
        self.swagger_parser = SwaggerParser()
        self.spec = None
        self.version = None
        self.schemas = {}
        self.definitions = {}
    
    def parse_specification(self, file_content: str = None, url: str = None, file_type: str = "json") -> Dict[str, Any]:
        """
        Parse OpenAPI specification and return structured data
        
        Args:
            file_content: File content string (for file upload)
            url: URL string (for URL import)
            file_type: 'json' or 'yaml'
            
        Returns:
            Dictionary with spec info and endpoints
        """
        if file_content:
            result = self.swagger_parser.parse_from_file(file_content, file_type)
        elif url:
            result = self.swagger_parser.parse_from_url(url)
        else:
            raise ValueError("Either file_content or url must be provided")
        
        self.spec = self.swagger_parser.spec
        self.version = self.swagger_parser.version
        
        # Extract schemas/definitions based on version
        if self.version == '2.0':
            self.definitions = self.spec.get('definitions', {})
        else:
            components = self.spec.get('components', {})
            self.schemas = components.get('schemas', {})
        
        return result
    
    def parse_endpoints(self) -> List[Dict[str, Any]]:
        """
        Parse all endpoints from the specification
        
        Returns:
            List of endpoint dictionaries with all required fields
        """
        endpoints = []
        paths = self.spec.get('paths', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                # Check if method is a string before calling .lower()
                if method and isinstance(method, str) and method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    endpoint_info = self._extract_endpoint(path, method.upper(), operation)
                    if endpoint_info:
                        endpoints.append(endpoint_info)
        
        return endpoints
    
    def _extract_endpoint(self, path: str, method: str, operation: Dict) -> Optional[Dict[str, Any]]:
        """
        Extract complete endpoint information
        
        Args:
            path: Endpoint path
            method: HTTP method
            operation: Operation object from OpenAPI spec
            
        Returns:
            Dictionary with all endpoint fields
        """
        # Extract request schema
        request_schema_ref, request_schema_json = self._extract_request_schema(operation)
        
        # Extract response schemas
        response_schema_ref, response_schema_json = self._extract_response_schema(operation)
        
        # Extract tags
        tags = operation.get('tags', [])
        tags_str = ','.join(tags) if tags else None
        
        return {
            'path': path,
            'method': method,
            'operation_id': operation.get('operationId'),
            'summary': operation.get('summary', ''),
            'request_schema_ref': request_schema_ref,
            'response_schema_ref': response_schema_ref,
            'request_schema_json': json.dumps(request_schema_json) if request_schema_json else None,
            'response_schema_json': json.dumps(response_schema_json) if response_schema_json else None,
            'tags': tags_str
        }
    
    def _extract_request_schema(self, operation: Dict) -> Tuple[Optional[str], Optional[Dict]]:
        """
        Extract request body schema
        
        Args:
            operation: Operation object
            
        Returns:
            Tuple of (schema_ref, resolved_schema_json)
        """
        request_schema_ref = None
        resolved_schema = None
        
        if self.version == '2.0':
            # Swagger 2.0: Look in parameters
            parameters = operation.get('parameters', [])
            for param in parameters:
                if param.get('in') == 'body':
                    schema = param.get('schema', {})
                    if '$ref' in schema:
                        request_schema_ref = schema['$ref']
                        resolved_schema = self._resolve_reference(request_schema_ref)
                    else:
                        resolved_schema = schema
                    break
        else:
            # OpenAPI 3.0: Look in requestBody
            request_body = operation.get('requestBody', {})
            if request_body:
                content = request_body.get('content', {})
                json_content = content.get('application/json')
                if json_content:
                    schema = json_content.get('schema', {})
                    if '$ref' in schema:
                        request_schema_ref = schema['$ref']
                        resolved_schema = self._resolve_reference(request_schema_ref)
                    else:
                        resolved_schema = schema
        
        return request_schema_ref, resolved_schema
    
    def _extract_response_schema(self, operation: Dict) -> Tuple[Optional[str], Dict]:
        """
        Extract response schemas for success status codes (200, 201, 202)
        
        Args:
            operation: Operation object
            
        Returns:
            Tuple of (response_schema_ref, resolved_schemas_dict)
        """
        responses = operation.get('responses', {})
        resolved_schemas = {}
        response_schema_ref = None
        
        # Extract schemas for success status codes
        success_codes = ['200', '201', '202']
        
        for status_code in success_codes:
            if status_code in responses:
                response = responses[status_code]
                
                if self.version == '2.0':
                    schema = response.get('schema')
                    if schema:
                        if '$ref' in schema:
                            if not response_schema_ref:
                                response_schema_ref = schema['$ref']
                            resolved_schemas[status_code] = self._resolve_reference(schema['$ref'])
                        else:
                            resolved_schemas[status_code] = schema
                else:
                    # OpenAPI 3.0
                    content = response.get('content', {})
                    json_content = content.get('application/json')
                    if json_content:
                        schema = json_content.get('schema', {})
                        if schema:
                            if '$ref' in schema:
                                if not response_schema_ref:
                                    response_schema_ref = schema['$ref']
                                resolved_schemas[status_code] = self._resolve_reference(schema['$ref'])
                            else:
                                resolved_schemas[status_code] = schema
        
        return response_schema_ref, resolved_schemas
    
    def _resolve_reference(self, ref_path: str) -> Optional[Dict]:
        """
        Resolve $ref reference to actual schema
        
        Args:
            ref_path: Reference path (e.g., '#/definitions/User' or '#/components/schemas/User')
            
        Returns:
            Resolved schema dictionary
        """
        if not ref_path or not ref_path.startswith('#'):
            return None
        
        try:
            if self.version == '2.0':
                # Swagger 2.0: #/definitions/ModelName
                if ref_path.startswith('#/definitions/'):
                    def_name = ref_path.replace('#/definitions/', '')
                    if def_name in self.definitions:
                        return self._deep_copy_and_resolve(self.definitions[def_name])
            else:
                # OpenAPI 3.0: #/components/schemas/ModelName
                if ref_path.startswith('#/components/schemas/'):
                    schema_name = ref_path.replace('#/components/schemas/', '')
                    if schema_name in self.schemas:
                        return self._deep_copy_and_resolve(self.schemas[schema_name])
        except Exception as e:
            print(f"Error resolving reference {ref_path}: {e}")
        
        return None
    
    def _deep_copy_and_resolve(self, schema: Dict) -> Dict:
        """
        Deep copy schema and resolve nested $ref references
        
        Args:
            schema: Schema dictionary
            
        Returns:
            Resolved schema dictionary
        """
        if not isinstance(schema, dict):
            return schema
        
        resolved = {}
        for key, value in schema.items():
            if key == '$ref' and isinstance(value, str):
                # Resolve nested reference
                nested = self._resolve_reference(value)
                if nested:
                    resolved.update(nested)
                else:
                    resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self._deep_copy_and_resolve(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self._deep_copy_and_resolve(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value
        
        return resolved
    
    def get_schema_fields(self, schema: Dict) -> List[Dict[str, Any]]:
        """
        Extract field properties from a schema
        
        Args:
            schema: Schema dictionary
            
        Returns:
            List of field dictionaries with properties:
            - name: Field name
            - type: Field type
            - format: Format (e.g., 'date-time', 'email')
            - description: Field description
            - required: Whether field is required
            - constraints: Dictionary with min, max, minLength, maxLength, pattern, enum
        """
        fields = []
        
        if not isinstance(schema, dict):
            return fields
        
        # Get properties
        properties = schema.get('properties', {})
        required_fields = schema.get('required', [])
        
        for field_name, field_schema in properties.items():
            if not isinstance(field_schema, dict):
                continue
            
            field_info = {
                'name': field_name,
                'type': field_schema.get('type', 'string'),
                'format': field_schema.get('format'),
                'description': field_schema.get('description', ''),
                'required': field_name in required_fields,
                'constraints': {}
            }
            
            # Extract constraints
            constraints = field_info['constraints']
            
            if 'minimum' in field_schema:
                constraints['minimum'] = field_schema['minimum']
            if 'maximum' in field_schema:
                constraints['maximum'] = field_schema['maximum']
            if 'minLength' in field_schema:
                constraints['minLength'] = field_schema['minLength']
            if 'maxLength' in field_schema:
                constraints['maxLength'] = field_schema['maxLength']
            if 'pattern' in field_schema:
                constraints['pattern'] = field_schema['pattern']
            if 'enum' in field_schema:
                constraints['enum'] = field_schema['enum']
            if 'minItems' in field_schema:
                constraints['minItems'] = field_schema['minItems']
            if 'maxItems' in field_schema:
                constraints['maxItems'] = field_schema['maxItems']
            
            # Check for custom extensions
            if 'x-foreign-key' in field_schema:
                field_info['x_foreign_key'] = field_schema['x-foreign-key']
            if 'x-primary-key' in field_schema:
                field_info['x_primary_key'] = field_schema['x-primary-key']
            
            fields.append(field_info)
        
        return fields
