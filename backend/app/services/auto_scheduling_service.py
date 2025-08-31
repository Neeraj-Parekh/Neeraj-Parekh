"""
Auto-Scheduling Intelligence Service
Calendar that optimizes itself based on productivity patterns
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
import numpy as np
import structlog
from enum import Enum

# Database imports
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, Task, PomodoroSession, TimeEntry, UserAnalytics

logger = structlog.get_logger()

class OptimizationType(Enum):
    MOVE_MEETING_FROM_PEAK_FOCUS = "move_meeting_from_peak_focus"
    BLOCK_FOCUS_TIME = "block_focus_time"
    RESCHEDULE_LOW_ENERGY_TASKS = "reschedule_low_energy_tasks"
    CONSOLIDATE_MEETINGS = "consolidate_meetings"
    ADD_BUFFER_TIME = "add_buffer_time"
    OPTIMIZE_CONTEXT_SWITCHING = "optimize_context_switching"

@dataclass
class ProductivityPattern:
    """User's productivity patterns by time"""
    hourly_productivity: Dict[int, Dict[str, float]]
    daily_productivity: Dict[str, float]
    optimal_focus_blocks: List[Dict[str, Any]]
    energy_levels: Dict[str, Any]
    peak_hours: List[int]
    low_energy_hours: List[int]
    context_switch_tolerance: float

@dataclass
class ScheduleOptimization:
    """Represents a schedule optimization opportunity"""
    optimization_type: OptimizationType
    title: str
    description: str
    confidence: float
    impact_score: float
    original_time: Optional[datetime] = None
    suggested_time: Optional[datetime] = None
    duration: Optional[int] = None
    reasoning: str = ""
    meeting_id: Optional[str] = None
    task_id: Optional[str] = None

@dataclass
class ScheduleBlock:
    """Represents a time block in the schedule"""
    start_time: datetime
    end_time: datetime
    title: str
    block_type: str  # meeting, task, focus_time, break, buffer
    moveable: bool = True
    importance: float = 0.5
    energy_requirement: float = 0.5  # 0.0 = low energy, 1.0 = high energy

class AutoSchedulingService:
    """Service for automatic schedule optimization based on productivity patterns"""
    
    def __init__(self, redis_client=None, calendar_api=None):
        self.redis = redis_client
        self.calendar_api = calendar_api
        self.optimization_cache = {}
    
    async def optimize_schedule(self, user_id: str, date_range: Tuple[datetime, datetime]) -> Dict[str, Any]:
        """Automatically reschedule meetings and tasks for optimal productivity"""
        logger.info("Starting schedule optimization", 
                   user_id=user_id, 
                   date_range=f"{date_range[0]} to {date_range[1]}")
        
        try:
            # Get user's productivity patterns
            productivity_map = await self._get_productivity_patterns(user_id)
            
            # Get current schedule
            current_schedule = await self._get_current_schedule(user_id, date_range)
            
            # Identify optimization opportunities
            optimizations = await self._identify_optimization_opportunities(
                current_schedule, productivity_map
            )
            
            # Execute optimizations (with user consent)
            optimization_results = []
            executed_count = 0
            
            for opportunity in optimizations:
                if (opportunity.confidence > 0.8 and 
                    opportunity.impact_score > 0.6 and 
                    executed_count < 5):  # Limit to 5 optimizations per run
                    
                    result = await self._execute_optimization(user_id, opportunity)
                    optimization_results.append(result)
                    executed_count += 1
                    
                    logger.info("Optimization executed", 
                              user_id=user_id,
                              optimization_type=opportunity.optimization_type.value,
                              confidence=opportunity.confidence,
                              impact=opportunity.impact_score)
            
            # Calculate optimization impact
            impact_summary = self._calculate_optimization_impact(optimization_results)
            
            # Cache results for user review
            await self._cache_optimization_results(user_id, {
                'executed_optimizations': optimization_results,
                'suggested_optimizations': [asdict(o) for o in optimizations[executed_count:]],
                'impact_summary': impact_summary
            })
            
            logger.info("Schedule optimization completed", 
                       user_id=user_id,
                       executed_count=executed_count,
                       total_opportunities=len(optimizations))
            
            return {
                'executed_optimizations': optimization_results,
                'suggested_optimizations': optimizations[executed_count:],
                'impact_summary': impact_summary,
                'productivity_gain_estimate': impact_summary.get('total_productivity_gain', 0)
            }
            
        except Exception as e:
            logger.error("Failed to optimize schedule", user_id=user_id, error=str(e))
            raise
    
    async def _get_productivity_patterns(self, user_id: str) -> ProductivityPattern:
        """Analyze user's historical productivity by time of day/week"""
        logger.debug("Analyzing productivity patterns", user_id=user_id)
        
        try:
            async with get_db() as db:
                # Get productivity data from the last 90 days
                start_date = datetime.now() - timedelta(days=90)
                
                # Get pomodoro sessions with focus scores
                sessions = db.query(PomodoroSession).filter(
                    PomodoroSession.user_id == user_id,
                    PomodoroSession.completed_at >= start_date,
                    PomodoroSession.completed_at.isnot(None)
                ).all()
                
                # Get tasks completion data
                tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.updated_at >= start_date,
                    Task.status == 'completed'
                ).all()
                
                patterns = ProductivityPattern(
                    hourly_productivity={},
                    daily_productivity={},
                    optimal_focus_blocks=[],
                    energy_levels={},
                    peak_hours=[],
                    low_energy_hours=[],
                    context_switch_tolerance=0.5
                )
                
                # Analyze hourly productivity
                hourly_data = {}
                for session in sessions:
                    if session.completed_at:
                        hour = session.completed_at.hour
                        if hour not in hourly_data:
                            hourly_data[hour] = []
                        
                        hourly_data[hour].append({
                            'focus_score': session.focus_score or 0.5,
                            'completion_rate': 1.0 if not session.interrupted else 0.7,
                            'interruptions': 1 if session.interrupted else 0
                        })
                
                # Calculate hourly averages
                for hour in range(24):
                    if hour in hourly_data:
                        hour_sessions = hourly_data[hour]
                        patterns.hourly_productivity[hour] = {
                            'avg_focus_score': np.mean([s['focus_score'] for s in hour_sessions]),
                            'avg_completion_rate': np.mean([s['completion_rate'] for s in hour_sessions]),
                            'interruption_rate': np.mean([s['interruptions'] for s in hour_sessions]),
                            'session_count': len(hour_sessions)
                        }
                    else:
                        patterns.hourly_productivity[hour] = {
                            'avg_focus_score': 0.5,
                            'avg_completion_rate': 0.5,
                            'interruption_rate': 0.5,
                            'session_count': 0
                        }
                
                # Identify peak hours (top 25% by focus score)
                hourly_scores = [(hour, data['avg_focus_score']) 
                               for hour, data in patterns.hourly_productivity.items()]
                hourly_scores.sort(key=lambda x: x[1], reverse=True)
                
                peak_threshold = len(hourly_scores) // 4
                patterns.peak_hours = [hour for hour, _ in hourly_scores[:peak_threshold]]
                patterns.low_energy_hours = [hour for hour, _ in hourly_scores[-peak_threshold:]]
                
                # Identify optimal focus blocks (2+ hour periods of high productivity)
                optimal_blocks = []
                for start_hour in range(22):  # Check all possible 2-hour blocks
                    block_score = 0
                    for hour in range(start_hour, start_hour + 2):
                        if hour in patterns.hourly_productivity:
                            block_score += patterns.hourly_productivity[hour]['avg_focus_score']
                    
                    avg_block_score = block_score / 2
                    if avg_block_score > 0.75:  # High productivity threshold
                        optimal_blocks.append({
                            'start_hour': start_hour,
                            'end_hour': start_hour + 2,
                            'productivity_score': avg_block_score,
                            'focus_quality': 'high' if avg_block_score > 0.85 else 'medium'
                        })
                
                patterns.optimal_focus_blocks = optimal_blocks
                
                # Calculate daily productivity patterns
                daily_data = {}
                for session in sessions:
                    if session.completed_at:
                        day_name = session.completed_at.strftime('%A')
                        if day_name not in daily_data:
                            daily_data[day_name] = []
                        daily_data[day_name].append(session.focus_score or 0.5)
                
                for day in ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']:
                    if day in daily_data:
                        patterns.daily_productivity[day] = np.mean(daily_data[day])
                    else:
                        patterns.daily_productivity[day] = 0.5
                
                # Estimate context switch tolerance based on interruption patterns
                if sessions:
                    interruption_rate = sum(1 for s in sessions if s.interrupted) / len(sessions)
                    patterns.context_switch_tolerance = max(0.1, 1.0 - interruption_rate)
                
                logger.debug("Productivity patterns analyzed", 
                           user_id=user_id,
                           peak_hours=patterns.peak_hours,
                           optimal_blocks=len(patterns.optimal_focus_blocks))
                
                return patterns
                
        except Exception as e:
            logger.error("Failed to analyze productivity patterns", user_id=user_id, error=str(e))
            # Return default patterns
            return ProductivityPattern(
                hourly_productivity={hour: {'avg_focus_score': 0.5, 'avg_completion_rate': 0.5, 
                                          'interruption_rate': 0.3, 'session_count': 0} 
                                   for hour in range(24)},
                daily_productivity={day: 0.5 for day in ['Monday', 'Tuesday', 'Wednesday', 
                                                        'Thursday', 'Friday', 'Saturday', 'Sunday']},
                optimal_focus_blocks=[{'start_hour': 9, 'end_hour': 11, 'productivity_score': 0.8}],
                energy_levels={'morning': 0.8, 'afternoon': 0.6, 'evening': 0.4},
                peak_hours=[9, 10, 14, 15],
                low_energy_hours=[12, 13, 16, 17],
                context_switch_tolerance=0.6
            )
    
    async def _get_current_schedule(self, user_id: str, date_range: Tuple[datetime, datetime]) -> List[ScheduleBlock]:
        """Get current schedule for the date range"""
        logger.debug("Getting current schedule", user_id=user_id)
        
        schedule_blocks = []
        
        try:
            # Mock calendar integration - in real implementation would connect to Google Calendar, Outlook, etc.
            # For now, create sample schedule blocks
            
            current_date = date_range[0].date()
            end_date = date_range[1].date()
            
            while current_date <= end_date:
                # Add some sample meetings and tasks
                if current_date.weekday() < 5:  # Weekdays only
                    # Morning standup
                    standup_time = datetime.combine(current_date, datetime.min.time().replace(hour=9))
                    schedule_blocks.append(ScheduleBlock(
                        start_time=standup_time,
                        end_time=standup_time + timedelta(minutes=30),
                        title="Daily Standup",
                        block_type="meeting",
                        moveable=False,  # Recurring meeting
                        importance=0.6,
                        energy_requirement=0.3
                    ))
                    
                    # Lunch meeting (moveable)
                    lunch_time = datetime.combine(current_date, datetime.min.time().replace(hour=12))
                    schedule_blocks.append(ScheduleBlock(
                        start_time=lunch_time,
                        end_time=lunch_time + timedelta(hours=1),
                        title="Client Lunch Meeting",
                        block_type="meeting",
                        moveable=True,
                        importance=0.8,
                        energy_requirement=0.7
                    ))
                    
                    # Afternoon task block
                    task_time = datetime.combine(current_date, datetime.min.time().replace(hour=14))
                    schedule_blocks.append(ScheduleBlock(
                        start_time=task_time,
                        end_time=task_time + timedelta(hours=2),
                        title="Deep Work Session",
                        block_type="task",
                        moveable=True,
                        importance=0.9,
                        energy_requirement=0.9
                    ))
                
                current_date += timedelta(days=1)
            
            # Get actual tasks from database
            async with get_db() as db:
                tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.status.in_(['pending', 'in_progress']),
                    Task.due_date.between(date_range[0], date_range[1])
                ).all()
                
                for task in tasks:
                    if task.due_date:
                        # Schedule task 2 hours before due date if no specific time
                        task_time = task.due_date - timedelta(hours=2)
                        duration = task.estimated_pomodoros * 25  # minutes
                        
                        schedule_blocks.append(ScheduleBlock(
                            start_time=task_time,
                            end_time=task_time + timedelta(minutes=duration),
                            title=task.title,
                            block_type="task",
                            moveable=True,
                            importance=0.8 if task.priority == 'high' else 0.6,
                            energy_requirement=0.7
                        ))
            
            logger.debug("Current schedule retrieved", 
                        user_id=user_id,
                        blocks_count=len(schedule_blocks))
            
            return schedule_blocks
            
        except Exception as e:
            logger.error("Failed to get current schedule", user_id=user_id, error=str(e))
            return []
    
    async def _identify_optimization_opportunities(self, 
                                                  schedule: List[ScheduleBlock], 
                                                  patterns: ProductivityPattern) -> List[ScheduleOptimization]:
        """Identify opportunities to optimize the schedule"""
        logger.debug("Identifying optimization opportunities", 
                    schedule_blocks=len(schedule))
        
        optimizations = []
        
        try:
            for block in schedule:
                if not block.moveable:
                    continue
                
                block_hour = block.start_time.hour
                
                # Check if high-energy task is scheduled during low-energy time
                if (block.block_type == "task" and 
                    block.energy_requirement > 0.7 and 
                    block_hour in patterns.low_energy_hours):
                    
                    # Find better time slot
                    suggested_hour = self._find_optimal_time_slot(block, patterns)
                    if suggested_hour != block_hour:
                        optimizations.append(ScheduleOptimization(
                            optimization_type=OptimizationType.RESCHEDULE_LOW_ENERGY_TASKS,
                            title=f"Reschedule {block.title}",
                            description=f"Move high-energy task from low-energy time to optimal slot",
                            confidence=0.85,
                            impact_score=0.7,
                            original_time=block.start_time,
                            suggested_time=block.start_time.replace(hour=suggested_hour),
                            reasoning=f"Task requires high energy but scheduled at {block_hour}:00 (low energy time)"
                        ))
                
                # Check if meetings are scheduled during peak focus hours
                if (block.block_type == "meeting" and 
                    block_hour in patterns.peak_hours and
                    block.importance < 0.9):  # Don't move very important meetings
                    
                    # Suggest moving to non-peak hours
                    alternative_hour = self._find_meeting_alternative_time(block, patterns)
                    if alternative_hour != block_hour:
                        optimizations.append(ScheduleOptimization(
                            optimization_type=OptimizationType.MOVE_MEETING_FROM_PEAK_FOCUS,
                            title=f"Reschedule {block.title}",
                            description="Move meeting out of peak productivity hours",
                            confidence=0.8,
                            impact_score=0.6,
                            original_time=block.start_time,
                            suggested_time=block.start_time.replace(hour=alternative_hour),
                            reasoning=f"Meeting at {block_hour}:00 conflicts with peak focus time"
                        ))
            
            # Look for opportunities to create focus blocks
            focus_opportunities = self._identify_focus_block_opportunities(schedule, patterns)
            optimizations.extend(focus_opportunities)
            
            # Look for meeting consolidation opportunities
            consolidation_opportunities = self._identify_meeting_consolidation(schedule)
            optimizations.extend(consolidation_opportunities)
            
            # Sort by impact score
            optimizations.sort(key=lambda x: x.impact_score, reverse=True)
            
            logger.debug("Optimization opportunities identified", 
                        count=len(optimizations))
            
            return optimizations
            
        except Exception as e:
            logger.error("Failed to identify optimization opportunities", error=str(e))
            return []
    
    def _find_optimal_time_slot(self, block: ScheduleBlock, patterns: ProductivityPattern) -> int:
        """Find the optimal time slot for a task based on energy requirements"""
        if block.energy_requirement > 0.7:
            # High energy task - schedule during peak hours
            best_hour = max(patterns.peak_hours, 
                          key=lambda h: patterns.hourly_productivity[h]['avg_focus_score'])
            return best_hour
        else:
            # Low energy task - can be scheduled during any reasonable working hour
            working_hours = list(range(9, 18))  # 9 AM to 6 PM
            best_hour = min(working_hours,
                          key=lambda h: patterns.hourly_productivity[h]['avg_focus_score'])
            return best_hour
    
    def _find_meeting_alternative_time(self, block: ScheduleBlock, patterns: ProductivityPattern) -> int:
        """Find alternative time for a meeting outside peak hours"""
        working_hours = list(range(9, 18))
        non_peak_hours = [h for h in working_hours if h not in patterns.peak_hours]
        
        if non_peak_hours:
            # Choose hour with moderate productivity (good for meetings)
            return min(non_peak_hours,
                      key=lambda h: abs(patterns.hourly_productivity[h]['avg_focus_score'] - 0.6))
        else:
            return block.start_time.hour  # No change if no alternatives
    
    def _identify_focus_block_opportunities(self, 
                                          schedule: List[ScheduleBlock], 
                                          patterns: ProductivityPattern) -> List[ScheduleOptimization]:
        """Identify opportunities to create dedicated focus blocks"""
        opportunities = []
        
        for focus_block in patterns.optimal_focus_blocks:
            start_hour = focus_block['start_hour']
            end_hour = focus_block['end_hour']
            
            # Check if this time slot is free or has low-priority items
            conflicts = [block for block in schedule 
                        if (start_hour <= block.start_time.hour < end_hour and
                            block.moveable and block.importance < 0.7)]
            
            if len(conflicts) <= 1:  # At most one low-priority conflict
                opportunities.append(ScheduleOptimization(
                    optimization_type=OptimizationType.BLOCK_FOCUS_TIME,
                    title=f"Block focus time {start_hour}:00-{end_hour}:00",
                    description="Create dedicated focus block during high-productivity time",
                    confidence=0.9,
                    impact_score=0.8,
                    suggested_time=datetime.now().replace(hour=start_hour, minute=0, second=0, microsecond=0),
                    duration=(end_hour - start_hour) * 60,  # minutes
                    reasoning=f"High productivity period ({focus_block['productivity_score']:.2f} score)"
                ))
        
        return opportunities
    
    def _identify_meeting_consolidation(self, schedule: List[ScheduleBlock]) -> List[ScheduleOptimization]:
        """Identify opportunities to consolidate meetings"""
        opportunities = []
        
        meetings = [block for block in schedule if block.block_type == "meeting" and block.moveable]
        
        # Group meetings by day
        daily_meetings = {}
        for meeting in meetings:
            day = meeting.start_time.date()
            if day not in daily_meetings:
                daily_meetings[day] = []
            daily_meetings[day].append(meeting)
        
        # Look for days with scattered meetings that could be consolidated
        for day, day_meetings in daily_meetings.items():
            if len(day_meetings) >= 2:
                # Calculate time spread
                start_times = [m.start_time.hour for m in day_meetings]
                time_spread = max(start_times) - min(start_times)
                
                if time_spread > 4:  # Meetings spread over more than 4 hours
                    opportunities.append(ScheduleOptimization(
                        optimization_type=OptimizationType.CONSOLIDATE_MEETINGS,
                        title=f"Consolidate meetings on {day.strftime('%A')}",
                        description="Group meetings together to create longer focus periods",
                        confidence=0.7,
                        impact_score=0.5,
                        reasoning=f"Meetings spread over {time_spread} hours, causing fragmentation"
                    ))
        
        return opportunities
    
    async def _execute_optimization(self, user_id: str, opportunity: ScheduleOptimization) -> Dict[str, Any]:
        """Execute a specific scheduling optimization"""
        logger.debug("Executing optimization", 
                    user_id=user_id,
                    optimization_type=opportunity.optimization_type.value)
        
        try:
            if opportunity.optimization_type == OptimizationType.MOVE_MEETING_FROM_PEAK_FOCUS:
                # Move meetings out of peak productivity hours
                result = await self._reschedule_meeting(user_id, opportunity)
                
            elif opportunity.optimization_type == OptimizationType.BLOCK_FOCUS_TIME:
                # Block calendar for deep work during peak hours
                result = await self._create_focus_block(user_id, opportunity)
                
            elif opportunity.optimization_type == OptimizationType.RESCHEDULE_LOW_ENERGY_TASKS:
                # Reschedule high-energy tasks to optimal times
                result = await self._reschedule_task(user_id, opportunity)
                
            elif opportunity.optimization_type == OptimizationType.CONSOLIDATE_MEETINGS:
                # Consolidate scattered meetings
                result = await self._consolidate_meetings(user_id, opportunity)
                
            else:
                result = {
                    'optimization_type': opportunity.optimization_type.value,
                    'status': 'not_implemented',
                    'message': 'Optimization type not yet implemented'
                }
            
            result['productivity_gain_estimate'] = opportunity.impact_score
            result['confidence'] = opportunity.confidence
            
            return result
            
        except Exception as e:
            logger.error("Failed to execute optimization", 
                        user_id=user_id,
                        optimization_type=opportunity.optimization_type.value,
                        error=str(e))
            return {
                'optimization_type': opportunity.optimization_type.value,
                'status': 'failed',
                'error': str(e)
            }
    
    async def _reschedule_meeting(self, user_id: str, opportunity: ScheduleOptimization) -> Dict[str, Any]:
        """Reschedule a meeting to a better time"""
        # In real implementation, would integrate with calendar APIs
        # For now, return mock result
        
        return {
            'optimization_type': 'meeting_reschedule',
            'original_time': opportunity.original_time.isoformat() if opportunity.original_time else None,
            'suggested_time': opportunity.suggested_time.isoformat() if opportunity.suggested_time else None,
            'status': 'suggested',  # In real app: 'completed', 'pending', 'failed'
            'message': 'Reschedule suggestion sent to meeting organizer',
            'calendar_integration': 'mock_success'
        }
    
    async def _create_focus_block(self, user_id: str, opportunity: ScheduleOptimization) -> Dict[str, Any]:
        """Create a focus block in the calendar"""
        try:
            # In real implementation, would create calendar event
            # For now, create a task placeholder
            
            async with get_db() as db:
                focus_task = Task(
                    user_id=int(user_id),
                    title="🎯 Focus Block",
                    description=f"Dedicated focus time - {opportunity.description}",
                    status="pending",
                    priority="high",
                    estimated_pomodoros=opportunity.duration // 25 if opportunity.duration else 2,
                    due_date=opportunity.suggested_time
                )
                
                db.add(focus_task)
                db.commit()
                db.refresh(focus_task)
                
                return {
                    'optimization_type': 'focus_block_created',
                    'block_details': {
                        'id': focus_task.id,
                        'start_time': opportunity.suggested_time.isoformat() if opportunity.suggested_time else None,
                        'duration_minutes': opportunity.duration,
                        'title': focus_task.title
                    },
                    'status': 'created',
                    'message': 'Focus block created successfully'
                }
                
        except Exception as e:
            logger.error("Failed to create focus block", user_id=user_id, error=str(e))
            return {
                'optimization_type': 'focus_block_created',
                'status': 'failed',
                'error': str(e)
            }
    
    async def _reschedule_task(self, user_id: str, opportunity: ScheduleOptimization) -> Dict[str, Any]:
        """Reschedule a task to optimal time"""
        # Mock implementation - in real app would update task scheduling
        return {
            'optimization_type': 'task_reschedule',
            'original_time': opportunity.original_time.isoformat() if opportunity.original_time else None,
            'suggested_time': opportunity.suggested_time.isoformat() if opportunity.suggested_time else None,
            'status': 'rescheduled',
            'message': 'Task rescheduled to optimal productivity time'
        }
    
    async def _consolidate_meetings(self, user_id: str, opportunity: ScheduleOptimization) -> Dict[str, Any]:
        """Consolidate scattered meetings"""
        # Mock implementation - in real app would suggest meeting time changes
        return {
            'optimization_type': 'meeting_consolidation',
            'status': 'suggested',
            'message': 'Meeting consolidation suggestions sent',
            'consolidation_proposal': 'Group meetings between 2-4 PM to create morning focus block'
        }
    
    def _calculate_optimization_impact(self, optimization_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate the overall impact of optimizations"""
        if not optimization_results:
            return {'total_productivity_gain': 0, 'optimizations_count': 0}
        
        total_gain = sum(result.get('productivity_gain_estimate', 0) for result in optimization_results)
        successful_optimizations = sum(1 for result in optimization_results 
                                     if result.get('status') in ['completed', 'created', 'rescheduled'])
        
        return {
            'total_productivity_gain': total_gain,
            'optimizations_count': len(optimization_results),
            'successful_optimizations': successful_optimizations,
            'average_confidence': np.mean([result.get('confidence', 0) for result in optimization_results]),
            'estimated_focus_time_gained': sum(result.get('block_details', {}).get('duration_minutes', 0) 
                                             for result in optimization_results 
                                             if result.get('optimization_type') == 'focus_block_created')
        }
    
    async def _cache_optimization_results(self, user_id: str, results: Dict[str, Any]):
        """Cache optimization results for user review"""
        if self.redis:
            try:
                await self.redis.setex(
                    f"schedule_optimizations:{user_id}",
                    3600,  # 1 hour TTL
                    json.dumps(results, default=str)
                )
                logger.debug("Optimization results cached", user_id=user_id)
            except Exception as e:
                logger.warning("Failed to cache optimization results", user_id=user_id, error=str(e))
    
    # Public methods for manual optimization
    async def suggest_optimal_meeting_time(self, user_id: str, meeting_duration: int, 
                                          participants: List[str] = None) -> Dict[str, Any]:
        """Suggest optimal time for a new meeting"""
        logger.debug("Suggesting optimal meeting time", 
                    user_id=user_id, 
                    duration=meeting_duration)
        
        try:
            patterns = await self._get_productivity_patterns(user_id)
            
            # Find time slots that don't conflict with peak focus hours
            working_hours = list(range(9, 18))
            suitable_hours = [h for h in working_hours if h not in patterns.peak_hours]
            
            # Prefer times with moderate productivity (good for collaboration)
            optimal_hour = min(suitable_hours,
                             key=lambda h: abs(patterns.hourly_productivity[h]['avg_focus_score'] - 0.6))
            
            suggested_time = datetime.now().replace(hour=optimal_hour, minute=0, second=0, microsecond=0)
            
            return {
                'suggested_time': suggested_time.isoformat(),
                'reasoning': f"Optimal for meetings (avoids peak focus hours: {patterns.peak_hours})",
                'confidence': 0.8,
                'alternative_times': [
                    (suggested_time + timedelta(hours=1)).isoformat(),
                    (suggested_time + timedelta(hours=2)).isoformat()
                ]
            }
            
        except Exception as e:
            logger.error("Failed to suggest meeting time", user_id=user_id, error=str(e))
            return {}
    
    async def get_productivity_calendar(self, user_id: str, date: datetime) -> Dict[str, Any]:
        """Get productivity-optimized calendar view for a specific date"""
        try:
            patterns = await self._get_productivity_patterns(user_id)
            schedule = await self._get_current_schedule(user_id, (date, date + timedelta(days=1)))
            
            hourly_view = {}
            for hour in range(24):
                productivity_data = patterns.hourly_productivity.get(hour, {})
                scheduled_block = next((block for block in schedule 
                                      if block.start_time.hour == hour), None)
                
                hourly_view[hour] = {
                    'productivity_score': productivity_data.get('avg_focus_score', 0.5),
                    'energy_level': 'high' if hour in patterns.peak_hours else 
                                   'low' if hour in patterns.low_energy_hours else 'medium',
                    'scheduled_activity': {
                        'title': scheduled_block.title,
                        'type': scheduled_block.block_type,
                        'optimal': self._is_optimal_scheduling(scheduled_block, patterns)
                    } if scheduled_block else None,
                    'recommendation': self._get_hour_recommendation(hour, patterns)
                }
            
            return {
                'date': date.isoformat(),
                'hourly_view': hourly_view,
                'optimal_focus_blocks': patterns.optimal_focus_blocks,
                'daily_productivity_score': patterns.daily_productivity.get(date.strftime('%A'), 0.5)
            }
            
        except Exception as e:
            logger.error("Failed to get productivity calendar", user_id=user_id, error=str(e))
            return {}
    
    def _is_optimal_scheduling(self, block: ScheduleBlock, patterns: ProductivityPattern) -> bool:
        """Check if a scheduled block is optimally timed"""
        hour = block.start_time.hour
        
        if block.block_type == "task" and block.energy_requirement > 0.7:
            return hour in patterns.peak_hours
        elif block.block_type == "meeting":
            return hour not in patterns.peak_hours
        else:
            return True  # Neutral activities are fine anytime
    
    def _get_hour_recommendation(self, hour: int, patterns: ProductivityPattern) -> str:
        """Get recommendation for what to do at a specific hour"""
        if hour in patterns.peak_hours:
            return "Ideal for deep work and complex tasks"
        elif hour in patterns.low_energy_hours:
            return "Good for meetings, administrative tasks, or breaks"
        else:
            return "Suitable for moderate-intensity work"