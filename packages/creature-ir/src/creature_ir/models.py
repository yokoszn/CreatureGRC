"""
Core data models for CreatureGRC.

These models define the stable contract between all system components.
Breaking changes require a major version bump and compatibility tests.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field, ConfigDict


class CreatureType(str, Enum):
    """Types of creatures in the environment"""

    IDENTITY = "identity"
    ACCOUNT = "account"
    INFRASTRUCTURE = "infrastructure"
    APPLICATION = "application"


class Creature(BaseModel):
    """
    A creature is any entity in your environment with security implications.

    Examples:
    - Identity: jane.doe (person), github-actions-bot (AI agent)
    - Account: jane.doe@keycloak, jane.doe@aws, jane-ssh-key-prod
    - Infrastructure: prod-web-01 (server), k8s-cluster-prod (cluster)
    - Application: postgresql-prod (database), api-gateway (service)
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="Unique identifier")
    name: str = Field(..., description="Human-readable name")
    type: CreatureType = Field(..., description="Creature type")
    class_: str = Field(..., alias="class", description="Specific class (e.g., server, person)")
    domain: str = Field(..., description="Domain or system")
    criticality: Optional[str] = Field(None, description="Criticality level")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    discovered_at: datetime = Field(..., description="When creature was discovered")
    source_system: str = Field(..., description="Source system (netbox, keycloak, etc.)")
    relationships: list[dict[str, Any]] = Field(
        default_factory=list, description="Relationships to other creatures"
    )


class ControlFamily(str, Enum):
    """Control families from NIST 800-53"""

    AC = "AC"  # Access Control
    AU = "AU"  # Audit and Accountability
    AT = "AT"  # Awareness and Training
    CM = "CM"  # Configuration Management
    CP = "CP"  # Contingency Planning
    IA = "IA"  # Identification and Authentication
    IR = "IR"  # Incident Response
    MA = "MA"  # Maintenance
    MP = "MP"  # Media Protection
    PS = "PS"  # Personnel Security
    PE = "PE"  # Physical and Environmental Protection
    PL = "PL"  # Planning
    PM = "PM"  # Program Management
    RA = "RA"  # Risk Assessment
    CA = "CA"  # Assessment, Authorization, and Monitoring
    SC = "SC"  # System and Communications Protection
    SI = "SI"  # System and Information Integrity
    SA = "SA"  # System and Services Acquisition


class Control(BaseModel):
    """Security control from a compliance framework"""

    model_config = ConfigDict(use_enum_values=True)

    control_code: str = Field(..., description="Control identifier (e.g., AC-2, CC6.1)")
    framework: str = Field(..., description="Framework name (NIST, SOC2, ISO27001)")
    family: Optional[str] = Field(None, description="Control family code")
    domain: str = Field(..., description="Control domain")
    name: str = Field(..., description="Control name")
    description: str = Field(..., description="Control description")
    testing_procedures: Optional[str] = Field(None, description="How to test this control")
    implementation_guidance: Optional[str] = Field(
        None, description="How to implement this control"
    )
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class EvidenceType(str, Enum):
    """Types of compliance evidence"""

    LOG = "log"
    CONFIG = "config"
    SCREENSHOT = "screenshot"
    DOCUMENT = "document"
    SCAN_RESULT = "scan_result"
    AUDIT_TRAIL = "audit_trail"
    POLICY = "policy"
    PROCEDURE = "procedure"


class Evidence(BaseModel):
    """Collected compliance evidence"""

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(..., description="Unique identifier")
    control_code: str = Field(..., description="Related control")
    source: str = Field(..., description="Source system (wazuh, keycloak, etc.)")
    collected_at: datetime = Field(..., description="Collection timestamp")
    evidence_type: EvidenceType = Field(..., description="Type of evidence")
    content: dict[str, Any] = Field(..., description="Evidence content")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Framework(BaseModel):
    """Compliance framework definition"""

    name: str = Field(..., description="Framework name (NIST-800-53, SOC2)")
    version: str = Field(..., description="Framework version")
    description: str = Field(..., description="Framework description")
    controls: list[Control] = Field(default_factory=list, description="Controls in framework")


class Mapping(BaseModel):
    """Mapping between creature and control"""

    creature_id: str = Field(..., description="Creature ID")
    control_code: str = Field(..., description="Control code")
    justification: Optional[str] = Field(None, description="Why this mapping exists")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Mapping confidence (0-1)")
    automated: bool = Field(False, description="Automatically mapped vs manual")
    created_at: datetime = Field(..., description="Mapping creation time")


class AuditPackage(BaseModel):
    """Generated audit package output"""

    framework: str = Field(..., description="Framework being audited")
    period_start: datetime = Field(..., description="Audit period start")
    period_end: datetime = Field(..., description="Audit period end")
    generated_at: datetime = Field(..., description="Package generation time")
    controls: list[Control] = Field(..., description="Controls in scope")
    evidence: list[Evidence] = Field(..., description="Collected evidence")
    creatures: list[Creature] = Field(..., description="Creatures in scope")
    mappings: list[Mapping] = Field(..., description="Creature-control mappings")
    gaps: list[dict[str, Any]] = Field(default_factory=list, description="Identified gaps")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
