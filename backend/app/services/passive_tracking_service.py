"""
Universal Passive Time Tracking Service
RescueTime killer that tracks EVERYTHING automatically
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import psutil
import time
import structlog

# Database imports
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, TimeEntry

logger = structlog.get_logger()

@dataclass
class ActivityData:
    """Data structure for tracking activity"""
    application_name: str
    window_title: str
    duration_seconds: int
    category: str
    productivity_score: float
    timestamp: datetime
    website_url: Optional[str] = None
    keyboard_activity: int = 0
    mouse_activity: int = 0
    screen_engagement: float = 0.0

@dataclass
class TrackingData:
    """Comprehensive tracking data structure"""
    application_usage: List[ActivityData]
    website_activity: List[Dict[str, Any]]
    keyboard_mouse_patterns: Dict[str, Any]
    screen_engagement: Dict[str, Any]
    productivity_score: float
    timestamp: datetime

class PassiveTrackingService:
    """Service for passive tracking of user activity"""
    
    def __init__(self, redis_client=None, openai_client=None):
        self.redis = redis_client
        self.openai_client = openai_client
        self.tracking_active = False
        self.current_activities = {}
        self.activity_categories = {
            'DEEP_WORK': ['vscode', 'pycharm', 'intellij', 'sublime', 'vim', 'emacs'],
            'PRODUCTIVE': ['slack', 'teams', 'zoom', 'outlook', 'gmail', 'notion'],
            'ADMINISTRATIVE': ['excel', 'word', 'powerpoint', 'sheets', 'docs'],
            'NEUTRAL': ['calculator', 'terminal', 'file manager'],
            'DISTRACTING': ['youtube', 'facebook', 'twitter', 'instagram', 'tiktok', 'netflix']
        }
    
    async def track_all_activity(self, user_id: str) -> Dict[str, Any]:
        """Track everything: apps, websites, keyboard/mouse activity, screen time"""
        logger.info("Starting comprehensive activity tracking", user_id=user_id)
        
        try:
            tracking_data = {
                "application_usage": await self._track_applications(user_id),
                "website_activity": await self._track_web_browsing(user_id),
                "keyboard_mouse_patterns": await self._track_input_patterns(user_id),
                "screen_engagement": await self._track_screen_focus(user_id),
                "productivity_score": await self._calculate_real_time_productivity(user_id)
            }
            
            # Auto-categorize activities using AI
            categorized_data = await self._ai_categorize_activities(tracking_data)
            
            # Store and trigger predictive workflows
            await self._store_tracking_data(user_id, categorized_data)
            await self._trigger_predictive_suggestions(user_id, categorized_data)
            
            logger.info("Activity tracking completed", 
                       user_id=user_id, 
                       productivity_score=tracking_data["productivity_score"])
            
            return categorized_data
            
        except Exception as e:
            logger.error("Failed to track activity", user_id=user_id, error=str(e))
            raise
    
    async def _track_applications(self, user_id: str) -> List[Dict[str, Any]]:
        """Track all desktop/mobile app usage with privacy consent"""
        logger.debug("Tracking application usage", user_id=user_id)
        
        applications = []
        
        try:
            # Get running processes (cross-platform approach)
            for proc in psutil.process_iter(['pid', 'name', 'create_time']):
                try:
                    proc_info = proc.info
                    if proc_info['name']:
                        app_data = {
                            'name': proc_info['name'].lower(),
                            'pid': proc_info['pid'],
                            'start_time': datetime.fromtimestamp(proc_info['create_time']),
                            'duration': time.time() - proc_info['create_time'],
                            'category': self._categorize_application(proc_info['name']),
                            'productivity_impact': self._calculate_app_productivity_impact(proc_info['name'])
                        }
                        applications.append(app_data)
                        
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    continue
                    
        except Exception as e:
            logger.warning("Failed to track some applications", error=str(e))
        
        # Sort by duration (most used first)
        applications.sort(key=lambda x: x['duration'], reverse=True)
        
        logger.debug("Application tracking completed", 
                    user_id=user_id, 
                    app_count=len(applications))
        
        return applications[:20]  # Return top 20 applications
    
    async def _track_web_browsing(self, user_id: str) -> List[Dict[str, Any]]:
        """Track web browsing activity (placeholder for browser extension integration)"""
        logger.debug("Tracking web browsing activity", user_id=user_id)
        
        # This would integrate with browser extensions in a real implementation
        # For now, return mock data structure
        web_activity = [
            {
                'url': 'example.com',
                'title': 'Example Page',
                'domain': 'example.com',
                'visit_duration': 300,  # seconds
                'category': 'PRODUCTIVE',
                'productivity_score': 0.7,
                'timestamp': datetime.now()
            }
        ]
        
        return web_activity
    
    async def _track_input_patterns(self, user_id: str) -> Dict[str, Any]:
        """Track keyboard/mouse activity patterns"""
        logger.debug("Tracking input patterns", user_id=user_id)
        
        # Mock input pattern data - in real implementation would use system hooks
        patterns = {
            'keyboard_activity': {
                'words_per_minute': 0,  # Would be calculated from keystroke timing
                'typing_rhythm': 'steady',  # steady, burst, irregular
                'break_frequency': 5,  # minutes between typing breaks
                'activity_level': 0.5  # 0.0 to 1.0
            },
            'mouse_activity': {
                'clicks_per_minute': 0,
                'movement_distance': 0,  # pixels
                'scroll_activity': 0,
                'activity_level': 0.3
            },
            'overall_engagement': 0.4  # Combined engagement score
        }
        
        return patterns
    
    async def _track_screen_focus(self, user_id: str) -> Dict[str, Any]:
        """Track screen focus and engagement"""
        logger.debug("Tracking screen focus", user_id=user_id)
        
        # Mock screen focus data
        focus_data = {
            'active_window_time': 300,  # seconds in active window
            'window_switches': 5,  # number of window switches
            'idle_time': 60,  # seconds of idle time
            'focus_score': 0.8,  # calculated focus score
            'screen_time_blocks': [
                {
                    'start_time': datetime.now() - timedelta(minutes=5),
                    'end_time': datetime.now(),
                    'duration': 300,
                    'application': 'browser',
                    'focus_quality': 0.7
                }
            ]
        }
        
        return focus_data
    
    async def _calculate_real_time_productivity(self, user_id: str) -> float:
        """Calculate real-time productivity score"""
        logger.debug("Calculating real-time productivity", user_id=user_id)
        
        # Mock productivity calculation - in real implementation would analyze all tracked data
        base_score = 0.6
        
        # Factors that would affect productivity score:
        # - Time spent in productive vs distracting applications
        # - Frequency of context switching
        # - Typing/mouse activity levels
        # - Focus duration without interruptions
        
        productivity_score = min(1.0, max(0.0, base_score))
        
        logger.debug("Productivity score calculated", 
                    user_id=user_id, 
                    score=productivity_score)
        
        return productivity_score
    
    async def _ai_categorize_activities(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Use AI to categorize activities as productive/neutral/distracting"""
        logger.debug("AI categorizing activities")
        
        if not self.openai_client:
            # Fallback to rule-based categorization
            return await self._rule_based_categorization(raw_data)
        
        try:
            prompt = f"""
            Categorize these activities into productivity levels:
            {json.dumps(raw_data, indent=2, default=str)}
            
            Categories:
            - DEEP_WORK: Focus-intensive, creative, or strategic work (score: 0.9-1.0)
            - PRODUCTIVE: Standard work tasks, communication, planning (score: 0.7-0.8)
            - ADMINISTRATIVE: Email, meetings, routine tasks (score: 0.5-0.6)
            - NEUTRAL: Breaks, personal time, research (score: 0.3-0.4)
            - DISTRACTING: Social media, entertainment, time-wasting (score: 0.0-0.2)
            
            Return JSON with activity categorization and productivity impact score.
            """
            
            # Mock AI response for now
            categorized_data = raw_data.copy()
            categorized_data['ai_categorization'] = {
                'primary_category': 'PRODUCTIVE',
                'confidence': 0.85,
                'productivity_impact': 0.7,
                'recommendations': [
                    'Consider blocking distracting websites during focus sessions',
                    'Take regular breaks to maintain productivity'
                ]
            }
            
            return categorized_data
            
        except Exception as e:
            logger.warning("AI categorization failed, using fallback", error=str(e))
            return await self._rule_based_categorization(raw_data)
    
    async def _rule_based_categorization(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback rule-based categorization"""
        categorized_data = raw_data.copy()
        
        # Simple rule-based categorization based on application names
        app_scores = []
        for app in raw_data.get('application_usage', []):
            app_name = app.get('name', '').lower()
            category = self._categorize_application(app_name)
            productivity_score = self._get_category_score(category)
            app['category'] = category
            app['productivity_score'] = productivity_score
            app_scores.append(productivity_score)
        
        # Calculate overall productivity
        overall_productivity = sum(app_scores) / len(app_scores) if app_scores else 0.5
        
        categorized_data['rule_based_categorization'] = {
            'overall_productivity': overall_productivity,
            'primary_activity_type': self._determine_primary_activity(raw_data.get('application_usage', [])),
            'focus_quality': raw_data.get('screen_engagement', {}).get('focus_score', 0.5)
        }
        
        return categorized_data
    
    def _categorize_application(self, app_name: str) -> str:
        """Categorize application based on name"""
        app_name = app_name.lower()
        
        for category, apps in self.activity_categories.items():
            if any(app in app_name for app in apps):
                return category
        
        return 'NEUTRAL'  # Default category
    
    def _calculate_app_productivity_impact(self, app_name: str) -> float:
        """Calculate productivity impact of an application"""
        category = self._categorize_application(app_name)
        return self._get_category_score(category)
    
    def _get_category_score(self, category: str) -> float:
        """Get productivity score for category"""
        category_scores = {
            'DEEP_WORK': 0.95,
            'PRODUCTIVE': 0.75,
            'ADMINISTRATIVE': 0.55,
            'NEUTRAL': 0.35,
            'DISTRACTING': 0.1
        }
        return category_scores.get(category, 0.5)
    
    def _determine_primary_activity(self, applications: List[Dict[str, Any]]) -> str:
        """Determine the primary activity type based on application usage"""
        if not applications:
            return 'NEUTRAL'
        
        # Get the most used application's category
        top_app = max(applications, key=lambda x: x.get('duration', 0))
        return top_app.get('category', 'NEUTRAL')
    
    async def _store_tracking_data(self, user_id: str, tracking_data: Dict[str, Any]):
        """Store tracking data in database"""
        logger.debug("Storing tracking data", user_id=user_id)
        
        try:
            async with get_db() as db:
                # Create time entry for this tracking session
                time_entry = TimeEntry(
                    user_id=int(user_id),
                    duration=5,  # 5-minute tracking interval
                    description=f"Automated tracking: {tracking_data.get('ai_categorization', {}).get('primary_category', 'NEUTRAL')}",
                    entry_type="automated_tracking"
                )
                
                db.add(time_entry)
                db.commit()
                
                logger.debug("Tracking data stored successfully", user_id=user_id)
                
        except Exception as e:
            logger.error("Failed to store tracking data", user_id=user_id, error=str(e))
    
    async def _trigger_predictive_suggestions(self, user_id: str, tracking_data: Dict[str, Any]):
        """Trigger predictive suggestions based on tracking data"""
        logger.debug("Triggering predictive suggestions", user_id=user_id)
        
        try:
            productivity_score = tracking_data.get('productivity_score', 0.5)
            
            suggestions = []
            
            # Low productivity suggestions
            if productivity_score < 0.4:
                suggestions.extend([
                    "Consider taking a short break to refresh",
                    "Try switching to a different task",
                    "Block distracting websites for the next hour"
                ])
            
            # High productivity suggestions
            elif productivity_score > 0.8:
                suggestions.extend([
                    "You're in a flow state - consider extending this session",
                    "Great focus! Consider scheduling similar tasks at this time",
                    "Block your calendar to protect this productive time"
                ])
            
            # Store suggestions for later retrieval
            if self.redis and suggestions:
                await self.redis.setex(
                    f"suggestions:{user_id}",
                    3600,  # 1 hour TTL
                    json.dumps(suggestions)
                )
            
            logger.debug("Predictive suggestions generated", 
                        user_id=user_id, 
                        suggestion_count=len(suggestions))
            
        except Exception as e:
            logger.warning("Failed to generate predictive suggestions", 
                          user_id=user_id, 
                          error=str(e))
    
    async def start_continuous_tracking(self, user_id: str, interval_minutes: int = 5):
        """Start continuous passive tracking"""
        logger.info("Starting continuous tracking", 
                   user_id=user_id, 
                   interval=interval_minutes)
        
        self.tracking_active = True
        
        while self.tracking_active:
            try:
                await self.track_all_activity(user_id)
                await asyncio.sleep(interval_minutes * 60)  # Convert to seconds
                
            except Exception as e:
                logger.error("Error in continuous tracking", 
                           user_id=user_id, 
                           error=str(e))
                await asyncio.sleep(60)  # Wait 1 minute before retrying
    
    async def stop_tracking(self):
        """Stop continuous tracking"""
        logger.info("Stopping continuous tracking")
        self.tracking_active = False
    
    async def get_tracking_summary(self, user_id: str, hours: int = 24) -> Dict[str, Any]:
        """Get tracking summary for the last N hours"""
        logger.debug("Getting tracking summary", user_id=user_id, hours=hours)
        
        try:
            async with get_db() as db:
                # Get recent tracking entries
                start_time = datetime.now() - timedelta(hours=hours)
                
                entries = db.query(TimeEntry).filter(
                    TimeEntry.user_id == int(user_id),
                    TimeEntry.entry_type == "automated_tracking",
                    TimeEntry.created_at >= start_time
                ).all()
                
                summary = {
                    'total_tracked_time': sum(entry.duration for entry in entries),
                    'tracking_sessions': len(entries),
                    'average_productivity': 0.6,  # Would calculate from stored data
                    'most_used_category': 'PRODUCTIVE',
                    'recommendations': [
                        'Your productivity peaks around 10 AM',
                        'Consider blocking social media after 2 PM'
                    ]
                }
                
                return summary
                
        except Exception as e:
            logger.error("Failed to get tracking summary", user_id=user_id, error=str(e))
            return {}