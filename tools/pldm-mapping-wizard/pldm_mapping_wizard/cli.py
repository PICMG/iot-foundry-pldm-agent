"""CLI entry point for PLDM Mapping Wizard."""

import click
from rich.console import Console
from pldm_mapping_wizard.redfish import SchemaLoader
from pldm_mapping_wizard.discovery import PortMonitor
from pldm_mapping_wizard.discovery.pdr_retriever import PDRRetriever
from pldm_mapping_wizard.mapping import MappingAccumulator, DeviceMapping

__version__ = "0.1.0"

console = Console()


@click.group()
@click.version_option(version=__version__)
def cli():
    """PLDM Mapping Wizard - Interactive PDR to Redfish mapping configuration."""
    pass


@cli.command()
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    default="pdr_redfish_mappings.json",
    help="Output file for mappings (default: pdr_redfish_mappings.json)",
)
@click.option(
    "--local-eid",
    type=int,
    default=16,
    show_default=True,
    help="Local endpoint ID for MCTP communication",
)
@click.option(
    "--remote-eid",
    type=int,
    default=0,
    show_default=True,
    help="Remote endpoint ID for the attached device",
)
@click.option(
    "--baud",
    type=int,
    default=115200,
    show_default=True,
    help="Serial baud rate",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable debug logging of raw frames",
)
def setup(output, local_eid, remote_eid, baud, debug):
    """Interactively configure PDR-to-Redfish mappings via sequential USB device insertion."""
    console.print("\n[bold cyan]PLDM Mapping Wizard - Device Configuration Setup[/bold cyan]\n")
    console.print(f"📍 Output file: {output}\n")
    
    # Load schemas at startup
    schema_loader = SchemaLoader()
    schema_loader.load_schemas()
    
    # Initialize port monitor and accumulator
    port_monitor = PortMonitor()
    accumulator = MappingAccumulator(output)
    
    device_count = 0
    
    # Device loop
    while True:
        device_count += 1
        console.print(f"[bold]Device #{device_count}[/bold]")
        
        device_info = port_monitor.wait_for_device()
        if device_info is None:
            break
        
        # Prompt for connector name
        connector_name = console.input(
            f"Device identifier (connector/slot name) [Node_{device_count}]: "
        ).strip()
        if not connector_name:
            connector_name = f"Node_{device_count}"
        
        port = device_info["port"]
        usb_address = device_info["usb_address"]
        
        # Try to retrieve PDRs with retry on failure
        retriever = PDRRetriever(
            port,
            local_eid=local_eid,
            remote_eid=remote_eid,
            baudrate=baud,
            debug=debug,
        )
        
        while True:
            if not retriever.connect():
                console.print("\n[red]✗ Connection failed[/red]")
                user_choice = console.input(
                    "\nOptions:\n"
                    "  [r] Retry (remove device, reinsert, and try again)\n"
                    "  [s] Skip this device\n"
                    "  [q] Quit\n"
                    "Choose: [r]: "
                ).strip().lower()
                
                if user_choice == "q":
                    retriever.disconnect()
                    return
                elif user_choice == "s":
                    break
                elif user_choice == "r":
                    console.print("\nRemove device and press ENTER when ready: ", end="")
                    input()
                    console.print("Insert device and press ENTER when ready: ", end="")
                    input()
                    console.print()
                    retriever = PDRRetriever(
                        port,
                        local_eid=local_eid,
                        remote_eid=remote_eid,
                        baudrate=baud,
                        debug=debug,
                    )
                    continue
                else:
                    continue
            
            # Try to get PDR repository info
            repo_info = retriever.get_repository_info()
            if repo_info is None:
                console.print("\n[red]✗ Failed to retrieve PDR repository info[/red]")
                user_choice = console.input(
                    "\nOptions:\n"
                    "  [r] Retry\n"
                    "  [s] Skip this device\n"
                    "  [q] Quit\n"
                    "Choose: [r]: "
                ).strip().lower()
                
                if user_choice == "q":
                    retriever.disconnect()
                    return
                elif user_choice == "s":
                    retriever.disconnect()
                    break
                else:
                    continue
            
            # Retrieve PDRs
            pdrs = retriever.get_pdrs()
            retriever.disconnect()
            
            if pdrs:
                console.print(f"\n✅ Retrieved {len(pdrs)} PDRs\n")
                
                # Display summary of PDRs
                sensor_count = 0
                effecter_count = 0
                entity_count = 0
                other_count = 0
                
                for pdr in pdrs:
                    pdr_type = pdr.get("type_name", "UNKNOWN")
                    if "SENSOR" in pdr_type:
                        sensor_count += 1
                    elif "EFFECTER" in pdr_type:
                        effecter_count += 1
                    elif "ENTITY" in pdr_type:
                        entity_count += 1
                    else:
                        other_count += 1
                
                console.print(f"PDR Breakdown:")
                if sensor_count > 0:
                    console.print(f"  • {sensor_count} Sensor PDR(s)")
                if effecter_count > 0:
                    console.print(f"  • {effecter_count} Effecter PDR(s)")
                if entity_count > 0:
                    console.print(f"  • {entity_count} Entity PDR(s)")
                if other_count > 0:
                    console.print(f"  • {other_count} Other PDR(s)")
                console.print()
                
                # Create a basic device mapping (will be enhanced in Phase 2)
                device_mapping = DeviceMapping(
                    connector=connector_name,
                    usb_hardware_address=usb_address,
                    eid=remote_eid,  # Remote endpoint ID
                    chassis_resource=f"/redfish/v1/Chassis/{connector_name}",
                    sensors=[],  # TODO: Parse PDRs into sensors
                    controls=[],  # TODO: Parse PDRs into controls
                    fru_mappings={},  # TODO: Parse FRU data
                )
                
                accumulator.add_device(device_mapping)
                console.print(f"✓ Stored mapping for {connector_name}\n")
            else:
                console.print("\n[yellow]⚠️  No PDRs retrieved[/yellow]\n")
            
            break
        
        # Prompt for next device
        console.print("─" * 60)
        user_input = console.input(
            "Remove device and insert next one, then press ENTER\n(or 'q' to finish): "
        )
        
        if user_input.lower() == "q":
            break
        
        console.print()
    
    # Save accumulated mappings
    if accumulator.devices:
        accumulator.save()
        console.print(f"\n✅ Configuration complete! {len(accumulator.devices)} device(s) configured.\n")
    else:
        console.print("\n[yellow]ℹ️  No devices configured.[/yellow]\n")


@cli.command()
@click.option(
    "--mappings",
    "-m",
    type=click.Path(exists=True),
    required=True,
    help="Path to pdr_redfish_mappings.json",
)
def validate(mappings):
    """Validate existing PDR mappings against schemas."""
    console.print(f"\n[bold cyan]Validating mappings: {mappings}[/bold cyan]\n")
    console.print("   [yellow]⚠️  Not yet implemented[/yellow]\n")


def main():
    """Entry point."""
    cli()


if __name__ == "__main__":
    main()
