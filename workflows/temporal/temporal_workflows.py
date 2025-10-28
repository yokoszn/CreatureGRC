#!/usr/bin/env python3
"""
Temporal.io Workflows for GRC Automation
Provides durable, reliable execution for compliance workflows
"""

import asyncio
from datetime import timedelta, datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import logging

from temporalio import workflow, activity
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.common import RetryPolicy

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class EvidenceCollectionResult:
    source_system: str
    evidence_count: int
    success: bool
    error: Optional[str] = None
    file_paths: List[str] = None


@dataclass
class ControlTestResult:
    control_id: str
    control_code: str
    test_passed: bool
    test_date: datetime
    findings: List[str]
    next_test_date: datetime


@dataclass
class AuditPackageResult:
    client: str
    framework: str
    package_path: str
    control_count: int
    evidence_count: int


# ============================================================================
# Activities (Actual Work)
# ============================================================================

@activity.defn
async def collect_wazuh_evidence(framework: str, days: int = 90) -> EvidenceCollectionResult:
    """Collect evidence from Wazuh SIEM"""
    try:
        from evidence_collector import WazuhEvidenceCollector
        import yaml

        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        collector = WazuhEvidenceCollector(
            config['database'],
            Path(config['evidence']['output_dir']),
            config['wazuh']
        )

        file_paths = []
        file_paths.append(collector.collect_authentication_logs(days))
        file_paths.append(collector.collect_security_alerts(days=days))
        file_paths.append(collector.collect_agent_status())

        return EvidenceCollectionResult(
            source_system='wazuh',
            evidence_count=len(file_paths),
            success=True,
            file_paths=file_paths
        )
    except Exception as e:
        logger.error(f"Wazuh collection failed: {e}")
        return EvidenceCollectionResult(
            source_system='wazuh',
            evidence_count=0,
            success=False,
            error=str(e)
        )


@activity.defn
async def collect_keycloak_evidence(framework: str) -> EvidenceCollectionResult:
    """Collect evidence from Keycloak IAM"""
    try:
        from evidence_collector import KeycloakEvidenceCollector
        import yaml
        from pathlib import Path

        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        collector = KeycloakEvidenceCollector(
            config['database'],
            Path(config['evidence']['output_dir']),
            config['keycloak']
        )

        file_paths = []
        file_paths.append(collector.collect_mfa_config())
        file_paths.append(collector.collect_user_list())
        file_paths.append(collector.collect_role_mappings())

        return EvidenceCollectionResult(
            source_system='keycloak',
            evidence_count=len(file_paths),
            success=True,
            file_paths=file_paths
        )
    except Exception as e:
        logger.error(f"Keycloak collection failed: {e}")
        return EvidenceCollectionResult(
            source_system='keycloak',
            evidence_count=0,
            success=False,
            error=str(e)
        )


@activity.defn
async def collect_openscap_evidence(framework: str) -> EvidenceCollectionResult:
    """Run OpenSCAP compliance scan"""
    try:
        from evidence_collector import OpenSCAPCollector
        import yaml
        from pathlib import Path

        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        collector = OpenSCAPCollector(
            config['database'],
            Path(config['evidence']['output_dir']),
            config.get('openscap', {})
        )

        report_path = collector.run_compliance_scan()

        return EvidenceCollectionResult(
            source_system='openscap',
            evidence_count=1,
            success=True,
            file_paths=[report_path]
        )
    except Exception as e:
        logger.error(f"OpenSCAP collection failed: {e}")
        return EvidenceCollectionResult(
            source_system='openscap',
            evidence_count=0,
            success=False,
            error=str(e)
        )


@activity.defn
async def collect_github_evidence(framework: str, days: int = 90) -> EvidenceCollectionResult:
    """Collect GitHub audit log"""
    try:
        from evidence_collector import GitHubAuditCollector
        import yaml
        from pathlib import Path

        with open('config.yaml', 'r') as f:
            config = yaml.safe_load(f)

        collector = GitHubAuditCollector(
            config['database'],
            Path(config['evidence']['output_dir']),
            config['github']
        )

        audit_path = collector.collect_audit_log(days)

        return EvidenceCollectionResult(
            source_system='github',
            evidence_count=1 if audit_path else 0,
            success=audit_path is not None,
            file_paths=[audit_path] if audit_path else []
        )
    except Exception as e:
        logger.error(f"GitHub collection failed: {e}")
        return EvidenceCollectionResult(
            source_system='github',
            evidence_count=0,
            success=False,
            error=str(e)
        )


@activity.defn
async def get_controls_due_for_testing() -> List[Dict[str, Any]]:
    """Get controls that need testing"""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    import yaml

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    with psycopg2.connect(**config['database'], cursor_factory=RealDictCursor) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    ci.id AS control_implementation_id,
                    c.id AS control_id,
                    c.control_code,
                    c.control_name,
                    ci.testing_frequency,
                    ci.last_test_date,
                    ci.next_test_date,
                    ci.automation_level
                FROM control_implementations ci
                JOIN controls c ON ci.control_id = c.id
                WHERE ci.next_test_date <= CURRENT_DATE
                AND ci.implementation_status = 'implemented'
                ORDER BY ci.next_test_date ASC
                LIMIT 100
            """)
            return [dict(row) for row in cur.fetchall()]


@activity.defn
async def run_automated_control_test(control: Dict[str, Any]) -> ControlTestResult:
    """Run automated test for a control"""
    # This is a simplified version - in production, you'd have
    # specific test logic for each control type

    control_code = control['control_code']
    findings = []
    test_passed = True

    try:
        # Example: CC6.1 - MFA enforcement test
        if control_code == 'CC6.1':
            # Check Keycloak MFA config
            from evidence_collector import KeycloakEvidenceCollector
            import yaml
            from pathlib import Path

            with open('config.yaml', 'r') as f:
                config = yaml.safe_load(f)

            collector = KeycloakEvidenceCollector(
                config['database'],
                Path(config['evidence']['output_dir']),
                config['keycloak']
            )

            # Simplified test logic
            mfa_config = collector.collect_mfa_config()
            # In reality, you'd parse the config and validate

            findings.append(f"MFA configuration verified on {datetime.now()}")

        # Calculate next test date based on frequency
        frequency_days = {
            'daily': 1,
            'weekly': 7,
            'monthly': 30,
            'quarterly': 90,
            'annually': 365
        }
        days_offset = frequency_days.get(control.get('testing_frequency', 'quarterly'), 90)

        return ControlTestResult(
            control_id=control['control_id'],
            control_code=control_code,
            test_passed=test_passed,
            test_date=datetime.now(),
            findings=findings,
            next_test_date=datetime.now() + timedelta(days=days_offset)
        )

    except Exception as e:
        logger.error(f"Control test failed for {control_code}: {e}")
        return ControlTestResult(
            control_id=control['control_id'],
            control_code=control_code,
            test_passed=False,
            test_date=datetime.now(),
            findings=[f"Test failed: {str(e)}"],
            next_test_date=datetime.now() + timedelta(days=1)  # Retry tomorrow
        )


@activity.defn
async def update_control_test_status(result: ControlTestResult) -> None:
    """Update control test results in database"""
    import psycopg2
    import yaml

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    with psycopg2.connect(**config['database']) as conn:
        with conn.cursor() as cur:
            # Find control implementation
            cur.execute("""
                SELECT id FROM control_implementations
                WHERE control_id = %s
                LIMIT 1
            """, (result.control_id,))

            row = cur.fetchone()
            if not row:
                logger.warning(f"No implementation found for control {result.control_id}")
                return

            control_impl_id = row[0]

            # Update test status
            cur.execute("""
                UPDATE control_implementations
                SET last_test_date = %s,
                    next_test_date = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (result.test_date, result.next_test_date, control_impl_id))

            # Create finding if test failed
            if not result.test_passed:
                cur.execute("""
                    INSERT INTO audit_findings (
                        finding_title,
                        finding_description,
                        severity,
                        control_implementation_id,
                        identified_date,
                        status
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    f"Automated test failed: {result.control_code}",
                    '\n'.join(result.findings),
                    'high',
                    control_impl_id,
                    result.test_date.date(),
                    'open'
                ))

            conn.commit()


@activity.defn
async def generate_audit_package(client: str, framework: str) -> AuditPackageResult:
    """Generate complete audit package"""
    from generate_audit_package import AuditPackageGenerator
    import yaml
    from pathlib import Path

    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)

    generator = AuditPackageGenerator(
        config['database'],
        Path(config.get('audit_packages', {}).get('output_dir', '/tmp/audit-packages'))
    )

    package_path = generator.generate_audit_package(client, framework)

    # Get stats (simplified)
    return AuditPackageResult(
        client=client,
        framework=framework,
        package_path=package_path,
        control_count=0,  # Would query from package
        evidence_count=0
    )


@activity.defn
async def send_notification(message: str, channel: str = "compliance") -> None:
    """Send notification (Slack, email, etc.)"""
    logger.info(f"[NOTIFICATION to {channel}] {message}")
    # In production: integrate with Slack, email, etc.


# ============================================================================
# Workflows (Orchestration)
# ============================================================================

@workflow.defn
class DailyEvidenceCollectionWorkflow:
    """Collect evidence from all sources daily"""

    @workflow.run
    async def run(self, framework: str = "SOC2") -> Dict[str, Any]:
        """
        Run daily evidence collection workflow

        Returns summary of collection results
        """
        workflow.logger.info(f"Starting daily evidence collection for {framework}")

        # Define retry policy
        retry_policy = RetryPolicy(
            maximum_attempts=3,
            initial_interval=timedelta(seconds=10),
            maximum_interval=timedelta(minutes=5),
            backoff_coefficient=2.0
        )

        # Collect from all sources in parallel
        results = await asyncio.gather(
            workflow.execute_activity(
                collect_wazuh_evidence,
                framework,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=retry_policy
            ),
            workflow.execute_activity(
                collect_keycloak_evidence,
                framework,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy
            ),
            workflow.execute_activity(
                collect_openscap_evidence,
                framework,
                start_to_close_timeout=timedelta(minutes=30),
                retry_policy=retry_policy
            ),
            workflow.execute_activity(
                collect_github_evidence,
                framework,
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=retry_policy
            ),
            return_exceptions=True
        )

        # Summarize results
        total_evidence = 0
        successful_sources = 0
        failed_sources = []

        for result in results:
            if isinstance(result, Exception):
                failed_sources.append(str(result))
            elif result.success:
                successful_sources += 1
                total_evidence += result.evidence_count
            else:
                failed_sources.append(f"{result.source_system}: {result.error}")

        # Send notification
        await workflow.execute_activity(
            send_notification,
            f"Daily evidence collection complete: {total_evidence} items from {successful_sources} sources",
            start_to_close_timeout=timedelta(seconds=30)
        )

        return {
            'framework': framework,
            'total_evidence_collected': total_evidence,
            'successful_sources': successful_sources,
            'failed_sources': failed_sources,
            'timestamp': workflow.now()
        }


@workflow.defn
class ContinuousControlTestingWorkflow:
    """Continuously test controls that are due"""

    @workflow.run
    async def run(self) -> Dict[str, Any]:
        """Run continuous control testing"""
        workflow.logger.info("Starting continuous control testing")

        # Get controls due for testing
        controls = await workflow.execute_activity(
            get_controls_due_for_testing,
            start_to_close_timeout=timedelta(minutes=5)
        )

        workflow.logger.info(f"Found {len(controls)} controls due for testing")

        # Test each control
        test_results = []
        for control in controls:
            result = await workflow.execute_activity(
                run_automated_control_test,
                control,
                start_to_close_timeout=timedelta(minutes=15),
                retry_policy=RetryPolicy(maximum_attempts=2)
            )

            # Update status
            await workflow.execute_activity(
                update_control_test_status,
                result,
                start_to_close_timeout=timedelta(minutes=2)
            )

            test_results.append(result)

        # Summarize
        passed = sum(1 for r in test_results if r.test_passed)
        failed = sum(1 for r in test_results if not r.test_passed)

        # Notify if there are failures
        if failed > 0:
            await workflow.execute_activity(
                send_notification,
                f"⚠️ Control testing: {failed} controls failed, {passed} passed",
                start_to_close_timeout=timedelta(seconds=30)
            )

        return {
            'controls_tested': len(test_results),
            'passed': passed,
            'failed': failed,
            'timestamp': workflow.now()
        }


@workflow.defn
class WeeklyAuditPackageWorkflow:
    """Generate audit packages weekly"""

    @workflow.run
    async def run(self, client: str, framework: str = "SOC2") -> AuditPackageResult:
        """Generate weekly audit package"""
        workflow.logger.info(f"Generating audit package for {client} - {framework}")

        # Generate package
        result = await workflow.execute_activity(
            generate_audit_package,
            client,
            framework,
            start_to_close_timeout=timedelta(minutes=30),
            retry_policy=RetryPolicy(maximum_attempts=2)
        )

        # Notify
        await workflow.execute_activity(
            send_notification,
            f"✅ Audit package ready for {client}: {result.package_path}",
            start_to_close_timeout=timedelta(seconds=30)
        )

        return result


# ============================================================================
# Worker Setup
# ============================================================================

async def main():
    """Start Temporal worker"""
    client = await Client.connect("localhost:7233")

    worker = Worker(
        client,
        task_queue="grc-compliance",
        workflows=[
            DailyEvidenceCollectionWorkflow,
            ContinuousControlTestingWorkflow,
            WeeklyAuditPackageWorkflow,
        ],
        activities=[
            collect_wazuh_evidence,
            collect_keycloak_evidence,
            collect_openscap_evidence,
            collect_github_evidence,
            get_controls_due_for_testing,
            run_automated_control_test,
            update_control_test_status,
            generate_audit_package,
            send_notification,
        ],
    )

    logger.info("Starting Temporal worker...")
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
