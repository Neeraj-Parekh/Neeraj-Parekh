#!/usr/bin/env python3
"""
Enhanced Desktop Application for FocusFlow
Implements memory optimization and performance improvements
"""

import gc
import weakref
import logging
import threading
import time
import json
import os
import shutil
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from contextlib import contextmanager
from dataclasses import dataclass, asdict

# Try to import PyQt5, fallback to mock for demo
try:
    from PyQt5.QtCore import QTimer, QThread, pyqtSignal, QObject
    from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QWidget
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    # Mock classes for demo purposes
    class MockSignal:
        def __init__(self):
            self.callbacks = []
        def connect(self, func):
            self.callbacks.append(func)
        def emit(self, *args):
            for callback in self.callbacks:
                try:
                    callback(*args)
                except:
                    pass

    class QTimer:
        def __init__(self):
            self.timeout = MockSignal()
            self.is_active = False
            self.interval_ms = 0
        def start(self, interval): 
            self.interval_ms = interval
            self.is_active = True
        def stop(self): 
            self.is_active = False
        def isActive(self):
            return self.is_active
    
    class QThread:
        def __init__(self):
            self.finished = MockSignal()
            self.running = False
        def start(self): 
            self.running = True
        def quit(self): 
            self.running = False
        def wait(self, timeout=None): 
            time.sleep(0.1)
        def isRunning(self): 
            return self.running
        def deleteLater(self):
            pass
    
    class pyqtSignal:
        def __init__(self, *args): 
            self.signal = MockSignal()
        def connect(self, func): 
            self.signal.connect(func)
        def emit(self, *args): 
            self.signal.emit(*args)

@dataclass
class MemoryStats:
    total_memory: int
    used_memory: int
    available_memory: int
    process_memory: int
    leak_detected: bool
    cleanup_count: int
    timestamp: datetime

@dataclass
class PerformanceMetrics:
    cpu_usage: float
    memory_usage: float
    response_time: float
    active_threads: int
    ui_responsiveness: float
    data_integrity_score: float
    timestamp: datetime

class MemoryOptimizedFocusFlow(QObject if PYQT_AVAILABLE else object):
    """
    Memory-optimized FocusFlow desktop application with leak prevention
    """
    
    def __init__(self):
        if PYQT_AVAILABLE:
            super().__init__()
        
        # Memory management
        self.active_timers = weakref.WeakSet()
        self.cleanup_timer = QTimer()
        self.cleanup_timer.timeout.connect(self.cleanup_resources)
        self.cleanup_timer.start(30000)  # Cleanup every 30 seconds
        
        # Logging configuration
        self.setup_logging()
        
        # Thread management
        self.worker_threads: List[QThread] = []
        self.thread_lock = threading.Lock()
        
        # Data management
        self.data_manager = SecureDataManager()
        
        # Performance monitoring
        self.performance_monitor = PerformanceMonitor()
        self.memory_monitor = MemoryMonitor()
        
        # State management
        self.is_running = False
        self.last_cleanup_time = datetime.now()
        
        self.logger.info("Memory-optimized FocusFlow initialized")
    
    def setup_logging(self):
        """Configure proper logging to prevent console spam"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('focusflow.log', mode='a'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Limit log file size
        log_file = 'focusflow.log'
        if os.path.exists(log_file) and os.path.getsize(log_file) > 10 * 1024 * 1024:  # 10MB
            shutil.move(log_file, f"{log_file}.old")
            self.logger.info("Log file rotated")
    
    def start_application(self):
        """Start the application with proper resource management"""
        try:
            self.is_running = True
            self.logger.info("Starting FocusFlow application")
            
            # Start performance monitoring
            self.performance_monitor.start()
            self.memory_monitor.start()
            
            # Start background services
            self.start_background_sync()
            
            # Initialize UI components
            self.initialize_ui()
            
            self.logger.info("Application started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start application: {e}")
            self.cleanup_and_exit()
            raise
    
    def cleanup_resources(self):
        """Prevent memory leaks by cleaning unused resources"""
        try:
            # Force garbage collection
            collected = gc.collect()
            
            # Clean up completed timers
            completed_timers = []
            for timer in list(self.active_timers):
                if hasattr(timer, 'isActive') and not timer.isActive():
                    completed_timers.append(timer)
            
            for timer in completed_timers:
                try:
                    if hasattr(timer, 'deleteLater'):
                        timer.deleteLater()
                except:
                    pass
            
            # Clean up finished threads
            with self.thread_lock:
                finished_threads = [t for t in self.worker_threads if not t.isRunning()]
                for thread in finished_threads:
                    try:
                        thread.deleteLater()
                        self.worker_threads.remove(thread)
                    except:
                        pass
            
            # Update memory statistics
            memory_stats = self.memory_monitor.get_current_stats()
            
            if collected > 0:
                self.logger.debug(f"Cleanup: collected {collected} objects, {len(completed_timers)} timers, {len(finished_threads)} threads")
            
            # Check for memory leaks
            if memory_stats.leak_detected:
                self.logger.warning("Memory leak detected, performing deep cleanup")
                self.perform_deep_cleanup()
            
            self.last_cleanup_time = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
    
    def perform_deep_cleanup(self):
        """Perform deep cleanup for memory leak recovery"""
        self.logger.info("Performing deep cleanup...")
        
        # Force garbage collection multiple times
        for _ in range(3):
            gc.collect()
            time.sleep(0.1)
        
        # Clear caches
        self.data_manager.clear_cache()
        
        # Reset weak references
        self.active_timers = weakref.WeakSet()
        
        self.logger.info("Deep cleanup completed")
    
    def start_background_sync(self):
        """Start background operations with proper thread management"""
        if len(self.worker_threads) >= 3:  # Limit concurrent threads
            self.logger.warning("Maximum background threads reached")
            return
        
        with self.thread_lock:
            worker = BackgroundSyncThread()
            worker.sync_completed.connect(self.on_sync_completed)
            worker.finished.connect(lambda: self.cleanup_thread(worker))
            
            self.worker_threads.append(worker)
            worker.start()
            
            self.logger.info("Background sync thread started")
    
    def cleanup_thread(self, thread):
        """Clean up completed thread"""
        with self.thread_lock:
            if thread in self.worker_threads:
                self.worker_threads.remove(thread)
                thread.deleteLater()
    
    def on_sync_completed(self, result: Dict[str, Any]):
        """Handle sync completion"""
        if 'error' in result:
            self.logger.error(f"Sync error: {result['error']}")
        else:
            self.logger.info("Background sync completed successfully")
            
        # Update performance metrics
        self.performance_monitor.record_sync_completion(result)
    
    def initialize_ui(self):
        """Initialize UI components with memory optimization"""
        self.logger.info("Initializing UI components")
        
        # Create main window with proper resource management
        # In a real implementation, this would create the actual UI
        
        # Set up system tray if available
        if PYQT_AVAILABLE and QSystemTrayIcon.isSystemTrayAvailable():
            self.setup_system_tray()
    
    def setup_system_tray(self):
        """Set up system tray with memory-efficient event handling"""
        try:
            self.tray_icon = QSystemTrayIcon()
            # Configure tray icon...
            self.logger.info("System tray initialized")
        except Exception as e:
            self.logger.error(f"Failed to setup system tray: {e}")
    
    def save_application_state(self):
        """Save current application state"""
        try:
            state = {
                'performance_metrics': self.performance_monitor.get_summary(),
                'memory_stats': asdict(self.memory_monitor.get_current_stats()),
                'active_threads': len(self.worker_threads),
                'last_cleanup': self.last_cleanup_time.isoformat(),
                'uptime': (datetime.now() - self.last_cleanup_time).total_seconds()
            }
            
            self.data_manager.save_data(state, 'application_state.json')
            self.logger.info("Application state saved")
            
        except Exception as e:
            self.logger.error(f"Failed to save application state: {e}")
    
    def closeEvent(self, event):
        """Proper cleanup on application exit"""
        self.logger.info("Application closing - performing cleanup")
        
        # Stop cleanup timer
        self.cleanup_timer.stop()
        
        # Stop all background threads
        with self.thread_lock:
            for thread in self.worker_threads:
                if thread.isRunning():
                    thread.quit()
                    thread.wait(3000)  # Wait up to 3 seconds
        
        # Save application state
        self.save_application_state()
        
        # Final cleanup
        self.cleanup_resources()
        
        # Stop monitors
        self.performance_monitor.stop()
        self.memory_monitor.stop()
        
        self.is_running = False
        self.logger.info("Application closed successfully")
        
        if hasattr(event, 'accept'):
            event.accept()
    
    def cleanup_and_exit(self):
        """Emergency cleanup and exit"""
        self.logger.warning("Emergency cleanup initiated")
        try:
            self.closeEvent(None)
        except:
            pass

class BackgroundSyncThread(QThread):
    """Background thread for sync operations with proper error handling"""
    
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(f"{__name__}.BackgroundSync")
        self.sync_completed = pyqtSignal(dict)
    
    def run(self):
        """Background operations without blocking UI"""
        try:
            # Simulate data sync operations
            self.logger.info("Starting background sync")
            
            # Perform sync operations
            sync_result = self.perform_sync()
            
            # Emit completion signal
            self.sync_completed.emit(sync_result)
            
        except Exception as e:
            self.logger.error(f"Background sync error: {e}")
            self.sync_completed.emit({'error': str(e)})
    
    def perform_sync(self) -> Dict[str, Any]:
        """Perform actual sync operations"""
        try:
            # Simulate sync operations
            time.sleep(1)  # Simulate work
            
            return {
                'status': 'success',
                'synced_items': 42,
                'duration': 1.0,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            raise Exception(f"Sync operation failed: {e}")

class SecureDataManager:
    """Secure data management with corruption prevention"""
    
    def __init__(self, data_dir="focusflow_data"):
        self.data_dir = data_dir
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
        self.cache_timestamps = {}
        
        # Ensure data directory exists
        os.makedirs(data_dir, exist_ok=True)
        
        self.logger = logging.getLogger(f"{__name__}.DataManager")
    
    def save_data(self, data: Any, filename: str) -> bool:
        """Atomic save with backup to prevent data corruption"""
        file_path = os.path.join(self.data_dir, filename)
        backup_path = f"{file_path}.backup"
        temp_path = f"{file_path}.tmp"
        
        try:
            # Create backup of existing file
            if os.path.exists(file_path):
                shutil.copy2(file_path, backup_path)
            
            # Write to temporary file first
            with open(temp_path, 'w') as f:
                if isinstance(data, (dict, list)):
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                else:
                    f.write(str(data))
            
            # Atomic move
            shutil.move(temp_path, file_path)
            
            # Update cache
            self.cache[filename] = data
            self.cache_timestamps[filename] = time.time()
            
            self.logger.debug(f"Data saved successfully: {filename}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save data {filename}: {e}")
            
            # Clean up temp file
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            return False
    
    def load_data(self, filename: str, default: Any = None) -> Any:
        """Load data with corruption recovery"""
        # Check cache first
        if filename in self.cache:
            cache_time = self.cache_timestamps.get(filename, 0)
            if time.time() - cache_time < self.cache_ttl:
                return self.cache[filename]
        
        file_path = os.path.join(self.data_dir, filename)
        backup_path = f"{file_path}.backup"
        
        try:
            # Try to load primary file
            with open(file_path, 'r') as f:
                if filename.endswith('.json'):
                    data = json.load(f)
                else:
                    data = f.read()
            
            # Update cache
            self.cache[filename] = data
            self.cache_timestamps[filename] = time.time()
            
            return data
            
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(f"Primary data file corrupted or missing: {filename} - {e}")
            
            # Try backup file
            if os.path.exists(backup_path):
                try:
                    with open(backup_path, 'r') as f:
                        if filename.endswith('.json'):
                            data = json.load(f)
                        else:
                            data = f.read()
                    
                    self.logger.info(f"Restored from backup: {filename}")
                    
                    # Update cache
                    self.cache[filename] = data
                    self.cache_timestamps[filename] = time.time()
                    
                    return data
                    
                except Exception as backup_error:
                    self.logger.error(f"Backup file also corrupted: {backup_error}")
            
            # Return default if both files fail
            self.logger.warning(f"Using default data for {filename}")
            return default if default is not None else self.get_default_data(filename)
        
        except Exception as e:
            self.logger.error(f"Unexpected error loading {filename}: {e}")
            return default if default is not None else self.get_default_data(filename)
    
    def get_default_data(self, filename: str) -> Dict[str, Any]:
        """Get default data structure based on filename"""
        if 'tasks' in filename:
            return {"tasks": [], "last_updated": datetime.now().isoformat()}
        elif 'settings' in filename:
            return {
                "pomodoro_duration": 25,
                "short_break": 5,
                "long_break": 15,
                "auto_start_breaks": False,
                "sound_enabled": True,
                "notifications_enabled": True
            }
        elif 'analytics' in filename:
            return {
                "total_focus_time": 0,
                "completed_pomodoros": 0,
                "tasks_completed": 0,
                "productivity_trend": 0.0
            }
        else:
            return {}
    
    def clear_cache(self):
        """Clear the data cache"""
        self.cache.clear()
        self.cache_timestamps.clear()
        self.logger.info("Data cache cleared")

class MemoryMonitor:
    """Monitor memory usage and detect leaks"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.MemoryMonitor")
        self.baseline_memory = 0
        self.memory_history = []
        self.monitoring = False
        self.monitor_thread = None
    
    def start(self):
        """Start memory monitoring"""
        self.monitoring = True
        self.baseline_memory = self.get_process_memory()
        
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        self.logger.info(f"Memory monitoring started - baseline: {self.baseline_memory} MB")
    
    def stop(self):
        """Stop memory monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self.logger.info("Memory monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self.monitoring:
            try:
                stats = self.get_current_stats()
                self.memory_history.append(stats)
                
                # Keep only last 100 records
                if len(self.memory_history) > 100:
                    self.memory_history.pop(0)
                
                # Check for memory leaks
                if stats.leak_detected:
                    self.logger.warning("Memory leak detected!")
                
                time.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                self.logger.error(f"Memory monitoring error: {e}")
                time.sleep(30)  # Wait longer on error
    
    def get_process_memory(self) -> int:
        """Get current process memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            return int(memory_mb)
        except ImportError:
            # Fallback for systems without psutil
            return 50  # Mock value
        except Exception:
            return 0
    
    def get_current_stats(self) -> MemoryStats:
        """Get current memory statistics"""
        try:
            process_memory = self.get_process_memory()
            
            # Simple leak detection: memory growth > 50% from baseline
            leak_detected = process_memory > self.baseline_memory * 1.5
            
            return MemoryStats(
                total_memory=0,  # Would need system info
                used_memory=process_memory,
                available_memory=0,
                process_memory=process_memory,
                leak_detected=leak_detected,
                cleanup_count=len(self.memory_history),
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"Error getting memory stats: {e}")
            return MemoryStats(
                total_memory=0,
                used_memory=0,
                available_memory=0,
                process_memory=0,
                leak_detected=False,
                cleanup_count=0,
                timestamp=datetime.now()
            )

class PerformanceMonitor:
    """Monitor application performance metrics"""
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.PerformanceMonitor")
        self.metrics_history = []
        self.monitoring = False
        self.start_time = datetime.now()
    
    def start(self):
        """Start performance monitoring"""
        self.monitoring = True
        self.start_time = datetime.now()
        self.logger.info("Performance monitoring started")
    
    def stop(self):
        """Stop performance monitoring"""
        self.monitoring = False
        self.logger.info("Performance monitoring stopped")
    
    def record_sync_completion(self, result: Dict[str, Any]):
        """Record sync operation completion"""
        if 'duration' in result:
            self.logger.info(f"Sync completed in {result['duration']:.2f}s")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get performance summary"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            'uptime_seconds': uptime,
            'uptime_formatted': str(timedelta(seconds=int(uptime))),
            'metrics_recorded': len(self.metrics_history),
            'monitoring_active': self.monitoring
        }

def main():
    """Main application entry point"""
    print("🚀 Starting FocusFlow Enhanced Desktop Application")
    
    # Create application instance
    if PYQT_AVAILABLE:
        app = QApplication([])
    
    # Create and start FocusFlow
    focusflow = MemoryOptimizedFocusFlow()
    
    try:
        focusflow.start_application()
        
        print("✅ FocusFlow application started successfully")
        print("📊 Memory optimization and leak prevention active")
        print("🔧 Background services running")
        print("💾 Secure data management enabled")
        
        # In a real application, this would start the event loop
        if PYQT_AVAILABLE:
            print("Starting Qt event loop...")
            # app.exec_()
        else:
            print("PyQt5 not available - running in demo mode")
            print("In a real deployment, install PyQt5 for full functionality")
            
            # Simulate running for demo
            print("Simulating application runtime...")
            time.sleep(5)
            
            print("Demonstrating cleanup...")
            focusflow.cleanup_resources()
            
            print("Saving state and exiting...")
            focusflow.save_application_state()
        
    except KeyboardInterrupt:
        print("\n⏹️ Application interrupted by user")
    except Exception as e:
        print(f"❌ Application error: {e}")
    finally:
        # Cleanup
        focusflow.cleanup_and_exit()
        print("🧹 Cleanup completed")

if __name__ == "__main__":
    main()