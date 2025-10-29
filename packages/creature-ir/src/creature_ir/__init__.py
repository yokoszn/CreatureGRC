"""
creature-ir: CreatureGRC Intermediate Representation

This is the ONLY stable contract across all CreatureGRC packages.
All other packages are internal and may change.

The IR defines:
- Creature: Infrastructure, identities, accounts, applications
- Control: Security controls from frameworks
- Evidence: Collected compliance evidence
- AuditPackage: Generated audit output
"""

from creature_ir.models import (
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

__version__ = "2.0.0"
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
