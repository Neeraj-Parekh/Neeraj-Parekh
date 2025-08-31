#!/usr/bin/env python3
"""
Example usage of the Next-Generation AI Service for FocusFlow Enterprise
This script demonstrates how to use the advanced AI capabilities
"""

import asyncio
import os
from datetime import datetime
from backend.app.services.next_gen_ai_service import NextGenAIService

async def main():
    """Demonstrate AI service capabilities"""
    
    # Initialize the AI service
    # Note: In production, these would come from environment variables
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    openai_api_key = os.getenv("OPENAI_API_KEY", "your-openai-api-key-here")
    
    if openai_api_key == "your-openai-api-key-here":
        print("⚠️  Please set your OPENAI_API_KEY environment variable")
        print("   For demonstration purposes, we'll continue with limited functionality")
    
    # Create AI service instance
    ai_service = NextGenAIService(redis_url, openai_api_key)
    
    print("🚀 Initializing FocusFlow Enterprise Next-Generation AI Service...")
    
    try:
        # Initialize the service (this may take some time for model downloads)
        await ai_service.initialize()
        print("✅ AI Service initialized successfully!")
        
        # Example 1: Productivity Prediction
        print("\n📊 Example 1: Advanced Productivity Prediction")
        print("-" * 50)
        
        user_id = "demo_user_123"
        context = {
            "sleep_hours": 7.5,
            "exercise_minutes": 30,
            "stress_level": 4,  # 1-10 scale
            "environment_score": 8,  # 1-10 scale
            "meetings_today": 2,
            "calendar_density": 0.6
        }
        
        prediction = await ai_service.advanced_productivity_prediction(user_id, context)
        
        print(f"Predicted Productivity Score: {prediction.predicted_score:.2f}")
        print(f"Confidence Level: {prediction.confidence.value}")
        print(f"Top Factors:")
        for factor, importance in list(prediction.factors.items())[:3]:
            print(f"  - {factor}: {importance:.2f}")
        
        print(f"\nRecommendations:")
        for rec in prediction.recommendations[:3]:
            print(f"  • {rec}")
        
        # Example 2: Intelligent Task Breakdown
        print("\n🎯 Example 2: Intelligent Task Breakdown")
        print("-" * 50)
        
        task_description = """
        Develop a comprehensive machine learning model for predicting user productivity
        patterns in the FocusFlow application. The model should analyze historical data,
        user behavior patterns, and environmental factors to provide accurate predictions
        and personalized recommendations for optimal work scheduling.
        """
        
        user_context = {
            "experience_level": 0.8,  # 0-1 scale
            "skills": ["python", "machine learning", "data analysis", "tensorflow"],
            "duration_accuracy": 1.2,  # Historical multiplier
        }
        
        breakdown = await ai_service.intelligent_task_breakdown(task_description.strip(), user_context)
        
        print(f"Task Complexity Score: {breakdown.complexity_score:.2f}")
        print(f"Estimated Total Duration: {breakdown.estimated_total_duration} minutes")
        print(f"Recommended Approach: {breakdown.recommended_approach}")
        
        print(f"\nSubtasks ({len(breakdown.subtasks)}):")
        for i, subtask in enumerate(breakdown.subtasks, 1):
            print(f"  {i}. {subtask['title']}")
            print(f"     Duration: {subtask.get('estimated_duration', 'N/A')} min")
            print(f"     Priority: {subtask.get('priority', 'N/A')}")
            if 'difficulty_score' in subtask:
                print(f"     Difficulty: {subtask['difficulty_score']:.2f}")
            print()
        
        print(f"Risk Assessment:")
        risk_assessment = breakdown.risk_assessment
        print(f"  Overall Risk Score: {risk_assessment.get('overall_risk_score', 0):.2f}")
        if 'mitigation_strategies' in risk_assessment:
            print(f"  Mitigation Strategies:")
            for strategy in risk_assessment['mitigation_strategies'][:2]:
                print(f"    • {strategy}")
        
        print("\n🎉 Demo completed successfully!")
        print("\nThe Next-Generation AI Service provides:")
        print("  ✓ Advanced productivity predictions using ensemble ML models")
        print("  ✓ Intelligent task breakdown with complexity analysis")
        print("  ✓ Personalized recommendations based on user context")
        print("  ✓ Risk assessment and mitigation strategies")
        print("  ✓ Optimal scheduling and timing recommendations")
        print("  ✓ Comprehensive NLP analysis for task understanding")
        
    except Exception as e:
        print(f"❌ Error during demo: {str(e)}")
        print("\nThis is expected if dependencies are not installed.")
        print("To run the full demo, install requirements:")
        print("  pip install -r requirements.txt")
        print("  python -m spacy download en_core_web_sm")

if __name__ == "__main__":
    asyncio.run(main())