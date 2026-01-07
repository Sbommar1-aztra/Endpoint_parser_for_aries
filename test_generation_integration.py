"""
Test Generation Integration - Task 10
Integrates OpenAPI-derived prerequisites and field mappings into test generation workflow
"""
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from models import PrerequisiteSuggestion, OpenAPIEndpoint
import re


class TestGenerationIntegration:
    """
    Test Generation Integration - Task 10
    Uses prerequisite configurations and field mappings for test generation
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def generate_test_config(
        self,
        api_requirement_id: int,
        endpoint_id: int
    ) -> Dict[str, Any]:
        """
        Generate test configuration using prerequisites and field mappings
        
        Args:
            api_requirement_id: API requirement ID
            endpoint_id: OpenAPI endpoint ID
            
        Returns:
            Test configuration dictionary
        """
        # Get prerequisite suggestion
        suggestion = self.db.query(PrerequisiteSuggestion).filter(
            PrerequisiteSuggestion.api_requirement_id == api_requirement_id,
            PrerequisiteSuggestion.endpoint_id == endpoint_id
        ).first()
        
        if not suggestion:
            return {
                'has_prerequisites': False,
                'message': 'No prerequisite suggestions found for this endpoint'
            }
        
        # Get endpoint
        endpoint = self.db.query(OpenAPIEndpoint).filter(
            OpenAPIEndpoint.id == endpoint_id
        ).first()
        
        if not endpoint:
            return {
                'success': False,
                'error': 'Endpoint not found'
            }
        
        # Parse prerequisites and field mappings
        prerequisites = suggestion.get_prerequisites()
        field_mappings = suggestion.get_field_mappings()
        
        # Build test configuration
        test_config = {
            'api_requirement_id': api_requirement_id,
            'endpoint_id': endpoint_id,
            'endpoint_path': endpoint.path,
            'method': endpoint.method,
            'execution_order': suggestion.execution_order,
            'prerequisites': self._build_prerequisite_configs(prerequisites),
            'field_mappings': field_mappings,
            'test_payload_template': self._build_payload_template(endpoint, field_mappings)
        }
        
        return test_config
    
    def execute_prerequisites(
        self,
        prerequisites: List[Dict[str, Any]],
        cache_store: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Execute prerequisites based on execution order and caching strategy
        
        Args:
            prerequisites: List of prerequisite configurations
            cache_store: Optional cache store for responses
            
        Returns:
            Dictionary with prerequisite responses
        """
        if cache_store is None:
            cache_store = {}
        
        responses = {}
        
        # Sort by execution order if available
        sorted_prereqs = sorted(
            prerequisites,
            key=lambda p: p.get('execution_order', 0)
        )
        
        for prereq in sorted_prereqs:
            endpoint_key = f"{prereq['method']} {prereq['endpoint']}"
            
            # Check cache
            if prereq.get('cache_response') and endpoint_key in cache_store:
                cache_entry = cache_store[endpoint_key]
                cache_time = cache_entry.get('cached_at', 0)
                cache_duration = prereq.get('cache_duration', 0)
                
                # Check if cache is still valid
                if cache_time + cache_duration > datetime.utcnow().timestamp():
                    responses[endpoint_key] = cache_entry['response']
                    continue
            
            # Execute prerequisite (mock implementation)
            # In real implementation, this would make actual API calls
            response = self._execute_prerequisite_request(prereq)
            
            # Store in cache if configured
            if prereq.get('cache_response'):
                cache_store[endpoint_key] = {
                    'response': response,
                    'cached_at': datetime.utcnow().timestamp()
                }
            
            responses[endpoint_key] = response
        
        return responses
    
    def apply_field_mappings(
        self,
        template: Dict[str, Any],
        field_mappings: Dict[str, Any],
        prerequisite_responses: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply field mappings to populate test request payload
        
        Args:
            template: Template payload
            field_mappings: Field mapping configuration
            prerequisite_responses: Responses from prerequisite execution
            
        Returns:
            Populated payload dictionary
        """
        payload = template.copy()
        
        for field_name, mapping in field_mappings.items():
            source_type = mapping.get('source_type')
            
            if source_type == 'prerequisite':
                # Extract value from prerequisite response using JSONPath
                prerequisite_endpoint_id = mapping.get('prerequisite_endpoint_id')
                response_path = mapping.get('response_path', '$.id')
                
                # Find prerequisite response
                response = self._find_prerequisite_response(
                    prerequisite_endpoint_id,
                    prerequisite_responses
                )
                
                if response:
                    value = self._extract_value_from_response(response, response_path)
                    if value is not None:
                        payload[field_name] = value
            
            elif source_type == 'generated':
                # Generate value based on type
                generation_type = mapping.get('generation_type')
                
                if generation_type == 'timestamp':
                    format_type = mapping.get('format', 'ISO8601')
                    payload[field_name] = self._generate_timestamp(format_type)
            
            elif source_type == 'llm_generated':
                # Mark for LLM generation with constraints
                constraints = mapping.get('constraints', '')
                # In real implementation, this would call LLM
                # For now, generate a placeholder
                payload[field_name] = f"[LLM_GENERATED: {constraints}]"
        
        return payload
    
    def generate_test_variations(
        self,
        base_config: Dict[str, Any],
        variations_count: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Generate multiple test variations with different field value combinations
        
        Args:
            base_config: Base test configuration
            variations_count: Number of variations to generate
            
        Returns:
            List of test variation configurations
        """
        variations = []
        
        field_mappings = base_config.get('field_mappings', {})
        
        # Identify fields that can be varied
        variable_fields = {
            name: mapping
            for name, mapping in field_mappings.items()
            if mapping.get('source_type') == 'llm_generated'
        }
        
        # Generate variations
        for i in range(variations_count):
            variation = base_config.copy()
            variation['variation_index'] = i
            
            # Modify variable fields
            for field_name, mapping in variable_fields.items():
                constraints = mapping.get('constraints', '')
                # Generate different values based on constraints
                variation['test_payload_template'][field_name] = \
                    self._generate_variant_value(field_name, mapping, i)
            
            variations.append(variation)
        
        return variations
    
    def _build_prerequisite_configs(
        self,
        prerequisites: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build prerequisite configurations for test execution"""
        configs = []
        
        for idx, prereq in enumerate(prerequisites):
            configs.append({
                'order': idx + 1,
                'endpoint': prereq.get('endpoint'),
                'method': prereq.get('method'),
                'execute_per_test': prereq.get('execute_per_test', True),
                'cache_response': prereq.get('cache_response', False),
                'cache_duration': prereq.get('cache_duration', 0),
                'description': prereq.get('description', '')
            })
        
        return configs
    
    def _build_payload_template(
        self,
        endpoint: OpenAPIEndpoint,
        field_mappings: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build payload template from endpoint schema and field mappings"""
        request_schema = endpoint.get_request_schema()
        
        if not request_schema:
            return {}
        
        template = {}
        properties = request_schema.get('properties', {})
        
        for field_name, field_schema in properties.items():
            # Check if there's a mapping for this field
            if field_name in field_mappings:
                mapping = field_mappings[field_name]
                
                if mapping.get('source_type') == 'prerequisite':
                    template[field_name] = '[FROM_PREREQUISITE]'
                elif mapping.get('source_type') == 'generated':
                    template[field_name] = '[GENERATED]'
                elif mapping.get('source_type') == 'llm_generated':
                    template[field_name] = '[LLM_GENERATED]'
            else:
                # Default value based on type
                field_type = field_schema.get('type', 'string')
                template[field_name] = self._get_default_value(field_type, field_schema)
        
        return template
    
    def _execute_prerequisite_request(self, prereq: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a prerequisite API request (mock implementation)"""
        # In real implementation, this would make an actual HTTP request
        return {
            'id': 123,
            'status': 'success',
            'data': {
                'id': 123,
                'created_at': datetime.utcnow().isoformat()
            }
        }
    
    def _find_prerequisite_response(
        self,
        endpoint_id: int,
        responses: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Find prerequisite response by endpoint ID"""
        # In real implementation, this would match by endpoint ID
        # For now, return first response
        if responses:
            return list(responses.values())[0]
        return None
    
    def _extract_value_from_response(
        self,
        response: Dict[str, Any],
        jsonpath: str
    ) -> Any:
        """Extract value from response using JSONPath expression"""
        # Simple JSONPath implementation (supports $.field and $.nested.field)
        if jsonpath.startswith('$.'):
            path_parts = jsonpath[2:].split('.')
            current = response
            
            for part in path_parts:
                if isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None
            
            return current
        
        return None
    
    def _generate_timestamp(self, format_type: str) -> str:
        """Generate timestamp in specified format"""
        if format_type == 'ISO8601':
            return datetime.utcnow().isoformat() + 'Z'
        return datetime.utcnow().isoformat()
    
    def _generate_variant_value(
        self,
        field_name: str,
        mapping: Dict[str, Any],
        variation_index: int
    ) -> Any:
        """Generate variant value for a field"""
        # Simple variation generation
        field_type = mapping.get('type', 'string')
        
        if field_type == 'string':
            return f"value_{variation_index}"
        elif field_type == 'integer':
            return 100 + variation_index
        elif field_type == 'number':
            return 100.0 + variation_index
        elif field_type == 'boolean':
            return variation_index % 2 == 0
        
        return f"variant_{variation_index}"
    
    def _get_default_value(self, field_type: str, field_schema: Dict) -> Any:
        """Get default value for a field based on type"""
        if field_type == 'string':
            return ''
        elif field_type == 'integer':
            return 0
        elif field_type == 'number':
            return 0.0
        elif field_type == 'boolean':
            return False
        elif field_type == 'array':
            return []
        elif field_type == 'object':
            return {}
        
        return None
