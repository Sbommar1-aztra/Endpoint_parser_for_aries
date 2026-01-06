"""
Swagger/OpenAPI Parser Service
Supports Swagger 2.0 and OpenAPI 3.0 specifications
"""
import json
import yaml
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse
import requests


class SwaggerParser:
    """Parser for Swagger 2.0 and OpenAPI 3.0 specifications"""
    
    def __init__(self):
        self.spec = None
        self.version = None
        self.resolved_refs = {}
    
    def parse_from_file(self, file_content: str, file_type: str = "json") -> Dict[str, Any]:
        """Parse Swagger/OpenAPI specification from file content"""
        try:
            if file_type.lower() in ["yaml", "yml"]:
                self.spec = yaml.safe_load(file_content)
            else:
                self.spec = json.loads(file_content)
            
            return self._detect_version_and_parse()
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format: {str(e)}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {str(e)}")
    
    def parse_from_url(self, url: str) -> Dict[str, Any]:
        """Fetch and parse Swagger/OpenAPI specification from URL"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            if 'yaml' in content_type or 'yml' in content_type:
                self.spec = yaml.safe_load(response.text)
            else:
                self.spec = response.json()
            
            return self._detect_version_and_parse()
        except requests.RequestException as e:
            raise ValueError(f"Failed to fetch specification from URL: {str(e)}")
    
    def _detect_version_and_parse(self) -> Dict[str, Any]:
        """Detect specification version and parse accordingly"""
        if not self.spec:
            raise ValueError("No specification data available")
        
        # Detect version
        if 'swagger' in self.spec:
            self.version = '2.0'
            return self._parse_swagger_2_0()
        elif 'openapi' in self.spec:
            version = self.spec.get('openapi', '').split('.')[0]
            if version == '3':
                self.version = '3.0'
                return self._parse_openapi_3_0()
        
        # Check if it's AsyncAPI
        if 'asyncapi' in self.spec:
            raise ValueError(
                "AsyncAPI specification detected. This parser only supports Swagger 2.0 and OpenAPI 3.0 specifications. "
                "AsyncAPI is a different specification format for asynchronous APIs (Kafka, MQTT, etc.) and is not supported."
            )
        
        raise ValueError(
            "Unsupported specification version. Only Swagger 2.0 and OpenAPI 3.0 are supported. "
            "The file must contain either 'swagger: \"2.0\"' or 'openapi: \"3.0\"' at the root level."
        )
    
    def _parse_swagger_2_0(self) -> Dict[str, Any]:
        """Parse Swagger 2.0 specification"""
        endpoints = []
        paths = self.spec.get('paths', {})
        definitions = self.spec.get('definitions', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    endpoint_info = self._extract_endpoint_info_swagger_2(
                        path, method.upper(), operation, definitions
                    )
                    if endpoint_info:
                        endpoints.append(endpoint_info)
        
        return {
            'spec_version': self.version,
            'title': self.spec.get('info', {}).get('title', 'Unknown API'),
            'api_version': self.spec.get('info', {}).get('version', '1.0.0'),
            'endpoints': endpoints
        }
    
    def _parse_openapi_3_0(self) -> Dict[str, Any]:
        """Parse OpenAPI 3.0 specification"""
        endpoints = []
        paths = self.spec.get('paths', {})
        components = self.spec.get('components', {})
        schemas = components.get('schemas', {})
        
        for path, path_item in paths.items():
            for method, operation in path_item.items():
                if method.lower() in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']:
                    endpoint_info = self._extract_endpoint_info_openapi_3(
                        path, method.upper(), operation, schemas
                    )
                    if endpoint_info:
                        endpoints.append(endpoint_info)
        
        return {
            'spec_version': self.version,
            'title': self.spec.get('info', {}).get('title', 'Unknown API'),
            'api_version': self.spec.get('info', {}).get('version', '1.0.0'),
            'endpoints': endpoints
        }
    
    def _extract_endpoint_info_swagger_2(
        self, path: str, method: str, operation: Dict, definitions: Dict
    ) -> Optional[Dict[str, Any]]:
        """Extract endpoint information from Swagger 2.0 operation"""
        # Extract request body schema
        request_schema = None
        parameters = operation.get('parameters', [])
        for param in parameters:
            if param.get('in') == 'body':
                schema_ref = param.get('schema', {})
                request_schema = self._resolve_schema_swagger_2(schema_ref, definitions)
                break
        
        # Extract response schemas
        response_schemas = {}
        responses = operation.get('responses', {})
        for status_code, response in responses.items():
            schema_ref = response.get('schema', {})
            if schema_ref:
                response_schemas[status_code] = self._resolve_schema_swagger_2(schema_ref, definitions)
        
        return {
            'method': method,
            'endpoint': path,
            'summary': operation.get('summary', ''),
            'description': operation.get('description', ''),
            'payload_schema': self._schema_to_text(request_schema) if request_schema else None,
            'response_schema': self._schema_to_text(response_schemas) if response_schemas else None,
            'tags': operation.get('tags', [])
        }
    
    def _extract_endpoint_info_openapi_3(
        self, path: str, method: str, operation: Dict, schemas: Dict
    ) -> Optional[Dict[str, Any]]:
        """Extract endpoint information from OpenAPI 3.0 operation"""
        # Extract request body schema
        request_schema = None
        request_body = operation.get('requestBody', {})
        if request_body:
            content = request_body.get('content', {})
            for content_type, media_type in content.items():
                schema_ref = media_type.get('schema', {})
                if schema_ref:
                    request_schema = self._resolve_schema_openapi_3(schema_ref, schemas)
                    break
        
        # Extract response schemas
        response_schemas = {}
        responses = operation.get('responses', {})
        for status_code, response in responses.items():
            content = response.get('content', {})
            for content_type, media_type in content.items():
                schema_ref = media_type.get('schema', {})
                if schema_ref:
                    response_schemas[status_code] = self._resolve_schema_openapi_3(schema_ref, schemas)
                    break
        
        return {
            'method': method,
            'endpoint': path,
            'summary': operation.get('summary', ''),
            'description': operation.get('description', ''),
            'payload_schema': self._schema_to_text(request_schema) if request_schema else None,
            'response_schema': self._schema_to_text(response_schemas) if response_schemas else None,
            'tags': operation.get('tags', [])
        }
    
    def _resolve_schema_swagger_2(self, schema: Dict, definitions: Dict) -> Dict:
        """Resolve $ref references in Swagger 2.0"""
        if '$ref' in schema:
            ref_path = schema['$ref']
            if ref_path.startswith('#/definitions/'):
                def_name = ref_path.replace('#/definitions/', '')
                if def_name in definitions:
                    return definitions[def_name]
        return schema
    
    def _resolve_schema_openapi_3(self, schema: Dict, schemas: Dict) -> Dict:
        """Resolve $ref references in OpenAPI 3.0"""
        if '$ref' in schema:
            ref_path = schema['$ref']
            if ref_path.startswith('#/components/schemas/'):
                schema_name = ref_path.replace('#/components/schemas/', '')
                if schema_name in schemas:
                    resolved = schemas[schema_name].copy()
                    # Recursively resolve nested refs
                    return self._resolve_nested_refs(resolved, schemas)
        return self._resolve_nested_refs(schema, schemas)
    
    def _resolve_nested_refs(self, schema: Dict, schemas: Dict) -> Dict:
        """Recursively resolve nested $ref references"""
        if isinstance(schema, dict):
            resolved = {}
            for key, value in schema.items():
                if key == '$ref' and isinstance(value, str):
                    if value.startswith('#/components/schemas/'):
                        schema_name = value.replace('#/components/schemas/', '')
                        if schema_name in schemas:
                            resolved.update(self._resolve_nested_refs(schemas[schema_name], schemas))
                    else:
                        resolved[key] = value
                elif isinstance(value, dict):
                    resolved[key] = self._resolve_nested_refs(value, schemas)
                elif isinstance(value, list):
                    resolved[key] = [self._resolve_nested_refs(item, schemas) if isinstance(item, dict) else item for item in value]
                else:
                    resolved[key] = value
            return resolved
        return schema
    
    def _schema_to_text(self, schema: Any) -> str:
        """Convert schema to human-readable text format"""
        if schema is None:
            return ""
        
        if isinstance(schema, dict):
            if isinstance(schema, dict) and len(schema) == 0:
                return ""
            
            # Handle response schemas dictionary
            if all(isinstance(k, str) and k.isdigit() for k in schema.keys()):
                result = []
                for status, resp_schema in schema.items():
                    result.append(f"Status {status}:")
                    result.append(self._format_schema_object(resp_schema, indent=2))
                return "\n".join(result)
            
            return self._format_schema_object(schema)
        
        return str(schema)
    
    def _format_schema_object(self, schema: Dict, indent: int = 0) -> str:
        """Format a schema object as readable text"""
        lines = []
        indent_str = " " * indent
        
        if 'type' in schema:
            schema_type = schema['type']
            
            if schema_type == 'object':
                lines.append(f"{indent_str}Object:")
                properties = schema.get('properties', {})
                required = schema.get('required', [])
                
                for prop_name, prop_schema in properties.items():
                    is_required = prop_name in required
                    req_marker = " (required)" if is_required else " (optional)"
                    
                    prop_type = prop_schema.get('type', 'unknown')
                    prop_desc = prop_schema.get('description', '')
                    
                    if prop_type == 'object':
                        lines.append(f"{indent_str}  - {prop_name}{req_marker}:")
                        lines.append(self._format_schema_object(prop_schema, indent + 4))
                    elif prop_type == 'array':
                        items = prop_schema.get('items', {})
                        lines.append(f"{indent_str}  - {prop_name}{req_marker}: Array of {items.get('type', 'any')}")
                        if 'items' in prop_schema and prop_schema['items'].get('type') == 'object':
                            lines.append(self._format_schema_object(prop_schema['items'], indent + 4))
                    else:
                        desc_text = f" - {prop_desc}" if prop_desc else ""
                        lines.append(f"{indent_str}  - {prop_name}{req_marker}: {prop_type}{desc_text}")
            
            elif schema_type == 'array':
                items = schema.get('items', {})
                lines.append(f"{indent_str}Array of {items.get('type', 'any')}:")
                if items.get('type') == 'object':
                    lines.append(self._format_schema_object(items, indent + 2))
            else:
                desc = schema.get('description', '')
                desc_text = f" - {desc}" if desc else ""
                lines.append(f"{indent_str}{schema_type}{desc_text}")
        
        elif 'allOf' in schema:
            lines.append(f"{indent_str}AllOf:")
            for sub_schema in schema['allOf']:
                lines.append(self._format_schema_object(sub_schema, indent + 2))
        
        elif 'oneOf' in schema:
            lines.append(f"{indent_str}OneOf:")
            for sub_schema in schema['oneOf']:
                lines.append(self._format_schema_object(sub_schema, indent + 2))
        
        else:
            # Fallback for unknown schema structure
            lines.append(f"{indent_str}{json.dumps(schema, indent=2)}")
        
        return "\n".join(lines)
