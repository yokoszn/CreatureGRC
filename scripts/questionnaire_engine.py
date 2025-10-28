#!/usr/bin/env python3
"""
AI-Powered Questionnaire Engine
Automatically answers security questionnaires using evidence database + Claude
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
import yaml
import anthropic
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class QuestionnaireAnswer:
    """Represents an answer to a questionnaire question"""
    question_id: str
    question_text: str
    answer_text: str
    confidence_score: float
    supporting_evidence_ids: List[str]
    requires_review: bool
    reasoning: str


class QuestionnaireEngine:
    """AI-powered questionnaire answering engine"""
    
    def __init__(self, db_config: Dict[str, str], anthropic_api_key: str):
        self.db_config = db_config
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model = "claude-sonnet-4-20250514"
    
    def get_db_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config, cursor_factory=RealDictCursor)
    
    def get_relevant_controls(self, question_category: str) -> List[Dict]:
        """Get controls relevant to a question category"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        c.id AS control_id,
                        c.control_code,
                        c.control_name,
                        c.control_description,
                        ci.implementation_status,
                        ci.implementation_description,
                        ci.automation_level,
                        ci.last_test_date,
                        p.policy_name,
                        p.document_url AS policy_url
                    FROM controls c
                    JOIN control_implementations ci ON c.id = ci.control_id
                    LEFT JOIN policies p ON ci.policy_id = p.id
                    WHERE c.control_description ILIKE %s
                    OR c.control_name ILIKE %s
                    AND ci.implementation_status IN ('implemented', 'partially_implemented')
                    ORDER BY ci.last_test_date DESC NULLS LAST
                    LIMIT 10
                """, (f'%{question_category}%', f'%{question_category}%'))
                return cur.fetchall()
    
    def get_control_evidence(self, control_id: str, limit: int = 5) -> List[Dict]:
        """Get recent evidence for a control"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        e.id,
                        e.evidence_name,
                        e.evidence_type,
                        e.collection_timestamp,
                        e.evidence_period_start,
                        e.evidence_period_end,
                        e.source_system,
                        e.file_path,
                        e.metadata
                    FROM evidence e
                    JOIN control_implementations ci ON e.control_implementation_id = ci.id
                    WHERE ci.control_id = %s
                    AND e.review_status = 'approved'
                    ORDER BY e.collection_timestamp DESC
                    LIMIT %s
                """, (control_id, limit))
                return cur.fetchall()
    
    def search_policies(self, keywords: List[str]) -> List[Dict]:
        """Search for relevant policies"""
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                search_query = ' OR '.join([f"policy_name ILIKE '%{kw}%' OR description ILIKE '%{kw}%'" for kw in keywords])
                cur.execute(f"""
                    SELECT 
                        policy_name,
                        policy_version,
                        description,
                        document_url,
                        effective_date,
                        status
                    FROM policies
                    WHERE ({search_query})
                    AND status = 'approved'
                    ORDER BY effective_date DESC
                    LIMIT 5
                """)
                return cur.fetchall()
    
    def build_context_for_question(self, question: str, question_category: str) -> Dict[str, Any]:
        """Build context from database for answering a question"""
        logger.info(f"Building context for question category: {question_category}")
        
        context = {
            'question': question,
            'category': question_category,
            'controls': [],
            'evidence': [],
            'policies': []
        }
        
        # Get relevant controls
        controls = self.get_relevant_controls(question_category)
        for control in controls:
            control_data = dict(control)
            
            # Get evidence for this control
            evidence = self.get_control_evidence(control['control_id'])
            control_data['evidence'] = [dict(e) for e in evidence]
            
            context['controls'].append(control_data)
        
        # Search for relevant policies
        keywords = self._extract_keywords(question)
        policies = self.search_policies(keywords)
        context['policies'] = [dict(p) for p in policies]
        
        return context
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from question text"""
        # Simple keyword extraction - in production, use NLP
        common_words = {'do', 'you', 'have', 'does', 'your', 'is', 'are', 'what', 'how', 'when', 'where', 'the', 'a', 'an', 'and', 'or', 'but'}
        words = text.lower().split()
        keywords = [w for w in words if len(w) > 3 and w not in common_words]
        return keywords[:5]  # Top 5 keywords
    
    def answer_question_with_ai(self, question: str, question_category: str, answer_type: str = "text") -> QuestionnaireAnswer:
        """Use Claude to answer a question based on evidence"""
        logger.info(f"Answering question: {question[:100]}...")
        
        # Build context from database
        context = self.build_context_for_question(question, question_category)
        
        # Prepare prompt for Claude
        prompt = self._build_ai_prompt(question, context, answer_type)
        
        # Call Claude API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            
            # Parse Claude's response
            response_text = response.content[0].text
            parsed_answer = self._parse_ai_response(response_text, context)
            
            return parsed_answer
            
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            # Return a fallback answer
            return QuestionnaireAnswer(
                question_id="",
                question_text=question,
                answer_text="Unable to automatically answer. Requires manual review.",
                confidence_score=0.0,
                supporting_evidence_ids=[],
                requires_review=True,
                reasoning=f"API error: {str(e)}"
            )
    
    def _build_ai_prompt(self, question: str, context: Dict, answer_type: str) -> str:
        """Build prompt for Claude"""
        
        # Format controls and evidence
        controls_summary = []
        for i, control in enumerate(context['controls'], 1):
            summary = f"""
Control {i}: {control['control_code']} - {control['control_name']}
Status: {control['implementation_status']}
Description: {control['control_description']}
Implementation: {control.get('implementation_description', 'Not described')}
"""
            if control.get('evidence'):
                summary += f"Evidence collected: {len(control['evidence'])} items\n"
                for ev in control['evidence'][:3]:  # Show first 3
                    summary += f"  - {ev['evidence_name']} ({ev['source_system']}, {ev['collection_timestamp']})\n"
            
            controls_summary.append(summary)
        
        # Format policies
        policies_summary = []
        for policy in context['policies']:
            policies_summary.append(f"- {policy['policy_name']} (v{policy['policy_version']}, effective {policy['effective_date']})")
        
        prompt = f"""You are a compliance expert helping answer a security questionnaire. Based on the organization's controls, evidence, and policies, provide an accurate answer to the question.

**QUESTION TO ANSWER:**
{question}

**EXPECTED ANSWER TYPE:** {answer_type}

**RELEVANT CONTROLS IMPLEMENTED:**
{"".join(controls_summary) if controls_summary else "No directly matching controls found."}

**RELEVANT POLICIES:**
{chr(10).join(policies_summary) if policies_summary else "No directly matching policies found."}

**INSTRUCTIONS:**
1. Answer the question accurately based ONLY on the information provided above
2. If the answer is YES, explain which controls and evidence support this
3. If the answer is NO or PARTIAL, be honest and explain what's missing
4. Provide your confidence level (0-100%) in the answer
5. List specific evidence IDs that support your answer
6. Be concise but complete

**RESPONSE FORMAT (JSON):**
{{
  "answer": "Your clear, direct answer to the question",
  "confidence": 85,
  "reasoning": "Brief explanation of why this answer is correct based on the evidence",
  "supporting_controls": ["CC6.1", "CC6.2"],
  "supporting_evidence_ids": ["uuid-1", "uuid-2"],
  "requires_human_review": false,
  "suggested_improvements": "Optional: What could strengthen this answer"
}}

CRITICAL: Only output valid JSON. Do not include any text outside the JSON structure.
"""
        return prompt
    
    def _parse_ai_response(self, response_text: str, context: Dict) -> QuestionnaireAnswer:
        """Parse Claude's JSON response"""
        try:
            # Strip any markdown formatting
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            data = json.loads(response_text)
            
            return QuestionnaireAnswer(
                question_id="",  # Will be set by caller
                question_text=context['question'],
                answer_text=data.get('answer', ''),
                confidence_score=data.get('confidence', 0) / 100.0,
                supporting_evidence_ids=data.get('supporting_evidence_ids', []),
                requires_review=data.get('requires_human_review', False) or data.get('confidence', 0) < 70,
                reasoning=data.get('reasoning', '')
            )
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response was: {response_text[:200]}...")
            # Try to extract answer from text
            return QuestionnaireAnswer(
                question_id="",
                question_text=context['question'],
                answer_text=response_text[:500],
                confidence_score=0.5,
                supporting_evidence_ids=[],
                requires_review=True,
                reasoning="Response could not be parsed as structured JSON"
            )
    
    def answer_questionnaire(self, template_id: str, save_to_db: bool = True) -> List[QuestionnaireAnswer]:
        """Answer all questions in a questionnaire template"""
        logger.info(f"Starting questionnaire answering for template: {template_id}")
        
        # Get all questions for the template
        with self.get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT 
                        id,
                        question_number,
                        question_text,
                        question_category,
                        answer_type,
                        help_text
                    FROM questionnaire_questions
                    WHERE template_id = %s
                    ORDER BY question_number
                """, (template_id,))
                questions = cur.fetchall()
        
        logger.info(f"Found {len(questions)} questions to answer")
        
        answers = []
        for question in questions:
            logger.info(f"Processing question {question['question_number']}: {question['question_text'][:50]}...")
            
            answer = self.answer_question_with_ai(
                question['question_text'],
                question['question_category'] or 'general',
                question['answer_type']
            )
            
            answer.question_id = str(question['id'])
            answers.append(answer)
            
            # Save to database if requested
            if save_to_db:
                with self.get_db_connection() as conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO questionnaire_responses (
                                question_id,
                                response_text,
                                evidence_ids,
                                confidence_score,
                                is_auto_generated,
                                requires_human_review
                            ) VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (question_id) DO UPDATE SET
                                response_text = EXCLUDED.response_text,
                                evidence_ids = EXCLUDED.evidence_ids,
                                confidence_score = EXCLUDED.confidence_score,
                                updated_at = NOW()
                            RETURNING id
                        """, (
                            answer.question_id,
                            answer.answer_text,
                            answer.supporting_evidence_ids,
                            answer.confidence_score,
                            True,
                            answer.requires_review
                        ))
                        response_id = cur.fetchone()['id']
                        conn.commit()
                        logger.info(f"Saved response: {response_id}")
            
            logger.info(f"Answer confidence: {answer.confidence_score*100:.1f}%, Review needed: {answer.requires_review}")
        
        return answers
    
    def generate_questionnaire_report(self, answers: List[QuestionnaireAnswer], output_path: Path):
        """Generate HTML report of questionnaire answers"""
        from jinja2 import Template
        
        template = Template('''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Security Questionnaire - Automated Answers</title>
    <style>
        body { font-family: Arial, sans-serif; max-width: 1200px; margin: 20px auto; padding: 0 20px; }
        h1 { color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        .question { background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 5px; border-left: 5px solid #3498db; }
        .answer { margin: 15px 0; padding: 15px; background: white; border-radius: 5px; }
        .confidence-high { color: #27ae60; font-weight: bold; }
        .confidence-medium { color: #f39c12; font-weight: bold; }
        .confidence-low { color: #e74c3c; font-weight: bold; }
        .review-needed { background: #fff3cd; border-left: 4px solid #ff9800; padding: 10px; margin: 10px 0; }
        .reasoning { color: #7f8c8d; font-size: 0.9em; font-style: italic; margin-top: 10px; }
        .stats { background: #ecf0f1; padding: 20px; border-radius: 5px; margin: 20px 0; }
    </style>
</head>
<body>
    <h1>Security Questionnaire - Automated Responses</h1>
    <p><strong>Generated:</strong> {{ generation_date }}</p>
    
    <div class="stats">
        <h2>Summary</h2>
        <p><strong>Total Questions:</strong> {{ total_questions }}</p>
        <p><strong>High Confidence Answers:</strong> {{ high_confidence }} ({{ (high_confidence/total_questions*100)|round(1) }}%)</p>
        <p><strong>Requiring Review:</strong> {{ needs_review }} ({{ (needs_review/total_questions*100)|round(1) }}%)</p>
        <p><strong>Average Confidence:</strong> {{ (avg_confidence*100)|round(1) }}%</p>
    </div>
    
    {% for answer in answers %}
    <div class="question">
        <h3>Question {{ loop.index }}</h3>
        <p><strong>{{ answer.question_text }}</strong></p>
        
        <div class="answer">
            <p><strong>Answer:</strong> {{ answer.answer_text }}</p>
            
            <p>
                <strong>Confidence:</strong> 
                {% if answer.confidence_score >= 0.8 %}
                    <span class="confidence-high">{{ (answer.confidence_score*100)|round(1) }}% - High</span>
                {% elif answer.confidence_score >= 0.5 %}
                    <span class="confidence-medium">{{ (answer.confidence_score*100)|round(1) }}% - Medium</span>
                {% else %}
                    <span class="confidence-low">{{ (answer.confidence_score*100)|round(1) }}% - Low</span>
                {% endif %}
            </p>
            
            {% if answer.requires_review %}
            <div class="review-needed">
                ⚠️ <strong>Human Review Required</strong> - This answer should be verified by a compliance expert
            </div>
            {% endif %}
            
            {% if answer.reasoning %}
            <p class="reasoning">{{ answer.reasoning }}</p>
            {% endif %}
            
            {% if answer.supporting_evidence_ids %}
            <p><strong>Supporting Evidence:</strong> {{ answer.supporting_evidence_ids|length }} items</p>
            {% endif %}
        </div>
    </div>
    {% endfor %}
    
</body>
</html>
        ''')
        
        # Calculate statistics
        total = len(answers)
        high_confidence = sum(1 for a in answers if a.confidence_score >= 0.8)
        needs_review = sum(1 for a in answers if a.requires_review)
        avg_confidence = sum(a.confidence_score for a in answers) / total if total > 0 else 0
        
        html = template.render(
            answers=answers,
            generation_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            total_questions=total,
            high_confidence=high_confidence,
            needs_review=needs_review,
            avg_confidence=avg_confidence
        )
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Generated questionnaire report: {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='AI-Powered Questionnaire Engine')
    parser.add_argument('--config', required=True, help='Path to config YAML file')
    parser.add_argument('--template-id', required=True, help='Questionnaire template UUID')
    parser.add_argument('--output', default='questionnaire-answers.html', help='Output HTML file')
    parser.add_argument('--save-to-db', action='store_true', help='Save answers to database')
    
    args = parser.parse_args()
    
    # Load config
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get Anthropic API key
    api_key = os.environ.get('ANTHROPIC_API_KEY') or config.get('anthropic', {}).get('api_key')
    if not api_key:
        print("❌ Error: ANTHROPIC_API_KEY not set in environment or config file")
        sys.exit(1)
    
    # Create engine
    engine = QuestionnaireEngine(
        config['database'],
        api_key
    )
    
    # Answer questionnaire
    print(f"\n🤖 Starting automated questionnaire answering...")
    print(f"📋 Template ID: {args.template_id}")
    
    answers = engine.answer_questionnaire(args.template_id, save_to_db=args.save_to_db)
    
    # Generate report
    engine.generate_questionnaire_report(answers, Path(args.output))
    
    # Print summary
    high_confidence = sum(1 for a in answers if a.confidence_score >= 0.8)
    needs_review = sum(1 for a in answers if a.requires_review)
    
    print(f"\n✅ Questionnaire answering complete!")
    print(f"📊 Results:")
    print(f"   Total questions: {len(answers)}")
    print(f"   High confidence: {high_confidence} ({high_confidence/len(answers)*100:.1f}%)")
    print(f"   Needs review: {needs_review} ({needs_review/len(answers)*100:.1f}%)")
    print(f"   Average confidence: {sum(a.confidence_score for a in answers)/len(answers)*100:.1f}%")
    print(f"\n📄 Report generated: {args.output}")
    
    if args.save_to_db:
        print(f"💾 Answers saved to database")


if __name__ == "__main__":
    main()
