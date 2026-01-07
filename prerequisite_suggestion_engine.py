"""
Prerequisite Suggestion Engine - Task 4
Automatically generates prerequisite configurations and field mapping suggestions
"""
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
import re


class PrerequisiteSuggestionEngine:
    """
    Prerequisite Suggestion Engine - Task 4
    Generates prerequisite configurations and field mappings based on detected dependencies
    """
    
    def __init__(self):
        self.dependencies = []
        self.endpoints = []
        self.endpoint_by_id = {}
    
    def generate_suggestions(
        self,
        endpoints: List[Dict[str, Any]],
        dependencies: List[Dict[str, Any]],
        api_requirement_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Generate prerequisite suggestions for endpoints
        
        Args:
            endpoints: List of endpoint dictionaries or database objects
            dependencies: List of detected field dependencies
            api_requirement_id: Optional API requirement ID to associate with
            
        Returns:
            List of suggestion dictionaries
        """
        self.endpoints = endpoints
        self.dependencies = dependencies
        self.endpoint_by_id = {ep.get('id') if isinstance(ep, dict) else ep.id: ep for ep in endpoints}
        
        suggestions = []
        
        # Group dependencies by source endpoint
        deps_by_endpoint = {}
        for dep in dependencies:
            source_id = dep.get('source_endpoint_id')
            if source_id not in deps_by_endpoint:
                deps_by_endpoint[source_id] = []
            deps_by_endpoint[source_id].append(dep)
        
        # Generate suggestions for each endpoint with dependencies
        for endpoint_id, endpoint_deps in deps_by_endpoint.items():
            endpoint = self.endpoint_by_id.get(endpoint_id)
            if not endpoint:
                continue
            
            suggestion = self._generate_endpoint_suggestion(
                endpoint, endpoint_deps, api_requirement_id
            )
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    def _generate_endpoint_suggestion(
        self,
        endpoint: Any,
        dependencies: List[Dict],
        api_requirement_id: Optional[int]
    ) -> Optional[Dict[str, Any]]:
        """Generate suggestion for a single endpoint"""
        
        # Build prerequisite configurations
        prerequisites = []
        field_mappings = {}
        confidence_scores = []
        
        # Get endpoint request schema
        if isinstance(endpoint, dict):
            request_schema_json = endpoint.get('request_schema_json')
            endpoint_id = endpoint.get('id')
        else:
            request_schema_json = endpoint.request_schema_json
            endpoint_id = endpoint.id
        
        request_schema = None
        if request_schema_json:
            try:
                request_schema = json.loads(request_schema_json) if isinstance(request_schema_json, str) else request_schema_json
            except:
                pass
        
        for dep in dependencies:
            target_endpoint_id = dep.get('target_endpoint_id')
            target_endpoint = self.endpoint_by_id.get(target_endpoint_id)
            
            if not target_endpoint:
                continue
            
            # Build prerequisite configuration
            prereq_config = self._build_prerequisite_config(dep, target_endpoint)
            prerequisites.append(prereq_config)
            
            # Build field mapping
            source_field = dep.get('source_field_name')
            response_path = dep.get('response_path', '$.id')
            
            if source_field:
                field_mappings[source_field] = {
                    'source_type': 'prerequisite',
                    'prerequisite_endpoint_id': target_endpoint_id,
                    'response_path': response_path,
                    'dependency_id': dep.get('id')
                }
            
            confidence_scores.append(dep.get('confidence_score', 0.0))
        
        # Process other fields (non-FK fields)
        if request_schema:
            other_field_mappings = self._build_other_field_mappings(
                request_schema, field_mappings
            )
            field_mappings.update(other_field_mappings)
        
        # Calculate overall confidence
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0
        
        # Calculate execution order
        execution_order = self._calculate_execution_order(dependencies)
        
        return {
            'api_requirement_id': api_requirement_id,
            'endpoint_id': endpoint_id,
            'suggested_prerequisites': json.dumps(prerequisites),
            'suggested_field_mappings': json.dumps(field_mappings),
            'execution_order': execution_order,
            'confidence_score': avg_confidence,
            'user_reviewed': False,
            'user_approved': False
        }
    
    def _build_prerequisite_config(
        self, dependency: Dict, target_endpoint: Any
    ) -> Dict[str, Any]:
        """Build prerequisite configuration"""
        
        if isinstance(target_endpoint, dict):
            target_path = target_endpoint.get('path', '')
            target_method = target_endpoint.get('method', '')
        else:
            target_path = target_endpoint.path
            target_method = target_endpoint.method
        
        # Determine caching strategy
        should_cache = self._should_cache(target_endpoint)
        cache_duration = 3600 if should_cache else 0  # 1 hour default for cacheable
        
        # Build description
        description = f"Required for {dependency.get('source_field_name')} field"
        
        return {
            'endpoint': target_path,
            'method': target_method,
            'execute_per_test': True,  # Default to executing per test
            'cache_response': should_cache,
            'cache_duration': cache_duration,
            'description': description,
            'dependency_id': dependency.get('id'),
            'confidence': dependency.get('confidence_score', 0.0)
        }
    
    def _should_cache(self, endpoint: Any) -> bool:
        """
        Determine if endpoint response should be cached
        Cache static data (products, categories), don't cache user-specific data
        """
        if isinstance(endpoint, dict):
            path = (endpoint.get('path') or '').lower()
            tags = (endpoint.get('tags') or '').lower()
        else:
            path = (endpoint.path or '').lower()
            tags = (endpoint.tags or '').lower()
        
        # Cache static/reference data
        cacheable_patterns = [
            r'/products',
            r'/categories',
            r'/countries',
            r'/states',
            r'/currencies',
            r'/languages',
            r'/reference',
            r'/lookup',
            r'/enums'
        ]
        
        # Don't cache user-specific data
        non_cacheable_patterns = [
            r'/users',
            r'/auth',
            r'/login',
            r'/logout',
            r'/sessions',
            r'/orders',
            r'/cart',
            r'/profile'
        ]
        
        # Check non-cacheable first (higher priority)
        for pattern in non_cacheable_patterns:
            if re.search(pattern, path) or re.search(pattern, tags):
                return False
        
        # Check cacheable
        for pattern in cacheable_patterns:
            if re.search(pattern, path) or re.search(pattern, tags):
                return True
        
        # Default: don't cache (safer for dynamic data)
        return False
    
    def _build_other_field_mappings(
        self, request_schema: Dict, existing_mappings: Dict
    ) -> Dict[str, Any]:
        """Build field mappings for non-FK fields"""
        mappings = {}
        properties = request_schema.get('properties', {})
        required_fields = request_schema.get('required', [])
        
        for field_name, field_schema in properties.items():
            # Skip if already mapped
            if field_name in existing_mappings:
                continue
            
            if not isinstance(field_schema, dict):
                continue
            
            field_type = field_schema.get('type', 'string')
            field_format = field_schema.get('format')
            description = field_schema.get('description', '').lower()
            
            # Check for timestamp fields
            if (field_type == 'string' and 
                (field_format in ['date-time', 'date', 'datetime'] or
                 'timestamp' in description or
                 'datetime' in description or
                 'date' in field_name.lower())):
                
                mappings[field_name] = {
                    'source_type': 'generated',
                    'generation_type': 'timestamp',
                    'format': 'ISO8601',
                    'required': field_name in required_fields
                }
            
            # Check for other fields that need LLM generation
            else:
                # Build constraints string for LLM
                constraints = self._build_constraints(field_schema)
                
                mappings[field_name] = {
                    'source_type': 'llm_generated',
                    'constraints': constraints,
                    'required': field_name in required_fields,
                    'type': field_type,
                    'format': field_format
                }
        
        return mappings
    
    def _build_constraints(self, field_schema: Dict) -> str:
        """Build constraint string for LLM generation"""
        constraints = []
        
        field_type = field_schema.get('type', 'string')
        constraints.append(f"type: {field_type}")
        
        if 'minimum' in field_schema:
            constraints.append(f"minimum: {field_schema['minimum']}")
        if 'maximum' in field_schema:
            constraints.append(f"maximum: {field_schema['maximum']}")
        if 'minLength' in field_schema:
            constraints.append(f"minLength: {field_schema['minLength']}")
        if 'maxLength' in field_schema:
            constraints.append(f"maxLength: {field_schema['maxLength']}")
        if 'pattern' in field_schema:
            constraints.append(f"pattern: {field_schema['pattern']}")
        if 'enum' in field_schema:
            enum_values = ', '.join(str(v) for v in field_schema['enum'])
            constraints.append(f"enum: [{enum_values}]")
        if 'format' in field_schema:
            constraints.append(f"format: {field_schema['format']}")
        
        description = field_schema.get('description')
        if description:
            constraints.append(f"description: {description}")
        
        return '; '.join(constraints)
    
    def _calculate_execution_order(self, dependencies: List[Dict]) -> int:
        """
        Calculate execution order based on dependency depth
        Higher order = deeper in dependency chain
        """
        # Simple implementation: count dependencies
        # More sophisticated implementation would use topological sort
        return len(dependencies)
