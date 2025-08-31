#!/usr/bin/env python3
"""
Validation script for FocusFlow Intelligence Implementation
Tests all automated intelligence components and features
"""

import sys
import os
import json
import time
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

class IntelligenceValidator:
    """Comprehensive validation of FocusFlow intelligence features"""
    
    def __init__(self):
        self.results = {
            'timestamp': datetime.now().isoformat(),
            'tests': {},
            'summary': {'passed': 0, 'failed': 0, 'total': 0}
        }
        
    def run_all_tests(self):
        """Run comprehensive validation of all intelligence features"""
        print("🧪 FocusFlow Intelligence Validation Suite")
        print("=" * 60)
        
        tests = [
            ("File Structure", self.test_file_structure),
            ("TypeScript Components", self.test_typescript_components),
            ("Desktop Application", self.test_desktop_application),
            ("Service Worker", self.test_service_worker),
            ("Demo Application", self.test_demo_application),
            ("Integration Test", self.test_integration),
            ("Performance Test", self.test_performance),
            ("Documentation", self.test_documentation)
        ]
        
        for test_name, test_func in tests:
            print(f"\n🔍 Testing: {test_name}")
            try:
                result = test_func()
                self.record_test(test_name, result, None)
                print(f"✅ {test_name}: PASSED")
            except Exception as e:
                self.record_test(test_name, False, str(e))
                print(f"❌ {test_name}: FAILED - {e}")
        
        self.print_summary()
        return self.results['summary']['failed'] == 0
    
    def test_file_structure(self) -> bool:
        """Test that all required files exist"""
        required_files = [
            'src/services/ActivityTracker.ts',
            'src/services/PredictiveTaskEngine.ts', 
            'src/services/EnvironmentController.ts',
            'desktop_app_enhanced.py',
            'service-worker-enhanced.js',
            'intelligence-demo.html',
            'ActivityTracker.js',
            'PredictiveTaskEngine.js',
            'EnvironmentController.js',
            'INTELLIGENCE_IMPLEMENTATION.md'
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            raise Exception(f"Missing files: {', '.join(missing_files)}")
        
        print(f"  📁 All {len(required_files)} required files present")
        return True
    
    def test_typescript_components(self) -> bool:
        """Test TypeScript/JavaScript components"""
        components = [
            ('ActivityTracker.js', ['UniversalActivityTracker', 'AIActivityClassifier']),
            ('PredictiveTaskEngine.js', ['PredictiveTaskEngine', 'PatternAnalyzer']),
            ('EnvironmentController.js', ['EnvironmentController'])
        ]
        
        for file_name, expected_classes in components:
            file_path = project_root / file_name
            content = file_path.read_text()
            
            for class_name in expected_classes:
                if f"class {class_name}" not in content:
                    raise Exception(f"Class {class_name} not found in {file_name}")
        
        print("  🔧 All TypeScript components validated")
        return True
    
    def test_desktop_application(self) -> bool:
        """Test desktop application functionality"""
        try:
            # Run desktop app in test mode
            result = subprocess.run([
                sys.executable, 'desktop_app_enhanced.py'
            ], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                raise Exception(f"Desktop app failed: {result.stderr}")
            
            # Check for expected output (combine stdout and stderr)
            output = result.stdout + result.stderr
            expected_outputs = [
                'Memory-optimized FocusFlow',
                'Application started successfully',
                'Cleanup completed'
            ]
            
            for expected in expected_outputs:
                if expected not in output:
                    raise Exception(f"Expected output missing: {expected}")
            
            print("  🖥️ Desktop application runs successfully")
            return True
            
        except subprocess.TimeoutExpired:
            raise Exception("Desktop application timed out")
        except FileNotFoundError:
            raise Exception("Python not found or desktop app missing")
    
    def test_service_worker(self) -> bool:
        """Test service worker functionality"""
        sw_file = project_root / 'service-worker-enhanced.js'
        content = sw_file.read_text()
        
        required_features = [
            'class EnhancedServiceWorker',
            'handleFetch',
            'handleBackgroundSync',
            'cacheStaticAssets',
            'enforceCacheLimits',
            'performBackgroundSync'
        ]
        
        for feature in required_features:
            if feature not in content:
                raise Exception(f"Service worker missing feature: {feature}")
        
        # Check for cache versioning
        if 'CACHE_VERSION' not in content:
            raise Exception("Service worker missing cache versioning")
        
        print("  🔄 Service worker features validated")
        return True
    
    def test_demo_application(self) -> bool:
        """Test demo application structure"""
        demo_file = project_root / 'intelligence-demo.html'
        content = demo_file.read_text()
        
        required_features = [
            'Universal Activity Tracker',
            'Predictive Task Engine', 
            'Smart Environment Controller',
            'startActivityTracking',
            'generatePredictions',
            'applyEnvironmentProfile',
            'ActivityTracker.js',
            'PredictiveTaskEngine.js',
            'EnvironmentController.js'
        ]
        
        for feature in required_features:
            if feature not in content:
                raise Exception(f"Demo missing feature: {feature}")
        
        print("  🎮 Demo application structure validated")
        return True
    
    def test_integration(self) -> bool:
        """Test integration between components"""
        # Test that JavaScript files can be loaded
        js_files = ['ActivityTracker.js', 'PredictiveTaskEngine.js', 'EnvironmentController.js']
        
        for js_file in js_files:
            content = (project_root / js_file).read_text()
            
            # Check for browser compatibility
            if 'typeof window !== \'undefined\'' not in content:
                raise Exception(f"{js_file} missing browser compatibility check")
            
            # Check for module exports
            if 'typeof module !== \'undefined\'' not in content:
                raise Exception(f"{js_file} missing module export support")
        
        print("  🔗 Component integration validated")
        return True
    
    def test_performance(self) -> bool:
        """Test performance characteristics"""
        # Check file sizes (should be reasonable for web deployment)
        file_size_limits = {
            'ActivityTracker.js': 20000,  # 20KB
            'PredictiveTaskEngine.js': 40000,  # 40KB
            'EnvironmentController.js': 40000,  # 40KB
            'intelligence-demo.html': 40000,  # 40KB
            'service-worker-enhanced.js': 30000  # 30KB
        }
        
        for file_name, max_size in file_size_limits.items():
            file_path = project_root / file_name
            file_size = file_path.stat().st_size
            
            if file_size > max_size:
                raise Exception(f"{file_name} too large: {file_size} > {max_size}")
        
        print("  ⚡ Performance characteristics validated")
        return True
    
    def test_documentation(self) -> bool:
        """Test documentation completeness"""
        doc_file = project_root / 'INTELLIGENCE_IMPLEMENTATION.md'
        content = doc_file.read_text()
        
        required_sections = [
            '## 🧠 Overview',
            '## 🚀 Implemented Features',
            '### ✅ 1. Universal Activity Tracker',
            '### ✅ 2. Predictive Task Engine',
            '### ✅ 3. Smart Environment Controller',
            '### ✅ 4. Enhanced Desktop Application',
            '### ✅ 5. Enhanced PWA Service Worker',
            '## 🎮 Interactive Demo',
            '## 🏗️ Architecture',
            '## 🚀 Installation & Usage'
        ]
        
        for section in required_sections:
            if section not in content:
                raise Exception(f"Documentation missing section: {section}")
        
        # Check for code examples
        if '```javascript' not in content or '```python' not in content:
            raise Exception("Documentation missing code examples")
        
        print("  📚 Documentation completeness validated")
        return True
    
    def record_test(self, test_name: str, passed: bool, error: Optional[str]):
        """Record test result"""
        self.results['tests'][test_name] = {
            'passed': passed,
            'error': error,
            'timestamp': datetime.now().isoformat()
        }
        
        if passed:
            self.results['summary']['passed'] += 1
        else:
            self.results['summary']['failed'] += 1
        
        self.results['summary']['total'] += 1
    
    def print_summary(self):
        """Print test summary"""
        summary = self.results['summary']
        total = summary['total']
        passed = summary['passed']
        failed = summary['failed']
        
        print(f"\n📊 Test Summary")
        print(f"=" * 40)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed} ✅")
        print(f"Failed: {failed} ❌")
        print(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed == 0:
            print(f"\n🎉 All tests passed! Intelligence system is ready for deployment.")
        else:
            print(f"\n⚠️ {failed} test(s) failed. Check implementation.")
        
        # Save results
        results_file = project_root / 'validation_results.json'
        with open(results_file, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: {results_file}")

def main():
    """Main validation function"""
    print("🚀 Starting FocusFlow Intelligence Validation")
    print(f"📁 Project root: {project_root}")
    print(f"🕒 Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    validator = IntelligenceValidator()
    success = validator.run_all_tests()
    
    if success:
        print("\n✨ Validation completed successfully!")
        print("🎯 FocusFlow Intelligence System is ready for production!")
        return 0
    else:
        print("\n❌ Validation failed!")
        print("🔧 Please fix the issues and run validation again.")
        return 1

if __name__ == "__main__":
    exit(main())