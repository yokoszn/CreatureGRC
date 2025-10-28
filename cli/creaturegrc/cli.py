#!/usr/bin/env python3
"""
CreatureGRC CLI - Main entry point
"""

import click
import os
import sys
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
@click.version_option(version="2.0.0")
@click.pass_context
def main(ctx):
    """
    CreatureGRC - CLI-driven GRC platform

    Integrates with your existing infrastructure stack for automated compliance.
    """
    ctx.ensure_object(dict)

    # Load config from environment
    ctx.obj['db_config'] = {
        'host': os.getenv('GRC_DB_HOST', 'localhost'),
        'port': int(os.getenv('GRC_DB_PORT', '5432')),
        'database': os.getenv('GRC_DB_NAME', 'grc_platform'),
        'user': os.getenv('GRC_DB_USER', 'grc_user'),
        'password': os.getenv('GRC_DB_PASSWORD', ''),
    }


# ============================================================================
# Evidence Collection Commands
# ============================================================================

@main.group()
def collect():
    """Collect evidence from integrated systems"""
    pass


@collect.command()
@click.option('--framework', default='soc2', help='Compliance framework')
@click.option('--source', help='Specific source (wazuh, keycloak, etc.)')
@click.option('--days', default=90, help='Number of days to collect')
@click.pass_context
def evidence(ctx, framework, source, days):
    """Collect compliance evidence"""
    console.print(f"[bold green]Collecting evidence for {framework}...[/bold green]")

    if source:
        console.print(f"  Source: {source}")
        console.print(f"  Days: {days}")
    else:
        console.print(f"  Sources: all")

    # TODO: Implement evidence collection
    console.print("[yellow]Evidence collection not yet implemented[/yellow]")
    console.print("Run: python evidence_collector.py --config config.yaml --framework SOC2")


# ============================================================================
# Creature Management Commands
# ============================================================================

@main.group()
def creatures():
    """Manage infrastructure creatures (assets)"""
    pass


@creatures.command()
@click.option('--source', default='netbox', help='Source system (netbox, yaml)')
@click.option('--file', help='YAML file path (if source=yaml)')
@click.pass_context
def sync(ctx, source, file):
    """Sync creatures from source system"""
    console.print(f"[bold green]Syncing creatures from {source}...[/bold green]")

    if source == 'netbox':
        netbox_url = os.getenv('NETBOX_API_URL')
        if not netbox_url:
            console.print("[red]Error: NETBOX_API_URL not set[/red]")
            sys.exit(1)
        console.print(f"  Netbox URL: {netbox_url}")

    # TODO: Implement creature sync
    console.print("[yellow]Creature sync not yet implemented[/yellow]")


@creatures.command()
@click.option('--class', 'creature_class', help='Filter by creature class')
@click.option('--criticality', help='Filter by criticality')
@click.pass_context
def list(ctx, creature_class, criticality):
    """List creatures"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        conn = psycopg2.connect(**ctx.obj['db_config'], cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            query = "SELECT id, name, creature_class, creature_domain, criticality FROM creatures"
            conditions = []
            params = []

            if creature_class:
                conditions.append("creature_class = %s")
                params.append(creature_class)

            if criticality:
                conditions.append("criticality = %s")
                params.append(criticality)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY criticality DESC, name"

            cur.execute(query, params)
            creatures = cur.fetchall()

            if not creatures:
                console.print("[yellow]No creatures found[/yellow]")
                return

            # Display as table
            table = Table(title="Creatures")
            table.add_column("Name", style="cyan")
            table.add_column("Class", style="magenta")
            table.add_column("Domain", style="blue")
            table.add_column("Criticality", style="red")

            for creature in creatures:
                table.add_row(
                    creature['name'],
                    creature['creature_class'],
                    creature['creature_domain'],
                    creature['criticality'] or 'unknown'
                )

            console.print(table)
            console.print(f"\n[green]Total: {len(creatures)} creatures[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ============================================================================
# Control Management Commands
# ============================================================================

@main.group()
def controls():
    """Manage compliance controls"""
    pass


@controls.command()
@click.option('--framework', help='Filter by framework')
@click.option('--domain', help='Filter by domain')
@click.pass_context
def list(ctx, framework, domain):
    """List controls"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        conn = psycopg2.connect(**ctx.obj['db_config'], cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            query = """
                SELECT
                    c.control_code,
                    c.control_name,
                    cd.domain_code,
                    cf.name AS framework_name
                FROM controls c
                JOIN control_domains cd ON c.domain_id = cd.id
                JOIN compliance_frameworks cf ON cd.framework_id = cf.id
            """

            conditions = []
            params = []

            if framework:
                conditions.append("cf.name = %s")
                params.append(framework.upper())

            if domain:
                conditions.append("cd.domain_code = %s")
                params.append(domain.upper())

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY cf.name, cd.domain_code, c.control_code"

            cur.execute(query, params)
            controls = cur.fetchall()

            if not controls:
                console.print("[yellow]No controls found[/yellow]")
                return

            # Display as table
            table = Table(title="Controls")
            table.add_column("Framework", style="cyan")
            table.add_column("Domain", style="magenta")
            table.add_column("Control Code", style="blue")
            table.add_column("Control Name", style="white")

            for control in controls:
                table.add_row(
                    control['framework_name'],
                    control['domain_code'],
                    control['control_code'],
                    control['control_name'][:60] + "..." if len(control['control_name']) > 60 else control['control_name']
                )

            console.print(table)
            console.print(f"\n[green]Total: {len(controls)} controls[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@controls.command()
@click.argument('control_code')
@click.pass_context
def show(ctx, control_code):
    """Show control details"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        conn = psycopg2.connect(**ctx.obj['db_config'], cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    c.*,
                    cd.domain_code,
                    cd.domain_name,
                    cf.name AS framework_name
                FROM controls c
                JOIN control_domains cd ON c.domain_id = cd.id
                JOIN compliance_frameworks cf ON cd.framework_id = cf.id
                WHERE c.control_code = %s
            """, (control_code.upper(),))

            control = cur.fetchone()

            if not control:
                console.print(f"[red]Control {control_code} not found[/red]")
                sys.exit(1)

            console.print(f"\n[bold cyan]{control['control_code']}: {control['control_name']}[/bold cyan]\n")
            console.print(f"Framework: {control['framework_name']}")
            console.print(f"Domain: {control['domain_code']} - {control['domain_name']}")
            console.print(f"Type: {control['control_type']}")
            console.print(f"\n[bold]Description:[/bold]")
            console.print(control['control_description'])

            if control['testing_procedures']:
                console.print(f"\n[bold]Testing Procedures:[/bold]")
                console.print(control['testing_procedures'])

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@controls.command()
@click.option('--framework', required=True, help='Framework to check')
@click.pass_context
def status(ctx, framework):
    """Show compliance status for framework"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        conn = psycopg2.connect(**ctx.obj['db_config'], cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM v_audit_readiness
                WHERE framework_name = %s
            """, (framework.upper(),))

            status = cur.fetchone()

            if not status:
                console.print(f"[red]Framework {framework} not found[/red]")
                sys.exit(1)

            # Display status
            console.print(f"\n[bold cyan]Compliance Status: {framework.upper()}[/bold cyan]\n")
            console.print(f"Total Controls: {status['total_controls']}")
            console.print(f"Implemented: {status['implemented_controls']} ({status['implementation_percentage']}%)")
            console.print(f"Not Implemented: {status['not_implemented_controls']}")
            console.print(f"With Evidence: {status['controls_with_evidence']}")
            console.print(f"Automated: {status['automated_controls']}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ============================================================================
# Framework Commands
# ============================================================================

@main.group()
def frameworks():
    """Manage compliance frameworks"""
    pass


@frameworks.command()
@click.pass_context
def list(ctx):
    """List available frameworks"""
    import psycopg2
    from psycopg2.extras import RealDictCursor

    try:
        conn = psycopg2.connect(**ctx.obj['db_config'], cursor_factory=RealDictCursor)
        with conn.cursor() as cur:
            cur.execute("SELECT name, version, source, description FROM compliance_frameworks ORDER BY name")
            frameworks = cur.fetchall()

            if not frameworks:
                console.print("[yellow]No frameworks found. Run import-controls first.[/yellow]")
                return

            table = Table(title="Compliance Frameworks")
            table.add_column("Name", style="cyan")
            table.add_column("Version", style="magenta")
            table.add_column("Source", style="blue")
            table.add_column("Description", style="white")

            for fw in frameworks:
                table.add_row(
                    fw['name'],
                    fw['version'],
                    fw['source'],
                    fw['description'][:50] + "..." if len(fw['description']) > 50 else fw['description']
                )

            console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# ============================================================================
# Status & Reporting Commands
# ============================================================================

@main.command()
@click.option('--framework', default='soc2', help='Framework to check')
@click.pass_context
def status(ctx, framework):
    """Show overall compliance status"""
    console.print(f"[bold green]Compliance Status Dashboard[/bold green]\n")

    # This is a wrapper that shows multiple views
    ctx.invoke(controls.commands['status'], framework=framework)


# ============================================================================
# Import Commands
# ============================================================================

@main.command()
@click.option('--framework', required=True, type=click.Choice(['nist-800-53', 'scf', 'ccm']), help='Framework to import')
@click.option('--file', help='File path (for SCF/CCM Excel)')
@click.pass_context
def import_controls(ctx, framework, file):
    """Import control libraries"""
    console.print(f"[bold green]Importing {framework} controls...[/bold green]")

    if framework == 'nist-800-53':
        console.print("Run: python import_oscal_controls.py --config config.yaml")
    elif framework == 'scf':
        if not file:
            console.print("[red]Error: --file required for SCF import[/red]")
            sys.exit(1)
        console.print(f"Run: python import_scf_controls.py --config config.yaml --scf-excel {file}")
    elif framework == 'ccm':
        console.print("Run: python import_csa_ccm.py --config config.yaml --download")


if __name__ == '__main__':
    main()
