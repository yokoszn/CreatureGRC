#!/usr/bin/env python3
"""
Cloud & SaaS Collectors for CreatureGRC

Discovers and tracks cloud services used by developers:
- Vercel projects and deployments
- Supabase database instances
- Neon serverless PostgreSQL databases
- GitHub repositories and actions
- Cloudflare DNS zones and CDN configs
- v0.dev AI-generated projects

Usage:
    python cloud_collectors.py --platform vercel
    python cloud_collectors.py --platform all
    python cloud_collectors.py --identity alex.johnson
"""

import os
import sys
import json
import requests
from datetime import datetime
from typing import List, Dict, Optional
import psycopg2


class VercelCollector:
    """Collect Vercel projects and detect v0.dev usage."""

    def __init__(self, api_token: str, team_id: Optional[str] = None):
        self.api_token = api_token
        self.team_id = team_id
        self.base_url = "https://api.vercel.com"

    def collect_projects(self) -> List[Dict]:
        """Collect all Vercel projects."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        url = f"{self.base_url}/v9/projects"

        if self.team_id:
            url += f"?teamId={self.team_id}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        projects = response.json()["projects"]
        creatures = []

        for project in projects:
            # Detect if project was created via v0.dev
            is_v0_project = self._detect_v0_source(project)

            # Count environment variables that might be secrets
            secret_count = self._count_secrets(project.get("env", []))

            creature = {
                "name": project["name"],
                "type": "application",
                "platform": "vercel",
                "category": "cloud-saas",
                "created_at": project["createdAt"],
                "metadata": {
                    "project_id": project["id"],
                    "url": self._get_project_url(project),
                    "framework": project.get("framework"),
                    "git_repo": project.get("link", {}).get("repo"),
                    "source": "v0.dev" if is_v0_project else "manual",
                    "env_var_count": len(project.get("env", [])),
                    "secret_count": secret_count,
                    "team": project.get("accountId"),
                },
                "controls": ["CM-8", "CM-3", "SA-9", "SC-13"],
                "risks": self._assess_risks(project, is_v0_project, secret_count)
            }

            creatures.append(creature)

        return creatures

    def _detect_v0_source(self, project: Dict) -> bool:
        """Detect if project was created via v0.dev."""
        # Check project metadata for v0.dev indicators
        name = project.get("name", "").lower()
        repo = project.get("link", {}).get("repo", "")

        v0_indicators = [
            "v0-" in name,
            "v0.dev" in repo,
            project.get("createdFrom") == "v0",
        ]

        return any(v0_indicators)

    def _count_secrets(self, env_vars: List[Dict]) -> int:
        """Count environment variables that likely contain secrets."""
        secret_keywords = ["secret", "key", "token", "password", "api"]
        count = 0

        for var in env_vars:
            key = var.get("key", "").lower()
            if any(keyword in key for keyword in secret_keywords):
                count += 1

        return count

    def _get_project_url(self, project: Dict) -> str:
        """Get the production URL for a project."""
        # Try to get custom domain first
        if project.get("alias"):
            return f"https://{project['alias'][0]}"
        return f"https://{project['name']}.vercel.app"

    def _assess_risks(self, project: Dict, is_v0: bool, secret_count: int) -> List[Dict]:
        """Assess risks for a Vercel project."""
        risks = []

        if is_v0:
            risks.append({
                "severity": "medium",
                "type": "shadow_it",
                "message": "Project created via v0.dev without security review"
            })

        if secret_count > 0:
            risks.append({
                "severity": "high",
                "type": "secrets_exposure",
                "message": f"{secret_count} environment variables may contain secrets"
            })

        return risks


class SupabaseCollector:
    """Collect Supabase database instances and scan for sensitive data."""

    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.supabase.com/v1"

    def collect_projects(self) -> List[Dict]:
        """Collect all Supabase projects."""
        headers = {"Authorization": f"Bearer {self.access_token}"}
        url = f"{self.base_url}/projects"

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        projects = response.json()
        creatures = []

        for project in projects:
            # Scan database schema for sensitive tables
            tables = self._scan_database_schema(project)
            data_classification = self._classify_data(tables)

            creature = {
                "name": project["name"],
                "type": "application",
                "platform": "supabase",
                "category": "cloud-saas",
                "created_at": project["created_at"],
                "metadata": {
                    "project_id": project["id"],
                    "region": project["region"],
                    "database_version": project.get("database", {}).get("version"),
                    "plan": project.get("subscription_tier"),
                    "table_count": len(tables),
                    "data_classification": data_classification,
                    "auth_enabled": project.get("settings", {}).get("auth_enabled"),
                    "storage_enabled": project.get("settings", {}).get("storage_enabled"),
                },
                "controls": ["CM-8", "SC-28", "AC-3", "CP-9"],
                "risks": self._assess_data_risks(tables, data_classification)
            }

            creatures.append(creature)

        return creatures

    def _scan_database_schema(self, project: Dict) -> List[str]:
        """Scan database schema to get table names."""
        # This would connect to the database and list tables
        # Simplified for example purposes
        db_url = project.get("database", {}).get("host")

        # In production, connect to DB and query information_schema
        # For now, return mock data
        return ["users", "posts", "comments", "profiles"]

    def _classify_data(self, tables: List[str]) -> str:
        """Classify data based on table names."""
        sensitive_indicators = {
            "pii": ["users", "customers", "profiles", "contacts", "employees"],
            "phi": ["patients", "medical", "health", "prescriptions"],
            "pci": ["payments", "cards", "transactions", "billing"],
            "financial": ["accounts", "invoices", "revenue", "payroll"]
        }

        for classification, keywords in sensitive_indicators.items():
            if any(keyword in table.lower() for table in tables for keyword in keywords):
                return classification.upper()

        return "UNKNOWN"

    def _assess_data_risks(self, tables: List[str], classification: str) -> List[Dict]:
        """Assess data-related risks."""
        risks = []

        if classification in ["PII", "PHI", "PCI"]:
            risks.append({
                "severity": "high",
                "type": "sensitive_data",
                "message": f"Database contains {classification} data without proper classification"
            })

        if "users" in [t.lower() for t in tables] or "customers" in [t.lower() for t in tables]:
            risks.append({
                "severity": "medium",
                "type": "pii_detected",
                "message": "Database likely contains PII (users/customers table detected)"
            })

        return risks


class NeonCollector:
    """Collect Neon serverless PostgreSQL databases."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://console.neon.tech/api/v2"

    def collect_projects(self) -> List[Dict]:
        """Collect all Neon projects."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/projects"

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        projects = response.json()["projects"]
        creatures = []

        for project in projects:
            # Get branches for this project
            branches = self._get_branches(project["id"])

            creature = {
                "name": project["name"],
                "type": "application",
                "platform": "neon",
                "category": "cloud-saas",
                "created_at": project["created_at"],
                "metadata": {
                    "project_id": project["id"],
                    "region": project["region_id"],
                    "platform_id": project["platform_id"],
                    "branch_count": len(branches),
                    "main_branch": next((b for b in branches if b.get("is_primary")), {}).get("name"),
                    "compute_config": project.get("settings", {}).get("compute"),
                },
                "controls": ["CM-8", "SC-28", "CM-3"],
                "risks": []
            }

            creatures.append(creature)

        return creatures

    def _get_branches(self, project_id: str) -> List[Dict]:
        """Get branches for a Neon project."""
        headers = {"Authorization": f"Bearer {self.api_key}"}
        url = f"{self.base_url}/projects/{project_id}/branches"

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        return response.json()["branches"]


class GitHubCollector:
    """Collect GitHub repositories and configuration."""

    def __init__(self, token: str, org: str):
        self.token = token
        self.org = org
        self.base_url = "https://api.github.com"

    def collect_repositories(self) -> List[Dict]:
        """Collect all repositories in organization."""
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"{self.base_url}/orgs/{self.org}/repos"

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        repos = response.json()
        creatures = []

        for repo in repos:
            # Get branch protection
            branch_protection = self._get_branch_protection(repo["name"], repo["default_branch"])

            creature = {
                "name": f"{self.org}/{repo['name']}",
                "type": "application",
                "platform": "github",
                "category": "cloud-saas",
                "created_at": repo["created_at"],
                "metadata": {
                    "repo_id": repo["id"],
                    "private": repo["private"],
                    "default_branch": repo["default_branch"],
                    "language": repo.get("language"),
                    "has_actions": self._check_github_actions(repo["name"]),
                    "branch_protection_enabled": branch_protection is not None,
                    "topics": repo.get("topics", []),
                },
                "controls": ["CM-3", "AC-3", "SA-10", "AU-2"],
                "risks": self._assess_repo_risks(repo, branch_protection)
            }

            creatures.append(creature)

        return creatures

    def _get_branch_protection(self, repo: str, branch: str) -> Optional[Dict]:
        """Check if branch protection is enabled."""
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"{self.base_url}/repos/{self.org}/{repo}/branches/{branch}/protection"

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return response.json()
        return None

    def _check_github_actions(self, repo: str) -> bool:
        """Check if GitHub Actions is enabled."""
        headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        url = f"{self.base_url}/repos/{self.org}/{repo}/actions/workflows"

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            workflows = response.json()
            return workflows.get("total_count", 0) > 0
        return False

    def _assess_repo_risks(self, repo: Dict, branch_protection: Optional[Dict]) -> List[Dict]:
        """Assess repository security risks."""
        risks = []

        if not branch_protection:
            risks.append({
                "severity": "medium",
                "type": "missing_branch_protection",
                "message": f"Branch protection not enabled on {repo['default_branch']}"
            })

        if not repo["private"]:
            risks.append({
                "severity": "low",
                "type": "public_repository",
                "message": "Repository is public"
            })

        return risks


class CloudflareCollector:
    """Collect Cloudflare zones and security configurations."""

    def __init__(self, api_token: str, account_id: str):
        self.api_token = api_token
        self.account_id = account_id
        self.base_url = "https://api.cloudflare.com/client/v4"

    def collect_zones(self) -> List[Dict]:
        """Collect all Cloudflare zones."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        url = f"{self.base_url}/zones?account.id={self.account_id}"

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        zones = response.json()["result"]
        creatures = []

        for zone in zones:
            # Get zone settings
            settings = self._get_zone_settings(zone["id"])

            creature = {
                "name": zone["name"],
                "type": "infrastructure",
                "platform": "cloudflare",
                "category": "cloud-saas",
                "created_at": zone["created_on"],
                "metadata": {
                    "zone_id": zone["id"],
                    "status": zone["status"],
                    "name_servers": zone.get("name_servers", []),
                    "ssl_mode": settings.get("ssl", {}).get("value"),
                    "proxy_enabled": zone.get("paused") is False,
                    "waf_enabled": settings.get("waf", {}).get("value") == "on",
                    "ddos_protection": True,  # Always enabled on Cloudflare
                },
                "controls": ["SC-7", "SC-8", "SC-13", "SI-4"],
                "risks": self._assess_zone_risks(zone, settings)
            }

            creatures.append(creature)

        return creatures

    def _get_zone_settings(self, zone_id: str) -> Dict:
        """Get zone settings."""
        headers = {"Authorization": f"Bearer {self.api_token}"}
        url = f"{self.base_url}/zones/{zone_id}/settings"

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        # Convert list of settings to dict
        settings_list = response.json()["result"]
        return {s["id"]: s for s in settings_list}

    def _assess_zone_risks(self, zone: Dict, settings: Dict) -> List[Dict]:
        """Assess zone security risks."""
        risks = []

        ssl_mode = settings.get("ssl", {}).get("value")
        if ssl_mode not in ["full", "strict"]:
            risks.append({
                "severity": "high",
                "type": "weak_ssl",
                "message": f"SSL/TLS mode is {ssl_mode}, should be 'full' or 'strict'"
            })

        return risks


def main():
    """Main entry point for cloud collectors."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect cloud/SaaS Creatures")
    parser.add_argument("--platform", choices=["vercel", "supabase", "neon", "github", "cloudflare", "all"],
                       default="all", help="Platform to collect from")
    parser.add_argument("--identity", help="Filter by identity (user)")
    args = parser.parse_args()

    # Load configuration from environment
    collectors = []

    if args.platform in ["vercel", "all"]:
        vercel_token = os.getenv("VERCEL_API_TOKEN")
        vercel_team = os.getenv("VERCEL_TEAM_ID")
        if vercel_token:
            collectors.append(("Vercel", VercelCollector(vercel_token, vercel_team)))

    if args.platform in ["supabase", "all"]:
        supabase_token = os.getenv("SUPABASE_ACCESS_TOKEN")
        if supabase_token:
            collectors.append(("Supabase", SupabaseCollector(supabase_token)))

    if args.platform in ["neon", "all"]:
        neon_key = os.getenv("NEON_API_KEY")
        if neon_key:
            collectors.append(("Neon", NeonCollector(neon_key)))

    if args.platform in ["github", "all"]:
        github_token = os.getenv("GITHUB_TOKEN")
        github_org = os.getenv("GITHUB_ORG")
        if github_token and github_org:
            collectors.append(("GitHub", GitHubCollector(github_token, github_org)))

    if args.platform in ["cloudflare", "all"]:
        cf_token = os.getenv("CLOUDFLARE_API_TOKEN")
        cf_account = os.getenv("CLOUDFLARE_ACCOUNT_ID")
        if cf_token and cf_account:
            collectors.append(("Cloudflare", CloudflareCollector(cf_token, cf_account)))

    # Run collectors
    all_creatures = []
    for name, collector in collectors:
        print(f"\n{'='*60}")
        print(f"Scanning {name}...")
        print(f"{'='*60}")

        try:
            if name == "GitHub":
                creatures = collector.collect_repositories()
            elif name == "Cloudflare":
                creatures = collector.collect_zones()
            else:
                creatures = collector.collect_projects()

            print(f"✓ Found {len(creatures)} {name} Creatures")

            # Print summary
            for creature in creatures:
                print(f"  - {creature['name']} ({creature['type']})")
                if creature.get('risks'):
                    for risk in creature['risks']:
                        print(f"    ⚠️  {risk['severity'].upper()}: {risk['message']}")

            all_creatures.extend(creatures)

        except Exception as e:
            print(f"✗ Error collecting from {name}: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"SUMMARY")
    print(f"{'='*60}")
    print(f"Total Creatures discovered: {len(all_creatures)}")

    platforms = {}
    for creature in all_creatures:
        platform = creature['platform']
        platforms[platform] = platforms.get(platform, 0) + 1

    for platform, count in platforms.items():
        print(f"  - {platform}: {count}")

    total_risks = sum(len(c.get('risks', [])) for c in all_creatures)
    print(f"\nTotal risks identified: {total_risks}")

    # TODO: Store creatures in database


if __name__ == "__main__":
    main()
