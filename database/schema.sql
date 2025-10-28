-- ============================================================================
-- GRC PLATFORM SCHEMA
-- Extends the Creature Database for Governance, Risk & Compliance
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "btree_gist";

-- ============================================================================
-- CORE CREATURE DATABASE (Foundation)
-- ============================================================================

CREATE TABLE IF NOT EXISTS creatures (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    creature_class TEXT NOT NULL, -- 'server', 'domain', 'application', 'network', etc.
    creature_domain TEXT NOT NULL, -- 'physical', 'network', 'platform', 'business', etc.
    description TEXT,
    owner_id UUID REFERENCES persons(id),
    criticality TEXT CHECK (criticality IN ('critical', 'high', 'medium', 'low')),
    sovereignty_status TEXT, -- 'self-hosted', 'vendor-controlled', 'hybrid'
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS creature_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source_creature_id UUID NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    target_creature_id UUID NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    dependency_type TEXT NOT NULL, -- 'runs_on', 'depends_on', 'uses_api', 'stores_data_in'
    criticality TEXT CHECK (criticality IN ('critical', 'high', 'medium', 'low')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- PEOPLE & ROLES (Identity Layer)
-- ============================================================================

CREATE TABLE IF NOT EXISTS persons (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    role TEXT, -- 'ciso', 'engineer', 'compliance_officer', etc.
    department TEXT,
    employment_type TEXT, -- 'full-time', 'contractor', 'vendor'
    start_date DATE,
    end_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- COMPLIANCE FRAMEWORKS (OSS Standards)
-- ============================================================================

CREATE TABLE IF NOT EXISTS compliance_frameworks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT UNIQUE NOT NULL, -- 'SOC2', 'ISO27001', 'NIST-800-53', etc.
    version TEXT NOT NULL,
    source TEXT NOT NULL, -- 'OSCAL', 'ComplianceForge-SCF', 'CSA-CCM', 'Custom'
    description TEXT,
    framework_url TEXT,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Example data for compliance frameworks
INSERT INTO compliance_frameworks (name, version, source, description, framework_url) VALUES
('SOC2', '2017', 'AICPA', 'Service Organization Control 2 - Trust Services Criteria', 'https://www.aicpa.org/soc2'),
('ISO27001', '2022', 'ISO', 'Information Security Management System', 'https://www.iso.org/standard/27001'),
('NIST-800-53', 'Rev5', 'NIST-OSCAL', 'Security and Privacy Controls for Information Systems', 'https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final'),
('NIST-CSF', '2.0', 'NIST', 'Cybersecurity Framework', 'https://www.nist.gov/cyberframework'),
('CSA-CCM', 'v4', 'Cloud Security Alliance', 'Cloud Controls Matrix', 'https://cloudsecurityalliance.org/research/cloud-controls-matrix'),
('HIPAA', '2013', 'HHS', 'Health Insurance Portability and Accountability Act', 'https://www.hhs.gov/hipaa'),
('PCI-DSS', 'v4.0', 'PCI-SSC', 'Payment Card Industry Data Security Standard', 'https://www.pcisecuritystandards.org/'),
('GDPR', '2018', 'EU', 'General Data Protection Regulation', 'https://gdpr.eu/')
ON CONFLICT (name) DO NOTHING;

-- ============================================================================
-- CONTROL DOMAINS (Control Categories)
-- ============================================================================

CREATE TABLE IF NOT EXISTS control_domains (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    framework_id UUID NOT NULL REFERENCES compliance_frameworks(id) ON DELETE CASCADE,
    domain_code TEXT NOT NULL, -- 'CC1', 'A.5', etc.
    domain_name TEXT NOT NULL, -- 'Control Environment', 'Organization of Information Security'
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(framework_id, domain_code)
);

-- SOC 2 Trust Services Criteria
INSERT INTO control_domains (framework_id, domain_code, domain_name, description) VALUES
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC1', 'Control Environment', 'The foundation for the system of internal control'),
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC2', 'Communication and Information', 'Communication and information systems support the internal control'),
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC3', 'Risk Assessment', 'Risks to achieving entity objectives are identified and assessed'),
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC4', 'Monitoring Activities', 'Monitoring activities are in place'),
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC5', 'Control Activities', 'Control activities support achieving entity objectives'),
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC6', 'Logical and Physical Access Controls', 'Logical and physical access controls'),
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC7', 'System Operations', 'System operations manage systems and detect anomalies'),
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC8', 'Change Management', 'Changes to the system are managed'),
((SELECT id FROM compliance_frameworks WHERE name = 'SOC2'), 'CC9', 'Risk Mitigation', 'Risk mitigation activities are performed')
ON CONFLICT DO NOTHING;

-- ============================================================================
-- CONTROLS (The actual requirements)
-- ============================================================================

CREATE TABLE IF NOT EXISTS controls (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    domain_id UUID NOT NULL REFERENCES control_domains(id) ON DELETE CASCADE,
    control_code TEXT NOT NULL, -- 'CC6.1', 'A.5.1.1', etc.
    control_name TEXT NOT NULL,
    control_description TEXT NOT NULL,
    control_type TEXT CHECK (control_type IN ('preventive', 'detective', 'corrective', 'directive')),
    implementation_guidance TEXT,
    testing_procedures TEXT,
    is_key_control BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb,
    UNIQUE(domain_id, control_code)
);

-- Sample SOC 2 CC6 controls (Access Controls)
INSERT INTO controls (domain_id, control_code, control_name, control_description, control_type, implementation_guidance, testing_procedures, is_key_control) VALUES
(
    (SELECT id FROM control_domains WHERE domain_code = 'CC6' AND framework_id = (SELECT id FROM compliance_frameworks WHERE name = 'SOC2')),
    'CC6.1',
    'Logical Access - Authentication',
    'The entity implements logical access security software, infrastructure, and architectures over protected information assets to protect them from security events to meet the entity''s objectives.',
    'preventive',
    'Implement MFA, strong password policies, session management',
    'Review authentication configs in Keycloak/IAM systems. Verify MFA is enforced for all users. Check Wazuh logs for authentication events.',
    true
),
(
    (SELECT id FROM control_domains WHERE domain_code = 'CC6' AND framework_id = (SELECT id FROM compliance_frameworks WHERE name = 'SOC2')),
    'CC6.2',
    'Access Authorization',
    'Prior to issuing system credentials and granting system access, the entity registers and authorizes new internal and external users whose access is administered by the entity.',
    'preventive',
    'Implement formal access request/approval workflows. Maintain access provisioning logs.',
    'Review user provisioning tickets. Verify approval records exist. Check for orphaned accounts.',
    true
),
(
    (SELECT id FROM control_domains WHERE domain_code = 'CC6' AND framework_id = (SELECT id FROM compliance_frameworks WHERE name = 'SOC2')),
    'CC6.3',
    'Access Reviews',
    'The entity authorizes, modifies, or removes access to data, software, functions, and other protected information assets based on roles, responsibilities, or the system design and changes.',
    'detective',
    'Quarterly access reviews by asset owners. Document review process and findings.',
    'Obtain evidence of quarterly access reviews. Verify remediation of findings.',
    true
);

-- ============================================================================
-- ASSETS (Extended from creatures)
-- ============================================================================

CREATE TABLE IF NOT EXISTS assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creature_id UUID UNIQUE REFERENCES creatures(id) ON DELETE CASCADE,
    asset_type TEXT NOT NULL, -- 'hardware', 'software', 'data', 'facility', 'person'
    classification TEXT CHECK (classification IN ('public', 'internal', 'confidential', 'restricted')),
    owner_id UUID REFERENCES persons(id),
    custodian_id UUID REFERENCES persons(id),
    location TEXT,
    value_usd NUMERIC(12, 2),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- RISKS
-- ============================================================================

CREATE TABLE IF NOT EXISTS risks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    risk_name TEXT NOT NULL,
    risk_description TEXT NOT NULL,
    risk_category TEXT, -- 'security', 'operational', 'compliance', 'financial', 'reputational'
    threat_source TEXT, -- 'external attacker', 'insider threat', 'natural disaster', 'vendor failure'
    asset_id UUID REFERENCES assets(id) ON DELETE SET NULL,
    likelihood TEXT CHECK (likelihood IN ('very_low', 'low', 'medium', 'high', 'very_high')),
    impact TEXT CHECK (impact IN ('very_low', 'low', 'medium', 'high', 'very_high')),
    inherent_risk_score INT GENERATED ALWAYS AS (
        CASE likelihood
            WHEN 'very_low' THEN 1
            WHEN 'low' THEN 2
            WHEN 'medium' THEN 3
            WHEN 'high' THEN 4
            WHEN 'very_high' THEN 5
        END *
        CASE impact
            WHEN 'very_low' THEN 1
            WHEN 'low' THEN 2
            WHEN 'medium' THEN 3
            WHEN 'high' THEN 4
            WHEN 'very_high' THEN 5
        END
    ) STORED,
    residual_risk_score INT,
    risk_owner_id UUID REFERENCES persons(id),
    status TEXT CHECK (status IN ('identified', 'assessed', 'mitigated', 'accepted', 'transferred', 'closed')),
    identified_date DATE DEFAULT CURRENT_DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- POLICIES (Documented rules/procedures)
-- ============================================================================

CREATE TABLE IF NOT EXISTS policies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    policy_name TEXT UNIQUE NOT NULL,
    policy_version TEXT NOT NULL DEFAULT '1.0',
    policy_type TEXT, -- 'security', 'privacy', 'hr', 'it', 'business'
    description TEXT,
    owner_id UUID REFERENCES persons(id),
    approver_id UUID REFERENCES persons(id),
    approval_date DATE,
    effective_date DATE,
    review_frequency_days INT DEFAULT 365,
    next_review_date DATE,
    document_url TEXT, -- Link to Confluence/Google Docs
    status TEXT CHECK (status IN ('draft', 'review', 'approved', 'archived')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- CONTROL IMPLEMENTATIONS (How controls are implemented)
-- ============================================================================

CREATE TABLE IF NOT EXISTS control_implementations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    control_id UUID NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    implementation_description TEXT NOT NULL,
    implementation_status TEXT CHECK (implementation_status IN ('not_implemented', 'planned', 'partially_implemented', 'implemented', 'not_applicable')),
    implementation_date DATE,
    responsible_party_id UUID REFERENCES persons(id),
    policy_id UUID REFERENCES policies(id),
    creature_id UUID REFERENCES creatures(id), -- What system implements this control
    testing_frequency TEXT, -- 'daily', 'weekly', 'monthly', 'quarterly', 'annually'
    last_test_date DATE,
    next_test_date DATE,
    automation_level TEXT CHECK (automation_level IN ('manual', 'semi_automated', 'fully_automated')),
    automation_tool TEXT, -- 'wazuh', 'keycloak', 'openscap', etc.
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- RISK-CONTROL MAPPING (Controls mitigate risks)
-- ============================================================================

CREATE TABLE IF NOT EXISTS risk_control_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    risk_id UUID NOT NULL REFERENCES risks(id) ON DELETE CASCADE,
    control_id UUID NOT NULL REFERENCES controls(id) ON DELETE CASCADE,
    mitigation_effectiveness TEXT CHECK (mitigation_effectiveness IN ('low', 'medium', 'high')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(risk_id, control_id)
);

-- ============================================================================
-- EVIDENCE (Proof that controls work)
-- ============================================================================

CREATE TABLE IF NOT EXISTS evidence (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    evidence_name TEXT NOT NULL,
    evidence_type TEXT NOT NULL, -- 'screenshot', 'log_export', 'configuration_file', 'policy_document', 'test_result', 'attestation'
    control_implementation_id UUID REFERENCES control_implementations(id) ON DELETE CASCADE,
    collection_method TEXT CHECK (collection_method IN ('manual', 'automated', 'api')),
    collection_timestamp TIMESTAMPTZ DEFAULT NOW(),
    evidence_period_start DATE,
    evidence_period_end DATE,
    file_path TEXT, -- Path to stored evidence file
    file_hash TEXT, -- SHA256 hash for integrity
    source_system TEXT, -- 'wazuh', 'keycloak', 'confluence', 'github', etc.
    source_query TEXT, -- API query or command used to collect evidence
    collected_by_id UUID REFERENCES persons(id),
    reviewer_id UUID REFERENCES persons(id),
    review_status TEXT CHECK (review_status IN ('pending', 'approved', 'rejected', 'needs_clarification')),
    review_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- ============================================================================
-- AUDIT FINDINGS (Issues discovered during testing)
-- ============================================================================

CREATE TABLE IF NOT EXISTS audit_findings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    finding_title TEXT NOT NULL,
    finding_description TEXT NOT NULL,
    severity TEXT CHECK (severity IN ('critical', 'high', 'medium', 'low', 'informational')),
    control_implementation_id UUID REFERENCES control_implementations(id),
    evidence_id UUID REFERENCES evidence(id),
    identified_date DATE DEFAULT CURRENT_DATE,
    identified_by_id UUID REFERENCES persons(id),
    status TEXT CHECK (status IN ('open', 'in_progress', 'resolved', 'risk_accepted', 'false_positive')),
    remediation_plan TEXT,
    remediation_owner_id UUID REFERENCES persons(id),
    due_date DATE,
    resolution_date DATE,
    resolution_notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- QUESTIONNAIRES (Customer security assessments)
-- ============================================================================

CREATE TABLE IF NOT EXISTS questionnaire_templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_name TEXT UNIQUE NOT NULL,
    template_type TEXT, -- 'vendor_assessment', 'customer_audit', 'internal_review'
    framework_id UUID REFERENCES compliance_frameworks(id),
    description TEXT,
    version TEXT DEFAULT '1.0',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS questionnaire_questions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    template_id UUID NOT NULL REFERENCES questionnaire_templates(id) ON DELETE CASCADE,
    question_number TEXT NOT NULL,
    question_text TEXT NOT NULL,
    question_category TEXT, -- 'access_control', 'encryption', 'incident_response', etc.
    control_id UUID REFERENCES controls(id), -- Maps question to specific control
    answer_type TEXT CHECK (answer_type IN ('yes_no', 'text', 'multiple_choice', 'file_upload')),
    required BOOLEAN DEFAULT false,
    help_text TEXT,
    suggested_evidence_types TEXT[], -- Array of evidence types that could answer this
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(template_id, question_number)
);

CREATE TABLE IF NOT EXISTS questionnaire_responses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    question_id UUID NOT NULL REFERENCES questionnaire_questions(id) ON DELETE CASCADE,
    respondent_id UUID REFERENCES persons(id),
    response_text TEXT,
    evidence_ids UUID[], -- Array of evidence IDs that support this answer
    confidence_score NUMERIC(3, 2), -- AI confidence in auto-generated answer (0.00-1.00)
    is_auto_generated BOOLEAN DEFAULT false,
    requires_human_review BOOLEAN DEFAULT false,
    reviewed_by_id UUID REFERENCES persons(id),
    review_timestamp TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- EVIDENCE COLLECTION JOBS (Automation tracking)
-- ============================================================================

CREATE TABLE IF NOT EXISTS evidence_collection_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    job_name TEXT NOT NULL,
    job_type TEXT NOT NULL, -- 'wazuh_logs', 'keycloak_config', 'github_audit', 'openscap_scan', etc.
    control_implementation_id UUID REFERENCES control_implementations(id),
    schedule_cron TEXT, -- Cron expression for scheduled collection
    last_run_timestamp TIMESTAMPTZ,
    last_run_status TEXT CHECK (last_run_status IN ('success', 'failed', 'partial', 'skipped')),
    last_run_error TEXT,
    next_run_timestamp TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT true,
    source_system TEXT NOT NULL,
    collection_config JSONB DEFAULT '{}'::jsonb, -- System-specific config (API endpoints, queries, etc.)
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================================
-- VENDOR RISK (Third-party dependencies)
-- ============================================================================

CREATE TABLE IF NOT EXISTS vendors (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_name TEXT UNIQUE NOT NULL,
    vendor_type TEXT, -- 'infrastructure', 'saas', 'professional_services', etc.
    criticality TEXT CHECK (criticality IN ('critical', 'high', 'medium', 'low')),
    contract_start_date DATE,
    contract_end_date DATE,
    primary_contact_name TEXT,
    primary_contact_email TEXT,
    last_security_review_date DATE,
    next_security_review_date DATE,
    has_soc2_report BOOLEAN DEFAULT false,
    soc2_report_date DATE,
    has_iso27001_cert BOOLEAN DEFAULT false,
    iso27001_cert_date DATE,
    status TEXT CHECK (status IN ('active', 'under_review', 'terminated', 'offboarding')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS vendor_creature_mappings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    vendor_id UUID NOT NULL REFERENCES vendors(id) ON DELETE CASCADE,
    creature_id UUID NOT NULL REFERENCES creatures(id) ON DELETE CASCADE,
    dependency_nature TEXT, -- What does this creature depend on the vendor for
    kill_switch_exists BOOLEAN DEFAULT false,
    kill_switch_plan TEXT,
    estimated_migration_days INT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(vendor_id, creature_id)
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_creatures_class ON creatures(creature_class);
CREATE INDEX idx_creatures_domain ON creatures(creature_domain);
CREATE INDEX idx_creatures_owner ON creatures(owner_id);
CREATE INDEX idx_creature_deps_source ON creature_dependencies(source_creature_id);
CREATE INDEX idx_creature_deps_target ON creature_dependencies(target_creature_id);

CREATE INDEX idx_controls_domain ON controls(domain_id);
CREATE INDEX idx_controls_code ON controls(control_code);
CREATE INDEX idx_control_implementations_control ON control_implementations(control_id);
CREATE INDEX idx_control_implementations_creature ON control_implementations(creature_id);

CREATE INDEX idx_evidence_control_impl ON evidence(control_implementation_id);
CREATE INDEX idx_evidence_collection_timestamp ON evidence(collection_timestamp);
CREATE INDEX idx_evidence_source_system ON evidence(source_system);

CREATE INDEX idx_risks_asset ON risks(asset_id);
CREATE INDEX idx_risks_owner ON risks(risk_owner_id);
CREATE INDEX idx_risks_status ON risks(status);

CREATE INDEX idx_policies_owner ON policies(owner_id);
CREATE INDEX idx_policies_status ON policies(status);

CREATE INDEX idx_questionnaire_responses_question ON questionnaire_responses(question_id);
CREATE INDEX idx_audit_findings_control_impl ON audit_findings(control_implementation_id);
CREATE INDEX idx_audit_findings_status ON audit_findings(status);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Compliance Coverage View: Which controls are implemented and tested
CREATE OR REPLACE VIEW v_compliance_coverage AS
SELECT 
    cf.name AS framework_name,
    cd.domain_code,
    cd.domain_name,
    c.control_code,
    c.control_name,
    ci.implementation_status,
    ci.automation_level,
    ci.last_test_date,
    ci.next_test_date,
    p.full_name AS responsible_party,
    COUNT(e.id) AS evidence_count,
    MAX(e.collection_timestamp) AS latest_evidence_date
FROM compliance_frameworks cf
JOIN control_domains cd ON cf.id = cd.framework_id
JOIN controls c ON cd.id = c.domain_id
LEFT JOIN control_implementations ci ON c.id = ci.control_id
LEFT JOIN persons p ON ci.responsible_party_id = p.id
LEFT JOIN evidence e ON ci.id = e.control_implementation_id
GROUP BY cf.name, cd.domain_code, cd.domain_name, c.control_code, c.control_name, 
         ci.implementation_status, ci.automation_level, ci.last_test_date, ci.next_test_date, p.full_name;

-- Risk Register View
CREATE OR REPLACE VIEW v_risk_register AS
SELECT 
    r.risk_name,
    r.risk_category,
    r.threat_source,
    r.likelihood,
    r.impact,
    r.inherent_risk_score,
    r.residual_risk_score,
    r.status,
    a.creature_id,
    cr.name AS asset_name,
    p.full_name AS risk_owner,
    STRING_AGG(DISTINCT c.control_code, ', ') AS mitigating_controls
FROM risks r
LEFT JOIN assets a ON r.asset_id = a.id
LEFT JOIN creatures cr ON a.creature_id = cr.id
LEFT JOIN persons p ON r.risk_owner_id = p.id
LEFT JOIN risk_control_mappings rcm ON r.id = rcm.risk_id
LEFT JOIN controls c ON rcm.control_id = c.id
GROUP BY r.id, r.risk_name, r.risk_category, r.threat_source, r.likelihood, r.impact,
         r.inherent_risk_score, r.residual_risk_score, r.status, a.creature_id, cr.name, p.full_name;

-- Audit Readiness Dashboard
CREATE OR REPLACE VIEW v_audit_readiness AS
SELECT 
    framework_name,
    COUNT(*) AS total_controls,
    COUNT(*) FILTER (WHERE implementation_status = 'implemented') AS implemented_controls,
    COUNT(*) FILTER (WHERE implementation_status = 'not_implemented') AS not_implemented_controls,
    COUNT(*) FILTER (WHERE evidence_count > 0) AS controls_with_evidence,
    COUNT(*) FILTER (WHERE automation_level = 'fully_automated') AS automated_controls,
    ROUND(
        100.0 * COUNT(*) FILTER (WHERE implementation_status = 'implemented') / COUNT(*),
        2
    ) AS implementation_percentage
FROM v_compliance_coverage
GROUP BY framework_name;

-- ============================================================================
-- FUNCTIONS
-- ============================================================================

-- Function to calculate residual risk after control implementation
CREATE OR REPLACE FUNCTION calculate_residual_risk(
    p_risk_id UUID
) RETURNS INT AS $$
DECLARE
    v_inherent_risk INT;
    v_control_effectiveness NUMERIC;
    v_residual_risk INT;
BEGIN
    -- Get inherent risk score
    SELECT inherent_risk_score INTO v_inherent_risk
    FROM risks
    WHERE id = p_risk_id;
    
    -- Calculate average control effectiveness
    SELECT AVG(
        CASE mitigation_effectiveness
            WHEN 'low' THEN 0.3
            WHEN 'medium' THEN 0.6
            WHEN 'high' THEN 0.9
            ELSE 0
        END
    ) INTO v_control_effectiveness
    FROM risk_control_mappings rcm
    JOIN control_implementations ci ON rcm.control_id = ci.control_id
    WHERE rcm.risk_id = p_risk_id
    AND ci.implementation_status = 'implemented';
    
    -- Calculate residual risk
    v_residual_risk := CEIL(v_inherent_risk * (1 - COALESCE(v_control_effectiveness, 0)));
    
    RETURN v_residual_risk;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update residual risk when controls change
CREATE OR REPLACE FUNCTION update_residual_risk_trigger()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE risks
    SET residual_risk_score = calculate_residual_risk(NEW.risk_id),
        updated_at = NOW()
    WHERE id = NEW.risk_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_residual_risk
AFTER INSERT OR UPDATE ON risk_control_mappings
FOR EACH ROW
EXECUTE FUNCTION update_residual_risk_trigger();

-- Function to auto-archive old evidence
CREATE OR REPLACE FUNCTION archive_old_evidence()
RETURNS void AS $$
BEGIN
    -- Move evidence older than 7 years to archive table (compliance retention)
    -- This is a placeholder - implement actual archival logic based on requirements
    UPDATE evidence
    SET metadata = jsonb_set(metadata, '{archived}', 'true'::jsonb)
    WHERE collection_timestamp < NOW() - INTERVAL '7 years'
    AND metadata->>'archived' IS NULL;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- SAMPLE DATA (for testing)
-- ============================================================================

-- Insert sample person
INSERT INTO persons (full_name, email, role, department) VALUES
('Jane Smith', 'jane.smith@example.com', 'ciso', 'security'),
('John Doe', 'john.doe@example.com', 'compliance_officer', 'compliance'),
('Alice Johnson', 'alice@example.com', 'engineer', 'engineering')
ON CONFLICT (email) DO NOTHING;

-- Insert sample policy
INSERT INTO policies (policy_name, policy_version, policy_type, description, owner_id, status, approval_date, effective_date) VALUES
(
    'Access Control Policy',
    '2.0',
    'security',
    'Defines requirements for logical and physical access to company systems and facilities',
    (SELECT id FROM persons WHERE email = 'jane.smith@example.com'),
    'approved',
    '2025-01-01',
    '2025-01-15'
)
ON CONFLICT (policy_name) DO NOTHING;

COMMENT ON TABLE creatures IS 'Core entity tracking all technology assets and dependencies';
COMMENT ON TABLE controls IS 'Compliance control requirements from various frameworks';
COMMENT ON TABLE evidence IS 'Proof that controls are implemented and operating effectively';
COMMENT ON TABLE risks IS 'Risk register tracking threats and their mitigation';
COMMENT ON TABLE control_implementations IS 'How controls are implemented in the organization';
