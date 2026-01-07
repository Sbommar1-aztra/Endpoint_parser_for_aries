"""
Contract Change Detection - Task 8
Detects when imported OpenAPI specifications are updated and identifies affected endpoints
"""
import json
from typing import Dict, List, Optional, Any, Set, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from models import OpenAPISpecification, OpenAPIEndpoint
from openapi_parser import OpenAPIParser


class ContractChangeDetector:
    """
    Contract Change Detector - Task 8
    Detects breaking and non-breaking changes in OpenAPI specifications
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def detect_changes(
        self,
        spec_id: int,
        new_spec_json: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect changes between existing specification and new version
        
        Args:
            spec_id: ID of existing specification
            new_spec_json: New specification JSON
            
        Returns:
            Dictionary with change detection results
        """
        # Get existing specification
        old_spec = self.db.query(OpenAPISpecification).filter(
            OpenAPISpecification.id == spec_id
        ).first()
        
        if not old_spec:
            return {
                'has_changes': False,
                'error': f'Specification {spec_id} not found'
            }
        
        old_spec_json = json.loads(old_spec.spec_json) if isinstance(old_spec.spec_json, str) else old_spec.spec_json
        
        # Get old endpoints
        old_endpoints = self.db.query(OpenAPIEndpoint).filter(
            OpenAPIEndpoint.spec_id == spec_id
        ).all()
        
        # Parse new specification
        parser = OpenAPIParser()
        parser.spec = new_spec_json
        parser.version = old_spec.spec_version
        if parser.version == '2.0':
            parser.definitions = new_spec_json.get('definitions', {})
        else:
            components = new_spec_json.get('components', {})
            parser.schemas = components.get('schemas', {})
        
        new_endpoints_data = parser.parse_endpoints()
        
        # Build endpoint maps
        old_endpoints_map = {
            (ep.path, ep.method): ep for ep in old_endpoints
        }
        new_endpoints_map = {
            (ep['path'], ep['method']): ep for ep in new_endpoints_data
        }
        
        # Detect changes
        breaking_changes = []
        non_breaking_changes = []
        removed_endpoints = []
        added_endpoints = []
        modified_endpoints = []
        
        # Check for removed endpoints
        for (path, method), old_ep in old_endpoints_map.items():
            if (path, method) not in new_endpoints_map:
                removed_endpoints.append({
                    'path': path,
                    'method': method,
                    'endpoint_id': old_ep.id
                })
                breaking_changes.append({
                    'type': 'endpoint_removed',
                    'severity': 'breaking',
                    'path': path,
                    'method': method,
                    'description': f'Endpoint {method} {path} was removed'
                })
        
        # Check for added endpoints
        for (path, method), new_ep in new_endpoints_map.items():
            if (path, method) not in old_endpoints_map:
                added_endpoints.append({
                    'path': path,
                    'method': method,
                    'operation_id': new_ep.get('operation_id')
                })
                non_breaking_changes.append({
                    'type': 'endpoint_added',
                    'severity': 'non-breaking',
                    'path': path,
                    'method': method,
                    'description': f'New endpoint {method} {path} was added'
                })
        
        # Check for modified endpoints
        for (path, method), new_ep in new_endpoints_map.items():
            if (path, method) in old_endpoints_map:
                old_ep = old_endpoints_map[(path, method)]
                changes = self._compare_endpoints(old_ep, new_ep)
                
                if changes:
                    modified_endpoints.append({
                        'path': path,
                        'method': method,
                        'endpoint_id': old_ep.id,
                        'changes': changes
                    })
                    
                    # Classify changes
                    for change in changes:
                        if change['severity'] == 'breaking':
                            breaking_changes.append({
                                'type': change['type'],
                                'severity': 'breaking',
                                'path': path,
                                'method': method,
                                'description': change['description']
                            })
                        else:
                            non_breaking_changes.append({
                                'type': change['type'],
                                'severity': 'non-breaking',
                                'path': path,
                                'method': method,
                                'description': change['description']
                            })
        
        return {
            'has_changes': len(breaking_changes) > 0 or len(non_breaking_changes) > 0,
            'specification_id': spec_id,
            'detected_at': datetime.utcnow().isoformat(),
            'breaking_changes': breaking_changes,
            'non_breaking_changes': non_breaking_changes,
            'removed_endpoints': removed_endpoints,
            'added_endpoints': added_endpoints,
            'modified_endpoints': modified_endpoints,
            'summary': {
                'breaking_count': len(breaking_changes),
                'non_breaking_count': len(non_breaking_changes),
                'removed_count': len(removed_endpoints),
                'added_count': len(added_endpoints),
                'modified_count': len(modified_endpoints)
            }
        }
    
    def _compare_endpoints(
        self,
        old_endpoint: OpenAPIEndpoint,
        new_endpoint: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Compare old and new endpoint versions"""
        changes = []
        
        # Compare request schema
        old_request_schema = old_endpoint.get_request_schema()
        new_request_schema = None
        if new_endpoint.get('request_schema_json'):
            try:
                new_request_schema = json.loads(new_endpoint['request_schema_json'])
            except:
                pass
        
        request_changes = self._compare_schemas(
            old_request_schema,
            new_request_schema,
            'request'
        )
        changes.extend(request_changes)
        
        # Compare response schema
        old_response_schema = old_endpoint.get_response_schema('200')
        new_response_schema = None
        if new_endpoint.get('response_schema_json'):
            try:
                new_response_schemas = json.loads(new_endpoint['response_schema_json'])
                new_response_schema = new_response_schemas.get('200')
            except:
                pass
        
        response_changes = self._compare_schemas(
            old_response_schema,
            new_response_schema,
            'response'
        )
        changes.extend(response_changes)
        
        # Compare operation ID
        if old_endpoint.operation_id != new_endpoint.get('operation_id'):
            changes.append({
                'type': 'operation_id_changed',
                'severity': 'non-breaking',
                'description': f'Operation ID changed from {old_endpoint.operation_id} to {new_endpoint.get("operation_id")}'
            })
        
        return changes
    
    def _compare_schemas(
        self,
        old_schema: Optional[Dict],
        new_schema: Optional[Dict],
        schema_type: str
    ) -> List[Dict[str, Any]]:
        """Compare two schemas and detect changes"""
        changes = []
        
        # Schema removed
        if old_schema and not new_schema:
            changes.append({
                'type': f'{schema_type}_schema_removed',
                'severity': 'breaking',
                'description': f'{schema_type.capitalize()} schema was removed'
            })
            return changes
        
        # Schema added
        if not old_schema and new_schema:
            changes.append({
                'type': f'{schema_type}_schema_added',
                'severity': 'non-breaking',
                'description': f'{schema_type.capitalize()} schema was added'
            })
            return changes
        
        if not old_schema or not new_schema:
            return changes
        
        # Compare properties
        old_props = old_schema.get('properties', {})
        new_props = new_schema.get('properties', {})
        old_required = old_schema.get('required', [])
        new_required = new_schema.get('required', [])
        
        # Check for removed required fields (breaking)
        removed_required = set(old_required) - set(new_required)
        for field in removed_required:
            changes.append({
                'type': 'required_field_removed',
                'severity': 'breaking',
                'description': f'Required field {field} was removed from {schema_type} schema'
            })
        
        # Check for new required fields (breaking if field didn't exist)
        new_required_fields = set(new_required) - set(old_required)
        for field in new_required_fields:
            if field not in old_props:
                changes.append({
                    'type': 'required_field_added',
                    'severity': 'breaking',
                    'description': f'New required field {field} was added to {schema_type} schema'
                })
            else:
                changes.append({
                    'type': 'field_made_required',
                    'severity': 'breaking',
                    'description': f'Field {field} is now required in {schema_type} schema'
                })
        
        # Check for removed fields
        removed_fields = set(old_props.keys()) - set(new_props.keys())
        for field in removed_fields:
            if field in old_required:
                changes.append({
                    'type': 'required_field_removed',
                    'severity': 'breaking',
                    'description': f'Required field {field} was removed from {schema_type} schema'
                })
            else:
                changes.append({
                    'type': 'optional_field_removed',
                    'severity': 'non-breaking',
                    'description': f'Optional field {field} was removed from {schema_type} schema'
                })
        
        # Check for added fields
        added_fields = set(new_props.keys()) - set(old_props.keys())
        for field in added_fields:
            if field in new_required:
                changes.append({
                    'type': 'required_field_added',
                    'severity': 'breaking',
                    'description': f'New required field {field} was added to {schema_type} schema'
                })
            else:
                changes.append({
                    'type': 'optional_field_added',
                    'severity': 'non-breaking',
                    'description': f'New optional field {field} was added to {schema_type} schema'
                })
        
        # Check for type changes
        common_fields = set(old_props.keys()) & set(new_props.keys())
        for field in common_fields:
            old_field = old_props[field]
            new_field = new_props[field]
            
            old_type = old_field.get('type')
            new_type = new_field.get('type')
            
            if old_type != new_type:
                changes.append({
                    'type': 'field_type_changed',
                    'severity': 'breaking',
                    'description': f'Field {field} type changed from {old_type} to {new_type} in {schema_type} schema'
                })
        
        return changes
    
    def get_affected_endpoints(self, changes: Dict[str, Any]) -> List[int]:
        """Get list of affected endpoint IDs from changes"""
        affected = set()
        
        for removed in changes.get('removed_endpoints', []):
            if 'endpoint_id' in removed:
                affected.add(removed['endpoint_id'])
        
        for modified in changes.get('modified_endpoints', []):
            if 'endpoint_id' in modified:
                affected.add(modified['endpoint_id'])
        
        return list(affected)
