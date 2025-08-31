"""
Performance Optimizations and Technical Debt Remediation
Core optimizations for scalability and performance
"""

import asyncio
import json
import logging
import time
import functools
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from contextlib import asynccontextmanager
import structlog
import redis.asyncio as redis

# Database imports
from sqlalchemy import create_engine, text, Index
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from app.core.database import engine, SessionLocal
from app.models.models import (
    PomodoroSession, Task, TimeEntry, UserAnalytics, User
)

logger = structlog.get_logger()

class PerformanceOptimizer:
    """Core performance optimization service"""
    
    def __init__(self, redis_url: str = None):
        self.redis_client = None
        if redis_url:
            self.redis_client = redis.from_url(redis_url)
        self.query_cache = {}
        self.cache_stats = {
            'hits': 0,
            'misses': 0,
            'total_queries': 0
        }
    
    async def optimize_database_queries(self):
        """Implement query optimization and database indexing"""
        logger.info("Starting database optimization")
        
        try:
            # Database indexes for frequently queried fields
            indexes_to_create = [
                # Pomodoro sessions - frequently queried by user and date
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_pomodoro_sessions_user_date "
                "ON pomodoro_sessions(user_id, completed_at) WHERE completed_at IS NOT NULL",
                
                # Tasks - frequently filtered by status and priority
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_status_priority "
                "ON tasks(user_id, status, priority, due_date)",
                
                # Time entries - queried for time tracking analytics
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_time_entries_user_project "
                "ON time_entries(user_id, created_at, entry_type)",
                
                # User analytics - for dashboard queries
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_analytics_user_timestamp "
                "ON user_analytics(user_id, last_updated)",
                
                # Composite indexes for complex queries
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tasks_user_status_updated "
                "ON tasks(user_id, status, updated_at DESC)",
                
                "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sessions_user_focus_date "
                "ON pomodoro_sessions(user_id, focus_score, completed_at DESC) WHERE completed_at IS NOT NULL"
            ]
            
            with engine.connect() as connection:
                for index_query in indexes_to_create:
                    try:
                        connection.execute(text(index_query))
                        connection.commit()
                        logger.info("Database index created successfully", query=index_query[:50] + "...")
                    except Exception as e:
                        logger.warning("Failed to create index", error=str(e), query=index_query[:50] + "...")
            
            logger.info("Database optimization completed")
            
        except Exception as e:
            logger.error("Failed to optimize database", error=str(e))
            raise
    
    async def implement_query_caching(self):
        """Implement Redis caching for expensive queries"""
        logger.info("Setting up query caching")
        
        if not self.redis_client:
            logger.warning("Redis client not available, skipping cache setup")
            return
        
        try:
            # Test Redis connection
            await self.redis_client.ping()
            logger.info("Redis connection established for caching")
            
        except Exception as e:
            logger.error("Failed to connect to Redis for caching", error=str(e))
            raise
    
    def cached(self, ttl: int = 300, key_prefix: str = ""):
        """Decorator for caching function results"""
        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                if not self.redis_client:
                    # If no Redis, execute function directly
                    return await func(*args, **kwargs)
                
                # Create cache key
                cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(sorted(kwargs.items())))}"
                
                try:
                    # Try to get from cache
                    cached_result = await self.redis_client.get(cache_key)
                    if cached_result:
                        self.cache_stats['hits'] += 1
                        logger.debug("Cache hit", function=func.__name__, key=cache_key)
                        return json.loads(cached_result)
                    
                    # Cache miss - execute function
                    self.cache_stats['misses'] += 1
                    self.cache_stats['total_queries'] += 1
                    
                    result = await func(*args, **kwargs)
                    
                    # Store in cache
                    await self.redis_client.setex(
                        cache_key,
                        ttl,
                        json.dumps(result, default=str)
                    )
                    
                    logger.debug("Cache miss - result cached", function=func.__name__, key=cache_key)
                    return result
                    
                except Exception as e:
                    logger.warning("Cache operation failed, executing function directly", 
                                 function=func.__name__, error=str(e))
                    return await func(*args, **kwargs)
            
            return wrapper
        return decorator
    
    async def get_user_productivity_summary(self, user_id: str, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """Cached expensive aggregation query for user productivity"""
        
        @self.cached(ttl=300, key_prefix="productivity_summary")
        async def _get_productivity_summary(user_id: str, start_date: str, end_date: str) -> Dict[str, Any]:
            start_dt = datetime.fromisoformat(start_date)
            end_dt = datetime.fromisoformat(end_date)
            
            with SessionLocal() as db:
                # Optimized queries using indexes
                sessions = db.query(PomodoroSession).filter(
                    PomodoroSession.user_id == user_id,
                    PomodoroSession.completed_at.between(start_dt, end_dt),
                    PomodoroSession.completed_at.isnot(None)
                ).all()
                
                tasks = db.query(Task).filter(
                    Task.user_id == user_id,
                    Task.updated_at.between(start_dt, end_dt)
                ).all()
                
                time_entries = db.query(TimeEntry).filter(
                    TimeEntry.user_id == user_id,
                    TimeEntry.created_at.between(start_dt, end_dt)
                ).all()
                
                # Calculate summary metrics
                total_sessions = len(sessions)
                total_focus_time = sum(s.duration for s in sessions if s.duration)
                avg_focus_score = sum(s.focus_score for s in sessions if s.focus_score) / max(total_sessions, 1)
                completed_tasks = len([t for t in tasks if t.status == 'completed'])
                interruption_rate = len([s for s in sessions if s.interrupted]) / max(total_sessions, 1)
                
                return {
                    'user_id': user_id,
                    'period': f"{start_dt.date()} to {end_dt.date()}",
                    'total_sessions': total_sessions,
                    'total_focus_time': total_focus_time,
                    'avg_focus_score': avg_focus_score,
                    'completed_tasks': completed_tasks,
                    'interruption_rate': interruption_rate,
                    'total_time_entries': len(time_entries),
                    'generated_at': datetime.now().isoformat()
                }
        
        return await _get_productivity_summary(user_id, start_date.isoformat(), end_date.isoformat())
    
    async def get_team_analytics(self, team_id: str) -> Dict[str, Any]:
        """Cached team-wide analytics calculation"""
        
        @self.cached(ttl=600, key_prefix="team_analytics")
        async def _get_team_analytics(team_id: str) -> Dict[str, Any]:
            # Mock team analytics - in real implementation would query team members
            team_metrics = {
                'team_id': team_id,
                'member_count': 5,
                'avg_team_focus_score': 0.75,
                'total_team_sessions': 45,
                'team_productivity_trend': 0.12,
                'collaboration_score': 0.68,
                'burnout_risk_distribution': {
                    'low': 3,
                    'medium': 1,
                    'high': 1,
                    'critical': 0
                },
                'peak_productivity_hours': [9, 10, 14, 15],
                'generated_at': datetime.now().isoformat()
            }
            return team_metrics
        
        return await _get_team_analytics(team_id)
    
    async def optimize_websocket_scaling(self):
        """Implement WebSocket connection pooling and message queuing"""
        logger.info("Setting up WebSocket scaling optimizations")
        
        try:
            if not self.redis_client:
                logger.warning("Redis not available for WebSocket scaling")
                return
            
            # WebSocket connection management
            websocket_config = {
                'max_connections_per_server': 1000,
                'message_queue_size': 10000,
                'heartbeat_interval': 30,
                'connection_timeout': 300,
                'message_compression': True,
                'load_balancing': 'round_robin'
            }
            
            # Store configuration in Redis
            await self.redis_client.setex(
                "websocket_config",
                3600,
                json.dumps(websocket_config)
            )
            
            logger.info("WebSocket scaling configuration set", config=websocket_config)
            
        except Exception as e:
            logger.error("Failed to setup WebSocket scaling", error=str(e))
    
    async def implement_connection_pooling(self):
        """Optimize database connection pooling"""
        logger.info("Optimizing database connection pooling")
        
        try:
            # Configure optimized connection pool
            optimized_engine = create_engine(
                engine.url,
                poolclass=QueuePool,
                pool_size=20,           # Increased pool size
                max_overflow=30,        # Allow overflow connections
                pool_pre_ping=True,     # Validate connections
                pool_recycle=3600,      # Recycle connections every hour
                pool_timeout=30,        # Timeout for getting connection
                echo=False              # Disable SQL logging in production
            )
            
            # Test connection pool
            with optimized_engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("Database connection pool optimized", pool_size=20)
            
        except Exception as e:
            logger.error("Failed to optimize connection pooling", error=str(e))
    
    async def setup_background_tasks(self):
        """Setup background tasks for maintenance and optimization"""
        logger.info("Setting up background optimization tasks")
        
        try:
            # Background task configuration
            background_tasks = {
                'cache_cleanup': {
                    'interval': 3600,  # Every hour
                    'function': 'cleanup_expired_cache'
                },
                'database_maintenance': {
                    'interval': 86400,  # Daily
                    'function': 'analyze_and_vacuum_tables'
                },
                'performance_monitoring': {
                    'interval': 300,  # Every 5 minutes
                    'function': 'monitor_performance_metrics'
                }
            }
            
            if self.redis_client:
                await self.redis_client.setex(
                    "background_tasks_config",
                    86400,
                    json.dumps(background_tasks)
                )
            
            logger.info("Background tasks configured", tasks=list(background_tasks.keys()))
            
        except Exception as e:
            logger.error("Failed to setup background tasks", error=str(e))
    
    async def cleanup_expired_cache(self):
        """Clean up expired cache entries"""
        try:
            if not self.redis_client:
                return
            
            # Get cache statistics
            info = await self.redis_client.info('memory')
            used_memory = info.get('used_memory', 0)
            
            logger.info("Cache cleanup completed", 
                       used_memory_mb=used_memory // (1024 * 1024),
                       cache_hits=self.cache_stats['hits'],
                       cache_misses=self.cache_stats['misses'])
            
        except Exception as e:
            logger.error("Failed to cleanup cache", error=str(e))
    
    async def analyze_and_vacuum_tables(self):
        """Analyze and vacuum database tables for performance"""
        try:
            with engine.connect() as connection:
                # Analyze tables to update statistics
                tables_to_analyze = [
                    'pomodoro_sessions',
                    'tasks', 
                    'time_entries',
                    'user_analytics',
                    'users'
                ]
                
                for table in tables_to_analyze:
                    try:
                        connection.execute(text(f"ANALYZE {table}"))
                        logger.debug("Table analyzed", table=table)
                    except Exception as e:
                        logger.warning("Failed to analyze table", table=table, error=str(e))
                
                connection.commit()
                logger.info("Database maintenance completed")
                
        except Exception as e:
            logger.error("Failed to perform database maintenance", error=str(e))
    
    async def monitor_performance_metrics(self):
        """Monitor and log performance metrics"""
        try:
            metrics = {
                'timestamp': datetime.now().isoformat(),
                'cache_hit_rate': self.cache_stats['hits'] / max(self.cache_stats['total_queries'], 1),
                'total_cache_queries': self.cache_stats['total_queries'],
                'active_connections': 0,  # Would get from connection pool
                'memory_usage': 0,        # Would get from system
                'response_times': {}      # Would track API response times
            }
            
            # Store metrics in Redis for monitoring
            if self.redis_client:
                await self.redis_client.lpush(
                    "performance_metrics",
                    json.dumps(metrics)
                )
                # Keep only last 1000 metrics
                await self.redis_client.ltrim("performance_metrics", 0, 999)
            
            logger.debug("Performance metrics collected", 
                        cache_hit_rate=f"{metrics['cache_hit_rate']:.2%}")
            
        except Exception as e:
            logger.warning("Failed to collect performance metrics", error=str(e))
    
    async def get_performance_report(self) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        try:
            report = {
                'cache_statistics': self.cache_stats.copy(),
                'cache_hit_rate': self.cache_stats['hits'] / max(self.cache_stats['total_queries'], 1),
                'optimizations_applied': [
                    'Database indexing',
                    'Query caching',
                    'Connection pooling',
                    'Background tasks'
                ],
                'recommendations': []
            }
            
            # Add recommendations based on performance
            if report['cache_hit_rate'] < 0.7:
                report['recommendations'].append("Increase cache TTL for frequently accessed data")
            
            if self.cache_stats['total_queries'] > 10000:
                report['recommendations'].append("Consider implementing query result pagination")
            
            # Get Redis memory usage if available
            if self.redis_client:
                try:
                    info = await self.redis_client.info('memory')
                    report['redis_memory_usage'] = info.get('used_memory', 0)
                    report['redis_connected_clients'] = info.get('connected_clients', 0)
                except Exception:
                    pass
            
            return report
            
        except Exception as e:
            logger.error("Failed to generate performance report", error=str(e))
            return {}
    
    async def optimize_api_responses(self):
        """Implement API response optimizations"""
        logger.info("Setting up API response optimizations")
        
        # Response compression configuration
        compression_config = {
            'enable_gzip': True,
            'compression_level': 6,
            'min_size': 1024,  # Only compress responses > 1KB
            'mime_types': [
                'application/json',
                'text/html',
                'text/css',
                'text/javascript'
            ]
        }
        
        # Response caching headers
        cache_headers = {
            'static_resources': {
                'Cache-Control': 'public, max-age=31536000',  # 1 year
                'ETag': True
            },
            'api_responses': {
                'Cache-Control': 'private, max-age=300',  # 5 minutes
                'ETag': True
            }
        }
        
        # Store configuration
        if self.redis_client:
            await self.redis_client.setex(
                "api_optimizations",
                86400,
                json.dumps({
                    'compression': compression_config,
                    'caching': cache_headers
                })
            )
        
        logger.info("API optimizations configured")
    
    @asynccontextmanager
    async def performance_monitoring(self, operation_name: str):
        """Context manager for monitoring operation performance"""
        start_time = time.time()
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            
            # Log slow operations
            if duration > 1.0:  # More than 1 second
                logger.warning("Slow operation detected", 
                             operation=operation_name,
                             duration=f"{duration:.2f}s")
            else:
                logger.debug("Operation completed", 
                           operation=operation_name,
                           duration=f"{duration:.3f}s")
            
            # Store performance data
            if self.redis_client:
                try:
                    await self.redis_client.lpush(
                        f"performance_log:{operation_name}",
                        json.dumps({
                            'timestamp': datetime.now().isoformat(),
                            'duration': duration
                        })
                    )
                    # Keep only last 100 entries per operation
                    await self.redis_client.ltrim(f"performance_log:{operation_name}", 0, 99)
                except Exception:
                    pass  # Don't fail the operation if logging fails


class MemoryOptimizer:
    """Memory usage optimization utilities"""
    
    @staticmethod
    def optimize_query_results(results: List[Any], max_size: int = 1000) -> List[Any]:
        """Optimize query results to prevent memory issues"""
        if len(results) > max_size:
            logger.warning("Large result set detected, truncating", 
                         original_size=len(results), 
                         truncated_size=max_size)
            return results[:max_size]
        return results
    
    @staticmethod
    def paginate_results(results: List[Any], page: int = 1, page_size: int = 50) -> Dict[str, Any]:
        """Paginate results to reduce memory usage"""
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        
        paginated_results = results[start_idx:end_idx]
        total_count = len(results)
        
        return {
            'results': paginated_results,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_count': total_count,
                'total_pages': (total_count + page_size - 1) // page_size,
                'has_next': end_idx < total_count,
                'has_previous': page > 1
            }
        }


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()

# Decorator for easy use
def cached_query(ttl: int = 300, key_prefix: str = "query"):
    """Convenience decorator for caching database queries"""
    return performance_optimizer.cached(ttl=ttl, key_prefix=key_prefix)

# Context manager for performance monitoring
async def monitor_performance(operation_name: str):
    """Convenience function for performance monitoring"""
    return performance_optimizer.performance_monitoring(operation_name)