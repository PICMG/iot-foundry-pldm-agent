"""Transform functions for unit conversions and enum mappings."""

from typing import Any, Callable, Dict
from rich.console import Console

console = Console()


class TransformRegistry:
    """Registry of PLDM-to-Redfish data transformations."""

    def __init__(self):
        """Initialize transform registry."""
        self.transforms: Dict[str, Callable] = {}
        self._register_default_transforms()

    def _register_default_transforms(self) -> None:
        """Register standard PLDM transform functions."""
        self.transforms["pldm_to_real"] = self._pldm_to_real
        self.transforms["state_to_percent"] = self._state_to_percent
        # TODO: Add more transforms

    def _pldm_to_real(self, value: int, scale: float = 1.0) -> float:
        """
        Convert PLDM sensor reading to real value.
        
        Args:
            value: Raw PLDM value.
            scale: Scale factor from PDR.
            
        Returns:
            Real value.
        """
        return value * scale

    def _state_to_percent(self, state: int, mapping: Dict[str, float] = None) -> float:
        """
        Convert state effecter to percentage.
        
        Args:
            state: State value.
            mapping: State-to-percent mapping.
            
        Returns:
            Percentage value.
        """
        if mapping is None:
            mapping = {0: 0.0, 1: 100.0}
        return mapping.get(state, 0.0)

    def apply(self, transform_name: str, value: Any, **kwargs) -> Any:
        """
        Apply a registered transform.
        
        Args:
            transform_name: Name of transform function.
            value: Value to transform.
            **kwargs: Additional arguments for the transform.
            
        Returns:
            Transformed value.
        """
        transform = self.transforms.get(transform_name)
        if transform:
            return transform(value, **kwargs)
        return value
