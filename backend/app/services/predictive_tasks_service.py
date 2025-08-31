"""
Predictive Task Creation Service
AI that creates tasks before users think of them
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import structlog
from enum import Enum

# Database imports
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, Task, PomodoroSession, TimeEntry, UserAnalytics

logger = structlog.get_logger()

class PredictionSource(Enum):
    PATTERN_BASED = "pattern_based"
    CALENDAR_BASED = "calendar_based"
    GOAL_BASED = "goal_based"
    DEADLINE_BASED = "deadline_based"
    AI_GENERATED = "ai_generated"

@dataclass
class PredictedTask:
    """Structure for predicted tasks"""
    title: str
    description: str
    estimated_duration: int  # minutes
    confidence: float  # 0.0 to 1.0
    source: PredictionSource
    priority: str = "medium"
    due_date: Optional[datetime] = None
    category: str = "work"
    reasoning: str = ""
    dependencies: List[str] = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []

@dataclass
class PredictionContext:
    """Context data for making predictions"""
    user_id: str
    historical_patterns: Dict[str, Any]
    calendar_events: List[Dict[str, Any]]
    active_projects: List[Dict[str, Any]]
    current_goals: List[Dict[str, Any]]
    recent_tasks: List[Dict[str, Any]]
    productivity_trends: Dict[str, Any]
    time_of_day: str
    day_of_week: str
    upcoming_deadlines: List[Dict[str, Any]]

class PredictiveTaskService:
    """Service for generating predictive tasks based on patterns and context"""
    
    def __init__(self, redis_client=None, openai_client=None):
        self.redis = redis_client
        self.openai_client = openai_client
        self.prediction_cache = {}
        self.user_patterns = {}
    
    async def generate_predictive_tasks(self, user_id: str) -> List[Dict[str, Any]]:
        """Generate tasks based on patterns, calendar, and context"""
        logger.info("Generating predictive tasks", user_id=user_id)
        
        try:
            # Gather contextual data
            context = await self._gather_prediction_context(user_id)
            
            # Use multiple prediction methods
            predictions = await asyncio.gather(
                self._pattern_based_prediction(context),
                self._calendar_based_prediction(context),
                self._goal_based_prediction(context),
                self._deadline_based_prediction(context)
            )
            
            # Combine and rank predictions
            combined_tasks = self._combine_predictions(predictions)
            ranked_tasks = await self._rank_by_importance(combined_tasks, context)
            
            # Auto-create high-confidence tasks
            auto_created = []
            for task in ranked_tasks[:3]:  # Top 3 only
                if task['confidence'] > 0.85:
                    created_task = await self._auto_create_task(user_id, task)
                    auto_created.append(created_task)
                    logger.info("Auto-created high-confidence task", 
                               user_id=user_id, 
                               task_title=task['title'],
                               confidence=task['confidence'])
            
            # Cache all predictions for user review
            await self._cache_predictions(user_id, ranked_tasks)
            
            logger.info("Predictive task generation completed", 
                       user_id=user_id, 
                       total_predictions=len(ranked_tasks),
                       auto_created=len(auto_created))
            
            return {
                'auto_created_tasks': auto_created,
                'suggested_tasks': ranked_tasks[:10],  # Top 10 suggestions
                'prediction_summary': {
                    'total_predictions': len(ranked_tasks),
                    'high_confidence_count': len([t for t in ranked_tasks if t['confidence'] > 0.8]),
                    'sources_used': list(set(t['source'] for t in ranked_tasks))
                }
            }
            
        except Exception as e:
            logger.error("Failed to generate predictive tasks", user_id=user_id, error=str(e))
            raise
    
    async def _gather_prediction_context(self, user_id: str) -> PredictionContext:
        """Gather comprehensive context for predictions"""
        logger.debug("Gathering prediction context", user_id=user_id)
        
        try:
            async with get_db() as db:
                # Get historical patterns
                historical_patterns = await self._analyze_user_patterns(user_id, db)
                
                # Get recent tasks
                recent_tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.created_at >= datetime.now() - timedelta(days=30)
                ).all()
                
                # Get productivity trends
                productivity_trends = await self._get_productivity_trends(user_id, db)
                
                # Mock calendar and project data (would integrate with real systems)
                calendar_events = await self._get_calendar_events(user_id)
                active_projects = await self._get_active_projects(user_id)
                current_goals = await self._get_current_goals(user_id)
                upcoming_deadlines = await self._get_upcoming_deadlines(user_id)
                
                current_time = datetime.now()
                
                context = PredictionContext(
                    user_id=user_id,
                    historical_patterns=historical_patterns,
                    calendar_events=calendar_events,
                    active_projects=active_projects,
                    current_goals=current_goals,
                    recent_tasks=[self._task_to_dict(t) for t in recent_tasks],
                    productivity_trends=productivity_trends,
                    time_of_day=self._get_time_period(current_time.hour),
                    day_of_week=current_time.strftime('%A'),
                    upcoming_deadlines=upcoming_deadlines
                )
                
                logger.debug("Context gathered successfully", 
                           user_id=user_id,
                           recent_tasks_count=len(recent_tasks),
                           calendar_events_count=len(calendar_events))
                
                return context
                
        except Exception as e:
            logger.error("Failed to gather prediction context", user_id=user_id, error=str(e))
            raise
    
    async def _pattern_based_prediction(self, context: PredictionContext) -> List[PredictedTask]:
        """Predict tasks based on historical patterns"""
        logger.debug("Generating pattern-based predictions", user_id=context.user_id)
        
        predictions = []
        user_patterns = context.historical_patterns
        current_time = datetime.now()
        
        try:
            # Weekly recurring patterns
            day_of_week = current_time.strftime('%A')
            if day_of_week in user_patterns.get('weekly_tasks', {}):
                weekly_tasks = user_patterns['weekly_tasks'][day_of_week]
                for task_pattern in weekly_tasks:
                    prediction = PredictedTask(
                        title=task_pattern['title'],
                        description=f"Recurring {day_of_week} task based on your patterns",
                        estimated_duration=task_pattern.get('avg_duration', 25),
                        confidence=task_pattern.get('occurrence_rate', 0.7),
                        source=PredictionSource.PATTERN_BASED,
                        reasoning=f"You typically do this task on {day_of_week}s"
                    )
                    predictions.append(prediction)
            
            # Time-of-day patterns
            current_hour = current_time.hour
            if current_hour in user_patterns.get('hourly_tasks', {}):
                hourly_tasks = user_patterns['hourly_tasks'][current_hour]
                for task_pattern in hourly_tasks:
                    prediction = PredictedTask(
                        title=task_pattern['title'],
                        description=f"Typical {context.time_of_day} task",
                        estimated_duration=task_pattern.get('avg_duration', 30),
                        confidence=task_pattern.get('frequency', 0.6),
                        source=PredictionSource.PATTERN_BASED,
                        reasoning=f"You often work on this around {current_hour}:00"
                    )
                    predictions.append(prediction)
            
            # Project milestone predictions
            for project in context.active_projects:
                if 'next_milestone_due' in project:
                    days_until_due = (project['next_milestone_due'] - current_time).days
                    if 0 <= days_until_due <= 3:
                        prediction = PredictedTask(
                            title=f"Prepare for {project['name']} milestone",
                            description="Predicted based on project timeline and your preparation patterns",
                            estimated_duration=60,
                            confidence=0.75,
                            source=PredictionSource.PATTERN_BASED,
                            due_date=project['next_milestone_due'] - timedelta(hours=4),
                            reasoning=f"Milestone due in {days_until_due} days"
                        )
                        predictions.append(prediction)
            
            # Task completion patterns
            incomplete_tasks = [t for t in context.recent_tasks if t['status'] != 'completed']
            for task in incomplete_tasks:
                task_age = (current_time - datetime.fromisoformat(task['created_at'])).days
                if task_age > 3:  # Old incomplete task
                    prediction = PredictedTask(
                        title=f"Follow up: {task['title']}",
                        description="Old incomplete task that might need attention",
                        estimated_duration=task.get('estimated_pomodoros', 1) * 25,
                        confidence=0.6,
                        source=PredictionSource.PATTERN_BASED,
                        reasoning=f"Task has been incomplete for {task_age} days"
                    )
                    predictions.append(prediction)
            
            logger.debug("Pattern-based predictions generated", 
                        user_id=context.user_id,
                        prediction_count=len(predictions))
            
            return predictions
            
        except Exception as e:
            logger.error("Failed to generate pattern-based predictions", 
                        user_id=context.user_id, error=str(e))
            return []
    
    async def _calendar_based_prediction(self, context: PredictionContext) -> List[PredictedTask]:
        """Predict tasks based on upcoming calendar events"""
        logger.debug("Generating calendar-based predictions", user_id=context.user_id)
        
        predictions = []
        
        try:
            for meeting in context.calendar_events:
                meeting_time = meeting.get('start_time')
                if not meeting_time:
                    continue
                
                # Predict prep tasks for important meetings
                if meeting.get('importance_score', 0) > 0.7:
                    prep_task = PredictedTask(
                        title=f"Prepare for {meeting['title']}",
                        description="Meeting preparation: agenda review, materials gathering",
                        estimated_duration=30,
                        confidence=0.8,
                        source=PredictionSource.CALENDAR_BASED,
                        due_date=meeting_time - timedelta(hours=2),
                        reasoning="Important meeting requires preparation"
                    )
                    predictions.append(prep_task)
                
                # Predict follow-up tasks
                if meeting.get('type') == 'client_meeting':
                    followup_task = PredictedTask(
                        title=f"Follow up on {meeting['title']}",
                        description="Send summary and action items to participants",
                        estimated_duration=20,
                        confidence=0.9,
                        source=PredictionSource.CALENDAR_BASED,
                        due_date=meeting.get('end_time', meeting_time + timedelta(hours=1)) + timedelta(hours=4),
                        reasoning="Client meetings typically require follow-up"
                    )
                    predictions.append(followup_task)
                
                # Predict review tasks for recurring meetings
                if meeting.get('recurring', False):
                    review_task = PredictedTask(
                        title=f"Review outcomes from {meeting['title']}",
                        description="Review meeting outcomes and plan next steps",
                        estimated_duration=15,
                        confidence=0.7,
                        source=PredictionSource.CALENDAR_BASED,
                        due_date=meeting.get('end_time', meeting_time + timedelta(hours=1)) + timedelta(days=1),
                        reasoning="Recurring meetings benefit from outcome reviews"
                    )
                    predictions.append(review_task)
            
            logger.debug("Calendar-based predictions generated", 
                        user_id=context.user_id,
                        prediction_count=len(predictions))
            
            return predictions
            
        except Exception as e:
            logger.error("Failed to generate calendar-based predictions", 
                        user_id=context.user_id, error=str(e))
            return []
    
    async def _goal_based_prediction(self, context: PredictionContext) -> List[PredictedTask]:
        """Predict tasks based on user goals"""
        logger.debug("Generating goal-based predictions", user_id=context.user_id)
        
        predictions = []
        
        try:
            for goal in context.current_goals:
                goal_deadline = goal.get('deadline')
                if not goal_deadline:
                    continue
                
                days_until_deadline = (goal_deadline - datetime.now()).days
                
                # Break down goal into actionable tasks
                if days_until_deadline > 0:
                    # Weekly progress check
                    progress_task = PredictedTask(
                        title=f"Review progress on: {goal['title']}",
                        description=f"Check progress and adjust approach for goal: {goal['description']}",
                        estimated_duration=25,
                        confidence=0.8,
                        source=PredictionSource.GOAL_BASED,
                        reasoning=f"Goal deadline in {days_until_deadline} days"
                    )
                    predictions.append(progress_task)
                    
                    # Action items based on goal type
                    if goal.get('type') == 'learning':
                        learning_task = PredictedTask(
                            title=f"Study session: {goal['title']}",
                            description="Dedicated learning session for goal achievement",
                            estimated_duration=50,
                            confidence=0.75,
                            source=PredictionSource.GOAL_BASED,
                            reasoning="Learning goals require regular study sessions"
                        )
                        predictions.append(learning_task)
                    
                    elif goal.get('type') == 'project':
                        project_task = PredictedTask(
                            title=f"Work on: {goal['title']}",
                            description="Project work session for goal achievement",
                            estimated_duration=75,
                            confidence=0.8,
                            source=PredictionSource.GOAL_BASED,
                            reasoning="Project goals require dedicated work sessions"
                        )
                        predictions.append(project_task)
                
                # Urgent goals (deadline within 7 days)
                if 0 < days_until_deadline <= 7:
                    urgent_task = PredictedTask(
                        title=f"URGENT: Final push for {goal['title']}",
                        description="Intensive work session to meet upcoming deadline",
                        estimated_duration=90,
                        confidence=0.95,
                        source=PredictionSource.GOAL_BASED,
                        priority="high",
                        reasoning=f"Goal deadline in only {days_until_deadline} days"
                    )
                    predictions.append(urgent_task)
            
            logger.debug("Goal-based predictions generated", 
                        user_id=context.user_id,
                        prediction_count=len(predictions))
            
            return predictions
            
        except Exception as e:
            logger.error("Failed to generate goal-based predictions", 
                        user_id=context.user_id, error=str(e))
            return []
    
    async def _deadline_based_prediction(self, context: PredictionContext) -> List[PredictedTask]:
        """Predict tasks based on upcoming deadlines"""
        logger.debug("Generating deadline-based predictions", user_id=context.user_id)
        
        predictions = []
        
        try:
            for deadline in context.upcoming_deadlines:
                deadline_date = deadline.get('date')
                if not deadline_date:
                    continue
                
                days_until_deadline = (deadline_date - datetime.now()).days
                
                if days_until_deadline <= 0:
                    continue  # Skip overdue deadlines
                
                # Create preparation tasks based on deadline urgency
                if days_until_deadline <= 1:
                    # Last-minute preparation
                    urgent_prep = PredictedTask(
                        title=f"URGENT PREP: {deadline['title']}",
                        description="Last-minute preparation for imminent deadline",
                        estimated_duration=60,
                        confidence=0.95,
                        source=PredictionSource.DEADLINE_BASED,
                        priority="critical",
                        due_date=deadline_date - timedelta(hours=2),
                        reasoning="Deadline is within 24 hours"
                    )
                    predictions.append(urgent_prep)
                
                elif days_until_deadline <= 3:
                    # Short-term preparation
                    prep_task = PredictedTask(
                        title=f"Prepare for: {deadline['title']}",
                        description="Preparation work for upcoming deadline",
                        estimated_duration=45,
                        confidence=0.85,
                        source=PredictionSource.DEADLINE_BASED,
                        priority="high",
                        reasoning=f"Deadline in {days_until_deadline} days"
                    )
                    predictions.append(prep_task)
                
                elif days_until_deadline <= 7:
                    # Medium-term planning
                    planning_task = PredictedTask(
                        title=f"Plan approach for: {deadline['title']}",
                        description="Strategic planning for upcoming deadline",
                        estimated_duration=30,
                        confidence=0.7,
                        source=PredictionSource.DEADLINE_BASED,
                        reasoning=f"Deadline in {days_until_deadline} days - good time to plan"
                    )
                    predictions.append(planning_task)
                
                # Add buffer tasks for complex deadlines
                if deadline.get('complexity', 0) > 0.7:
                    buffer_task = PredictedTask(
                        title=f"Buffer time: {deadline['title']}",
                        description="Additional time buffer for complex deadline",
                        estimated_duration=30,
                        confidence=0.6,
                        source=PredictionSource.DEADLINE_BASED,
                        due_date=deadline_date - timedelta(days=1),
                        reasoning="Complex deadline may need extra time"
                    )
                    predictions.append(buffer_task)
            
            logger.debug("Deadline-based predictions generated", 
                        user_id=context.user_id,
                        prediction_count=len(predictions))
            
            return predictions
            
        except Exception as e:
            logger.error("Failed to generate deadline-based predictions", 
                        user_id=context.user_id, error=str(e))
            return []
    
    def _combine_predictions(self, predictions_list: List[List[PredictedTask]]) -> List[Dict[str, Any]]:
        """Combine predictions from different sources"""
        combined = []
        
        for prediction_group in predictions_list:
            for prediction in prediction_group:
                combined.append(asdict(prediction))
        
        # Remove duplicates based on title similarity
        unique_predictions = []
        seen_titles = set()
        
        for pred in combined:
            title_key = pred['title'].lower().strip()
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                unique_predictions.append(pred)
        
        return unique_predictions
    
    async def _rank_by_importance(self, predictions: List[Dict[str, Any]], context: PredictionContext) -> List[Dict[str, Any]]:
        """Rank predictions by importance and relevance"""
        logger.debug("Ranking predictions by importance", user_id=context.user_id)
        
        # Calculate importance score for each prediction
        for pred in predictions:
            importance_score = 0.0
            
            # Base confidence weight
            importance_score += pred['confidence'] * 0.4
            
            # Priority weight
            priority_weights = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}
            importance_score += priority_weights.get(pred.get('priority', 'medium'), 0.5) * 0.3
            
            # Time urgency weight
            if pred.get('due_date'):
                due_date = pred['due_date']
                if isinstance(due_date, str):
                    due_date = datetime.fromisoformat(due_date)
                days_until_due = (due_date - datetime.now()).days
                if days_until_due <= 1:
                    importance_score += 0.3
                elif days_until_due <= 3:
                    importance_score += 0.2
                elif days_until_due <= 7:
                    importance_score += 0.1
            
            # Source reliability weight
            source_weights = {
                PredictionSource.DEADLINE_BASED: 0.9,
                PredictionSource.CALENDAR_BASED: 0.8,
                PredictionSource.PATTERN_BASED: 0.7,
                PredictionSource.GOAL_BASED: 0.6,
                PredictionSource.AI_GENERATED: 0.5
            }
            source_enum = PredictionSource(pred['source'])
            importance_score += source_weights.get(source_enum, 0.5) * 0.2
            
            pred['importance_score'] = min(1.0, importance_score)
        
        # Sort by importance score
        ranked = sorted(predictions, key=lambda x: x['importance_score'], reverse=True)
        
        logger.debug("Predictions ranked", 
                    user_id=context.user_id,
                    top_score=ranked[0]['importance_score'] if ranked else 0)
        
        return ranked
    
    async def _auto_create_task(self, user_id: str, prediction: Dict[str, Any]) -> Dict[str, Any]:
        """Auto-create a task from a high-confidence prediction"""
        logger.debug("Auto-creating task from prediction", 
                    user_id=user_id, 
                    task_title=prediction['title'])
        
        try:
            async with get_db() as db:
                # Create new task
                new_task = Task(
                    user_id=int(user_id),
                    title=prediction['title'],
                    description=f"[AUTO-GENERATED] {prediction['description']}\\n\\nReasoning: {prediction.get('reasoning', '')}",
                    priority=prediction.get('priority', 'medium'),
                    estimated_pomodoros=max(1, prediction.get('estimated_duration', 25) // 25),
                    due_date=prediction.get('due_date') if prediction.get('due_date') else None
                )
                
                db.add(new_task)
                db.commit()
                db.refresh(new_task)
                
                created_task = {
                    'id': new_task.id,
                    'title': new_task.title,
                    'description': new_task.description,
                    'confidence': prediction['confidence'],
                    'source': prediction['source'],
                    'auto_created': True,
                    'created_at': new_task.created_at.isoformat()
                }
                
                logger.info("Task auto-created successfully", 
                           user_id=user_id,
                           task_id=new_task.id,
                           confidence=prediction['confidence'])
                
                return created_task
                
        except Exception as e:
            logger.error("Failed to auto-create task", 
                        user_id=user_id, 
                        task_title=prediction['title'],
                        error=str(e))
            raise
    
    # Helper methods
    async def _analyze_user_patterns(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Analyze user's historical patterns"""
        # Mock pattern analysis - in real implementation would analyze historical data
        return {
            'weekly_tasks': {
                'Monday': [
                    {'title': 'Weekly planning', 'avg_duration': 30, 'occurrence_rate': 0.8},
                    {'title': 'Email review', 'avg_duration': 20, 'occurrence_rate': 0.9}
                ],
                'Friday': [
                    {'title': 'Week review', 'avg_duration': 25, 'occurrence_rate': 0.7}
                ]
            },
            'hourly_tasks': {
                9: [{'title': 'Deep work session', 'avg_duration': 90, 'frequency': 0.6}],
                14: [{'title': 'Administrative tasks', 'avg_duration': 45, 'frequency': 0.5}]
            }
        }
    
    async def _get_productivity_trends(self, user_id: str, db: Session) -> Dict[str, Any]:
        """Get user's productivity trends"""
        analytics = db.query(UserAnalytics).filter(UserAnalytics.user_id == user_id).first()
        if analytics:
            return {
                'avg_focus_score': analytics.avg_focus_score,
                'productivity_trend': analytics.productivity_trend,
                'best_focus_hour': analytics.best_focus_hour,
                'interruption_rate': analytics.interruption_rate
            }
        return {}
    
    async def _get_calendar_events(self, user_id: str) -> List[Dict[str, Any]]:
        """Get upcoming calendar events (mock data)"""
        return [
            {
                'title': 'Team standup',
                'start_time': datetime.now() + timedelta(hours=2),
                'end_time': datetime.now() + timedelta(hours=2, minutes=30),
                'type': 'meeting',
                'importance_score': 0.6,
                'recurring': True
            },
            {
                'title': 'Client presentation',
                'start_time': datetime.now() + timedelta(days=1),
                'end_time': datetime.now() + timedelta(days=1, hours=1),
                'type': 'client_meeting',
                'importance_score': 0.9,
                'recurring': False
            }
        ]
    
    async def _get_active_projects(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active projects (mock data)"""
        return [
            {
                'name': 'Website redesign',
                'next_milestone_due': datetime.now() + timedelta(days=3),
                'completion_percentage': 0.7
            }
        ]
    
    async def _get_current_goals(self, user_id: str) -> List[Dict[str, Any]]:
        """Get current user goals (mock data)"""
        return [
            {
                'title': 'Learn Python',
                'description': 'Complete Python certification course',
                'type': 'learning',
                'deadline': datetime.now() + timedelta(days=14)
            },
            {
                'title': 'Finish Q1 report',
                'description': 'Complete quarterly business report',
                'type': 'project',
                'deadline': datetime.now() + timedelta(days=7)
            }
        ]
    
    async def _get_upcoming_deadlines(self, user_id: str) -> List[Dict[str, Any]]:
        """Get upcoming deadlines (mock data)"""
        return [
            {
                'title': 'Tax filing',
                'date': datetime.now() + timedelta(days=5),
                'complexity': 0.8
            },
            {
                'title': 'Project proposal',
                'date': datetime.now() + timedelta(days=2),
                'complexity': 0.6
            }
        ]
    
    def _task_to_dict(self, task: Task) -> Dict[str, Any]:
        """Convert Task model to dictionary"""
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status,
            'priority': task.priority,
            'estimated_pomodoros': task.estimated_pomodoros,
            'created_at': task.created_at.isoformat(),
            'due_date': task.due_date.isoformat() if task.due_date else None
        }
    
    def _get_time_period(self, hour: int) -> str:
        """Get time period for the hour"""
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        else:
            return "night"
    
    async def _cache_predictions(self, user_id: str, predictions: List[Dict[str, Any]]):
        """Cache predictions for user review"""
        if self.redis:
            try:
                await self.redis.setex(
                    f"predictions:{user_id}",
                    3600,  # 1 hour TTL
                    json.dumps(predictions, default=str)
                )
                logger.debug("Predictions cached", user_id=user_id, count=len(predictions))
            except Exception as e:
                logger.warning("Failed to cache predictions", user_id=user_id, error=str(e))
    
    async def get_cached_predictions(self, user_id: str) -> List[Dict[str, Any]]:
        """Get cached predictions for user"""
        if self.redis:
            try:
                cached = await self.redis.get(f"predictions:{user_id}")
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning("Failed to get cached predictions", user_id=user_id, error=str(e))
        return []