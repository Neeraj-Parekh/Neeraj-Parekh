#!/usr/bin/env python3
"""
FocusFlow Enterprise - Comprehensive Productivity System Demo
Demonstrates all implemented services and features
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from typing import Dict, Any

# Add backend to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import all services
from backend.app.services.passive_tracking_service import PassiveTrackingService
from backend.app.services.predictive_tasks_service import PredictiveTaskService
from backend.app.services.auto_scheduling_service import AutoSchedulingService
from backend.app.services.content_generation_service import ContentGenerationService
from backend.app.services.environment_automation_service import EnvironmentAutomationService
from backend.app.services.virtual_coworking_service import VirtualCoworkingService
from backend.app.core.performance_optimizations import PerformanceOptimizer

def print_header(title: str):
    """Print a formatted header"""
    print("\\n" + "="*60)
    print(f"🚀 {title}")
    print("="*60)

def print_section(title: str):
    """Print a formatted section"""
    print(f"\\n📋 {title}")
    print("-" * 40)

def print_result(service: str, result: Dict[str, Any]):
    """Print service result"""
    print(f"✅ {service}: {result.get('status', 'completed')}")
    if 'message' in result:
        print(f"   💬 {result['message']}")
    if 'metrics' in result:
        print(f"   📊 Metrics: {result['metrics']}")

async def demo_passive_tracking():
    """Demo passive tracking service"""
    print_section("Universal Passive Time Tracking")
    
    service = PassiveTrackingService()
    user_id = "demo_user_001"
    
    try:
        # Track all activity
        print("🔍 Starting comprehensive activity tracking...")
        tracking_result = await service.track_all_activity(user_id)
        
        print(f"   📱 Applications tracked: {len(tracking_result.get('application_usage', []))}")
        print(f"   🌐 Website activity: {len(tracking_result.get('website_activity', []))}")
        print(f"   ⌨️  Input patterns analyzed: {'✓' if tracking_result.get('keyboard_mouse_patterns') else '✗'}")
        print(f"   📺 Screen engagement: {tracking_result.get('screen_engagement', {}).get('focus_score', 0):.2f}")
        print(f"   🎯 Productivity score: {tracking_result.get('productivity_score', 0):.2f}")
        
        # Get tracking summary
        summary = await service.get_tracking_summary(user_id, hours=24)
        print(f"   📈 24h summary: {summary.get('total_tracked_time', 0)} minutes tracked")
        
        return {"status": "success", "productivity_score": tracking_result.get('productivity_score', 0)}
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}

async def demo_predictive_tasks():
    """Demo predictive task creation"""
    print_section("Predictive Task Creation")
    
    service = PredictiveTaskService()
    user_id = "demo_user_001"
    
    try:
        print("🤖 Generating predictive tasks based on patterns...")
        
        # Generate predictive tasks
        predictions = await service.generate_predictive_tasks(user_id)
        
        auto_created = predictions.get('auto_created_tasks', [])
        suggested = predictions.get('suggested_tasks', [])
        summary = predictions.get('prediction_summary', {})
        
        print(f"   ✨ Auto-created tasks: {len(auto_created)}")
        print(f"   💡 Suggested tasks: {len(suggested)}")
        print(f"   🎯 High confidence predictions: {summary.get('high_confidence_count', 0)}")
        print(f"   📊 Total predictions: {summary.get('total_predictions', 0)}")
        
        # Show top 3 predictions
        if suggested:
            print("   🔝 Top 3 suggested tasks:")
            for i, task in enumerate(suggested[:3], 1):
                print(f"      {i}. {task.get('title', 'Unknown')} (confidence: {task.get('confidence', 0):.0%})")
        
        return {"status": "success", "predictions": len(suggested), "auto_created": len(auto_created)}
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}

async def demo_auto_scheduling():
    """Demo auto-scheduling intelligence"""
    print_section("Auto-Scheduling Intelligence")
    
    service = AutoSchedulingService()
    user_id = "demo_user_001"
    
    try:
        print("📅 Optimizing schedule based on productivity patterns...")
        
        # Define date range for optimization
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        
        # Optimize schedule
        optimization_result = await service.optimize_schedule(user_id, (start_date, end_date))
        
        executed = optimization_result.get('executed_optimizations', [])
        suggested = optimization_result.get('suggested_optimizations', [])
        impact = optimization_result.get('impact_summary', {})
        
        print(f"   ⚡ Optimizations executed: {len(executed)}")
        print(f"   💭 Additional suggestions: {len(suggested)}")
        print(f"   📈 Estimated productivity gain: {impact.get('total_productivity_gain', 0):.1%}")
        print(f"   🎯 Focus time gained: {impact.get('estimated_focus_time_gained', 0)} minutes")
        
        # Show optimization types
        if executed:
            print("   🔧 Optimizations applied:")
            for opt in executed:
                print(f"      • {opt.get('optimization_type', 'Unknown').replace('_', ' ').title()}")
        
        return {"status": "success", "optimizations": len(executed), "productivity_gain": impact.get('total_productivity_gain', 0)}
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}

async def demo_content_generation():
    """Demo smart content generation"""
    print_section("Smart Content Generation")
    
    service = ContentGenerationService()
    user_id = "demo_user_001"
    
    try:
        print("✍️  Generating smart content...")
        
        # Generate email draft
        email_context = {
            'purpose': 'Weekly project update',
            'recipient': {'name': 'Manager', 'relationship': 'supervisor'},
            'key_points': ['Completed milestone 1', 'Started milestone 2', 'Need feedback on design']
        }
        
        email_result = await service.generate_email_draft(user_id, email_context)
        
        print(f"   📧 Email draft generated: '{email_result.get('subject', 'Unknown')}'")
        print(f"   🎯 Confidence score: {email_result.get('confidence_score', 0):.0%}")
        print(f"   📝 Email type: {email_result.get('email_type', 'Unknown')}")
        print(f"   🎨 Tone: {email_result.get('tone', 'Unknown')}")
        print(f"   🔄 Alternative versions: {len(email_result.get('alternative_versions', []))}")
        
        # Generate progress report
        report_result = await service.generate_progress_report(user_id, "productivity", "weekly")
        
        print(f"   📊 Progress report generated: '{report_result.get('title', 'Unknown')}'")
        print(f"   📈 Sections included: {len(report_result.get('sections', []))}")
        print(f"   🎯 Key metrics: {len(report_result.get('key_metrics', {}))}")
        print(f"   💡 Recommendations: {len(report_result.get('recommendations', []))}")
        print(f"   📋 Action items: {len(report_result.get('action_items', []))}")
        
        return {"status": "success", "email_generated": True, "report_generated": True}
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}

async def demo_environment_automation():
    """Demo dynamic environment control"""
    print_section("Dynamic Environment Control")
    
    service = EnvironmentAutomationService()
    user_id = "demo_user_001"
    
    try:
        print("🏠 Optimizing environment for deep work...")
        
        # Optimize environment for deep work
        task_context = {
            'estimated_duration': 90,  # 90 minutes
            'task_importance': 'high'
        }
        
        env_result = await service.optimize_environment_for_task(user_id, "deep_work", task_context)
        
        changes = env_result.get('changes_made', [])
        boost = env_result.get('estimated_productivity_boost', 0)
        duration = env_result.get('duration_minutes', 0)
        
        print(f"   🌟 Environment optimizations: {len(changes)}")
        print(f"   📈 Estimated productivity boost: {boost:.1%}")
        print(f"   ⏱️  Session duration: {duration} minutes")
        print(f"   🔄 Auto-revert scheduled")
        
        # Show environment changes
        if changes:
            print("   🎛️  Applied changes:")
            for change in changes:
                print(f"      • {change.get('type', 'Unknown').replace('_', ' ').title()}")
        
        # Demo burnout detection
        print("\\n🧘 Checking burnout risk...")
        break_result = await service.enforce_break(user_id, "micro")
        
        break_enforced = break_result.get('break_enforced', False)
        stress_score = break_result.get('stress_score', 0)
        
        print(f"   ⚖️  Stress score: {stress_score:.2f}")
        print(f"   🛑 Break enforced: {'Yes' if break_enforced else 'No (suggestion only)'}")
        
        if break_enforced:
            print(f"   ⏱️  Break duration: {break_result.get('duration_minutes', 0)} minutes")
        
        return {"status": "success", "environment_optimized": True, "stress_monitored": True}
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}

async def demo_virtual_coworking():
    """Demo virtual body doubling"""
    print_section("Virtual Body Doubling")
    
    service = VirtualCoworkingService()
    user_id = "demo_user_001"
    
    try:
        print("👥 Creating virtual coworking environment...")
        
        # Create focus room
        room_config = {
            'name': 'Deep Work Session',
            'type': 'silent_coworking',
            'max_participants': 6,
            'duration': 120,  # 2 hours
            'privacy': 'team',
            'ambient_sounds': 'forest',
            'accountability': 'high'
        }
        
        room_result = await service.create_focus_room(user_id, room_config)
        room_id = room_result.get('room_id')
        
        print(f"   🏠 Focus room created: {room_id}")
        print(f"   👑 Room creator: {user_id}")
        print(f"   🎯 Room type: {room_config['type']}")
        print(f"   👥 Max participants: {room_config['max_participants']}")
        print(f"   ⏱️  Duration: {room_config['duration']} minutes")
        
        # Join the session
        session_goals = ["Complete project milestone", "Review code", "Plan next sprint"]
        join_result = await service.join_focus_session(user_id, room_id, session_goals)
        
        session_id = join_result.get('session_id')
        partner = join_result.get('accountability_partner')
        
        print(f"   ✅ Joined session: {session_id}")
        print(f"   🎯 Session goals: {len(session_goals)}")
        print(f"   🤝 Accountability partner: {'Assigned' if partner else 'None available'}")
        
        if partner:
            print(f"      • Compatibility: {partner.get('compatibility_score', 0):.0%}")
            print(f"      • Shared goals: {len(partner.get('shared_goals', []))}")
        
        # Get room activity
        activity = await service.get_room_activity(room_id)
        print(f"   📊 Current participants: {activity.get('participant_count', 0)}")
        
        # Leave session
        leave_result = await service.leave_focus_session(user_id, room_id)
        insights = leave_result.get('session_insights')
        
        if insights:
            print(f"   📈 Session insights generated")
            print(f"      • Focus score: {insights.focus_score:.0%}")
            print(f"      • Goals achieved: {insights.goals_achieved}/{insights.total_goals}")
            print(f"      • Session duration: {insights.session_duration} minutes")
        
        return {"status": "success", "room_created": True, "session_completed": True}
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}

async def demo_performance_optimizations():
    """Demo performance optimizations"""
    print_section("Performance Optimizations")
    
    optimizer = PerformanceOptimizer()
    
    try:
        print("⚡ Applying performance optimizations...")
        
        # Setup optimizations
        await optimizer.optimize_database_queries()
        print("   ✅ Database indexes created")
        
        await optimizer.implement_query_caching()
        print("   ✅ Query caching enabled")
        
        await optimizer.optimize_websocket_scaling()
        print("   ✅ WebSocket scaling configured")
        
        await optimizer.implement_connection_pooling()
        print("   ✅ Connection pooling optimized")
        
        await optimizer.setup_background_tasks()
        print("   ✅ Background tasks scheduled")
        
        # Demo cached query
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()
        
        print("\\n🔍 Testing cached queries...")
        summary = await optimizer.get_user_productivity_summary("demo_user_001", start_date, end_date)
        
        print(f"   📊 Productivity summary cached")
        print(f"   🎯 Focus score: {summary.get('avg_focus_score', 0):.2f}")
        print(f"   ⏱️  Total sessions: {summary.get('total_sessions', 0)}")
        
        # Get performance report
        report = await optimizer.get_performance_report()
        
        print(f"\\n📈 Performance Report:")
        print(f"   🎯 Cache hit rate: {report.get('cache_hit_rate', 0):.1%}")
        print(f"   📊 Total queries: {report.get('cache_statistics', {}).get('total_queries', 0)}")
        print(f"   ✅ Optimizations: {len(report.get('optimizations_applied', []))}")
        print(f"   💡 Recommendations: {len(report.get('recommendations', []))}")
        
        return {"status": "success", "optimizations_applied": True, "performance_monitored": True}
        
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {"status": "error", "error": str(e)}

async def main():
    """Main demo function"""
    print_header("FocusFlow Enterprise - Comprehensive Productivity System")
    
    print("🎯 Comprehensive AI-powered productivity platform")
    print("📊 Real-time tracking, predictive insights, and environment automation")
    print("🤖 Next-generation workplace optimization system")
    
    # Run all demos
    results = {}
    
    print_header("Running Service Demonstrations")
    
    # Demo each service
    results['passive_tracking'] = await demo_passive_tracking()
    results['predictive_tasks'] = await demo_predictive_tasks()
    results['auto_scheduling'] = await demo_auto_scheduling()
    results['content_generation'] = await demo_content_generation()
    results['environment_automation'] = await demo_environment_automation()
    results['virtual_coworking'] = await demo_virtual_coworking()
    results['performance_optimizations'] = await demo_performance_optimizations()
    
    # Summary
    print_header("Demo Summary")
    
    successful_services = [name for name, result in results.items() if result.get('status') == 'success']
    failed_services = [name for name, result in results.items() if result.get('status') == 'error']
    
    print(f"✅ Successful services: {len(successful_services)}/{len(results)}")
    print(f"❌ Failed services: {len(failed_services)}")
    
    if successful_services:
        print("\\n🎉 Successfully demonstrated:")
        for service in successful_services:
            print(f"   ✓ {service.replace('_', ' ').title()}")
    
    if failed_services:
        print("\\n⚠️  Services with errors:")
        for service in failed_services:
            error = results[service].get('error', 'Unknown error')
            print(f"   ✗ {service.replace('_', ' ').title()}: {error}")
    
    print("\\n" + "="*60)
    print("🚀 FocusFlow Enterprise Demo Complete!")
    print("📈 Next-generation productivity system ready for deployment")
    print("="*60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\n\\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\\n\\n❌ Demo failed with error: {e}")
        sys.exit(1)