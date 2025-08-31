"""
Virtual Body Doubling / Coworking Service
Creates virtual focus rooms for collaborative work sessions
"""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import structlog
from enum import Enum

# Database imports  
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User

logger = structlog.get_logger()

class RoomType(Enum):
    SILENT_COWORKING = "silent_coworking"
    DISCUSSION = "discussion"
    POMODORO = "pomodoro"
    STUDY_GROUP = "study_group"
    ACCOUNTABILITY = "accountability"

class ParticipantStatus(Enum):
    ACTIVE = "active"
    BREAK = "break"
    AWAY = "away"
    FOCUSED = "focused"

class AccountabilityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class FocusRoom:
    """Virtual focus room configuration"""
    id: str
    name: str
    creator_id: str
    room_type: RoomType
    max_participants: int
    session_duration: int  # minutes
    privacy: str  # public, team, private
    ambient_sounds: str
    focus_timer: bool
    accountability_level: AccountabilityLevel
    created_at: datetime
    is_active: bool = True
    current_participants: int = 0
    session_goals: List[str] = None
    
    def __post_init__(self):
        if self.session_goals is None:
            self.session_goals = []

@dataclass
class Participant:
    """Focus room participant"""
    user_id: str
    room_id: str
    joined_at: datetime
    session_goals: List[str]
    status: ParticipantStatus
    focus_streaks: int = 0
    break_count: int = 0
    accountability_partner_id: Optional[str] = None
    
@dataclass
class AccountabilityPartnership:
    """Accountability partnership between users"""
    id: str
    user1_id: str
    user2_id: str
    room_id: str
    compatibility_score: float
    created_at: datetime
    shared_goals: List[str] = None
    check_in_frequency: int = 30  # minutes
    
    def __post_init__(self):
        if self.shared_goals is None:
            self.shared_goals = []

@dataclass
class SessionInsight:
    """Insights from focus session"""
    session_id: str
    participant_id: str
    focus_score: float
    goals_achieved: int
    total_goals: int
    session_duration: int
    break_efficiency: float
    collaboration_score: float
    insights: List[str] = None
    
    def __post_init__(self):
        if self.insights is None:
            self.insights = []

class VirtualCoworkingService:
    """Service for virtual coworking and body doubling"""
    
    def __init__(self, redis_client=None, websocket_manager=None):
        self.redis = redis_client
        self.websocket_manager = websocket_manager
        self.active_rooms = {}
        self.room_participants = {}
        self.accountability_partnerships = {}
        self.session_data = {}
    
    async def create_focus_room(self, creator_id: str, room_config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a virtual focus room for collaborative work sessions"""
        logger.info("Creating focus room", creator_id=creator_id, config=room_config)
        
        try:
            room_id = str(uuid.uuid4())
            
            # Create room configuration
            room = FocusRoom(
                id=room_id,
                name=room_config.get('name', f"{creator_id}'s Focus Room"),
                creator_id=creator_id,
                room_type=RoomType(room_config.get('type', 'silent_coworking')),
                max_participants=room_config.get('max_participants', 8),
                session_duration=room_config.get('duration', 120),  # minutes
                privacy=room_config.get('privacy', 'team'),
                ambient_sounds=room_config.get('ambient_sounds', 'forest'),
                focus_timer=room_config.get('focus_timer', True),
                accountability_level=AccountabilityLevel(room_config.get('accountability', 'medium')),
                created_at=datetime.now(),
                session_goals=room_config.get('session_goals', [])
            )
            
            # Store room data
            self.active_rooms[room_id] = room
            self.room_participants[room_id] = []
            
            # Cache in Redis if available
            if self.redis:
                await self.redis.setex(
                    f"focus_room:{room_id}",
                    room.session_duration * 60 + 3600,  # Session duration + 1 hour buffer
                    json.dumps(asdict(room), default=str)
                )
            
            # Set up WebSocket room for real-time interaction
            if self.websocket_manager:
                await self.websocket_manager.create_room(room_id)
            
            # Schedule room cleanup
            await self._schedule_room_cleanup(room_id, room.session_duration)
            
            logger.info("Focus room created successfully", 
                       room_id=room_id,
                       creator_id=creator_id,
                       room_type=room.room_type.value)
            
            return {
                'room_id': room_id,
                'room': asdict(room),
                'join_url': f"/focus-room/{room_id}",
                'estimated_end_time': (datetime.now() + timedelta(minutes=room.session_duration)).isoformat()
            }
            
        except Exception as e:
            logger.error("Failed to create focus room", creator_id=creator_id, error=str(e))
            raise
    
    async def join_focus_session(self, user_id: str, room_id: str, session_goals: List[str]) -> Dict[str, Any]:
        """Join a virtual coworking session"""
        logger.info("User joining focus session", user_id=user_id, room_id=room_id)
        
        try:
            # Get room data
            room = await self._get_room(room_id)
            if not room:
                raise ValueError("Focus room not found")
            
            # Check room capacity
            current_participants = await self._get_active_participants(room_id)
            if len(current_participants) >= room.max_participants:
                raise ValueError("Room is full")
            
            # Create participation record
            participant = Participant(
                user_id=user_id,
                room_id=room_id,
                joined_at=datetime.now(),
                session_goals=session_goals,
                status=ParticipantStatus.ACTIVE
            )
            
            # Add to room participants
            if room_id not in self.room_participants:
                self.room_participants[room_id] = []
            self.room_participants[room_id].append(participant)
            
            # Update room participant count
            room.current_participants = len(self.room_participants[room_id])
            
            # Assign accountability partner
            accountability_partner = await self._assign_accountability_partner(user_id, room_id)
            if accountability_partner:
                participant.accountability_partner_id = accountability_partner['partner_id']
            
            # Notify other participants via WebSocket
            if self.websocket_manager:
                await self.websocket_manager.broadcast_to_room(room_id, {
                    'type': 'participant_joined',
                    'user_id': user_id,
                    'goals': session_goals,
                    'participant_count': room.current_participants,
                    'accountability_partner': accountability_partner
                })
            
            # Start session tracking
            session_id = await self._start_session_tracking(user_id, room_id, session_goals)
            
            logger.info("User joined focus session successfully", 
                       user_id=user_id,
                       room_id=room_id,
                       participant_count=room.current_participants)
            
            return {
                'session_id': session_id,
                'room': asdict(room),
                'participants': current_participants + [user_id],
                'session_started': True,
                'accountability_partner': accountability_partner,
                'ambient_sounds_url': f"/sounds/{room.ambient_sounds}",
                'focus_timer_enabled': room.focus_timer
            }
            
        except Exception as e:
            logger.error("Failed to join focus session", user_id=user_id, room_id=room_id, error=str(e))
            raise
    
    async def leave_focus_session(self, user_id: str, room_id: str) -> Dict[str, Any]:
        """Leave a focus session"""
        logger.info("User leaving focus session", user_id=user_id, room_id=room_id)
        
        try:
            # Remove participant
            if room_id in self.room_participants:
                self.room_participants[room_id] = [
                    p for p in self.room_participants[room_id] if p.user_id != user_id
                ]
            
            # Update room participant count
            room = await self._get_room(room_id)
            if room:
                room.current_participants = len(self.room_participants.get(room_id, []))
            
            # End session tracking
            session_insights = await self._end_session_tracking(user_id, room_id)
            
            # Notify other participants
            if self.websocket_manager:
                await self.websocket_manager.broadcast_to_room(room_id, {
                    'type': 'participant_left',
                    'user_id': user_id,
                    'participant_count': room.current_participants if room else 0
                })
            
            # Clean up accountability partnership
            await self._cleanup_accountability_partnership(user_id, room_id)
            
            logger.info("User left focus session", 
                       user_id=user_id,
                       room_id=room_id,
                       session_insights=session_insights is not None)
            
            return {
                'left_successfully': True,
                'session_insights': session_insights,
                'remaining_participants': room.current_participants if room else 0
            }
            
        except Exception as e:
            logger.error("Failed to leave focus session", user_id=user_id, room_id=room_id, error=str(e))
            raise
    
    async def update_participant_status(self, user_id: str, room_id: str, status: str) -> Dict[str, Any]:
        """Update participant status (active, break, away, focused)"""
        
        try:
            participant_status = ParticipantStatus(status)
            
            # Update participant status
            if room_id in self.room_participants:
                for participant in self.room_participants[room_id]:
                    if participant.user_id == user_id:
                        old_status = participant.status
                        participant.status = participant_status
                        
                        # Update counters
                        if participant_status == ParticipantStatus.BREAK:
                            participant.break_count += 1
                        elif participant_status == ParticipantStatus.FOCUSED:
                            participant.focus_streaks += 1
                        
                        # Notify accountability partner
                        if participant.accountability_partner_id:
                            await self._notify_accountability_partner(
                                participant.accountability_partner_id,
                                user_id,
                                old_status,
                                participant_status
                            )
                        
                        break
            
            # Broadcast status update
            if self.websocket_manager:
                await self.websocket_manager.broadcast_to_room(room_id, {
                    'type': 'status_update',
                    'user_id': user_id,
                    'status': status,
                    'timestamp': datetime.now().isoformat()
                })
            
            return {
                'status_updated': True,
                'new_status': status
            }
            
        except Exception as e:
            logger.error("Failed to update participant status", 
                        user_id=user_id, 
                        room_id=room_id, 
                        error=str(e))
            raise
    
    async def _assign_accountability_partner(self, user_id: str, room_id: str) -> Optional[Dict[str, Any]]:
        """Intelligently pair users for mutual accountability"""
        logger.debug("Assigning accountability partner", user_id=user_id, room_id=room_id)
        
        try:
            # Get current participants
            room_participants = self.room_participants.get(room_id, [])
            
            # Get user profile for compatibility matching
            user_profile = await self._get_user_profile(user_id)
            
            best_partner = None
            best_compatibility_score = 0
            
            # Find best accountability partner
            for participant in room_participants:
                if (participant.user_id == user_id or 
                    participant.accountability_partner_id is not None):
                    continue
                
                partner_profile = await self._get_user_profile(participant.user_id)
                compatibility = await self._calculate_compatibility(user_profile, partner_profile)
                
                if compatibility > best_compatibility_score:
                    best_compatibility_score = compatibility
                    best_partner = participant
            
            if best_partner and best_compatibility_score > 0.6:
                # Create accountability partnership
                partnership = await self._create_accountability_partnership(
                    user_id, best_partner.user_id, room_id, best_compatibility_score
                )
                
                # Update both participants
                best_partner.accountability_partner_id = user_id
                
                logger.info("Accountability partnership created", 
                           user1=user_id,
                           user2=best_partner.user_id,
                           compatibility=best_compatibility_score)
                
                return {
                    'partner_id': best_partner.user_id,
                    'partnership_id': partnership['id'],
                    'compatibility_score': best_compatibility_score,
                    'shared_goals': partnership['shared_goals']
                }
            
            return None
            
        except Exception as e:
            logger.error("Failed to assign accountability partner", user_id=user_id, error=str(e))
            return None
    
    async def _calculate_compatibility(self, user1_profile: Dict[str, Any], user2_profile: Dict[str, Any]) -> float:
        """Calculate compatibility score between two users"""
        
        compatibility_score = 0.0
        
        # Work style compatibility
        if user1_profile.get('work_style') == user2_profile.get('work_style'):
            compatibility_score += 0.3
        
        # Productivity goals similarity
        user1_goals = set(user1_profile.get('productivity_goals', []))
        user2_goals = set(user2_profile.get('productivity_goals', []))
        goal_overlap = len(user1_goals.intersection(user2_goals)) / max(len(user1_goals), len(user2_goals), 1)
        compatibility_score += goal_overlap * 0.4
        
        # Time zone compatibility
        if abs(user1_profile.get('timezone_offset', 0) - user2_profile.get('timezone_offset', 0)) <= 2:
            compatibility_score += 0.2
        
        # Communication preference
        if user1_profile.get('communication_style') == user2_profile.get('communication_style'):
            compatibility_score += 0.1
        
        return min(1.0, compatibility_score)
    
    async def _create_accountability_partnership(self, user1_id: str, user2_id: str, room_id: str, compatibility_score: float) -> Dict[str, Any]:
        """Create accountability partnership between two users"""
        
        partnership_id = str(uuid.uuid4())
        
        # Get shared goals
        user1_profile = await self._get_user_profile(user1_id)
        user2_profile = await self._get_user_profile(user2_id)
        
        shared_goals = list(set(user1_profile.get('current_goals', [])).intersection(
            set(user2_profile.get('current_goals', []))
        ))
        
        partnership = AccountabilityPartnership(
            id=partnership_id,
            user1_id=user1_id,
            user2_id=user2_id,
            room_id=room_id,
            compatibility_score=compatibility_score,
            created_at=datetime.now(),
            shared_goals=shared_goals
        )
        
        # Store partnership
        self.accountability_partnerships[partnership_id] = partnership
        
        # Cache in Redis
        if self.redis:
            await self.redis.setex(
                f"accountability_partnership:{partnership_id}",
                3600,  # 1 hour TTL
                json.dumps(asdict(partnership), default=str)
            )
        
        return {
            'id': partnership_id,
            'compatibility_score': compatibility_score,
            'shared_goals': shared_goals,
            'check_in_frequency': partnership.check_in_frequency
        }
    
    async def _notify_accountability_partner(self, partner_id: str, user_id: str, old_status: ParticipantStatus, new_status: ParticipantStatus):
        """Notify accountability partner of status changes"""
        
        try:
            # Create status notification
            notification = {
                'type': 'partner_status_update',
                'partner_id': user_id,
                'old_status': old_status.value,
                'new_status': new_status.value,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send via WebSocket if available
            if self.websocket_manager:
                await self.websocket_manager.send_to_user(partner_id, notification)
            
            # Provide encouragement based on status change
            if new_status == ParticipantStatus.FOCUSED:
                encouragement = f"Your accountability partner is in deep focus mode! 🎯"
            elif new_status == ParticipantStatus.BREAK:
                encouragement = f"Your accountability partner is taking a well-deserved break 😌"
            elif new_status == ParticipantStatus.AWAY:
                encouragement = f"Your accountability partner stepped away - stay motivated! 💪"
            else:
                encouragement = f"Your accountability partner updated their status"
            
            notification['encouragement'] = encouragement
            
            logger.debug("Accountability partner notified", 
                        partner_id=partner_id,
                        user_id=user_id,
                        new_status=new_status.value)
            
        except Exception as e:
            logger.warning("Failed to notify accountability partner", 
                          partner_id=partner_id, 
                          error=str(e))
    
    async def _start_session_tracking(self, user_id: str, room_id: str, goals: List[str]) -> str:
        """Start tracking a focus session"""
        
        session_id = f"session_{user_id}_{int(datetime.now().timestamp())}"
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'room_id': room_id,
            'goals': goals,
            'start_time': datetime.now().isoformat(),
            'status_changes': [],
            'focus_events': [],
            'goal_progress': {goal: 0.0 for goal in goals}
        }
        
        self.session_data[session_id] = session_data
        
        logger.debug("Session tracking started", 
                    session_id=session_id,
                    user_id=user_id,
                    goals_count=len(goals))
        
        return session_id
    
    async def _end_session_tracking(self, user_id: str, room_id: str) -> Optional[SessionInsight]:
        """End session tracking and generate insights"""
        
        try:
            # Find active session
            session = None
            session_id = None
            
            for sid, data in self.session_data.items():
                if data['user_id'] == user_id and data['room_id'] == room_id:
                    session = data
                    session_id = sid
                    break
            
            if not session:
                return None
            
            # Calculate session metrics
            start_time = datetime.fromisoformat(session['start_time'])
            session_duration = (datetime.now() - start_time).total_seconds() / 60  # minutes
            
            # Calculate focus score based on status changes
            focus_periods = []
            current_status_start = start_time
            
            for status_change in session['status_changes']:
                if status_change['status'] == 'focused':
                    focus_periods.append({
                        'start': current_status_start,
                        'end': datetime.fromisoformat(status_change['timestamp'])
                    })
                current_status_start = datetime.fromisoformat(status_change['timestamp'])
            
            total_focus_time = sum(
                (period['end'] - period['start']).total_seconds() / 60
                for period in focus_periods
            )
            
            focus_score = min(1.0, total_focus_time / max(session_duration, 1))
            
            # Analyze goal completion (mock calculation)
            goals_achieved = len([g for g in session['goals'] if session['goal_progress'][g] > 0.8])
            
            # Generate insights
            insights = []
            if focus_score > 0.8:
                insights.append("Excellent focus session! You maintained high concentration.")
            if goals_achieved == len(session['goals']):
                insights.append("Outstanding! You achieved all your session goals.")
            if session_duration > 90:
                insights.append("Long session detected - remember to take regular breaks.")
            
            session_insight = SessionInsight(
                session_id=session_id,
                participant_id=user_id,
                focus_score=focus_score,
                goals_achieved=goals_achieved,
                total_goals=len(session['goals']),
                session_duration=int(session_duration),
                break_efficiency=0.8,  # Mock calculation
                collaboration_score=0.7,  # Mock calculation
                insights=insights
            )
            
            # Clean up session data
            del self.session_data[session_id]
            
            logger.info("Session tracking ended", 
                       session_id=session_id,
                       user_id=user_id,
                       focus_score=focus_score,
                       goals_achieved=goals_achieved)
            
            return session_insight
            
        except Exception as e:
            logger.error("Failed to end session tracking", user_id=user_id, error=str(e))
            return None
    
    async def _get_room(self, room_id: str) -> Optional[FocusRoom]:
        """Get room data"""
        
        # Try memory first
        if room_id in self.active_rooms:
            return self.active_rooms[room_id]
        
        # Try Redis cache
        if self.redis:
            try:
                cached_room = await self.redis.get(f"focus_room:{room_id}")
                if cached_room:
                    room_data = json.loads(cached_room)
                    room = FocusRoom(**room_data)
                    self.active_rooms[room_id] = room
                    return room
            except Exception as e:
                logger.warning("Failed to get room from cache", room_id=room_id, error=str(e))
        
        return None
    
    async def _get_active_participants(self, room_id: str) -> List[str]:
        """Get list of active participants in room"""
        if room_id in self.room_participants:
            return [p.user_id for p in self.room_participants[room_id]]
        return []
    
    async def _get_user_profile(self, user_id: str) -> Dict[str, Any]:
        """Get user profile for compatibility matching"""
        
        try:
            async with get_db() as db:
                user = db.query(User).filter(User.id == user_id).first()
                if not user:
                    return {}
                
                # Mock profile data - in real implementation would be stored in user profile
                profile = {
                    'user_id': user_id,
                    'username': user.username,
                    'work_style': 'focused',  # focused, collaborative, flexible
                    'productivity_goals': ['deep_work', 'learning', 'project_completion'],
                    'timezone_offset': 0,  # UTC offset
                    'communication_style': 'minimal',  # minimal, moderate, frequent
                    'current_goals': ['finish_project', 'learn_new_skill'],
                    'focus_preferences': {
                        'ambient_sounds': 'nature',
                        'session_length': 90,
                        'break_frequency': 25
                    }
                }
                
                return profile
                
        except Exception as e:
            logger.error("Failed to get user profile", user_id=user_id, error=str(e))
            return {}
    
    async def _schedule_room_cleanup(self, room_id: str, duration_minutes: int):
        """Schedule room cleanup after session ends"""
        
        # In real implementation would use background task scheduler
        cleanup_time = datetime.now() + timedelta(minutes=duration_minutes + 30)  # 30 min grace period
        
        cleanup_task = {
            'room_id': room_id,
            'cleanup_time': cleanup_time.isoformat(),
            'action': 'cleanup_room'
        }
        
        if self.redis:
            await self.redis.setex(
                f"room_cleanup:{room_id}",
                (duration_minutes + 30) * 60,  # TTL in seconds
                json.dumps(cleanup_task)
            )
        
        logger.debug("Room cleanup scheduled", 
                    room_id=room_id,
                    cleanup_time=cleanup_time.isoformat())
    
    async def _cleanup_accountability_partnership(self, user_id: str, room_id: str):
        """Clean up accountability partnership when user leaves"""
        
        # Find and remove partnership
        partnership_to_remove = None
        for partnership_id, partnership in self.accountability_partnerships.items():
            if (partnership.room_id == room_id and 
                (partnership.user1_id == user_id or partnership.user2_id == user_id)):
                partnership_to_remove = partnership_id
                break
        
        if partnership_to_remove:
            del self.accountability_partnerships[partnership_to_remove]
            
            # Remove from Redis
            if self.redis:
                await self.redis.delete(f"accountability_partnership:{partnership_to_remove}")
            
            logger.debug("Accountability partnership cleaned up", 
                        partnership_id=partnership_to_remove)
    
    # Public utility methods
    async def get_available_rooms(self, user_id: str, room_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get list of available focus rooms"""
        
        try:
            available_rooms = []
            
            for room_id, room in self.active_rooms.items():
                # Check if room has space
                if room.current_participants < room.max_participants:
                    # Check room type filter
                    if room_type and room.room_type.value != room_type:
                        continue
                    
                    # Check privacy settings
                    if room.privacy == 'private' and room.creator_id != user_id:
                        continue
                    
                    room_data = asdict(room)
                    room_data['participants'] = await self._get_active_participants(room_id)
                    available_rooms.append(room_data)
            
            # Sort by participant count (more active rooms first)
            available_rooms.sort(key=lambda x: x['current_participants'], reverse=True)
            
            return available_rooms
            
        except Exception as e:
            logger.error("Failed to get available rooms", user_id=user_id, error=str(e))
            return []
    
    async def get_room_activity(self, room_id: str) -> Dict[str, Any]:
        """Get real-time room activity"""
        
        try:
            room = await self._get_room(room_id)
            if not room:
                return {}
            
            participants = self.room_participants.get(room_id, [])
            
            activity = {
                'room_id': room_id,
                'room_name': room.name,
                'participant_count': len(participants),
                'room_type': room.room_type.value,
                'session_duration_remaining': 0,  # Would calculate remaining time
                'participants': [
                    {
                        'user_id': p.user_id,
                        'status': p.status.value,
                        'goals': p.session_goals,
                        'focus_streaks': p.focus_streaks,
                        'break_count': p.break_count,
                        'has_accountability_partner': p.accountability_partner_id is not None
                    }
                    for p in participants
                ],
                'ambient_sounds': room.ambient_sounds,
                'focus_timer_active': room.focus_timer
            }
            
            return activity
            
        except Exception as e:
            logger.error("Failed to get room activity", room_id=room_id, error=str(e))
            return {}
    
    async def send_encouragement(self, sender_id: str, recipient_id: str, room_id: str, message: str) -> bool:
        """Send encouragement message between accountability partners"""
        
        try:
            # Verify partnership exists
            partnership_exists = False
            for partnership in self.accountability_partnerships.values():
                if (partnership.room_id == room_id and
                    ((partnership.user1_id == sender_id and partnership.user2_id == recipient_id) or
                     (partnership.user1_id == recipient_id and partnership.user2_id == sender_id))):
                    partnership_exists = True
                    break
            
            if not partnership_exists:
                return False
            
            # Send message via WebSocket
            if self.websocket_manager:
                await self.websocket_manager.send_to_user(recipient_id, {
                    'type': 'encouragement_message',
                    'sender_id': sender_id,
                    'message': message,
                    'timestamp': datetime.now().isoformat()
                })
            
            logger.info("Encouragement message sent", 
                       sender=sender_id,
                       recipient=recipient_id,
                       room_id=room_id)
            
            return True
            
        except Exception as e:
            logger.error("Failed to send encouragement", 
                        sender=sender_id, 
                        recipient=recipient_id, 
                        error=str(e))
            return False
    
    async def get_session_analytics(self, user_id: str, days: int = 7) -> Dict[str, Any]:
        """Get user's coworking session analytics"""
        
        try:
            # Mock analytics - in real implementation would query historical data
            analytics = {
                'total_sessions': 12,
                'total_focus_time': 480,  # minutes
                'average_session_duration': 90,
                'goals_completion_rate': 0.75,
                'favorite_room_types': ['silent_coworking', 'pomodoro'],
                'accountability_partnerships': 3,
                'focus_score_trend': 0.05,  # 5% improvement
                'collaboration_score': 0.68,
                'peak_productivity_hours': [9, 10, 14, 15],
                'session_insights': [
                    "Your focus improves significantly in accountability partnerships",
                    "Silent coworking sessions yield your highest productivity scores",
                    "You're most effective in 90-minute sessions with 15-minute breaks"
                ]
            }
            
            return analytics
            
        except Exception as e:
            logger.error("Failed to get session analytics", user_id=user_id, error=str(e))
            return {}
    
    async def cleanup_inactive_rooms(self):
        """Clean up inactive or expired rooms"""
        
        try:
            current_time = datetime.now()
            rooms_to_cleanup = []
            
            for room_id, room in self.active_rooms.items():
                # Check if room has expired
                room_end_time = room.created_at + timedelta(minutes=room.session_duration + 30)
                if current_time > room_end_time:
                    rooms_to_cleanup.append(room_id)
                
                # Check if room is empty for too long
                elif (room.current_participants == 0 and 
                      current_time > room.created_at + timedelta(minutes=30)):
                    rooms_to_cleanup.append(room_id)
            
            # Clean up identified rooms
            for room_id in rooms_to_cleanup:
                await self._cleanup_room(room_id)
            
            logger.info("Room cleanup completed", rooms_cleaned=len(rooms_to_cleanup))
            
        except Exception as e:
            logger.error("Failed to cleanup inactive rooms", error=str(e))
    
    async def _cleanup_room(self, room_id: str):
        """Clean up a specific room"""
        
        try:
            # Remove from active rooms
            if room_id in self.active_rooms:
                del self.active_rooms[room_id]
            
            # Remove participants
            if room_id in self.room_participants:
                del self.room_participants[room_id]
            
            # Clean up partnerships
            partnerships_to_remove = [
                pid for pid, p in self.accountability_partnerships.items()
                if p.room_id == room_id
            ]
            
            for partnership_id in partnerships_to_remove:
                del self.accountability_partnerships[partnership_id]
            
            # Remove from Redis
            if self.redis:
                await self.redis.delete(f"focus_room:{room_id}")
            
            # Close WebSocket room
            if self.websocket_manager:
                await self.websocket_manager.close_room(room_id)
            
            logger.info("Room cleaned up successfully", room_id=room_id)
            
        except Exception as e:
            logger.error("Failed to cleanup room", room_id=room_id, error=str(e))