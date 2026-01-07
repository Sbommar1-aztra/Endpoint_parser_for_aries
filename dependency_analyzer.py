"""
Dependency Analyzer Service - Phase 0C
Analyzes dependencies between API endpoints to detect Foreign Key (FK) relationships
Uses three methods: explicit, naming, description
"""
from typing import Dict, List, Optional, Any, Set, Tuple
import re


class DependencyAnalyzer:
    """Analyzes dependencies between API endpoints"""
    
    def __init__(self):
        self.endpoints = []
        self.dependencies = []
    
    def analyze(self, endpoints: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analyze dependencies between endpoints
        
        Args:
            endpoints: List of parsed endpoint dictionaries
            
        Returns:
            List of dependency relationships found
        """
        self.endpoints = endpoints
        self.dependencies = []
        
        # Analyze each endpoint for dependencies
        for endpoint in endpoints:
            deps = self._analyze_endpoint_dependencies(endpoint)
            if deps:
                self.dependencies.extend(deps)
        
        return self.dependencies
    
    def _analyze_endpoint_dependencies(self, endpoint: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Analyze dependencies for a single endpoint"""
        dependencies = []
        
        endpoint_path = endpoint.get('endpoint', '') or ''
        endpoint_method = endpoint.get('method', '') or ''
        payload_schema = endpoint.get('payload_schema', '') or ''
        response_schema = endpoint.get('response_schema', '') or ''
        description = endpoint.get('description', '') or ''
        summary = endpoint.get('summary', '') or ''
        
        # Ensure all values are strings before combining
        payload_schema = str(payload_schema) if payload_schema else ''
        response_schema = str(response_schema) if response_schema else ''
        description = str(description) if description else ''
        summary = str(summary) if summary else ''
        
        # Combine all text for analysis
        all_text = f"{description} {summary} {payload_schema} {response_schema}".lower()
        
        # Method 1: Explicit dependencies (references in description/schema)
        explicit_deps = self._detect_explicit_dependencies(
            endpoint, all_text
        )
        dependencies.extend(explicit_deps)
        
        # Method 2: Naming conventions (e.g., userId, productId, orderId)
        naming_deps = self._detect_naming_dependencies(
            endpoint, endpoint_path, all_text
        )
        dependencies.extend(naming_deps)
        
        # Method 3: Description-based dependencies
        desc_deps = self._detect_description_dependencies(
            endpoint, description, summary
        )
        dependencies.extend(desc_deps)
        
        return dependencies
    
    def _detect_explicit_dependencies(
        self, endpoint: Dict[str, Any], text: str
    ) -> List[Dict[str, Any]]:
        """Method 1: Detect explicit references to other endpoints"""
        dependencies = []
        
        # Look for explicit references like "requires", "depends on", "needs"
        patterns = [
            r'requires?\s+(?:the\s+)?(?:endpoint|api|call)\s+(?:to\s+)?([A-Z]+\s+[^\s]+)',
            r'depends?\s+on\s+(?:the\s+)?(?:endpoint|api|call)\s+(?:to\s+)?([A-Z]+\s+[^\s]+)',
            r'needs?\s+(?:the\s+)?(?:endpoint|api|call)\s+(?:to\s+)?([A-Z]+\s+[^\s]+)',
            r'after\s+(?:the\s+)?(?:endpoint|api|call)\s+(?:to\s+)?([A-Z]+\s+[^\s]+)',
            r'following\s+(?:the\s+)?(?:endpoint|api|call)\s+(?:to\s+)?([A-Z]+\s+[^\s]+)',
        ]
        
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                referenced = match.group(1).strip()
                # Try to find the referenced endpoint
                target_endpoint = self._find_endpoint_by_reference(referenced)
                if target_endpoint:
                    dependencies.append({
                        'source_endpoint': f"{endpoint.get('method')} {endpoint.get('endpoint')}",
                        'target_endpoint': f"{target_endpoint.get('method')} {target_endpoint.get('endpoint')}",
                        'dependency_type': 'explicit',
                        'confidence': 'high',
                        'reason': f"Explicit reference found: {referenced}"
                    })
        
        return dependencies
    
    def _detect_naming_dependencies(
        self, endpoint: Dict[str, Any], path: str, text: str
    ) -> List[Dict[str, Any]]:
        """Method 2: Detect dependencies based on naming conventions"""
        dependencies = []
        
        # Extract entity IDs from path (e.g., /users/{userId}, /orders/{orderId})
        path_id_pattern = r'/\{(\w+Id)\}'
        path_ids = re.findall(path_id_pattern, path)
        
        # Extract IDs from text (e.g., userId, productId, orderId)
        id_pattern = r'\b(\w+Id)\b'
        text_ids = re.findall(id_pattern, text)
        
        all_ids = set(path_ids + text_ids)
        
        # For each ID found, look for endpoints that create/return that entity
        for entity_id in all_ids:
            # Skip if entity_id is None or not a string
            if not entity_id or not isinstance(entity_id, str):
                continue
            # Extract entity name (e.g., "user" from "userId")
            entity_name = entity_id.replace('Id', '').lower()
            
            # Find endpoints that might be prerequisites:
            # 1. POST endpoints that create the entity
            # 2. GET endpoints that return the entity
            potential_prereqs = self._find_entity_endpoints(entity_name, entity_id)
            
            for prereq in potential_prereqs:
                # Check if this endpoint uses the entity
                if self._endpoint_uses_entity(endpoint, entity_name, entity_id):
                    dependencies.append({
                        'source_endpoint': f"{endpoint.get('method')} {endpoint.get('endpoint')}",
                        'target_endpoint': f"{prereq.get('method')} {prereq.get('endpoint')}",
                        'dependency_type': 'naming',
                        'confidence': 'medium',
                        'reason': f"Uses {entity_id} which is created/returned by prerequisite endpoint",
                        'entity': entity_name,
                        'entity_id': entity_id
                    })
        
        return dependencies
    
    def _detect_description_dependencies(
        self, endpoint: Dict[str, Any], description: str, summary: str
    ) -> List[Dict[str, Any]]:
        """Method 3: Detect dependencies from descriptions"""
        dependencies = []
        
        # Ensure description and summary are strings
        description = str(description) if description else ''
        summary = str(summary) if summary else ''
        
        combined_text = f"{description} {summary}".lower()
        
        # Look for common dependency patterns in descriptions
        dependency_keywords = {
            'create': ['create', 'add', 'new', 'register'],
            'read': ['get', 'fetch', 'retrieve', 'find', 'list', 'show'],
            'update': ['update', 'modify', 'edit', 'change'],
            'delete': ['delete', 'remove', 'cancel']
        }
        
        # Check if this endpoint needs a created entity
        if any(keyword in combined_text for keyword in ['existing', 'created', 'previous']):
            # Look for entity mentions
            entity_patterns = [
                r'(?:existing|created|previous)\s+(\w+)',
                r'(\w+)\s+(?:must|should|needs?)\s+(?:be\s+)?(?:created|exists)',
            ]
            
            for pattern in entity_patterns:
                matches = re.finditer(pattern, combined_text, re.IGNORECASE)
                for match in matches:
                    entity = match.group(1).lower()
                    # Find POST endpoint that creates this entity
                    create_endpoint = self._find_create_endpoint(entity)
                    if create_endpoint:
                        dependencies.append({
                            'source_endpoint': f"{endpoint.get('method')} {endpoint.get('endpoint')}",
                            'target_endpoint': f"{create_endpoint.get('method')} {create_endpoint.get('endpoint')}",
                            'dependency_type': 'description',
                            'confidence': 'medium',
                            'reason': f"Description indicates need for existing {entity}",
                            'entity': entity
                        })
        
        return dependencies
    
    def _find_endpoint_by_reference(self, reference: str) -> Optional[Dict[str, Any]]:
        """Find endpoint based on a text reference"""
        if not reference:
            return None
        reference_lower = reference.lower()
        
        for ep in self.endpoints:
            # Check if reference matches method + endpoint
            method_endpoint = f"{ep.get('method')} {ep.get('endpoint')}".lower()
            if reference_lower in method_endpoint or method_endpoint in reference_lower:
                return ep
            
            # Check if reference matches summary or description
            summary = ep.get('summary', '').lower()
            description = ep.get('description', '').lower()
            if reference_lower in summary or reference_lower in description:
                return ep
        
        return None
    
    def _find_entity_endpoints(self, entity_name: str, entity_id: str) -> List[Dict[str, Any]]:
        """Find endpoints related to an entity"""
        related_endpoints = []
        
        for ep in self.endpoints:
            endpoint_path = ep.get('endpoint', '').lower()
            method = ep.get('method', '').upper()
            summary = ep.get('summary', '').lower()
            description = ep.get('description', '').lower()
            
            # Check if endpoint is related to the entity
            if (entity_name in endpoint_path or 
                entity_name in summary or 
                entity_name in description):
                
                # Prioritize POST (create) and GET (read) endpoints
                if method in ['POST', 'GET']:
                    related_endpoints.append(ep)
        
        return related_endpoints
    
    def _endpoint_uses_entity(
        self, endpoint: Dict[str, Any], entity_name: str, entity_id: str
    ) -> bool:
        """Check if endpoint uses a specific entity"""
        # Ensure entity_id and entity_name are strings before calling .lower()
        if not entity_id or not isinstance(entity_id, str):
            return False
        if not entity_name or not isinstance(entity_name, str):
            return False
            
        path = endpoint.get('endpoint', '').lower()
        payload = endpoint.get('payload_schema', '').lower()
        response = endpoint.get('response_schema', '').lower()
        description = endpoint.get('description', '').lower()
        
        # Check if entity is referenced in path, payload, response, or description
        return (entity_id.lower() in path or 
                entity_id.lower() in payload or 
                entity_id.lower() in response or
                entity_name in path or
                entity_name in description)
    
    def _find_create_endpoint(self, entity: str) -> Optional[Dict[str, Any]]:
        """Find POST endpoint that creates an entity"""
        for ep in self.endpoints:
            if ep.get('method', '').upper() == 'POST':
                endpoint_path = ep.get('endpoint', '').lower()
                summary = ep.get('summary', '').lower()
                description = ep.get('description', '').lower()
                
                if (entity in endpoint_path or 
                    'create' in summary or 
                    'create' in description or
                    'add' in summary or
                    'new' in summary):
                    return ep
        
        return None


