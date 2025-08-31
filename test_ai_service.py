#!/usr/bin/env python3
"""
Basic validation test for the Next-Generation AI Service
This test validates the service structure without requiring all dependencies
"""

import sys
import os
import asyncio
from unittest.mock import Mock, patch

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import_structure():
    """Test that the basic module structure can be imported"""
    try:
        from backend.app.services.next_gen_ai_service import (
            NextGenAIService,
            AIModelType,
            PredictionConfidence,
            ProductivityPrediction,
            TaskBreakdown,
            AIInsight
        )
        print("✅ Successfully imported AI service components")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

def test_enum_values():
    """Test that enums are properly defined"""
    try:
        from backend.app.services.next_gen_ai_service import AIModelType, PredictionConfidence
        
        # Test AIModelType enum
        assert AIModelType.PRODUCTIVITY_PREDICTOR.value == "productivity_predictor"
        assert AIModelType.TASK_PRIORITIZER.value == "task_prioritizer"
        assert AIModelType.BURNOUT_DETECTOR.value == "burnout_detector"
        
        # Test PredictionConfidence enum
        assert PredictionConfidence.LOW.value == "low"
        assert PredictionConfidence.HIGH.value == "high"
        
        print("✅ Enum values are correctly defined")
        return True
    except Exception as e:
        print(f"❌ Enum test failed: {e}")
        return False

def test_dataclass_structure():
    """Test that dataclasses are properly structured"""
    try:
        from backend.app.services.next_gen_ai_service import ProductivityPrediction, PredictionConfidence
        from datetime import datetime
        
        # Create a sample prediction
        prediction = ProductivityPrediction(
            predicted_score=0.75,
            confidence=PredictionConfidence.HIGH,
            factors={"sleep": 0.3, "stress": 0.2},
            recommendations=["Take breaks", "Exercise"],
            optimal_schedule={"start": "09:00"},
            risk_factors=["Fatigue"]
        )
        
        assert prediction.predicted_score == 0.75
        assert prediction.confidence == PredictionConfidence.HIGH
        assert len(prediction.recommendations) == 2
        
        print("✅ Dataclass structure is valid")
        return True
    except Exception as e:
        print(f"❌ Dataclass test failed: {e}")
        return False

def test_service_initialization():
    """Test that the service can be initialized (without actually loading models)"""
    try:
        from backend.app.services.next_gen_ai_service import NextGenAIService
        
        # Mock the dependencies to avoid requiring actual installations
        with patch('redis.asyncio.from_url'), \
             patch('openai.OpenAI'):
            
            service = NextGenAIService(
                redis_url="redis://localhost:6379",
                openai_api_key="test-key"
            )
            
            assert service.cache_ttl == 3600
            assert service.is_initialized == False
            assert len(service.model_configs) == 3
            
        print("✅ Service can be initialized")
        return True
    except Exception as e:
        print(f"❌ Service initialization test failed: {e}")
        return False

async def test_basic_methods():
    """Test that basic methods exist and have correct signatures"""
    try:
        from backend.app.services.next_gen_ai_service import NextGenAIService
        
        with patch('redis.asyncio.from_url'), \
             patch('openai.OpenAI'):
            
            service = NextGenAIService("redis://localhost", "test-key")
            
            # Check that required methods exist
            assert hasattr(service, 'initialize')
            assert hasattr(service, 'advanced_productivity_prediction')
            assert hasattr(service, 'intelligent_task_breakdown')
            assert hasattr(service, '_rule_based_productivity_prediction')
            
        print("✅ Required methods are present")
        return True
    except Exception as e:
        print(f"❌ Method test failed: {e}")
        return False

def test_model_configurations():
    """Test that model configurations are properly defined"""
    try:
        from backend.app.services.next_gen_ai_service import NextGenAIService, AIModelType
        
        with patch('redis.asyncio.from_url'), \
             patch('openai.OpenAI'):
            
            service = NextGenAIService("redis://localhost", "test-key")
            
            # Check model configurations
            configs = service.model_configs
            
            assert AIModelType.PRODUCTIVITY_PREDICTOR in configs
            assert AIModelType.TASK_PRIORITIZER in configs
            assert AIModelType.BURNOUT_DETECTOR in configs
            
            # Check configuration structure
            for model_type, config in configs.items():
                assert "features" in config
                assert "model_class" in config
                assert "params" in config
                assert isinstance(config["features"], list)
                
        print("✅ Model configurations are valid")
        return True
    except Exception as e:
        print(f"❌ Model configuration test failed: {e}")
        return False

async def main():
    """Run all validation tests"""
    print("🧪 Running Next-Generation AI Service Validation Tests")
    print("=" * 60)
    
    tests = [
        ("Import Structure", test_import_structure),
        ("Enum Values", test_enum_values),
        ("Dataclass Structure", test_dataclass_structure),
        ("Service Initialization", test_service_initialization),
        ("Basic Methods", test_basic_methods),
        ("Model Configurations", test_model_configurations),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
    
    print(f"\n📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validation tests passed!")
        print("\nThe Next-Generation AI Service structure is valid.")
        print("To run with full functionality, install dependencies:")
        print("  pip install -r requirements.txt")
        print("  python demo_ai_service.py")
    else:
        print("⚠️  Some tests failed. Check the implementation.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())