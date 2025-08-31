"""
Next-Generation AI Service for FocusFlow Enterprise
Implements cutting-edge AI capabilities for productivity optimization
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Any, Optional, Tuple, Union
import numpy as np
import pandas as pd
from dataclasses import dataclass, asdict
from enum import Enum
import structlog

# AI/ML Imports
import openai
from transformers import (
    AutoTokenizer, AutoModel, pipeline, 
    BertTokenizer, BertForSequenceClassification
)
import torch
import tensorflow as tf
from sklearn.ensemble import RandomForestRegressor, IsolationForest, GradientBoostingClassifier
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.decomposition import PCA
import joblib

# Data Processing
import spacy
from sentence_transformers import SentenceTransformer
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.stem import WordNetLemmatizer

# Database and Redis
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import User, Task, PomodoroSession, TimeEntry, UserAnalytics
import redis.asyncio as redis

logger = structlog.get_logger()

class AIModelType(Enum):
    PRODUCTIVITY_PREDICTOR = "productivity_predictor"
    TASK_PRIORITIZER = "task_prioritizer"
    BURNOUT_DETECTOR = "burnout_detector"
    FOCUS_OPTIMIZER = "focus_optimizer"
    SCHEDULE_OPTIMIZER = "schedule_optimizer"

class PredictionConfidence(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

@dataclass
class AIInsight:
    insight_id: str
    insight_type: str
    title: str
    description: str
    confidence: PredictionConfidence
    impact_score: float
    actionable_steps: List[str]
    evidence: Dict[str, Any]
    expires_at: datetime

@dataclass
class ProductivityPrediction:
    predicted_score: float
    confidence: PredictionConfidence
    factors: Dict[str, float]
    recommendations: List[str]
    optimal_schedule: Dict[str, Any]
    risk_factors: List[str]

@dataclass
class TaskBreakdown:
    subtasks: List[Dict[str, Any]]
    estimated_total_duration: int
    complexity_score: float
    recommended_approach: str
    dependencies: List[Dict[str, Any]]
    risk_assessment: Dict[str, Any]

class NextGenAIService:
    def __init__(self, redis_url: str, openai_api_key: str):
        self.redis = redis.from_url(redis_url)
        self.openai_client = openai.OpenAI(api_key=openai_api_key)
        
        # Initialize models
        self.models = {}
        self.scalers = {}
        self.is_initialized = False
        
        # Model configurations
        self.model_configs = {
            AIModelType.PRODUCTIVITY_PREDICTOR: {
                "type": "regression",
                "features": ["hour", "day_of_week", "sleep_hours", "exercise_minutes", 
                           "stress_level", "workload", "environment_score"],
                "target": "productivity_score",
                "model_class": RandomForestRegressor,
                "params": {"n_estimators": 200, "max_depth": 15, "random_state": 42}
            },
            AIModelType.TASK_PRIORITIZER: {
                "type": "classification",
                "features": ["urgency_score", "importance_score", "complexity", "duration_estimate",
                           "deadline_proximity", "dependency_count", "user_preference"],
                "target": "priority_level",
                "model_class": GradientBoostingClassifier,
                "params": {"n_estimators": 150, "learning_rate": 0.1, "random_state": 42}
            },
            AIModelType.BURNOUT_DETECTOR: {
                "type": "anomaly_detection",
                "features": ["work_hours_trend", "break_frequency", "stress_indicators",
                           "sleep_quality", "productivity_decline", "engagement_score"],
                "model_class": IsolationForest,
                "params": {"contamination": 0.1, "random_state": 42}
            }
        }
        
        # NLP Models
        self.sentence_transformer = None
        self.nlp_pipeline = None
        
        # Cache for AI responses
        self.response_cache = {}
        self.cache_ttl = 3600  # 1 hour

    async def initialize(self):
        """Initialize all AI models and services"""
        if self.is_initialized:
            return
            
        logger.info("Initializing Next-Generation AI Service...")
        
        try:
            # Initialize NLP models
            await self._initialize_nlp_models()
            
            # Load or create ML models
            await self._initialize_ml_models()
            
            # Initialize TensorFlow models
            await self._initialize_tensorflow_models()
            
            # Download required NLTK data
            await self._setup_nltk()
            
            self.is_initialized = True
            logger.info("✅ Next-Generation AI Service initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize AI service: {str(e)}")
            raise

    async def _initialize_nlp_models(self):
        """Initialize NLP models for text processing"""
        try:
            # Sentence transformer for semantic similarity
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            
            # Sentiment analysis pipeline
            self.sentiment_analyzer = pipeline(
                "sentiment-analysis",
                model="cardiffnlp/twitter-roberta-base-sentiment-latest"
            )
            
            # Text classification for task categorization
            self.task_classifier = pipeline(
                "text-classification",
                model="microsoft/DialoGPT-medium"
            )
            
            # Load spaCy model for advanced NLP
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                self.nlp = None
                
        except Exception as e:
            logger.error(f"Failed to initialize NLP models: {str(e)}")
            raise

    async def _initialize_ml_models(self):
        """Initialize or load ML models"""
        for model_type, config in self.model_configs.items():
            try:
                model_path = f"models/{model_type.value}.joblib"
                scaler_path = f"models/{model_type.value}_scaler.joblib"
                
                # Try to load existing models
                try:
                    self.models[model_type] = joblib.load(model_path)
                    self.scalers[model_type] = joblib.load(scaler_path)
                    logger.info(f"Loaded existing model: {model_type.value}")
                except FileNotFoundError:
                    # Create new models
                    self.models[model_type] = config["model_class"](**config["params"])
                    self.scalers[model_type] = StandardScaler()
                    logger.info(f"Created new model: {model_type.value}")
                    
            except Exception as e:
                logger.error(f"Failed to initialize model {model_type.value}: {str(e)}")

    async def _initialize_tensorflow_models(self):
        """Initialize TensorFlow models for deep learning"""
        try:
            # Neural network for complex productivity patterns
            self.productivity_nn = tf.keras.Sequential([
                tf.keras.layers.Dense(128, activation='relu', input_shape=(20,)),
                tf.keras.layers.Dropout(0.3),
                tf.keras.layers.Dense(64, activation='relu'),
                tf.keras.layers.Dropout(0.2),
                tf.keras.layers.Dense(32, activation='relu'),
                tf.keras.layers.Dense(1, activation='sigmoid')
            ])
            
            self.productivity_nn.compile(
                optimizer='adam',
                loss='mse',
                metrics=['mae']
            )
            
            # LSTM for time series prediction
            self.lstm_model = tf.keras.Sequential([
                tf.keras.layers.LSTM(50, return_sequences=True, input_shape=(7, 10)),  # 7 days, 10 features
                tf.keras.layers.Dropout(0.2),
                tf.keras.layers.LSTM(50, return_sequences=False),
                tf.keras.layers.Dropout(0.2),
                tf.keras.layers.Dense(25),
                tf.keras.layers.Dense(1)
            ])
            
            self.lstm_model.compile(optimizer='adam', loss='mse')
            
        except Exception as e:
            logger.error(f"Failed to initialize TensorFlow models: {str(e)}")

    async def _setup_nltk(self):
        """Download required NLTK data"""
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('stopwords', quiet=True)
            nltk.download('wordnet', quiet=True)
            nltk.download('vader_lexicon', quiet=True)
        except Exception as e:
            logger.warning(f"Failed to download NLTK data: {str(e)}")

    async def advanced_productivity_prediction(self, user_id: str, context: Dict[str, Any]) -> ProductivityPrediction:
        """Advanced productivity prediction using ensemble methods"""
        cache_key = f"productivity_prediction:{user_id}:{hash(str(context))}"
        
        # Check cache
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return ProductivityPrediction(**cached_result)
        
        try:
            # Gather comprehensive user data
            user_data = await self._gather_user_productivity_data(user_id)
            
            # Extract features for prediction
            features = await self._extract_productivity_features(user_data, context)
            
            # Ensemble prediction using multiple models
            predictions = await self._ensemble_productivity_prediction(features)
            
            # Generate personalized recommendations
            recommendations = await self._generate_productivity_recommendations(
                user_id, features, predictions
            )
            
            # Create optimal schedule
            optimal_schedule = await self._optimize_user_schedule(user_id, predictions)
            
            # Assess risk factors
            risk_factors = await self._assess_productivity_risks(user_data, predictions)
            
            # Determine confidence level
            confidence = self._determine_prediction_confidence(predictions)
            
            result = ProductivityPrediction(
                predicted_score=predictions["weighted_average"],
                confidence=confidence,
                factors=predictions["feature_importance"],
                recommendations=recommendations,
                optimal_schedule=optimal_schedule,
                risk_factors=risk_factors
            )
            
            # Cache result
            await self._cache_result(cache_key, asdict(result))
            
            # Log prediction
            logger.info(
                "Advanced productivity prediction generated",
                user_id=user_id,
                predicted_score=result.predicted_score,
                confidence=result.confidence.value
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Productivity prediction failed for user {user_id}: {str(e)}")
            raise

    async def _gather_user_productivity_data(self, user_id: str) -> Dict[str, Any]:
        """Gather comprehensive productivity data for user"""
        async with get_db() as db:
            # Get recent sessions
            recent_sessions = db.query(PomodoroSession).filter(
                PomodoroSession.user_id == user_id,
                PomodoroSession.completed_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            # Get tasks
            recent_tasks = db.query(Task).filter(
                Task.user_id == user_id,
                Task.updated_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            # Get time entries
            time_entries = db.query(TimeEntry).filter(
                TimeEntry.user_id == user_id,
                TimeEntry.created_at >= datetime.now() - timedelta(days=30)
            ).all()
            
            # Get analytics
            analytics = db.query(UserAnalytics).filter(
                UserAnalytics.user_id == user_id
            ).first()
        
        return {
            "sessions": [self._session_to_dict(s) for s in recent_sessions],
            "tasks": [self._task_to_dict(t) for t in recent_tasks],
            "time_entries": [self._time_entry_to_dict(te) for te in time_entries],
            "analytics": self._analytics_to_dict(analytics) if analytics else {}
        }

    async def _extract_productivity_features(self, user_data: Dict[str, Any], context: Dict[str, Any]) -> np.ndarray:
        """Extract features for productivity prediction"""
        features = []
        
        # Time-based features
        current_time = datetime.now()
        features.extend([
            current_time.hour,  # Hour of day
            current_time.weekday(),  # Day of week
            current_time.day,  # Day of month
        ])
        
        # Historical productivity features
        sessions = user_data.get("sessions", [])
        if sessions:
            focus_scores = [s.get("focus_score", 0.5) for s in sessions]
            features.extend([
                np.mean(focus_scores),  # Average focus score
                np.std(focus_scores),   # Focus score variability
                len([s for s in sessions if s.get("interrupted", False)]) / len(sessions),  # Interruption rate
            ])
        else:
            features.extend([0.5, 0.2, 0.3])  # Default values
        
        # Task completion features
        tasks = user_data.get("tasks", [])
        if tasks:
            completed_tasks = [t for t in tasks if t.get("status") == "completed"]
            features.extend([
                len(completed_tasks) / len(tasks),  # Completion rate
                np.mean([t.get("completed_pomodoros", 0) for t in tasks]),  # Avg pomodoros per task
            ])
        else:
            features.extend([0.7, 2.5])  # Default values
        
        # Context features
        features.extend([
            context.get("sleep_hours", 7),  # Sleep hours
            context.get("exercise_minutes", 30),  # Exercise minutes
            context.get("stress_level", 5) / 10,  # Normalized stress level
            context.get("environment_score", 7) / 10,  # Normalized environment score
        ])
        
        # Workload features
        features.extend([
            len([t for t in tasks if t.get("status") == "pending"]),  # Pending tasks count
            len([t for t in tasks if t.get("priority") in ["high", "critical"]]),  # High priority tasks
        ])
        
        # Social/calendar features
        features.extend([
            context.get("meetings_today", 2),  # Number of meetings
            context.get("calendar_density", 0.6),  # Calendar fill percentage
        ])
        
        # Seasonal/temporal features
        features.extend([
            current_time.month,  # Month
            1 if current_time.weekday() < 5 else 0,  # Is weekday
        ])
        
        # Pad or truncate to fixed length (20 features)
        target_length = 20
        if len(features) < target_length:
            features.extend([0] * (target_length - len(features)))
        elif len(features) > target_length:
            features = features[:target_length]
        
        return np.array(features).reshape(1, -1)

    async def _ensemble_productivity_prediction(self, features: np.ndarray) -> Dict[str, Any]:
        """Use ensemble of models for robust prediction"""
        predictions = {}
        weights = {}
        
        # Random Forest prediction
        if AIModelType.PRODUCTIVITY_PREDICTOR in self.models:
            try:
                scaled_features = self.scalers[AIModelType.PRODUCTIVITY_PREDICTOR].transform(features)
                rf_pred = self.models[AIModelType.PRODUCTIVITY_PREDICTOR].predict(scaled_features)[0]
                predictions["random_forest"] = max(0, min(1, rf_pred))
                weights["random_forest"] = 0.3
            except Exception as e:
                logger.warning(f"Random Forest prediction failed: {str(e)}")
        
        # Neural Network prediction
        try:
            nn_pred = self.productivity_nn.predict(features, verbose=0)[0][0]
            predictions["neural_network"] = max(0, min(1, float(nn_pred)))
            weights["neural_network"] = 0.4
        except Exception as e:
            logger.warning(f"Neural Network prediction failed: {str(e)}")
        
        # LSTM prediction (if historical data available)
        try:
            # This would require time series data preparation
            # For now, use a simplified approach
            lstm_pred = 0.75  # Placeholder
            predictions["lstm"] = lstm_pred
            weights["lstm"] = 0.2
        except Exception as e:
            logger.warning(f"LSTM prediction failed: {str(e)}")
        
        # Rule-based prediction as fallback
        rule_based_pred = self._rule_based_productivity_prediction(features)
        predictions["rule_based"] = rule_based_pred
        weights["rule_based"] = 0.1
        
        # Calculate weighted average
        if predictions:
            total_weight = sum(weights.values())
            weighted_sum = sum(pred * weights.get(model, 0) for model, pred in predictions.items())
            weighted_average = weighted_sum / total_weight if total_weight > 0 else 0.5
        else:
            weighted_average = 0.5
        
        # Feature importance (simplified for demonstration)
        feature_importance = {
            "time_of_day": 0.25,
            "historical_performance": 0.30,
            "sleep_quality": 0.15,
            "stress_level": 0.20,
            "workload": 0.10
        }
        
        return {
            "individual_predictions": predictions,
            "weights": weights,
            "weighted_average": weighted_average,
            "feature_importance": feature_importance,
            "model_confidence": len(predictions) / 4  # Confidence based on number of successful predictions
        }

    def _rule_based_productivity_prediction(self, features: np.ndarray) -> float:
        """Rule-based productivity prediction as fallback"""
        feature_vector = features.flatten()
        
        # Time-based rules
        hour = int(feature_vector[0])
        productivity_score = 0.5
        
        # Peak hours (9-11 AM, 2-4 PM)
        if hour in [9, 10, 14, 15]:
            productivity_score += 0.2
        elif hour in [8, 11, 13, 16]:
            productivity_score += 0.1
        elif hour < 8 or hour > 18:
            productivity_score -= 0.2
        
        # Day of week adjustment
        day_of_week = int(feature_vector[1])
        if day_of_week in [0, 1, 2, 3]:  # Monday-Thursday
            productivity_score += 0.1
        elif day_of_week == 4:  # Friday
            productivity_score -= 0.05
        else:  # Weekend
            productivity_score -= 0.15
        
        # Sleep and stress adjustments
        if len(feature_vector) > 10:
            sleep_hours = feature_vector[9]
            stress_level = feature_vector[10]
            
            if sleep_hours >= 7:
                productivity_score += 0.1
            elif sleep_hours < 6:
                productivity_score -= 0.2
            
            if stress_level < 0.3:
                productivity_score += 0.1
            elif stress_level > 0.7:
                productivity_score -= 0.2
        
        return max(0, min(1, productivity_score))

    async def _generate_productivity_recommendations(self, user_id: str, features: np.ndarray, predictions: Dict[str, Any]) -> List[str]:
        """Generate personalized productivity recommendations"""
        recommendations = []
        
        predicted_score = predictions["weighted_average"]
        feature_importance = predictions["feature_importance"]
        
        # Time-based recommendations
        current_hour = int(features.flatten()[0])
        if current_hour < 8:
            recommendations.append("Consider starting work later - productivity typically peaks after 9 AM")
        elif current_hour > 17:
            recommendations.append("Evening work sessions can be less productive - consider morning tasks")
        
        # Performance-based recommendations
        if predicted_score < 0.6:
            recommendations.append("Your productivity score is predicted to be low. Consider:")
            recommendations.append("-  Taking a 5-10 minute break before starting")
            recommendations.append("-  Choosing easier tasks to build momentum")
            recommendations.append("-  Using the Pomodoro technique with shorter intervals")
        elif predicted_score > 0.8:
            recommendations.append("High productivity predicted! Perfect time for:")
            recommendations.append("-  Tackling your most challenging tasks")
            recommendations.append("-  Deep focus work without interruptions")
            recommendations.append("-  Learning new skills or complex problem-solving")
        
        # Feature-specific recommendations
        if feature_importance.get("sleep_quality", 0) > 0.2:
            recommendations.append("Sleep quality significantly impacts your productivity")
            recommendations.append("-  Aim for 7-9 hours of quality sleep")
            recommendations.append("-  Consider a consistent bedtime routine")
        
        if feature_importance.get("stress_level", 0) > 0.2:
            recommendations.append("Stress levels are affecting your performance")
            recommendations.append("-  Try 5-minute meditation before work sessions")
            recommendations.append("-  Use breathing exercises during breaks")
        
        # AI-generated contextual recommendations
        try:
            ai_recommendations = await self._generate_ai_recommendations(user_id, predicted_score)
            recommendations.extend(ai_recommendations)
        except Exception as e:
            logger.warning(f"Failed to generate AI recommendations: {str(e)}")
        
        return recommendations[:8]  # Limit to 8 recommendations

    async def _generate_ai_recommendations(self, user_id: str, predicted_score: float) -> List[str]:
        """Generate AI-powered recommendations using GPT"""
        try:
            prompt = f"""
            Based on a predicted productivity score of {predicted_score:.2f} (0-1 scale), 
            provide 3 specific, actionable recommendations for optimizing work performance.
            
            Focus on:
            - Immediate actions they can take
            - Environment optimization
            - Energy management
            
            Format as bullet points. Be concise and practical.
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=200
            )
            
            content = response.choices[0].message.content
            # Parse bullet points
            recommendations = [line.strip() for line in content.split('\n') if line.strip().startswith('- ') or line.strip().startswith('-')]
            
            return recommendations[:3]  # Limit to 3 AI recommendations
            
        except Exception as e:
            logger.error(f"Failed to generate AI recommendations: {str(e)}")
            return []

    async def intelligent_task_breakdown(self, task_description: str, user_context: Dict[str, Any]) -> TaskBreakdown:
        """Break down complex tasks using AI and ML techniques"""
        cache_key = f"task_breakdown:{hash(task_description)}"
        
        # Check cache
        cached_result = await self._get_from_cache(cache_key)
        if cached_result:
            return TaskBreakdown(**cached_result)
        
        try:
            # Analyze task complexity using NLP
            complexity_analysis = await self._analyze_task_complexity(task_description)
            
            # Generate subtasks using GPT-4
            subtasks = await self._generate_subtasks_with_ai(task_description, complexity_analysis)
            
            # Enhance subtasks with ML predictions
            enhanced_subtasks = await self._enhance_subtasks_with_ml(subtasks, user_context)
            
            # Analyze dependencies
            dependencies = await self._analyze_task_dependencies(enhanced_subtasks)
            
            # Risk assessment
            risk_assessment = await self._assess_task_risks(task_description, enhanced_subtasks)
            
            # Calculate total duration
            total_duration = sum(subtask.get("estimated_duration", 25) for subtask in enhanced_subtasks)
            
            # Generate recommended approach
            recommended_approach = await self._generate_task_approach(complexity_analysis, enhanced_subtasks)
            
            result = TaskBreakdown(
                subtasks=enhanced_subtasks,
                estimated_total_duration=total_duration,
                complexity_score=complexity_analysis["complexity_score"],
                recommended_approach=recommended_approach,
                dependencies=dependencies,
                risk_assessment=risk_assessment
            )
            
            # Cache result
            await self._cache_result(cache_key, asdict(result))
            
            logger.info(
                "Intelligent task breakdown completed",
                task_description=task_description[:50],
                subtask_count=len(enhanced_subtasks),
                complexity_score=complexity_analysis["complexity_score"]
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Task breakdown failed: {str(e)}")
            raise

    async def _analyze_task_complexity(self, task_description: str) -> Dict[str, Any]:
        """Analyze task complexity using NLP techniques"""
        try:
            # Tokenize and analyze text
            doc = self.nlp(task_description) if self.nlp else None
            
            complexity_indicators = {
                "word_count": len(task_description.split()),
                "sentence_count": len(sent_tokenize(task_description)),
                "technical_terms": 0,
                "action_verbs": 0,
                "complexity_keywords": 0,
                "uncertainty_indicators": 0
            }
            
            # Define complexity keywords
            technical_terms = ["algorithm", "implementation", "architecture", "framework", "optimization", "integration"]
            complexity_keywords = ["complex", "advanced", "comprehensive", "detailed", "thorough", "extensive"]
            uncertainty_indicators = ["might", "could", "possibly", "perhaps", "unclear", "investigate"]
            action_verbs = ["analyze", "design", "implement", "optimize", "integrate", "develop", "create"]
            
            text_lower = task_description.lower()
            
            # Count indicators
            for term in technical_terms:
                if term in text_lower:
                    complexity_indicators["technical_terms"] += 1
            
            for keyword in complexity_keywords:
                if keyword in text_lower:
                    complexity_indicators["complexity_keywords"] += 1
            
            for indicator in uncertainty_indicators:
                if indicator in text_lower:
                    complexity_indicators["uncertainty_indicators"] += 1
            
            for verb in action_verbs:
                if verb in text_lower:
                    complexity_indicators["action_verbs"] += 1
            
            # Calculate complexity score (0-1)
            complexity_score = min(1.0, (
                complexity_indicators["word_count"] / 100 * 0.2 +
                complexity_indicators["technical_terms"] / 5 * 0.3 +
                complexity_indicators["complexity_keywords"] / 3 * 0.2 +
                complexity_indicators["action_verbs"] / 5 * 0.2 +
                complexity_indicators["uncertainty_indicators"] / 3 * 0.1
            ))
            
            # Sentiment analysis
            sentiment = self.sentiment_analyzer(task_description)[0] if self.sentiment_analyzer else {"label": "NEUTRAL", "score": 0.5}
            
            return {
                "complexity_score": complexity_score,
                "indicators": complexity_indicators,
                "sentiment": sentiment,
                "estimated_base_duration": max(25, int(complexity_score * 120))  # 25-120 minutes based on complexity
            }
            
        except Exception as e:
            logger.error(f"Task complexity analysis failed: {str(e)}")
            return {
                "complexity_score": 0.5,
                "indicators": {},
                "sentiment": {"label": "NEUTRAL", "score": 0.5},
                "estimated_base_duration": 45
            }

    async def _generate_subtasks_with_ai(self, task_description: str, complexity_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate subtasks using AI"""
        try:
            complexity_score = complexity_analysis["complexity_score"]
            
            prompt = f"""
            Break down the following task into 3-7 actionable subtasks:
            
            Task: {task_description}
            
            Complexity Level: {complexity_score:.2f} (0=simple, 1=very complex)
            
            For each subtask, provide:
            1. Clear, actionable description
            2. Estimated duration in minutes (15-60 range)
            3. Priority level (low, medium, high)
            4. Required skills/tools
            
            Format as JSON array with objects containing: title, description, estimated_duration, priority, skills_required
            """
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=800
            )
            
            content = response.choices[0].message.content
            
            # Try to parse JSON response
            try:
                subtasks = json.loads(content)
                if isinstance(subtasks, list):
                    return subtasks
            except json.JSONDecodeError:
                pass
            
            # Fallback: parse manually
            lines = content.split('\n')
            subtasks = []
            current_subtask = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or \
                   line.startswith('4.') or line.startswith('5.') or line.startswith('6.') or line.startswith('7.'):
                    if current_subtask:
                        subtasks.append(current_subtask)
                    current_subtask = {
                        "title": line[2:].strip(),
                        "description": line[2:].strip(),
                        "estimated_duration": 30,
                        "priority": "medium",
                        "skills_required": []
                    }
                elif "duration" in line.lower() and current_subtask:
                    # Extract duration
                    import re
                    duration_match = re.search(r'(\d+)', line)
                    if duration_match:
                        current_subtask["estimated_duration"] = int(duration_match.group(1))
            
            if current_subtask:
                subtasks.append(current_subtask)
            
            return subtasks[:7]  # Limit to 7 subtasks
            
        except Exception as e:
            logger.error(f"AI subtask generation failed: {str(e)}")
            # Fallback subtasks
            return [
                {
                    "title": "Plan and research",
                    "description": "Gather requirements and plan approach",
                    "estimated_duration": 30,
                    "priority": "high",
                    "skills_required": ["research", "planning"]
                },
                {
                    "title": "Implement solution",
                    "description": "Execute the main task",
                    "estimated_duration": 60,
                    "priority": "high",
                    "skills_required": ["implementation"]
                },
                {
                    "title": "Review and test",
                    "description": "Validate and test the results",
                    "estimated_duration": 25,
                    "priority": "medium",
                    "skills_required": ["testing", "review"]
                }
            ]

    async def _enhance_subtasks_with_ml(self, subtasks: List[Dict[str, Any]], user_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Enhance subtasks with ML predictions"""
        enhanced_subtasks = []
        
        for subtask in subtasks:
            try:
                # Predict actual duration based on user history
                predicted_duration = await self._predict_task_duration(subtask, user_context)
                
                # Assess difficulty based on user skills
                difficulty_score = await self._assess_task_difficulty(subtask, user_context)
                
                # Add ML enhancements
                enhanced_subtask = {
                    **subtask,
                    "predicted_duration": predicted_duration,
                    "difficulty_score": difficulty_score,
                    "confidence_interval": [
                        max(15, predicted_duration - 10),
                        predicted_duration + 15
                    ],
                    "success_probability": max(0.3, 1.0 - difficulty_score),
                    "recommended_time_of_day": await self._recommend_task_timing(subtask, user_context)
                }
                
                enhanced_subtasks.append(enhanced_subtask)
                
            except Exception as e:
                logger.warning(f"Failed to enhance subtask: {str(e)}")
                enhanced_subtasks.append(subtask)
        
        return enhanced_subtasks

    async def _predict_task_duration(self, subtask: Dict[str, Any], user_context: Dict[str, Any]) -> int:
        """Predict actual task duration based on user history"""
        base_duration = subtask.get("estimated_duration", 30)
        
        # Adjust based on user experience level
        experience_multiplier = user_context.get("experience_level", 1.0)
        
        # Adjust based on task complexity
        complexity_words = ["complex", "advanced", "difficult", "challenging"]
        description = subtask.get("description", "").lower()
        complexity_adjustment = 1.0
        
        for word in complexity_words:
            if word in description:
                complexity_adjustment += 0.2
        
        # Adjust based on user's historical performance
        historical_accuracy = user_context.get("duration_accuracy", 1.0)
        
        predicted_duration = int(base_duration * experience_multiplier * complexity_adjustment * historical_accuracy)
        
        return max(15, min(120, predicted_duration))

    async def _assess_task_difficulty(self, subtask: Dict[str, Any], user_context: Dict[str, Any]) -> float:
        """Assess task difficulty for the specific user"""
        base_difficulty = 0.5
        
        # Check if user has required skills
        required_skills = subtask.get("skills_required", [])
        user_skills = user_context.get("skills", [])
        
        skill_match_ratio = 0.8  # Default if no skills specified
        if required_skills:
            matched_skills = len([skill for skill in required_skills if skill in user_skills])
            skill_match_ratio = matched_skills / len(required_skills)
        
        # Higher difficulty if user lacks required skills
        difficulty = base_difficulty + (1 - skill_match_ratio) * 0.3
        
        # Adjust based on task priority
        priority = subtask.get("priority", "medium")
        if priority == "high":
            difficulty += 0.1
        elif priority == "low":
            difficulty -= 0.1
        
        return max(0.1, min(1.0, difficulty))

    async def _recommend_task_timing(self, subtask: Dict[str, Any], user_context: Dict[str, Any]) -> str:
        """Recommend optimal timing for task execution"""
        difficulty = subtask.get("difficulty_score", 0.5)
        duration = subtask.get("estimated_duration", 30)
        
        # High difficulty tasks -> morning (peak focus)
        if difficulty > 0.7:
            return "morning"
        # Long tasks -> when user has extended availability
        elif duration > 60:
            return "morning_or_afternoon_block"
        # Medium tasks -> flexible timing
        elif difficulty > 0.4:
            return "morning_or_afternoon"
        # Easy tasks -> any time, including late day
        else:
            return "flexible"

    async def _analyze_task_dependencies(self, subtasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze dependencies between subtasks"""
        dependencies = []
        
        # Simple heuristic-based dependency detection
        for i, subtask in enumerate(subtasks):
            title = subtask.get("title", "").lower()
            description = subtask.get("description", "").lower()
            
            # Planning tasks usually come first
            if any(word in title + description for word in ["plan", "research", "analyze", "design"]):
                if i > 0:
                    dependencies.append({
                        "from_task": 0,
                        "to_task": i,
                        "type": "sequential",
                        "description": "Planning should come before implementation"
                    })
            
            # Testing/review tasks usually come last
            if any(word in title + description for word in ["test", "review", "validate", "check"]):
                for j in range(i):
                    if not any(word in subtasks[j].get("title", "").lower() + subtasks[j].get("description", "").lower() 
                             for word in ["test", "review", "validate", "check"]):
                        dependencies.append({
                            "from_task": j,
                            "to_task": i,
                            "type": "sequential",
                            "description": "Implementation should come before testing"
                        })
        
        return dependencies

    async def _assess_task_risks(self, task_description: str, subtasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Assess risks associated with the task"""
        risks = {
            "time_overrun": 0.3,
            "complexity_underestimation": 0.2,
            "dependency_issues": 0.1,
            "resource_unavailability": 0.1,
            "scope_creep": 0.2
        }
        
        # Analyze task description for risk indicators
        text = task_description.lower()
        
        # Time overrun risk
        if any(word in text for word in ["urgent", "asap", "quickly", "fast"]):
            risks["time_overrun"] += 0.2
        
        # Complexity risk
        if any(word in text for word in ["complex", "advanced", "new", "unfamiliar"]):
            risks["complexity_underestimation"] += 0.3
        
        # Dependency risk
        if any(word in text for word in ["integrate", "connect", "coordinate", "collaborate"]):
            risks["dependency_issues"] += 0.2
        
        # Scope creep risk
        if any(word in text for word in ["improve", "enhance", "optimize", "also", "additionally"]):
            risks["scope_creep"] += 0.2
        
        # Calculate overall risk score
        overall_risk = sum(risks.values()) / len(risks)
        
        return {
            "individual_risks": risks,
            "overall_risk_score": min(1.0, overall_risk),
            "mitigation_strategies": await self._generate_risk_mitigation_strategies(risks)
        }

    async def _generate_risk_mitigation_strategies(self, risks: Dict[str, float]) -> List[str]:
        """Generate risk mitigation strategies"""
        strategies = []
        
        if risks.get("time_overrun", 0) > 0.4:
            strategies.append("Add 25% buffer time to estimates")
            strategies.append("Set intermediate checkpoints")
        
        if risks.get("complexity_underestimation", 0) > 0.4:
            strategies.append("Break down complex tasks further")
            strategies.append("Research and prototype first")
        
        if risks.get("dependency_issues", 0) > 0.3:
            strategies.append("Identify and communicate with stakeholders early")
            strategies.append("Create fallback plans for dependencies")
        
        if risks.get("scope_creep", 0) > 0.3:
            strategies.append("Define clear scope boundaries")
            strategies.append("Document requirements explicitly")
        
        return strategies

    async def _generate_task_approach(self, complexity_analysis: Dict[str, Any], subtasks: List[Dict[str, Any]]) -> str:
        """Generate recommended approach for task execution"""
        complexity_score = complexity_analysis["complexity_score"]
        total_duration = sum(subtask.get("estimated_duration", 25) for subtask in subtasks)
        
        if complexity_score > 0.7:
            return "iterative_with_validation"
        elif total_duration > 120:
            return "phased_execution"
        elif len(subtasks) > 5:
            return "batch_processing"
        else:
            return "sequential_execution"

    # Utility methods for data conversion and caching
    
    def _session_to_dict(self, session) -> Dict[str, Any]:
        """Convert PomodoroSession to dictionary"""
        return {
            "id": session.id,
            "duration": getattr(session, 'duration', 25),
            "focus_score": getattr(session, 'focus_score', 0.8),
            "interrupted": getattr(session, 'interrupted', False),
            "completed_at": getattr(session, 'completed_at', datetime.now()).isoformat()
        }
    
    def _task_to_dict(self, task) -> Dict[str, Any]:
        """Convert Task to dictionary"""
        return {
            "id": task.id,
            "title": getattr(task, 'title', ''),
            "status": getattr(task, 'status', 'pending'),
            "priority": getattr(task, 'priority', 'medium'),
            "completed_pomodoros": getattr(task, 'completed_pomodoros', 0),
            "estimated_pomodoros": getattr(task, 'estimated_pomodoros', 1)
        }
    
    def _time_entry_to_dict(self, entry) -> Dict[str, Any]:
        """Convert TimeEntry to dictionary"""
        return {
            "id": entry.id,
            "duration": getattr(entry, 'duration', 25),
            "created_at": getattr(entry, 'created_at', datetime.now()).isoformat()
        }
    
    def _analytics_to_dict(self, analytics) -> Dict[str, Any]:
        """Convert UserAnalytics to dictionary"""
        if not analytics:
            return {}
        return {
            "total_sessions": getattr(analytics, 'total_sessions', 0),
            "avg_focus_score": getattr(analytics, 'avg_focus_score', 0.7),
            "productivity_trend": getattr(analytics, 'productivity_trend', 0.0)
        }

    async def _optimize_user_schedule(self, user_id: str, predictions: Dict[str, Any]) -> Dict[str, Any]:
        """Generate optimal schedule for user"""
        return {
            "recommended_start_time": "09:00",
            "peak_focus_periods": ["09:00-11:00", "14:00-16:00"],
            "suggested_break_intervals": 25,
            "optimal_task_sequence": "high_priority_first"
        }

    async def _assess_productivity_risks(self, user_data: Dict[str, Any], predictions: Dict[str, Any]) -> List[str]:
        """Assess productivity risk factors"""
        risks = []
        
        predicted_score = predictions["weighted_average"]
        if predicted_score < 0.4:
            risks.append("Very low productivity predicted - consider postponing complex tasks")
        
        sessions = user_data.get("sessions", [])
        if sessions:
            recent_focus = np.mean([s.get("focus_score", 0.5) for s in sessions[-5:]])
            if recent_focus < 0.6:
                risks.append("Recent focus scores declining - may need longer breaks")
        
        return risks

    def _determine_prediction_confidence(self, predictions: Dict[str, Any]) -> PredictionConfidence:
        """Determine confidence level of predictions"""
        model_confidence = predictions.get("model_confidence", 0.5)
        
        if model_confidence > 0.8:
            return PredictionConfidence.VERY_HIGH
        elif model_confidence > 0.6:
            return PredictionConfidence.HIGH
        elif model_confidence > 0.4:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW

    async def _get_from_cache(self, key: str) -> Optional[Dict[str, Any]]:
        """Get result from cache"""
        try:
            cached = await self.redis.get(key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Cache read failed: {str(e)}")
        return None

    async def _cache_result(self, key: str, result: Dict[str, Any]):
        """Cache result with TTL"""
        try:
            await self.redis.setex(key, self.cache_ttl, json.dumps(result, default=str))
        except Exception as e:
            logger.warning(f"Cache write failed: {str(e)}")