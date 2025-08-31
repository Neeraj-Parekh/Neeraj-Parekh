"""
Smart Content Generation Service
AI that writes emails, reports, and documents for users
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import structlog
import numpy as np
from enum import Enum

# Database imports
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, Task, PomodoroSession, TimeEntry, UserAnalytics

logger = structlog.get_logger()

class ContentType(Enum):
    EMAIL_DRAFT = "email_draft"
    PROGRESS_REPORT = "progress_report"
    MEETING_SUMMARY = "meeting_summary"
    PROJECT_UPDATE = "project_update"
    TASK_BREAKDOWN = "task_breakdown"
    PERFORMANCE_REVIEW = "performance_review"

class EmailType(Enum):
    FOLLOW_UP = "follow_up"
    REQUEST = "request"
    UPDATE = "update"
    MEETING_INVITE = "meeting_invite"
    THANK_YOU = "thank_you"
    PROPOSAL = "proposal"
    CLARIFICATION = "clarification"

class Tone(Enum):
    PROFESSIONAL = "professional"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    CASUAL = "casual"
    URGENT = "urgent"
    DIPLOMATIC = "diplomatic"

@dataclass
class EmailDraft:
    """Structure for email drafts"""
    subject: str
    body: str
    recipient_info: Dict[str, Any]
    email_type: EmailType
    tone: Tone
    confidence_score: float
    suggested_send_time: Optional[datetime] = None
    alternative_versions: List[Dict[str, str]] = None
    
    def __post_init__(self):
        if self.alternative_versions is None:
            self.alternative_versions = []

@dataclass
class ReportSection:
    """Structure for report sections"""
    title: str
    content: str
    metrics: Dict[str, Any]
    charts_data: Optional[Dict[str, Any]] = None

@dataclass
class ProgressReport:
    """Structure for progress reports"""
    title: str
    period: str
    executive_summary: str
    sections: List[ReportSection]
    key_metrics: Dict[str, Any]
    recommendations: List[str]
    action_items: List[str]
    export_formats: List[str]
    
    def __post_init__(self):
        if not self.export_formats:
            self.export_formats = ['pdf', 'docx', 'html', 'markdown']

class ContentGenerationService:
    """Service for generating various types of content using AI"""
    
    def __init__(self, redis_client=None, openai_client=None):
        self.redis = redis_client
        self.openai_client = openai_client
        self.content_cache = {}
        self.user_preferences = {}
    
    async def generate_email_draft(self, user_id: str, context: Dict[str, Any]) -> EmailDraft:
        """Generate contextual email drafts based on user's current work"""
        logger.info("Generating email draft", user_id=user_id, context_keys=list(context.keys()))
        
        try:
            # Gather user context
            user_context = await self._get_user_context(user_id)
            current_tasks = context.get('current_tasks', [])
            recipient_info = context.get('recipient', {})
            
            # Determine email type and tone
            email_type = await self._classify_email_type(context)
            appropriate_tone = await self._determine_tone(recipient_info, email_type)
            
            # Generate email using AI (mock for now)
            email_content = await self._generate_email_content(
                user_context, context, email_type, appropriate_tone
            )
            
            # Create email draft
            draft = EmailDraft(
                subject=email_content['subject'],
                body=email_content['body'],
                recipient_info=recipient_info,
                email_type=email_type,
                tone=appropriate_tone,
                confidence_score=0.85,
                suggested_send_time=await self._suggest_optimal_send_time(recipient_info),
                alternative_versions=await self._generate_alternative_versions(email_content)
            )
            
            # Save as draft
            saved_draft = await self._save_email_draft(user_id, draft, context)
            
            logger.info("Email draft generated successfully", 
                       user_id=user_id,
                       email_type=email_type.value,
                       confidence=draft.confidence_score)
            
            return {
                'draft_id': saved_draft['id'],
                'subject': draft.subject,
                'body': draft.body,
                'confidence_score': draft.confidence_score,
                'email_type': email_type.value,
                'tone': appropriate_tone.value,
                'suggested_send_time': draft.suggested_send_time.isoformat() if draft.suggested_send_time else None,
                'alternative_versions': draft.alternative_versions,
                'recipient': recipient_info.get('name', 'Unknown')
            }
            
        except Exception as e:
            logger.error("Failed to generate email draft", user_id=user_id, error=str(e))
            raise
    
    async def generate_progress_report(self, user_id: str, report_type: str, period: str) -> ProgressReport:
        """Auto-generate progress reports based on tracked activity"""
        logger.info("Generating progress report", 
                   user_id=user_id, 
                   report_type=report_type, 
                   period=period)
        
        try:
            # Gather data for report period
            start_date, end_date = self._get_period_dates(period)
            report_data = await self._gather_report_data(user_id, start_date, end_date)
            
            # Generate comprehensive report
            report = await self._generate_report_content(user_id, report_type, period, report_data)
            
            # Format and save report
            formatted_report = await self._format_report(report, report_data)
            saved_report = await self._save_report(user_id, formatted_report)
            
            logger.info("Progress report generated successfully", 
                       user_id=user_id,
                       report_type=report_type,
                       period=period)
            
            return {
                'report_id': saved_report['id'],
                'title': report.title,
                'period': report.period,
                'executive_summary': report.executive_summary,
                'sections': [asdict(section) for section in report.sections],
                'key_metrics': report.key_metrics,
                'recommendations': report.recommendations,
                'action_items': report.action_items,
                'charts_generated': await self._generate_report_charts(report_data),
                'suggested_recipients': await self._suggest_report_recipients(user_id),
                'export_formats': report.export_formats
            }
            
        except Exception as e:
            logger.error("Failed to generate progress report", user_id=user_id, error=str(e))
            raise
    
    async def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive user context for content generation"""
        try:
            async with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {}
                
                # Get user analytics
                analytics = db.query(UserAnalytics).filter(UserAnalytics.user_id == user_id).first()
                
                # Get recent tasks
                recent_tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.updated_at >= datetime.now() - timedelta(days=30)
                ).all()
                
                context = {
                    'username': user.username,
                    'email': user.email,
                    'role': 'Professional',  # Would be stored in user profile
                    'communication_style': 'Direct and friendly',  # User preference
                    'current_projects': [task.title for task in recent_tasks if task.status == 'in_progress'],
                    'productivity_stats': {
                        'avg_focus_score': analytics.avg_focus_score if analytics else 0.7,
                        'total_sessions': analytics.total_sessions if analytics else 0,
                        'productivity_trend': analytics.productivity_trend if analytics else 0.0
                    }
                }
                
                return context
                
        except Exception as e:
            logger.error("Failed to get user context", user_id=user_id, error=str(e))
            return {}
    
    async def _classify_email_type(self, context: Dict[str, Any]) -> EmailType:
        """Determine the type of email based on context"""
        purpose = context.get('purpose', '').lower()
        key_points = [point.lower() for point in context.get('key_points', [])]
        
        # Simple classification based on keywords
        if any(word in purpose for word in ['follow', 'followup', 'follow-up']):
            return EmailType.FOLLOW_UP
        elif any(word in purpose for word in ['request', 'ask', 'need', 'require']):
            return EmailType.REQUEST
        elif any(word in purpose for word in ['update', 'progress', 'status']):
            return EmailType.UPDATE
        elif any(word in purpose for word in ['meeting', 'schedule', 'invite']):
            return EmailType.MEETING_INVITE
        elif any(word in purpose for word in ['thank', 'appreciate', 'grateful']):
            return EmailType.THANK_YOU
        elif any(word in purpose for word in ['proposal', 'suggest', 'recommend']):
            return EmailType.PROPOSAL
        elif any(word in purpose for word in ['clarify', 'question', 'unclear']):
            return EmailType.CLARIFICATION
        else:
            return EmailType.UPDATE  # Default
    
    async def _determine_tone(self, recipient_info: Dict[str, Any], email_type: EmailType) -> Tone:
        """Determine appropriate tone based on recipient and email type"""
        relationship = recipient_info.get('relationship', 'colleague').lower()
        
        # Adjust tone based on relationship
        if relationship in ['boss', 'manager', 'supervisor', 'client']:
            base_tone = Tone.PROFESSIONAL
        elif relationship in ['colleague', 'peer', 'teammate']:
            base_tone = Tone.FRIENDLY
        elif relationship in ['direct_report', 'subordinate']:
            base_tone = Tone.PROFESSIONAL
        else:
            base_tone = Tone.PROFESSIONAL
        
        # Adjust based on email type
        if email_type == EmailType.REQUEST:
            return Tone.DIPLOMATIC
        elif email_type == EmailType.THANK_YOU:
            return Tone.FRIENDLY
        elif email_type in [EmailType.PROPOSAL, EmailType.MEETING_INVITE]:
            return Tone.PROFESSIONAL
        
        return base_tone
    
    async def _generate_email_content(self, 
                                    user_context: Dict[str, Any], 
                                    email_context: Dict[str, Any],
                                    email_type: EmailType,
                                    tone: Tone) -> Dict[str, str]:
        """Generate email content using AI"""
        
        # Mock email generation - in real implementation would use GPT-4
        purpose = email_context.get('purpose', 'General communication')
        key_points = email_context.get('key_points', [])
        recipient_name = email_context.get('recipient', {}).get('name', 'there')
        
        if email_type == EmailType.FOLLOW_UP:
            subject = f"Following up on {purpose}"
            body = f"""Hi {recipient_name},

I wanted to follow up on our recent discussion about {purpose}.

{self._format_key_points(key_points)}

Please let me know if you have any questions or need any additional information.

Best regards,
{user_context.get('username', 'User')}"""
            
        elif email_type == EmailType.REQUEST:
            subject = f"Request: {purpose}"
            body = f"""Hi {recipient_name},

I hope this email finds you well. I'm reaching out to request your assistance with {purpose}.

{self._format_key_points(key_points)}

I would greatly appreciate your help with this. Please let me know if you need any additional details.

Thank you for your time and consideration.

Best regards,
{user_context.get('username', 'User')}"""
            
        elif email_type == EmailType.UPDATE:
            subject = f"Update: {purpose}"
            body = f"""Hi {recipient_name},

I wanted to provide you with an update on {purpose}.

{self._format_key_points(key_points)}

Please let me know if you have any questions or need clarification on any of these points.

Best regards,
{user_context.get('username', 'User')}"""
            
        else:
            # Default email structure
            subject = f"Re: {purpose}"
            body = f"""Hi {recipient_name},

{self._format_key_points(key_points)}

Please let me know if you have any questions.

Best regards,
{user_context.get('username', 'User')}"""
        
        return {
            'subject': subject,
            'body': body
        }
    
    def _format_key_points(self, key_points: List[str]) -> str:
        """Format key points for inclusion in email"""
        if not key_points:
            return "I wanted to touch base with you on this matter."
        
        if len(key_points) == 1:
            return f"Specifically, {key_points[0]}."
        
        formatted = "Key points to discuss:\n"
        for i, point in enumerate(key_points, 1):
            formatted += f"{i}. {point}\n"
        
        return formatted.strip()
    
    async def _suggest_optimal_send_time(self, recipient_info: Dict[str, Any]) -> Optional[datetime]:
        """Suggest optimal time to send email based on recipient preferences"""
        # Mock implementation - in real app would analyze recipient's response patterns
        timezone = recipient_info.get('timezone', 'UTC')
        preferred_hours = recipient_info.get('preferred_contact_hours', [9, 10, 14, 15])
        
        current_time = datetime.now()
        current_hour = current_time.hour
        
        # If current time is within preferred hours, suggest sending now
        if current_hour in preferred_hours:
            return current_time + timedelta(minutes=5)  # Small delay for review
        
        # Otherwise, suggest next preferred hour
        next_preferred = min([h for h in preferred_hours if h > current_hour], default=preferred_hours[0])
        
        suggested_time = current_time.replace(hour=next_preferred, minute=0, second=0, microsecond=0)
        if next_preferred <= current_hour:
            suggested_time += timedelta(days=1)  # Next day
        
        return suggested_time
    
    async def _generate_alternative_versions(self, email_content: Dict[str, str]) -> List[Dict[str, str]]:
        """Generate alternative versions of the email"""
        original_body = email_content['body']
        
        # Generate shorter version
        shorter_version = {
            'version': 'concise',
            'subject': email_content['subject'],
            'body': self._create_shorter_version(original_body),
            'description': 'More concise version'
        }
        
        # Generate more formal version
        formal_version = {
            'version': 'formal',
            'subject': email_content['subject'],
            'body': self._create_formal_version(original_body),
            'description': 'More formal tone'
        }
        
        return [shorter_version, formal_version]
    
    def _create_shorter_version(self, original_body: str) -> str:
        """Create a shorter version of the email"""
        lines = original_body.split('\n')
        # Keep greeting, main content (condensed), and closing
        greeting = lines[0] if lines else ""
        closing_lines = lines[-2:] if len(lines) >= 2 else lines
        
        # Simplified body
        short_body = f"""{greeting}

Quick update on the items we discussed. Please let me know if you need any clarification.

{closing_lines[-1] if closing_lines else "Best regards"}"""
        
        return short_body
    
    def _create_formal_version(self, original_body: str) -> str:
        """Create a more formal version of the email"""
        # Replace casual words with formal equivalents
        formal_replacements = {
            "Hi": "Dear",
            "let me know": "please advise",
            "thanks": "thank you",
            "Best regards": "Sincerely"
        }
        
        formal_body = original_body
        for casual, formal in formal_replacements.items():
            formal_body = formal_body.replace(casual, formal)
        
        return formal_body
    
    async def _save_email_draft(self, user_id: str, draft: EmailDraft, context: Dict[str, Any]) -> Dict[str, Any]:
        """Save email draft to database/cache"""
        # Mock save operation
        draft_id = f"draft_{user_id}_{int(datetime.now().timestamp())}"
        
        if self.redis:
            try:
                await self.redis.setex(
                    f"email_draft:{draft_id}",
                    3600,  # 1 hour TTL
                    json.dumps(asdict(draft), default=str)
                )
            except Exception as e:
                logger.warning("Failed to cache email draft", user_id=user_id, error=str(e))
        
        return {
            'id': draft_id,
            'status': 'saved',
            'created_at': datetime.now().isoformat()
        }
    
    def _get_period_dates(self, period: str) -> Tuple[datetime, datetime]:
        """Get start and end dates for reporting period"""
        end_date = datetime.now()
        
        if period == 'daily':
            start_date = end_date - timedelta(days=1)
        elif period == 'weekly':
            start_date = end_date - timedelta(days=7)
        elif period == 'monthly':
            start_date = end_date - timedelta(days=30)
        elif period == 'quarterly':
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=7)  # Default to weekly
        
        return start_date, end_date
    
    async def _gather_report_data(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Gather data for report generation"""
        try:
            async with get_db() as db:
                # Get sessions data
                sessions = db.query(PomodoroSession).filter(
                    PomodoroSession.user_id == user_id,
                    PomodoroSession.completed_at >= start_date,
                    PomodoroSession.completed_at <= end_date,
                    PomodoroSession.completed_at.isnot(None)
                ).all()
                
                # Get tasks data
                tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.updated_at >= start_date,
                    Task.updated_at <= end_date
                ).all()
                
                # Get time entries
                time_entries = db.query(TimeEntry).filter(
                    TimeEntry.user_id == user_id,
                    TimeEntry.created_at >= start_date,
                    TimeEntry.created_at <= end_date
                ).all()
                
                # Calculate metrics
                total_focus_time = sum(session.duration for session in sessions if session.duration)
                completed_tasks = [task for task in tasks if task.status == 'completed']
                avg_productivity_score = np.mean([session.focus_score for session in sessions if session.focus_score]) if sessions else 0.5
                
                # Identify peak performance times
                hourly_performance = {}
                for session in sessions:
                    if session.completed_at:
                        hour = session.completed_at.hour
                        if hour not in hourly_performance:
                            hourly_performance[hour] = []
                        hourly_performance[hour].append(session.focus_score or 0.5)
                
                peak_times = [hour for hour, scores in hourly_performance.items() 
                             if np.mean(scores) > 0.7] if hourly_performance else [9, 10]
                
                # Identify achievements
                achievements = []
                if len(completed_tasks) > 0:
                    achievements.append(f"Completed {len(completed_tasks)} tasks")
                if total_focus_time > 0:
                    achievements.append(f"Achieved {total_focus_time} minutes of focused work")
                if avg_productivity_score > 0.7:
                    achievements.append(f"Maintained high productivity score of {avg_productivity_score:.2f}")
                
                # Identify challenges
                challenges = []
                interrupted_sessions = [s for s in sessions if s.interrupted]
                if len(interrupted_sessions) > len(sessions) * 0.3:
                    challenges.append("High interruption rate affecting focus")
                
                pending_tasks = [task for task in tasks if task.status == 'pending']
                if len(pending_tasks) > 10:
                    challenges.append("Large backlog of pending tasks")
                
                # Project progress (mock data)
                project_progress = {
                    'active_projects': len(set(task.title.split()[0] for task in tasks if task.status == 'in_progress')),
                    'completion_rate': len(completed_tasks) / len(tasks) if tasks else 0,
                    'on_track_projects': 0.8  # Mock percentage
                }
                
                return {
                    'total_focus_time': total_focus_time,
                    'completed_tasks': completed_tasks,
                    'avg_productivity_score': avg_productivity_score,
                    'peak_times': peak_times,
                    'achievements': achievements,
                    'challenges': challenges,
                    'project_progress': project_progress,
                    'sessions_count': len(sessions),
                    'interruption_rate': len(interrupted_sessions) / len(sessions) if sessions else 0,
                    'time_entries': time_entries
                }
                
        except Exception as e:
            logger.error("Failed to gather report data", user_id=user_id, error=str(e))
            return {}
    
    async def _generate_report_content(self, 
                                     user_id: str, 
                                     report_type: str, 
                                     period: str, 
                                     report_data: Dict[str, Any]) -> ProgressReport:
        """Generate comprehensive report content"""
        
        # Executive summary
        total_focus_time = report_data.get('total_focus_time', 0)
        completed_tasks_count = len(report_data.get('completed_tasks', []))
        avg_productivity = report_data.get('avg_productivity_score', 0)
        
        executive_summary = f"""
        During this {period} period, you achieved {total_focus_time} minutes of focused work 
        across {completed_tasks_count} completed tasks. Your average productivity score was 
        {avg_productivity:.2f}, indicating {'strong' if avg_productivity > 0.7 else 'moderate'} 
        performance levels.
        """.strip()
        
        # Create report sections
        sections = []
        
        # Productivity metrics section
        productivity_section = ReportSection(
            title="Productivity Metrics",
            content=f"""
            Key productivity indicators for this {period}:
            
            - Total Focus Time: {total_focus_time} minutes
            - Tasks Completed: {completed_tasks_count}
            - Average Productivity Score: {avg_productivity:.2f}
            - Sessions Count: {report_data.get('sessions_count', 0)}
            - Interruption Rate: {report_data.get('interruption_rate', 0):.1%}
            """.strip(),
            metrics={
                'focus_time': total_focus_time,
                'completion_rate': len(report_data.get('completed_tasks', [])),
                'productivity_score': avg_productivity
            }
        )
        sections.append(productivity_section)
        
        # Achievements section
        achievements = report_data.get('achievements', [])
        achievements_section = ReportSection(
            title="Key Achievements",
            content="\\n".join(f"• {achievement}" for achievement in achievements) or "No specific achievements recorded for this period.",
            metrics={'achievement_count': len(achievements)}
        )
        sections.append(achievements_section)
        
        # Challenges section
        challenges = report_data.get('challenges', [])
        challenges_section = ReportSection(
            title="Challenges Identified",
            content="\\n".join(f"• {challenge}" for challenge in challenges) or "No significant challenges identified.",
            metrics={'challenge_count': len(challenges)}
        )
        sections.append(challenges_section)
        
        # Generate recommendations
        recommendations = []
        if avg_productivity < 0.6:
            recommendations.append("Consider adjusting work schedule to align with peak productivity hours")
        if report_data.get('interruption_rate', 0) > 0.3:
            recommendations.append("Implement focus techniques to reduce interruption rate")
        if len(challenges) > 2:
            recommendations.append("Prioritize addressing identified challenges to improve performance")
        
        recommendations.extend([
            "Schedule deep work sessions during peak performance times",
            "Review and optimize task prioritization strategies"
        ])
        
        # Generate action items
        action_items = [
            f"Schedule {period} review meeting to discuss progress",
            "Identify tools to improve focus and reduce interruptions",
            "Set specific productivity goals for next period"
        ]
        
        # Key metrics
        key_metrics = {
            'focus_time_hours': total_focus_time / 60,
            'productivity_trend': '+5%' if avg_productivity > 0.7 else '-2%',  # Mock trend
            'goal_completion_rate': '85%',  # Mock data
            'efficiency_score': avg_productivity
        }
        
        return ProgressReport(
            title=f"{period.title()} Progress Report",
            period=period,
            executive_summary=executive_summary,
            sections=sections,
            key_metrics=key_metrics,
            recommendations=recommendations,
            action_items=action_items,
            export_formats=['pdf', 'docx', 'html', 'markdown']
        )
    
    async def _format_report(self, report: ProgressReport, report_data: Dict[str, Any]) -> Dict[str, Any]:
        """Format report for different output formats"""
        
        # Create formatted content
        formatted_content = {
            'html': self._format_as_html(report),
            'markdown': self._format_as_markdown(report),
            'plain_text': self._format_as_text(report)
        }
        
        return {
            'title': report.title,
            'period': report.period,
            'generated_at': datetime.now().isoformat(),
            'executive_summary': report.executive_summary,
            'sections': [asdict(section) for section in report.sections],
            'key_metrics': report.key_metrics,
            'recommendations': report.recommendations,
            'action_items': report.action_items,
            'formatted_content': formatted_content,
            'export_formats': report.export_formats
        }
    
    def _format_as_html(self, report: ProgressReport) -> str:
        """Format report as HTML"""
        html = f"""
        <html>
        <head><title>{report.title}</title></head>
        <body>
            <h1>{report.title}</h1>
            <h2>Executive Summary</h2>
            <p>{report.executive_summary}</p>
            
            <h2>Key Metrics</h2>
            <ul>
        """
        
        for key, value in report.key_metrics.items():
            html += f"<li><strong>{key.replace('_', ' ').title()}:</strong> {value}</li>"
        
        html += "</ul>"
        
        for section in report.sections:
            html += f"""
            <h2>{section.title}</h2>
            <p>{section.content.replace('\n', '<br>')}</p>
            """
        
        html += """
            <h2>Recommendations</h2>
            <ul>
        """
        
        for rec in report.recommendations:
            html += f"<li>{rec}</li>"
        
        html += """
            </ul>
            <h2>Action Items</h2>
            <ul>
        """
        
        for item in report.action_items:
            html += f"<li>{item}</li>"
        
        html += """
            </ul>
        </body>
        </html>
        """
        
        return html
    
    def _format_as_markdown(self, report: ProgressReport) -> str:
        """Format report as Markdown"""
        markdown = f"""# {report.title}

## Executive Summary
{report.executive_summary}

## Key Metrics
"""
        
        for key, value in report.key_metrics.items():
            markdown += f"- **{key.replace('_', ' ').title()}:** {value}\\n"
        
        for section in report.sections:
            markdown += f"""
## {section.title}
{section.content}
"""
        
        markdown += "\n## Recommendations\n"
        for rec in report.recommendations:
            markdown += f"- {rec}\\n"
        
        markdown += "\n## Action Items\n"
        for item in report.action_items:
            markdown += f"- {item}\\n"
        
        return markdown
    
    def _format_as_text(self, report: ProgressReport) -> str:
        """Format report as plain text"""
        text = f"""{report.title}
{'=' * len(report.title)}

Executive Summary:
{report.executive_summary}

Key Metrics:
"""
        
        for key, value in report.key_metrics.items():
            text += f"  {key.replace('_', ' ').title()}: {value}\\n"
        
        for section in report.sections:
            text += f"""
{section.title}:
{'-' * len(section.title)}
{section.content}
"""
        
        text += "\nRecommendations:\n"
        for i, rec in enumerate(report.recommendations, 1):
            text += f"  {i}. {rec}\\n"
        
        text += "\nAction Items:\n"
        for i, item in enumerate(report.action_items, 1):
            text += f"  {i}. {item}\\n"
        
        return text
    
    async def _save_report(self, user_id: str, formatted_report: Dict[str, Any]) -> Dict[str, Any]:
        """Save generated report"""
        report_id = f"report_{user_id}_{int(datetime.now().timestamp())}"
        
        if self.redis:
            try:
                await self.redis.setex(
                    f"report:{report_id}",
                    7200,  # 2 hours TTL
                    json.dumps(formatted_report, default=str)
                )
            except Exception as e:
                logger.warning("Failed to cache report", user_id=user_id, error=str(e))
        
        return {
            'id': report_id,
            'status': 'saved',
            'created_at': datetime.now().isoformat()
        }
    
    async def _generate_report_charts(self, report_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate chart data for reports"""
        charts = []
        
        # Productivity trend chart
        if report_data.get('sessions_count', 0) > 0:
            charts.append({
                'type': 'line',
                'title': 'Productivity Trend',
                'data': {
                    'labels': ['Week 1', 'Week 2', 'Week 3', 'Week 4'],
                    'values': [0.6, 0.7, 0.8, report_data.get('avg_productivity_score', 0.7)]
                }
            })
        
        # Task completion chart
        completed_count = len(report_data.get('completed_tasks', []))
        if completed_count > 0:
            charts.append({
                'type': 'pie',
                'title': 'Task Status Distribution',
                'data': {
                    'labels': ['Completed', 'In Progress', 'Pending'],
                    'values': [completed_count, 3, 5]  # Mock data
                }
            })
        
        return charts
    
    async def _suggest_report_recipients(self, user_id: str) -> List[Dict[str, str]]:
        """Suggest recipients for the report"""
        # Mock recipients - in real app would analyze user's contacts
        return [
            {'name': 'Manager', 'email': 'manager@company.com', 'relationship': 'supervisor'},
            {'name': 'Team Lead', 'email': 'lead@company.com', 'relationship': 'colleague'},
            {'name': 'HR Partner', 'email': 'hr@company.com', 'relationship': 'support'}
        ]
    
    # Public utility methods
    async def get_content_suggestions(self, user_id: str, content_type: ContentType) -> List[Dict[str, Any]]:
        """Get content suggestions based on user activity"""
        suggestions = []
        
        try:
            if content_type == ContentType.EMAIL_DRAFT:
                # Suggest emails based on recent activities
                suggestions.extend([
                    {
                        'type': 'follow_up',
                        'title': 'Follow up on project status',
                        'confidence': 0.8,
                        'reasoning': 'You have pending tasks that may need stakeholder updates'
                    },
                    {
                        'type': 'update',
                        'title': 'Weekly progress update',
                        'confidence': 0.7,
                        'reasoning': 'Regular update schedule detected'
                    }
                ])
            
            elif content_type == ContentType.PROGRESS_REPORT:
                suggestions.extend([
                    {
                        'type': 'weekly_report',
                        'title': 'Weekly productivity report',
                        'confidence': 0.9,
                        'reasoning': 'Sufficient data available for weekly analysis'
                    }
                ])
            
            return suggestions
            
        except Exception as e:
            logger.error("Failed to get content suggestions", user_id=user_id, error=str(e))
            return []