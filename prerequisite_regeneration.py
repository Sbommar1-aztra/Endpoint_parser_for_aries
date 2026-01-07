"""
Prerequisite Regeneration Workflow - Task 9
Prompts users to regenerate prerequisites when specification changes affect dependencies
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.orm import Session
from models import (
    OpenAPIEndpoint, OpenAPIFieldDependency, PrerequisiteSuggestion,
    APIRequirement
)
from field_dependency_detector import FieldDependencyDetector
from prerequisite_suggestion_engine import PrerequisiteSuggestionEngine
from contract_change_detector import ContractChangeDetector


class PrerequisiteRegeneration:
    """
    Prerequisite Regeneration Workflow - Task 9
    Handles regeneration of prerequisites when specifications change
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def check_and_regenerate(
        self,
        spec_id: int,
        changes: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if changes affect dependencies and regenerate prerequisites
        
        Args:
            spec_id: Specification ID
            changes: Change detection results from ContractChangeDetector
            
        Returns:
            Regeneration results
        """
        affected_endpoint_ids = self._get_endpoints_affected_by_changes(changes)
        
        if not affected_endpoint_ids:
            return {
                'needs_regeneration': False,
                'message': 'No endpoints with dependencies were affected by changes'
            }
        
        # Get affected endpoints
        affected_endpoints = self.db.query(OpenAPIEndpoint).filter(
            OpenAPIEndpoint.id.in_(affected_endpoint_ids)
        ).all()
        
        # Get API requirements that use these endpoints
        # (Assuming there's a relationship or we need to match by method/path)
        requirements_needing_update = self._find_requirements_for_endpoints(
            affected_endpoints
        )
        
        return {
            'needs_regeneration': True,
            'affected_endpoints': [ep.id for ep in affected_endpoints],
            'requirements_needing_update': requirements_needing_update,
            'regeneration_prompt': self._generate_regeneration_prompt(changes, affected_endpoints)
        }
    
    def regenerate_for_endpoints(
        self,
        endpoint_ids: List[int],
        api_requirement_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Regenerate prerequisites for specific endpoints
        
        Args:
            endpoint_ids: List of endpoint IDs to regenerate for
            api_requirement_id: Optional API requirement ID to associate with
            
        Returns:
            Regeneration results
        """
        # Get endpoints
        endpoints = self.db.query(OpenAPIEndpoint).filter(
            OpenAPIEndpoint.id.in_(endpoint_ids)
        ).all()
        
        if not endpoints:
            return {
                'success': False,
                'error': 'No endpoints found'
            }
        
        # Convert to dict format for detector
        endpoints_data = []
        for ep in endpoints:
            endpoints_data.append({
                'id': ep.id,
                'path': ep.path,
                'method': ep.method,
                'request_schema_json': ep.request_schema_json,
                'response_schema_json': ep.response_schema_json
            })
        
        # Re-detect dependencies
        detector = FieldDependencyDetector()
        dependencies_data = detector.detect_dependencies(endpoints_data, endpoints)
        
        # Store new dependencies (delete old ones first)
        self.db.query(OpenAPIFieldDependency).filter(
            OpenAPIFieldDependency.source_endpoint_id.in_(endpoint_ids)
        ).delete()
        
        dependency_objects = []
        for dep_data in dependencies_data:
            dependency = OpenAPIFieldDependency(
                source_endpoint_id=dep_data['source_endpoint_id'],
                target_endpoint_id=dep_data['target_endpoint_id'],
                source_field_name=dep_data['source_field_name'],
                target_field_name=dep_data['target_field_name'],
                dependency_type=dep_data['dependency_type'],
                confidence_score=dep_data['confidence_score'],
                detection_method=dep_data['detection_method'],
                response_path=dep_data['response_path'],
                is_mandatory=dep_data['is_mandatory']
            )
            self.db.add(dependency)
            dependency_objects.append(dependency)
        
        self.db.flush()
        
        # Regenerate suggestions
        suggestion_engine = PrerequisiteSuggestionEngine()
        suggestions_data = suggestion_engine.generate_suggestions(
            endpoints, dependencies_data, api_requirement_id
        )
        
        # Delete old suggestions
        self.db.query(PrerequisiteSuggestion).filter(
            PrerequisiteSuggestion.endpoint_id.in_(endpoint_ids)
        ).delete()
        
        # Store new suggestions
        for sugg_data in suggestions_data:
            suggestion = PrerequisiteSuggestion(
                api_requirement_id=sugg_data.get('api_requirement_id'),
                endpoint_id=sugg_data['endpoint_id'],
                suggested_prerequisites=sugg_data['suggested_prerequisites'],
                suggested_field_mappings=sugg_data['suggested_field_mappings'],
                execution_order=sugg_data['execution_order'],
                confidence_score=sugg_data['confidence_score'],
                user_reviewed=False,  # Reset review status
                user_approved=False
            )
            self.db.add(suggestion)
        
        self.db.commit()
        
        return {
            'success': True,
            'regenerated_endpoints': endpoint_ids,
            'dependencies_count': len(dependency_objects),
            'suggestions_count': len(suggestions_data),
            'message': f'Successfully regenerated prerequisites for {len(endpoint_ids)} endpoint(s)'
        }
    
    def compare_suggestions(
        self,
        endpoint_id: int
    ) -> Dict[str, Any]:
        """
        Compare old and new suggestions for an endpoint
        
        Args:
            endpoint_id: Endpoint ID
            
        Returns:
            Comparison results
        """
        # This would ideally store old suggestions before regenerating
        # For now, we'll return current suggestions
        suggestions = self.db.query(PrerequisiteSuggestion).filter(
            PrerequisiteSuggestion.endpoint_id == endpoint_id
        ).all()
        
        if not suggestions:
            return {
                'has_suggestions': False,
                'message': 'No suggestions found for this endpoint'
            }
        
        # Get the most recent suggestion
        latest_suggestion = max(suggestions, key=lambda s: s.updated_at)
        
        return {
            'has_suggestions': True,
            'current_suggestion': latest_suggestion.to_dict(),
            'comparison_note': 'To compare old vs new, store previous version before regeneration'
        }
    
    def _get_endpoints_affected_by_changes(
        self,
        changes: Dict[str, Any]
    ) -> List[int]:
        """Get endpoint IDs affected by specification changes"""
        affected = set()
        
        # Endpoints that were removed or modified
        for removed in changes.get('removed_endpoints', []):
            if 'endpoint_id' in removed:
                affected.add(removed['endpoint_id'])
        
        for modified in changes.get('modified_endpoints', []):
            if 'endpoint_id' in modified:
                affected.add(modified['endpoint_id'])
        
        # Also check if any dependencies were affected
        # (field changes that affect FK relationships)
        breaking_changes = changes.get('breaking_changes', [])
        for change in breaking_changes:
            if change.get('type') in ['required_field_added', 'required_field_removed', 'field_type_changed']:
                # Find endpoints that have dependencies on this field
                path = change.get('path')
                method = change.get('method')
                
                if path and method:
                    endpoint = self.db.query(OpenAPIEndpoint).filter(
                        OpenAPIEndpoint.path == path,
                        OpenAPIEndpoint.method == method
                    ).first()
                    
                    if endpoint:
                        affected.add(endpoint.id)
        
        return list(affected)
    
    def _find_requirements_for_endpoints(
        self,
        endpoints: List[OpenAPIEndpoint]
    ) -> List[Dict[str, Any]]:
        """Find API requirements that use these endpoints"""
        requirements = []
        
        for endpoint in endpoints:
            # Match by method and path
            matching_requirements = self.db.query(APIRequirement).filter(
                APIRequirement.method == endpoint.method,
                APIRequirement.endpoint == endpoint.path
            ).all()
            
            for req in matching_requirements:
                requirements.append({
                    'id': req.id,
                    'method': req.method,
                    'endpoint': req.endpoint,
                    'endpoint_id': endpoint.id
                })
        
        return requirements
    
    def _generate_regeneration_prompt(
        self,
        changes: Dict[str, Any],
        affected_endpoints: List[OpenAPIEndpoint]
    ) -> str:
        """Generate user-friendly prompt for regeneration"""
        breaking_count = changes.get('summary', {}).get('breaking_count', 0)
        modified_count = changes.get('summary', {}).get('modified_count', 0)
        
        prompt = f"Specification changes detected:\n"
        prompt += f"- {breaking_count} breaking changes\n"
        prompt += f"- {modified_count} modified endpoints\n"
        prompt += f"- {len(affected_endpoints)} endpoints with dependencies affected\n\n"
        prompt += "Prerequisites need to be regenerated for these endpoints.\n"
        prompt += "Would you like to regenerate prerequisites now?"
        
        return prompt
