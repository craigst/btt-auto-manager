#!/usr/bin/env python3
import os
import sys
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()

def main():
    """Main launcher function"""
    console.print("[bold blue]BTT SQL Database Tool[/bold blue]")
    console.print("Choose your option:\n")
    
    # Menu options
    menu_table = Table(box=box.SIMPLE, title="Available Tools")
    menu_table.add_column("Option", style="bold")
    menu_table.add_column("Description")
    
    menu_table.add_row("1", "Run Single SQL Extraction (getsql.py)")
    menu_table.add_row("2", "Auto Manager (btt_auto.py)")
    menu_table.add_row("3", "Exit")
    
    console.print(menu_table)
    
    choice = console.input("\n[bold]Select option (1-3): [/bold]").strip()
    
    if choice == "1":
        console.print("[blue]Starting single SQL extraction...[/blue]")
        subprocess.run([sys.executable, 'getsql.py'], cwd=os.path.dirname(__file__))
    elif choice == "2":
        console.print("[blue]Starting Auto Manager...[/blue]")
        subprocess.run([sys.executable, 'btt_auto.py'], cwd=os.path.dirname(__file__))
    elif choice == "3":
        console.print("[blue]Goodbye![/blue]")
    else:
        console.print("[red]Invalid option. Please try again.[/red]")

if __name__ == "__main__":
    main() 