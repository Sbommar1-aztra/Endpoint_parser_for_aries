"""
Request & Response Schema Validation - Task 7
Validates API request payloads and responses against OpenAPI schemas
"""
import json
from typing import Dict, List, Optional, Any, Tuple
from models import OpenAPIEndpoint
import re
from datetime import datetime


class SchemaValidator:
    """
    Schema Validator - Task 7
    Validates request payloads and responses against OpenAPI schemas
    """
    
    def __init__(self):
        self.errors = []
        self.warnings = []
    
    def validate_request_payload(
        self,
        payload: Dict[str, Any],
        endpoint: OpenAPIEndpoint
    ) -> Dict[str, Any]:
        """
        Validate request payload against request schema
        
        Args:
            payload: Request payload dictionary
            endpoint: OpenAPIEndpoint object with request schema
            
        Returns:
            Validation result dictionary
        """
        self.errors = []
        self.warnings = []
        
        request_schema = endpoint.get_request_schema()
        if not request_schema:
            return {
                'valid': True,
                'errors': [],
                'warnings': ['No request schema defined for this endpoint'],
                'coverage_percentage': 0.0
            }
        
        # Validate structure
        self._validate_structure(payload, request_schema, '')
        
        # Calculate coverage
        coverage = self._calculate_coverage(payload, request_schema)
        
        # Identify missing required fields
        missing_required = self._find_missing_required(payload, request_schema)
        
        # Identify extra fields
        extra_fields = self._find_extra_fields(payload, request_schema)
        
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings + extra_fields,
            'coverage_percentage': coverage,
            'missing_required_fields': missing_required,
            'extra_fields': extra_fields,
            'suggestions': self._generate_suggestions()
        }
    
    def validate_response(
        self,
        response_body: Dict[str, Any],
        status_code: str,
        endpoint: OpenAPIEndpoint
    ) -> Dict[str, Any]:
        """
        Validate response against response schema
        
        Args:
            response_body: Response body dictionary
            status_code: HTTP status code (e.g., '200', '201')
            endpoint: OpenAPIEndpoint object with response schema
            
        Returns:
            Validation result dictionary
        """
        self.errors = []
        self.warnings = []
        
        response_schema = endpoint.get_response_schema(status_code)
        if not response_schema:
            return {
                'valid': True,
                'errors': [],
                'warnings': [f'No response schema defined for status code {status_code}'],
                'compliance_percentage': 0.0
            }
        
        # Validate structure
        self._validate_structure(response_body, response_schema, '')
        
        # Calculate compliance
        compliance = self._calculate_coverage(response_body, response_schema)
        
        # Validate required fields
        missing_required = self._find_missing_required(response_body, response_schema)
        
        return {
            'valid': len(self.errors) == 0,
            'errors': self.errors,
            'warnings': self.warnings,
            'compliance_percentage': compliance,
            'missing_required_fields': missing_required
        }
    
    def _validate_structure(
        self,
        data: Any,
        schema: Dict,
        path: str
    ) -> None:
        """Recursively validate data structure against schema"""
        schema_type = schema.get('type')
        
        if schema_type == 'object':
            if not isinstance(data, dict):
                self.errors.append(f"{path}: Expected object, got {type(data).__name__}")
                return
            
            # Validate properties
            properties = schema.get('properties', {})
            for prop_name, prop_schema in properties.items():
                prop_path = f"{path}.{prop_name}" if path else prop_name
                
                if prop_name in data:
                    self._validate_field(data[prop_name], prop_schema, prop_path)
                elif prop_name in schema.get('required', []):
                    self.errors.append(f"{prop_path}: Required field is missing")
        
        elif schema_type == 'array':
            if not isinstance(data, list):
                self.errors.append(f"{path}: Expected array, got {type(data).__name__}")
                return
            
            items_schema = schema.get('items', {})
            min_items = schema.get('minItems')
            max_items = schema.get('maxItems')
            
            if min_items is not None and len(data) < min_items:
                self.errors.append(f"{path}: Array has {len(data)} items, minimum is {min_items}")
            
            if max_items is not None and len(data) > max_items:
                self.errors.append(f"{path}: Array has {len(data)} items, maximum is {max_items}")
            
            # Validate array items
            for i, item in enumerate(data):
                item_path = f"{path}[{i}]"
                self._validate_structure(item, items_schema, item_path)
        
        else:
            self._validate_field(data, schema, path)
    
    def _validate_field(
        self,
        value: Any,
        field_schema: Dict,
        path: str
    ) -> None:
        """Validate a single field"""
        field_type = field_schema.get('type')
        
        # Type validation
        if not self._validate_type(value, field_type):
            self.errors.append(
                f"{path}: Expected type {field_type}, got {type(value).__name__}"
            )
            return
        
        # Format validation
        if field_type == 'string':
            self._validate_string(value, field_schema, path)
        elif field_type == 'number' or field_type == 'integer':
            self._validate_number(value, field_schema, path)
        elif field_type == 'object':
            self._validate_structure(value, field_schema, path)
        elif field_type == 'array':
            self._validate_structure(value, field_schema, path)
    
    def _validate_type(self, value: Any, expected_type: str) -> bool:
        """Validate value type"""
        type_map = {
            'string': str,
            'integer': int,
            'number': float,
            'boolean': bool,
            'object': dict,
            'array': list
        }
        
        if expected_type not in type_map:
            return True  # Unknown type, skip validation
        
        expected_python_type = type_map[expected_type]
        
        # Special case: integer can be a number
        if expected_type == 'integer' and isinstance(value, (int, float)):
            return value == int(value)  # Check if it's a whole number
        
        return isinstance(value, expected_python_type)
    
    def _validate_string(
        self,
        value: str,
        field_schema: Dict,
        path: str
    ) -> None:
        """Validate string field constraints"""
        if not isinstance(value, str):
            return
        
        # Length constraints
        min_length = field_schema.get('minLength')
        max_length = field_schema.get('maxLength')
        
        if min_length is not None and len(value) < min_length:
            self.errors.append(
                f"{path}: String length {len(value)} is less than minimum {min_length}"
            )
        
        if max_length is not None and len(value) > max_length:
            self.errors.append(
                f"{path}: String length {len(value)} exceeds maximum {max_length}"
            )
        
        # Pattern validation
        pattern = field_schema.get('pattern')
        if pattern:
            if not re.match(pattern, value):
                self.errors.append(
                    f"{path}: String does not match required pattern {pattern}"
                )
        
        # Enum validation
        enum_values = field_schema.get('enum')
        if enum_values and value not in enum_values:
            self.errors.append(
                f"{path}: Value '{value}' is not in allowed enum values {enum_values}"
            )
        
        # Format validation
        field_format = field_schema.get('format')
        if field_format:
            if not self._validate_format(value, field_format):
                self.errors.append(
                    f"{path}: Value does not match format {field_format}"
                )
    
    def _validate_number(
        self,
        value: float,
        field_schema: Dict,
        path: str
    ) -> None:
        """Validate number/integer field constraints"""
        # Minimum/Maximum
        minimum = field_schema.get('minimum')
        maximum = field_schema.get('maximum')
        exclusive_minimum = field_schema.get('exclusiveMinimum', False)
        exclusive_maximum = field_schema.get('exclusiveMaximum', False)
        
        if minimum is not None:
            if exclusive_minimum:
                if value <= minimum:
                    self.errors.append(
                        f"{path}: Value {value} must be greater than {minimum}"
                    )
            else:
                if value < minimum:
                    self.errors.append(
                        f"{path}: Value {value} is less than minimum {minimum}"
                    )
        
        if maximum is not None:
            if exclusive_maximum:
                if value >= maximum:
                    self.errors.append(
                        f"{path}: Value {value} must be less than {maximum}"
                    )
            else:
                if value > maximum:
                    self.errors.append(
                        f"{path}: Value {value} exceeds maximum {maximum}"
                    )
    
    def _validate_format(self, value: str, format_type: str) -> bool:
        """Validate string format"""
        if format_type == 'email':
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            return bool(re.match(email_pattern, value))
        elif format_type == 'date':
            try:
                datetime.strptime(value, '%Y-%m-%d')
                return True
            except:
                return False
        elif format_type == 'date-time':
            # ISO 8601 format
            iso_pattern = r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$'
            return bool(re.match(iso_pattern, value))
        elif format_type == 'uri':
            uri_pattern = r'^https?://'
            return bool(re.match(uri_pattern, value))
        elif format_type == 'uuid':
            uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
            return bool(re.match(uuid_pattern, value, re.IGNORECASE))
        
        return True  # Unknown format, skip validation
    
    def _calculate_coverage(
        self,
        data: Dict[str, Any],
        schema: Dict
    ) -> float:
        """Calculate field coverage percentage"""
        if not isinstance(data, dict):
            return 0.0
        
        properties = schema.get('properties', {})
        if not properties:
            return 100.0  # No properties to validate
        
        matched_fields = 0
        total_fields = len(properties)
        
        for field_name in properties.keys():
            if field_name in data:
                matched_fields += 1
        
        return (matched_fields / total_fields * 100) if total_fields > 0 else 0.0
    
    def _find_missing_required(
        self,
        data: Dict[str, Any],
        schema: Dict
    ) -> List[str]:
        """Find missing required fields"""
        if not isinstance(data, dict):
            return []
        
        required_fields = schema.get('required', [])
        missing = []
        
        for field in required_fields:
            if field not in data:
                missing.append(field)
        
        return missing
    
    def _find_extra_fields(
        self,
        data: Dict[str, Any],
        schema: Dict
    ) -> List[str]:
        """Find fields in data that are not in schema"""
        if not isinstance(data, dict):
            return []
        
        properties = schema.get('properties', {})
        extra = []
        
        for field_name in data.keys():
            if field_name not in properties:
                extra.append(field_name)
        
        return [f"Extra field: {field}" for field in extra]
    
    def _generate_suggestions(self) -> List[str]:
        """Generate validation suggestions"""
        suggestions = []
        
        for error in self.errors:
            if 'Required field is missing' in error:
                field_path = error.split(':')[0]
                suggestions.append(f"Add required field: {field_path}")
            elif 'Expected type' in error:
                suggestions.append(f"Fix type mismatch: {error}")
            elif 'does not match pattern' in error:
                suggestions.append(f"Update value to match required pattern: {error}")
            elif 'not in allowed enum' in error:
                suggestions.append(f"Use one of the allowed enum values: {error}")
        
        return suggestions
