"""Interactive UI for field-by-field PDR mapping."""

from typing import Dict, Any
from rich.console import Console
from rich.table import Table

console = Console()


class InteractiveMapper:
    """Provide interactive prompts for mapping PDR fields to Redfish resources."""

    def __init__(self, schemas: Dict[str, Any]):
        """
        Initialize interactive mapper.
        
        Args:
            schemas: Loaded Redfish schemas.
        """
        self.schemas = schemas

    def display_pdr(self, pdr: Dict[str, Any]) -> None:
        """
        Display a PDR in a rich, readable format.
        
        Args:
            pdr: PDR dictionary from retriever.
        """
        # TODO: Implement rich table display
        console.print(f"[yellow]⚠️  PDR display not yet implemented[/yellow]")

    def prompt_mapping(self, pdr: Dict[str, Any]) -> Dict[str, Any]:
        """
        Interactively prompt user to map a PDR to Redfish.
        
        Args:
            pdr: PDR to map.
            
        Returns:
            Mapping configuration.
        """
        # TODO: Implement mapping prompts
        return {}
