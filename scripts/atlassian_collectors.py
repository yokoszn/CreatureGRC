#!/usr/bin/env python3
"""
Atlassian (Jira/Confluence) Collectors for CreatureGRC

Discovers and extracts compliance evidence from:
- Confluence: Policies, procedures, SOPs, runbooks
- Jira: Change tickets, incidents, risk items

Usage:
    python atlassian_collectors.py --source confluence
    python atlassian_collectors.py --source jira --jql "project = SEC AND created >= -90d"
    python atlassian_collectors.py --create-tickets --gaps gap-report.json
"""

import os
import re
import json
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from base64 import b64encode


class ConfluenceCollector:
    """Collect and analyze Confluence documentation for compliance evidence."""

    def __init__(self, url: str, email: str, api_token: str):
        self.url = url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.auth = self._create_auth()

    def _create_auth(self):
        """Create Basic Auth header."""
        credentials = f"{self.email}:{self.api_token}"
        token = b64encode(credentials.encode('utf-8')).decode('ascii')
        return {'Authorization': f'Basic {token}'}

    def get_spaces(self, keys: Optional[List[str]] = None) -> List[Dict]:
        """Get Confluence spaces to scan."""
        endpoint = f"{self.url}/rest/api/content"
        params = {'type': 'page', 'limit': 1000}

        if keys:
            # Filter by specific space keys
            spaces = []
            for key in keys:
                params['spaceKey'] = key
                response = requests.get(endpoint, headers=self.auth, params=params)
                response.raise_for_status()
                spaces.extend(response.json()['results'])
            return spaces
        else:
            # Get all spaces
            response = requests.get(endpoint, headers=self.auth, params=params)
            response.raise_for_status()
            return response.json()['results']

    def get_pages_by_label(self, labels: List[str], space_key: Optional[str] = None) -> List[Dict]:
        """Get pages with specific labels."""
        endpoint = f"{self.url}/rest/api/content/search"

        # Build CQL query
        cql_parts = [f'label = "{label}"' for label in labels]
        cql = ' OR '.join(cql_parts)

        if space_key:
            cql = f'({cql}) AND space = "{space_key}"'

        cql = f'type = page AND ({cql})'

        params = {
            'cql': cql,
            'limit': 1000,
            'expand': 'metadata.labels,version,body.storage'
        }

        response = requests.get(endpoint, headers=self.auth, params=params)
        response.raise_for_status()

        return response.json()['results']

    def get_page_content(self, page_id: str) -> Dict:
        """Get full page content including HTML body."""
        endpoint = f"{self.url}/rest/api/content/{page_id}"
        params = {'expand': 'body.storage,version,metadata.labels,history'}

        response = requests.get(endpoint, headers=self.auth, params=params)
        response.raise_for_status()

        return response.json()

    def extract_text_from_html(self, html: str) -> str:
        """Strip HTML tags and return plain text."""
        # Simple HTML tag removal (use BeautifulSoup for production)
        text = re.sub('<[^<]+?>', '', html)
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        return text.strip()

    def extract_controls_with_llm(self, page_title: str, page_content: str) -> List[Dict]:
        """Use LLM to extract compliance controls from policy document."""
        # This would integrate with LiteLLM
        # For now, return mock data

        # In production:
        # 1. Send page content to LiteLLM
        # 2. Prompt: "Extract NIST controls from this policy"
        # 3. Parse structured JSON response

        # Mock control extraction based on keywords
        controls = []

        keyword_map = {
            'access control': ['AC-2', 'AC-3', 'AC-6'],
            'password': ['IA-5', 'IA-5(1)'],
            'authentication': ['IA-2', 'IA-8'],
            'incident': ['IR-1', 'IR-4', 'IR-5', 'IR-6'],
            'backup': ['CP-9', 'CP-10'],
            'change management': ['CM-3', 'CM-4'],
            'configuration': ['CM-2', 'CM-6'],
            'monitoring': ['AU-2', 'AU-6', 'SI-4'],
            'encryption': ['SC-8', 'SC-13', 'SC-28']
        }

        content_lower = page_content.lower()

        for keyword, control_ids in keyword_map.items():
            if keyword in content_lower:
                for control_id in control_ids:
                    controls.append({
                        'control_id': control_id,
                        'framework': 'NIST 800-53 Rev 5',
                        'keyword_match': keyword,
                        'confidence': 'medium'  # Would be 'high' with LLM
                    })

        return controls

    def discover_policies(self, spaces: Optional[List[str]] = None,
                         labels: Optional[List[str]] = None) -> List[Dict]:
        """Discover all policy documents in Confluence."""

        if not labels:
            labels = ['policy', 'security', 'compliance', 'sop']

        print(f"Scanning Confluence for policies...")
        print(f"Spaces: {', '.join(spaces) if spaces else 'All'}")
        print(f"Labels: {', '.join(labels)}")

        all_pages = []

        if spaces:
            for space_key in spaces:
                pages = self.get_pages_by_label(labels, space_key)
                all_pages.extend(pages)
        else:
            pages = self.get_pages_by_label(labels)
            all_pages.extend(pages)

        # Process each page
        creatures = []

        for page in all_pages:
            # Get full page content
            full_page = self.get_page_content(page['id'])

            # Extract text from HTML
            html_content = full_page.get('body', {}).get('storage', {}).get('value', '')
            text_content = self.extract_text_from_html(html_content)

            # Extract controls
            controls = self.extract_controls_with_llm(page['title'], text_content)

            # Check freshness
            last_modified = full_page['version']['when']
            last_modified_dt = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            days_since_update = (datetime.now(last_modified_dt.tzinfo) - last_modified_dt).days

            creature = {
                'name': page['title'],
                'type': 'documentation',
                'platform': 'confluence',
                'category': 'policy',
                'metadata': {
                    'page_id': page['id'],
                    'space_key': page['space']['key'],
                    'url': f"{self.url}/wiki{page['_links']['webui']}",
                    'created': page['history']['createdDate'],
                    'last_modified': last_modified,
                    'days_since_update': days_since_update,
                    'labels': [l['name'] for l in full_page.get('metadata', {}).get('labels', {}).get('results', [])],
                    'word_count': len(text_content.split()),
                    'extracted_controls': [c['control_id'] for c in controls],
                },
                'controls': [c['control_id'] for c in controls],
                'control_details': controls,
                'risks': self._assess_policy_risks(page['title'], days_since_update)
            }

            creatures.append(creature)

        return creatures

    def _assess_policy_risks(self, title: str, days_since_update: int) -> List[Dict]:
        """Assess policy freshness and completeness risks."""
        risks = []

        # Policy staleness
        if days_since_update > 365:
            risks.append({
                'severity': 'high',
                'type': 'policy_stale',
                'message': f"Policy not updated in {days_since_update} days (>1 year)"
            })
        elif days_since_update > 180:
            risks.append({
                'severity': 'medium',
                'type': 'policy_review_needed',
                'message': f"Policy not updated in {days_since_update} days (>6 months)"
            })

        return risks


class JiraCollector:
    """Collect evidence from Jira tickets."""

    def __init__(self, url: str, email: str, api_token: str):
        self.url = url.rstrip('/')
        self.email = email
        self.api_token = api_token
        self.auth = self._create_auth()

    def _create_auth(self):
        """Create Basic Auth header."""
        credentials = f"{self.email}:{self.api_token}"
        token = b64encode(credentials.encode('utf-8')).decode('ascii')
        return {'Authorization': f'Basic {token}'}

    def search_issues(self, jql: str, max_results: int = 1000) -> List[Dict]:
        """Search Jira issues using JQL."""
        endpoint = f"{self.url}/rest/api/3/search"

        params = {
            'jql': jql,
            'maxResults': max_results,
            'fields': 'summary,description,created,updated,status,priority,assignee,labels,issuetype'
        }

        response = requests.get(endpoint, headers=self.auth, params=params)
        response.raise_for_status()

        return response.json()['issues']

    def collect_change_tickets(self, days: int = 90) -> List[Dict]:
        """Collect change management tickets."""
        # Example JQL for change tickets
        jql = f'type = "Change Request" AND created >= -{days}d ORDER BY created DESC'

        issues = self.search_issues(jql)

        creatures = []

        for issue in issues:
            fields = issue['fields']

            creature = {
                'name': f"{issue['key']}: {fields['summary']}",
                'type': 'documentation',
                'platform': 'jira',
                'category': 'change-ticket',
                'metadata': {
                    'issue_key': issue['key'],
                    'issue_type': fields['issuetype']['name'],
                    'status': fields['status']['name'],
                    'priority': fields.get('priority', {}).get('name'),
                    'created': fields['created'],
                    'updated': fields['updated'],
                    'assignee': fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
                    'labels': fields.get('labels', []),
                    'url': f"{self.url}/browse/{issue['key']}"
                },
                'controls': ['CM-3', 'CM-4'],  # Change control
                'evidence_type': 'change_management'
            }

            creatures.append(creature)

        return creatures

    def collect_incident_tickets(self, days: int = 180) -> List[Dict]:
        """Collect security incident tickets."""
        jql = f'type = Incident AND priority in (High, Critical) AND created >= -{days}d ORDER BY created DESC'

        issues = self.search_issues(jql)

        creatures = []

        for issue in issues:
            fields = issue['fields']

            creature = {
                'name': f"{issue['key']}: {fields['summary']}",
                'type': 'documentation',
                'platform': 'jira',
                'category': 'incident-ticket',
                'metadata': {
                    'issue_key': issue['key'],
                    'issue_type': fields['issuetype']['name'],
                    'status': fields['status']['name'],
                    'priority': fields.get('priority', {}).get('name'),
                    'created': fields['created'],
                    'updated': fields['updated'],
                    'assignee': fields.get('assignee', {}).get('displayName') if fields.get('assignee') else None,
                    'labels': fields.get('labels', []),
                    'url': f"{self.url}/browse/{issue['key']}"
                },
                'controls': ['IR-4', 'IR-5', 'IR-6', 'SI-4'],  # Incident response
                'evidence_type': 'incident_management'
            }

            creatures.append(creature)

        return creatures

    def create_remediation_ticket(self, gap: Dict, project_key: str = 'SEC') -> Dict:
        """Create a Jira ticket for a compliance gap."""
        endpoint = f"{self.url}/rest/api/3/issue"

        # Build ticket description
        description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": f"Gap identified during {gap['framework']} audit preparation:",
                            "marks": [{"type": "strong"}]
                        }
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": f"\nControl: {gap['control_id']} - {gap['control_name']}"
                        }
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": f"\nGap Description:\n{gap['gap_description']}"
                        }
                    ]
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": f"\nRecommendation:\n{gap['recommendation']}"
                        }
                    ]
                }
            ]
        }

        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": gap['summary'],
                "description": description,
                "issuetype": {"name": os.getenv('JIRA_GRC_ISSUE_TYPE', 'Task')},
                "priority": {"name": gap.get('priority', 'Medium')},
                "labels": gap.get('labels', ['compliance'])
            }
        }

        # Add assignee if specified
        if gap.get('assignee'):
            payload['fields']['assignee'] = {"name": gap['assignee']}

        # Add due date if specified
        if gap.get('due_date'):
            payload['fields']['duedate'] = gap['due_date']

        response = requests.post(endpoint, headers=self.auth, json=payload)
        response.raise_for_status()

        created_issue = response.json()

        return {
            'key': created_issue['key'],
            'url': f"{self.url}/browse/{created_issue['key']}",
            'self': created_issue['self']
        }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Collect Atlassian (Jira/Confluence) evidence")
    parser.add_argument("--source", choices=["confluence", "jira", "both"], default="both")
    parser.add_argument("--jql", help="Jira JQL query")
    parser.add_argument("--spaces", help="Comma-separated Confluence space keys")
    parser.add_argument("--labels", help="Comma-separated Confluence labels")
    parser.add_argument("--create-tickets", action="store_true", help="Create remediation tickets")
    parser.add_argument("--gaps", help="Gap report JSON file (for ticket creation)")
    args = parser.parse_args()

    # Load config from environment
    jira_url = os.getenv("JIRA_URL")
    jira_email = os.getenv("JIRA_EMAIL")
    jira_token = os.getenv("JIRA_API_TOKEN")
    confluence_url = os.getenv("CONFLUENCE_URL", f"{jira_url}/wiki")

    # Confluence
    if args.source in ["confluence", "both"]:
        print("\n" + "="*60)
        print("CONFLUENCE POLICY DISCOVERY")
        print("="*60)

        collector = ConfluenceCollector(confluence_url, jira_email, jira_token)

        spaces = args.spaces.split(',') if args.spaces else os.getenv('CONFLUENCE_SPACES', '').split(',')
        labels = args.labels.split(',') if args.labels else os.getenv('CONFLUENCE_LABELS', 'policy,security,compliance').split(',')

        spaces = [s.strip() for s in spaces if s.strip()]
        labels = [l.strip() for l in labels if l.strip()]

        try:
            policies = collector.discover_policies(spaces, labels)

            print(f"\n✓ Found {len(policies)} policy documents\n")

            # Group by space
            by_space = {}
            for policy in policies:
                space = policy['metadata']['space_key']
                if space not in by_space:
                    by_space[space] = []
                by_space[space].append(policy)

            for space, space_policies in by_space.items():
                print(f"\nSpace: {space} ({len(space_policies)} policies)")
                for policy in space_policies[:5]:  # Show first 5
                    controls = ', '.join(policy['controls'][:3])
                    if len(policy['controls']) > 3:
                        controls += f" +{len(policy['controls']) - 3} more"
                    print(f"  ├─ {policy['name']} → {controls}")

                if len(space_policies) > 5:
                    print(f"  └─ ... ({len(space_policies) - 5} more policies)")

            # Summary
            total_controls = sum(len(p['controls']) for p in policies)
            print(f"\nTotal: {len(policies)} policies mapped to {total_controls} controls")

        except Exception as e:
            print(f"✗ Error collecting from Confluence: {e}")

    # Jira
    if args.source in ["jira", "both"]:
        print("\n" + "="*60)
        print("JIRA EVIDENCE COLLECTION")
        print("="*60)

        collector = JiraCollector(jira_url, jira_email, jira_token)

        try:
            if args.jql:
                # Custom JQL
                print(f"\nJQL: {args.jql}")
                issues = collector.search_issues(args.jql)
                print(f"✓ Found {len(issues)} issues")

                for issue in issues[:10]:
                    fields = issue['fields']
                    print(f"  ├─ {issue['key']}: {fields['summary']} ({fields['status']['name']})")

                if len(issues) > 10:
                    print(f"  └─ ... ({len(issues) - 10} more issues)")

            else:
                # Default: collect changes and incidents
                print("\nCollecting change management tickets (last 90 days)...")
                changes = collector.collect_change_tickets(90)
                print(f"✓ Found {len(changes)} change tickets")

                print("\nCollecting security incidents (last 180 days)...")
                incidents = collector.collect_incident_tickets(180)
                print(f"✓ Found {len(incidents)} incident tickets")

                print(f"\nTotal evidence: {len(changes) + len(incidents)} tickets")
                print(f"  ├─ Change Management (CM-3, CM-4): {len(changes)} tickets")
                print(f"  └─ Incident Response (IR-4, IR-5, IR-6): {len(incidents)} tickets")

        except Exception as e:
            print(f"✗ Error collecting from Jira: {e}")

    # Create remediation tickets
    if args.create_tickets and args.gaps:
        print("\n" + "="*60)
        print("CREATING REMEDIATION TICKETS")
        print("="*60)

        collector = JiraCollector(jira_url, jira_email, jira_token)

        with open(args.gaps) as f:
            gaps = json.load(f)

        project_key = os.getenv('JIRA_GRC_PROJECT_KEY', 'SEC')

        for gap in gaps:
            try:
                ticket = collector.create_remediation_ticket(gap, project_key)
                print(f"✓ Created {ticket['key']}: {gap['summary']}")
                print(f"  URL: {ticket['url']}")
            except Exception as e:
                print(f"✗ Error creating ticket for {gap['summary']}: {e}")


if __name__ == "__main__":
    main()
