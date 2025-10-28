# GRC Platform - Quick Start Guide

## 🚀 Get Running in 10 Minutes

### Step 1: Set Up Database (2 minutes)

```bash
# Using Docker (easiest)
docker-compose up -d postgres

# OR install PostgreSQL manually
sudo apt-get update
sudo apt-get install postgresql-16 postgresql-contrib

# Create database
sudo -u postgres createdb grc_platform
sudo -u postgres psql -c "CREATE USER grc_user WITH PASSWORD 'your-password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE grc_platform TO grc_user;"
```

### Step 2: Initialize Schema (1 minute)

```bash
# Load the schema (includes all control libraries)
psql -U grc_user -d grc_platform -f schema.sql

# Verify
psql -U grc_user -d grc_platform -c "SELECT name, version FROM compliance_frameworks;"

# Output should show:
#   SOC2         | 2017
#   ISO27001     | 2022
#   NIST-800-53  | Rev5
#   ... etc
```

### Step 3: Configure (3 minutes)

```bash
# Copy example config
cp config.example.yaml config.yaml

# Edit with your credentials
nano config.yaml

# Set required environment variables
export ANTHROPIC_API_KEY="sk-ant-your-key"
export DB_PASSWORD="your-db-password"
export WAZUH_PASSWORD="your-wazuh-password"
export KEYCLOAK_CLIENT_SECRET="your-keycloak-secret"
```

### Step 4: Collect Evidence (2 minutes)

```bash
# Install Python dependencies
pip install psycopg2-binary pyyaml requests anthropic jinja2

# Run evidence collection
python3 evidence_collector.py --config config.yaml --framework SOC2

# This will collect:
# - Wazuh authentication logs (last 90 days)
# - Keycloak MFA configuration
# - User access lists
# - Security alerts
# - Agent deployment status
```

### Step 5: Generate Audit Package (2 minutes)

```bash
# Generate audit package
python3 generate_audit_package.py \
  --client your-company \
  --framework SOC2 \
  --config config.yaml

# Output: your-company-SOC2-evidence-20250328.zip
```

**That's it!** You now have a working GRC platform.

---

## 📋 Common Tasks

### Daily Evidence Collection (Automated)

```bash
# Add to crontab
crontab -e

# Collect evidence daily at 2 AM
0 2 * * * cd /opt/grc-platform && python3 evidence_collector.py --config config.yaml --framework SOC2

# Generate weekly summary on Sundays at 3 AM
0 3 * * 0 cd /opt/grc-platform && python3 generate_audit_package.py --client your-company --framework SOC2 --config config.yaml
```

### Answer Security Questionnaires

```bash
# First, create a questionnaire template in the database
# (See examples in the docs)

# Then auto-answer with AI
python3 questionnaire_engine.py \
  --config config.yaml \
  --template-id <uuid-from-database> \
  --save-to-db \
  --output customer-security-questionnaire.html

# Review the HTML report
firefox customer-security-questionnaire.html
```

### Check Compliance Status

```bash
# Using psql
psql -U grc_user -d grc_platform -c "SELECT * FROM v_audit_readiness;"

# OR using CLI tool
chmod +x grc
./grc status
```

### Add New Evidence Source

```python
# Create custom collector (example: Confluence policies)
from evidence_collector import EvidenceCollector

class ConfluenceCollector(EvidenceCollector):
    def collect_policies(self):
        # Your implementation
        response = requests.get(f"{self.confluence_url}/api/...")
        
        # Save evidence
        filepath, file_hash = self.save_evidence_file(
            response.json(), 
            "confluence-policies.json",
            "policies"
        )
        return filepath
```

---

## 🎯 Use Cases

### Use Case 1: MSP Managing Multiple Clients

```bash
# Client 1: Acme Corp (SOC 2)
python3 evidence_collector.py --config acme-config.yaml --framework SOC2
python3 generate_audit_package.py --client acme-corp --framework SOC2

# Client 2: Globex (ISO 27001)
python3 evidence_collector.py --config globex-config.yaml --framework ISO27001
python3 generate_audit_package.py --client globex --framework ISO27001

# Store in separate databases or use multi-tenant schema
```

### Use Case 2: Internal Compliance Team

```bash
# Schedule automated evidence collection
# Monitor via Grafana dashboard
# Generate quarterly audit packages
# Auto-answer vendor questionnaires

# Example workflow:
1. Evidence collected daily → database
2. Compliance dashboard updated in real-time
3. Quarterly: generate audit package
4. Customer asks security questions: auto-answer from evidence
```

### Use Case 3: Startup Seeking SOC 2

```bash
# Day 1: Initialize platform
./grc init
./grc db init

# Week 1-2: Implement controls
# - Set up Wazuh monitoring
# - Configure Keycloak MFA
# - Document policies

# Week 3-4: Collect evidence
./grc collect --framework SOC2

# Week 5-6: Prepare for audit
./grc audit --client yourcompany --framework SOC2

# Hand off to auditor: audit package is ready
```

---

## 🐛 Troubleshooting

### "psycopg2 import error"

```bash
# Install binary version
pip install psycopg2-binary
```

### "Permission denied: schema.sql"

```bash
# Fix permissions
chmod 644 schema.sql
```

### "Wazuh API connection failed"

```bash
# Check connectivity
curl -u user:pass https://wazuh-api:55000/

# Verify SSL cert (or set verify_ssl: false in config)
```

### "Claude API rate limit"

```bash
# Add retry logic in questionnaire_engine.py
# Or spread out questionnaire answering over time
```

### "Evidence files not found"

```bash
# Check output directory permissions
mkdir -p /var/lib/grc/evidence
chown -R $(whoami) /var/lib/grc/evidence

# Update config.yaml with correct path
```

---

## 📊 Expected Results

After setup, you should have:

1. **Database with control libraries:**
   - 200+ SOC 2 controls
   - 114 ISO 27001 controls  
   - 1000+ NIST 800-53 controls

2. **Automated evidence collection:**
   - Daily Wazuh logs
   - Weekly Keycloak configs
   - Weekly OpenSCAP scans

3. **AI questionnaire engine:**
   - 80%+ auto-answer rate
   - 90%+ confidence on yes/no questions
   - 20% require human review

4. **Audit packages:**
   - Complete evidence by control domain
   - Executive summary dashboard
   - SHA256 hashes for integrity

---

## 🎓 Next Steps

1. **Read the full README.md** for architecture details
2. **Review ARCHITECTURE.txt** for system design
3. **Explore schema.sql** to understand data model
4. **Customize evidence collectors** for your stack
5. **Build Trust Center UI** (optional)

---

## 💬 Support

- **Issues:** Open GitHub issue
- **Discussions:** GitHub Discussions
- **Community:** Join Discord/Slack (coming soon)

---

## 🔐 Security Notes

**This platform handles sensitive compliance data. Please:**

1. Use strong passwords for database
2. Store API keys in environment variables, not config files
3. Enable SSL/TLS for all connections
4. Regularly update dependencies
5. Review evidence before sharing with auditors
6. Implement proper access controls
7. Enable database encryption at rest
8. Use VPN for remote access
9. Monitor for unauthorized access
10. Follow your organization's security policies

---

**You're now ready to automate your compliance!** 🎉
