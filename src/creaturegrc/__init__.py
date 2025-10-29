"""
CreatureGRC - Open-source compliance automation platform

This package connects infrastructure to security controls, automates evidence
collection, and generates audit packages for SOC 2, ISO 27001, NIST, and more.

Deployment modes:
- Agent: Lightweight evidence collection and export
- Server: Full GRC platform with database and integrations

Installation:
    pip install creaturegrc[agent]   # Agent mode
    pip install creaturegrc[server]  # Server mode

Usage:
    # Agent mode
    creaturegrc profile use acme-corp
    creaturegrc collect evidence --source wazuh

    # Server mode
    creaturegrc status --framework soc2
    creaturegrc audit generate --framework soc2 --output ./audit/
"""

# Re-export public APIs from workspace packages
try:
    from creature_ir import (
        Creature,
        CreatureType,
        Control,
        ControlFamily,
        Evidence,
        EvidenceType,
        AuditPackage,
        Framework,
        Mapping,
    )

    __all__ = [
        "Creature",
        "CreatureType",
        "Control",
        "ControlFamily",
        "Evidence",
        "EvidenceType",
        "AuditPackage",
        "Framework",
        "Mapping",
    ]
except ImportError:
    # Workspace packages not yet installed
    __all__ = []

__version__ = "2.0.0"
__author__ = "CreatureGRC Contributors"
__license__ = "MIT"
