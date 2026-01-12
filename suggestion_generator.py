"""
Suggestion Generator Service - Phase 0D
Generates suggestions for:
- Prerequisite configurations
- Field mappings
- Execution order
"""
from typing import Dict, List, Optional, Any, Set
from dependency_analyzer import DependencyAnalyzer


class SuggestionGenerator:
    """Generates suggestions for API requirements based on dependencies"""
    
    def __init__(self):
        self.dependency_analyzer = DependencyAnalyzer()
        self.dependencies = []
        self.suggestions = []
    
    def generate_suggestions(
        self, endpoints: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate all suggestions for endpoints
        
        Args:
            endpoints: List of parsed endpoint dictionaries
            
        Returns:
            Dictionary containing:
            - prerequisite_configs: List of prerequisite configurations
            - field_mappings: List of field mappings
            - execution_order: Ordered list of endpoints
        """
        # Step 1: Analyze dependencies
        self.dependencies = self.dependency_analyzer.analyze(endpoints)
        
        # Step 2: Generate prerequisite configs
        prerequisite_configs = self._generate_prerequisite_configs(endpoints)
        
        # Step 3: Generate field mappings
        field_mappings = self._generate_field_mappings(endpoints)
        
        # Step 4: Calculate execution order
        execution_order = self._calculate_execution_order(endpoints)
        
        return {
            'prerequisite_configs': prerequisite_configs,
            'field_mappings': field_mappings,
            'execution_order': execution_order,
            'dependencies': self.dependencies
        }
    
    def _generate_prerequisite_configs(
        self, endpoints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate prerequisite configurations for each endpoint"""
        prerequisite_configs = []
        
        # Group dependencies by source endpoint
        deps_by_source = {}
        for dep in self.dependencies:
            source = dep['source_endpoint']
            if source not in deps_by_source:
                deps_by_source[source] = []
            deps_by_source[source].append(dep)
        
        # Generate config for each endpoint
        for endpoint in endpoints:
            endpoint_key = f"{endpoint.get('method')} {endpoint.get('endpoint')}"
            endpoint_deps = deps_by_source.get(endpoint_key, [])
            
            if endpoint_deps:
                # Build prerequisite list
                prerequisites = []
                for dep in endpoint_deps:
                    prerequisites.append({
                        'endpoint': dep['target_endpoint'],
                        'method': self._extract_method(dep['target_endpoint']),
                        'path': self._extract_path(dep['target_endpoint']),
                        'dependency_type': dep['dependency_type'],
                        'confidence': dep['confidence'],
                        'reason': dep.get('reason', '')
                    })
                
                prerequisite_configs.append({
                    'endpoint': endpoint_key,
                    'method': endpoint.get('method'),
                    'path': endpoint.get('endpoint'),
                    'prerequisites': prerequisites,
                    'requires_prerequisites': len(prerequisites) > 0
                })
            else:
                # No prerequisites
                prerequisite_configs.append({
                    'endpoint': endpoint_key,
                    'method': endpoint.get('method'),
                    'path': endpoint.get('endpoint'),
                    'prerequisites': [],
                    'requires_prerequisites': False
                })
        
        return prerequisite_configs
    
    def _generate_field_mappings(
        self, endpoints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate field mappings between dependent endpoints"""
        field_mappings = []
        
        for dep in self.dependencies:
            source_endpoint = self._find_endpoint_by_key(dep['source_endpoint'], endpoints)
            target_endpoint = self._find_endpoint_by_key(dep['target_endpoint'], endpoints)
            
            if source_endpoint and target_endpoint:
                # Extract fields from target endpoint response
                target_response_fields = self._extract_response_fields(target_endpoint)
                # Map to source endpoint payload fields
                source_payload_fields = self._extract_payload_fields(source_endpoint)
                
                # Create mappings
                mappings = self._create_field_mappings(
                    target_response_fields,
                    source_payload_fields,
                    dep
                )
                
                if mappings:
                    field_mappings.append({
                        'source_endpoint': dep['source_endpoint'],
                        'target_endpoint': dep['target_endpoint'],
                        'mappings': mappings,
                        'dependency_type': dep['dependency_type']
                    })
        
        return field_mappings
    
    def _calculate_execution_order(
        self, endpoints: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Calculate optimal execution order based on dependencies"""
        # Build dependency graph
        endpoint_keys = {f"{ep.get('method')} {ep.get('endpoint')}": ep for ep in endpoints}
        
        # Topological sort to determine execution order
        ordered_endpoints = []
        visited = set()
        visiting = set()
        
        def visit(endpoint_key: str):
            if endpoint_key in visiting:
                # Circular dependency detected
                return
            if endpoint_key in visited:
                return
            
            visiting.add(endpoint_key)
            
            # Visit all prerequisites first
            for dep in self.dependencies:
                if dep['source_endpoint'] == endpoint_key:
                    visit(dep['target_endpoint'])
            
            visiting.remove(endpoint_key)
            visited.add(endpoint_key)
            
            if endpoint_key in endpoint_keys:
                ordered_endpoints.append({
                    'endpoint': endpoint_key,
                    'method': endpoint_keys[endpoint_key].get('method'),
                    'path': endpoint_keys[endpoint_key].get('endpoint'),
                    'order': len(ordered_endpoints) + 1
                })
        
        # Visit all endpoints
        for endpoint_key in endpoint_keys:
            if endpoint_key not in visited:
                visit(endpoint_key)
        
        # Add endpoints without dependencies at the end if not already included
        for endpoint in endpoints:
            endpoint_key = f"{endpoint.get('method')} {endpoint.get('endpoint')}"
            if endpoint_key not in visited:
                ordered_endpoints.append({
                    'endpoint': endpoint_key,
                    'method': endpoint.get('method'),
                    'path': endpoint.get('endpoint'),
                    'order': len(ordered_endpoints) + 1
                })
        
        return ordered_endpoints
    
    def _extract_method(self, endpoint_key: str) -> str:
        """Extract HTTP method from endpoint key"""
        parts = endpoint_key.split(' ', 1)
        return parts[0] if parts else ''
    
    def _extract_path(self, endpoint_key: str) -> str:
        """Extract path from endpoint key"""
        parts = endpoint_key.split(' ', 1)
        return parts[1] if len(parts) > 1 else ''
    
    def _find_endpoint_by_key(
        self, endpoint_key: str, endpoints: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Find endpoint by its key (method + path)"""
        for ep in endpoints:
            ep_key = f"{ep.get('method')} {ep.get('endpoint')}"
            if ep_key == endpoint_key:
                return ep
        return None
    
    def _extract_response_fields(self, endpoint: Dict[str, Any]) -> List[str]:
        """Extract field names from response schema"""
        fields = []
        response_schema = endpoint.get('response_schema', '')
        
        # Simple extraction: look for field patterns in schema text
        import re
        # Pattern: field names followed by type (e.g., "id (optional): integer")
        pattern = r'-\s+(\w+)\s*\([^)]+\):'
        matches = re.findall(pattern, response_schema)
        fields.extend(matches)
        
        return list(set(fields))  # Remove duplicates
    
    def _extract_payload_fields(self, endpoint: Dict[str, Any]) -> List[str]:
        """Extract field names from payload schema"""
        fields = []
        payload_schema = endpoint.get('payload_schema', '')
        
        # Simple extraction: look for field patterns in schema text
        import re
        # Pattern: field names followed by type
        pattern = r'-\s+(\w+)\s*\([^)]+\):'
        matches = re.findall(pattern, payload_schema)
        fields.extend(matches)
        
        return list(set(fields))  # Remove duplicates
    
    def _create_field_mappings(
        self, 
        target_fields: List[str],
        source_fields: List[str],
        dependency: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Create field mappings between target and source"""
        mappings = []
        
        # Match fields by name similarity
        for target_field in target_fields:
            # Look for exact match
            if target_field in source_fields:
                mappings.append({
                    'from_field': target_field,
                    'to_field': target_field,
                    'mapping_type': 'exact',
                    'confidence': 'high'
                })
            else:
                # Look for similar fields (e.g., userId -> user_id)
                for source_field in source_fields:
                    if self._fields_match(target_field, source_field):
                        mappings.append({
                            'from_field': target_field,
                            'to_field': source_field,
                            'mapping_type': 'similar',
                            'confidence': 'medium'
                        })
                        break
        
        return mappings
    
    def _fields_match(self, field1: str, field2: str) -> bool:
        """Check if two field names match (case-insensitive, ignoring underscores)"""
        f1_normalized = field1.lower().replace('_', '').replace('-', '')
        f2_normalized = field2.lower().replace('_', '').replace('-', '')
        return f1_normalized == f2_normalized


