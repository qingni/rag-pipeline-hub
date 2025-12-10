"""Chunking version management helper utilities."""
from typing import Dict, Any, Tuple
import json


class ChunkingVersionHelper:
    """Helper for managing chunking result versions and parameter changes."""
    
    # Critical parameters that indicate a major change
    CRITICAL_PARAMS = ['chunk_size', 'overlap', 'separator', 'min_chunk_size', 'max_chunk_size']
    
    # Threshold for considering numeric parameter change as minor (20%)
    MINOR_CHANGE_THRESHOLD = 0.20
    
    @classmethod
    def is_minor_param_change(
        cls,
        old_params: Dict[str, Any],
        new_params: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Determine if parameter change is minor (suitable for overwrite) or major (create new).
        
        Args:
            old_params: Previous parameters
            new_params: New parameters
            
        Returns:
            Tuple of (is_minor, reason):
            - is_minor: True if change is minor, False otherwise
            - reason: Explanation of the decision
            
        Examples:
            >>> ChunkingVersionHelper.is_minor_param_change(
            ...     {"chunk_size": 500, "overlap": 50},
            ...     {"chunk_size": 512, "overlap": 50}
            ... )
            (True, "Parameter change < 20%: chunk_size 500 -> 512")
            
            >>> ChunkingVersionHelper.is_minor_param_change(
            ...     {"chunk_size": 500, "overlap": 50},
            ...     {"chunk_size": 2000, "overlap": 50}
            ... )
            (False, "Significant change: chunk_size changed by 300.0%")
        """
        # If no old params, this is a new configuration
        if not old_params:
            return False, "Initial configuration"
        
        # If new params have different keys, consider it major
        old_keys = set(old_params.keys())
        new_keys = set(new_params.keys())
        
        if old_keys != new_keys:
            added = new_keys - old_keys
            removed = old_keys - new_keys
            details = []
            if added:
                details.append(f"added: {added}")
            if removed:
                details.append(f"removed: {removed}")
            return False, f"Parameter structure changed ({', '.join(details)})"
        
        # Check each critical parameter
        for param_name in cls.CRITICAL_PARAMS:
            if param_name not in old_params and param_name not in new_params:
                continue
            
            old_value = old_params.get(param_name)
            new_value = new_params.get(param_name)
            
            # If one exists but not the other
            if (old_value is None) != (new_value is None):
                return False, f"Parameter {param_name} added/removed"
            
            # Skip if both are None
            if old_value is None and new_value is None:
                continue
            
            # For numeric values, check percentage change
            if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                if old_value == 0:
                    # Avoid division by zero
                    if new_value != 0:
                        return False, f"Parameter {param_name} changed from 0 to {new_value}"
                    continue
                
                change_ratio = abs(new_value - old_value) / abs(old_value)
                if change_ratio > cls.MINOR_CHANGE_THRESHOLD:
                    return False, f"Significant change: {param_name} changed by {change_ratio*100:.1f}%"
            
            # For non-numeric values, must be exactly equal
            elif old_value != new_value:
                return False, f"Parameter {param_name} changed: {old_value} -> {new_value}"
        
        # Check non-critical parameters (should be equal)
        for key in old_keys:
            if key in cls.CRITICAL_PARAMS:
                continue
            
            if old_params[key] != new_params[key]:
                return False, f"Parameter {key} changed: {old_params[key]} -> {new_params[key]}"
        
        # If we got here, all changes are minor
        changes = []
        for param_name in cls.CRITICAL_PARAMS:
            if param_name in old_params and param_name in new_params:
                old_val = old_params[param_name]
                new_val = new_params[param_name]
                if old_val != new_val:
                    changes.append(f"{param_name}: {old_val} -> {new_val}")
        
        if changes:
            return True, f"Minor parameter optimization: {', '.join(changes)}"
        else:
            return True, "Parameters unchanged"
    
    @classmethod
    def params_to_comparable_string(cls, params: Dict[str, Any]) -> str:
        """
        Convert parameters to a comparable string (for detecting duplicates).
        
        Args:
            params: Parameters dictionary
            
        Returns:
            Normalized JSON string
        """
        return json.dumps(params, sort_keys=True, ensure_ascii=False)
    
    @classmethod
    def calculate_next_version(cls, current_max_version: int) -> int:
        """
        Calculate next version number.
        
        Args:
            current_max_version: Current maximum version for this document+strategy
            
        Returns:
            Next version number
        """
        return current_max_version + 1
    
    @classmethod
    def format_replacement_reason(
        cls,
        overwrite_mode: str,
        param_change_reason: str = None
    ) -> str:
        """
        Format replacement reason message.
        
        Args:
            overwrite_mode: The overwrite mode used (auto/always/never)
            param_change_reason: Reason from parameter change detection
            
        Returns:
            Formatted reason string
        """
        if overwrite_mode == "always":
            return "Manual override: always overwrite mode"
        elif overwrite_mode == "auto":
            if param_change_reason:
                return f"Auto-optimization: {param_change_reason}"
            else:
                return "Auto-optimization: parameters unchanged"
        else:
            return "New version created"


# Convenience function
def is_minor_param_change(old_params: Dict[str, Any], new_params: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Convenience function for parameter change detection.
    
    Args:
        old_params: Previous parameters
        new_params: New parameters
        
    Returns:
        Tuple of (is_minor, reason)
    """
    return ChunkingVersionHelper.is_minor_param_change(old_params, new_params)
