/**
 * Universal Activity Tracker for FocusFlow
 * Implements automated activity monitoring and AI-powered classification
 */

interface ActivityData {
    timestamp: number;
    activeWindow: string;
    applicationUsage: Record<string, number>;
    keyboardActivity: number;
    mouseActivity: number;
    productivityScore: number;
    category: 'DEEP_WORK' | 'PRODUCTIVE' | 'ADMINISTRATIVE' | 'NEUTRAL' | 'DISTRACTING';
}

interface UserPatterns {
    timeBasedTasks: Record<number, TaskPattern[]>;
    projectPatterns: ProjectPattern[];
    priorityPatterns: PriorityPattern[];
    durationPatterns: DurationPattern[];
    contextPatterns: ContextPattern[];
    seasonalPatterns: SeasonalPattern[];
}

interface TaskPattern {
    type: string;
    frequency: number;
    avgDuration: number;
    avgPriority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    commonProject: string;
    commonTags: string[];
    dayOfWeek: number;
}

interface ProjectPattern {
    name: string;
    optimalTimes: number[];
    averageSessionLength: number;
    productivityScore: number;
}

interface PriorityPattern {
    priority: string;
    preferredTimes: number[];
    completionRate: number;
}

interface DurationPattern {
    taskType: string;
    averageDuration: number;
    accuracy: number;
}

interface ContextPattern {
    context: string;
    productivityMultiplier: number;
    preferredActivities: string[];
}

interface SeasonalPattern {
    period: string;
    productivityTrend: number;
    preferredTaskTypes: string[];
}

interface UserContext {
    currentTime: Date;
    recentTasks: any[];
    currentProject: string;
    energyLevel: number;
    environmentScore: number;
    upcomingDeadlines: any[];
}

interface HistoricalData {
    tasks: Task[];
    sessions: Session[];
    timeEntries: TimeEntry[];
}

interface Task {
    id: string;
    title: string;
    project: string;
    priority: string;
    duration: number;
    completedAt: Date;
    tags: string[];
}

interface Session {
    duration: number;
    focusScore: number;
    startTime: Date;
    endTime: Date;
    taskId: string;
}

interface TimeEntry {
    activity: string;
    duration: number;
    timestamp: Date;
    productivityScore: number;
}

class UniversalActivityTracker {
    private trackingInterval: number = 30000; // 30 seconds
    private isTracking: boolean = false;
    private activityBuffer: ActivityData[] = [];
    private aiClassifier: AIActivityClassifier;
    private patternAnalyzer: PatternAnalyzer;
    
    constructor() {
        this.aiClassifier = new AIActivityClassifier();
        this.patternAnalyzer = new PatternAnalyzer();
    }
    
    async startTracking(userId: string): Promise<void> {
        // Request comprehensive permissions
        const permissions = await this.requestPermissions();
        if (!permissions.granted) {
            throw new Error('Tracking permissions required for full automation');
        }
        
        this.isTracking = true;
        this.trackingLoop(userId);
    }
    
    stopTracking(): void {
        this.isTracking = false;
    }
    
    private async trackingLoop(userId: string): Promise<void> {
        while (this.isTracking) {
            try {
                const activityData = await this.collectActivitySnapshot();
                const classifiedActivity = await this.aiClassifier.classify(activityData);
                
                this.activityBuffer.push(classifiedActivity);
                
                // Process predictions every 5 minutes
                if (this.activityBuffer.length >= 10) {
                    await this.processPredictions(userId, this.activityBuffer);
                    this.activityBuffer = [];
                }
                
                // Real-time optimizations
                await this.performRealtimeOptimizations(classifiedActivity);
                
            } catch (error) {
                console.error('Tracking error:', error);
            }
            
            await this.sleep(this.trackingInterval);
        }
    }
    
    private async collectActivitySnapshot(): Promise<ActivityData> {
        const snapshot: ActivityData = {
            timestamp: Date.now(),
            activeWindow: await this.getCurrentActiveWindow(),
            applicationUsage: await this.getApplicationUsage(),
            keyboardActivity: await this.getKeystrokeRate(),
            mouseActivity: await this.getMouseActivity(),
            productivityScore: 0,
            category: 'NEUTRAL'
        };
        
        return snapshot;
    }
    
    private async getCurrentActiveWindow(): Promise<string> {
        // For PWA - use Page Visibility API and focus detection
        if (typeof document !== 'undefined' && document.hasFocus()) {
            return `${document.title} - ${window.location.hostname}`;
        }
        return 'Unknown Application';
    }
    
    private async getApplicationUsage(): Promise<Record<string, number>> {
        // Simulate application usage tracking
        // In real implementation, would integrate with system APIs
        return {
            'browser': Date.now() - (Math.random() * 3600000), // Random usage time
            'code_editor': Math.random() * 1800000,
            'email': Math.random() * 600000
        };
    }
    
    private async getKeystrokeRate(): Promise<number> {
        // Simulate keystroke activity (keys per minute)
        return Math.random() * 100;
    }
    
    private async getMouseActivity(): Promise<number> {
        // Simulate mouse activity (movements per minute)
        return Math.random() * 200;
    }
    
    private async performRealtimeOptimizations(activity: ActivityData): Promise<void> {
        // Auto-adjust environment based on activity
        if (activity.category === 'DEEP_WORK' && activity.productivityScore > 0.8) {
            await this.optimizeEnvironmentForDeepWork();
        }
        
        // Auto-suggest breaks if distraction detected
        if (activity.category === 'DISTRACTING' && this.getConsecutiveDistractionTime() > 300000) { // 5 minutes
            await this.suggestBreakOrRefocus();
        }
        
        // Auto-create tasks from productive patterns
        if (activity.category === 'PRODUCTIVE') {
            await this.detectPotentialTasks(activity);
        }
    }
    
    private async optimizeEnvironmentForDeepWork(): Promise<void> {
        console.log('🎯 Optimizing environment for deep work');
        // Trigger environment controller to optimize for deep work
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('optimize-environment', {
                detail: { mode: 'DEEP_WORK' }
            }));
        }
    }
    
    private getConsecutiveDistractionTime(): number {
        const recentActivities = this.activityBuffer.slice(-10);
        let consecutiveDistractionTime = 0;
        
        for (let i = recentActivities.length - 1; i >= 0; i--) {
            if (recentActivities[i].category === 'DISTRACTING') {
                consecutiveDistractionTime += this.trackingInterval;
            } else {
                break;
            }
        }
        
        return consecutiveDistractionTime;
    }
    
    private async suggestBreakOrRefocus(): Promise<void> {
        console.log('⚠️ Distraction detected - suggesting break or refocus');
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('suggest-break', {
                detail: { reason: 'distraction_detected' }
            }));
        }
    }
    
    private async detectPotentialTasks(activity: ActivityData): Promise<void> {
        // Analyze current activity for potential task creation
        const taskPotential = await this.analyzeTaskPotential(activity);
        
        if (taskPotential.confidence > 0.7) {
            if (typeof window !== 'undefined') {
                window.dispatchEvent(new CustomEvent('potential-task-detected', {
                    detail: taskPotential
                }));
            }
        }
    }
    
    private async analyzeTaskPotential(activity: ActivityData): Promise<any> {
        // Simple heuristic for task detection
        const isProductiveWindow = activity.productivityScore > 0.6;
        const hasHighActivity = activity.keyboardActivity > 50;
        
        if (isProductiveWindow && hasHighActivity) {
            return {
                confidence: 0.8,
                suggestedTitle: `Work on ${activity.activeWindow}`,
                estimatedDuration: 25, // Standard pomodoro
                category: activity.category
            };
        }
        
        return { confidence: 0.1 };
    }
    
    private async processPredictions(userId: string, activities: ActivityData[]): Promise<void> {
        const patterns = await this.patternAnalyzer.analyzePatterns(activities);
        
        // Store patterns for future predictions
        await this.storeUserPatterns(userId, patterns);
        
        // Generate insights
        const insights = await this.generateInsights(patterns);
        console.log('📊 Generated insights:', insights);
    }
    
    private async storeUserPatterns(userId: string, patterns: any): Promise<void> {
        // Store in local storage or send to backend
        if (typeof localStorage !== 'undefined') {
            localStorage.setItem(`user_patterns_${userId}`, JSON.stringify(patterns));
        }
    }
    
    private async generateInsights(patterns: any): Promise<string[]> {
        const insights = [];
        
        if (patterns.avgProductivity < 0.5) {
            insights.push('Your productivity has been low recently. Consider taking longer breaks.');
        }
        
        if (patterns.mostProductiveTime) {
            insights.push(`You're most productive at ${patterns.mostProductiveTime}. Schedule important tasks then.`);
        }
        
        return insights;
    }
    
    private async requestPermissions(): Promise<{ granted: boolean }> {
        // Request necessary permissions for activity tracking
        try {
            // Request notification permission
            if (typeof window !== 'undefined' && 'Notification' in window) {
                await Notification.requestPermission();
            }
            
            // For now, always grant permissions in demo
            return { granted: true };
        } catch (error) {
            console.error('Permission request failed:', error);
            return { granted: false };
        }
    }
    
    private sleep(ms: number): Promise<void> {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

class AIActivityClassifier {
    private classificationCache: Map<string, any> = new Map();
    
    async classify(activity: ActivityData): Promise<ActivityData> {
        const cacheKey = this.generateCacheKey(activity);
        
        if (this.classificationCache.has(cacheKey)) {
            return { ...activity, ...this.classificationCache.get(cacheKey) };
        }
        
        try {
            const classification = await this.classifyWithAI(activity);
            this.classificationCache.set(cacheKey, classification);
            return { ...activity, ...classification };
        } catch (error) {
            // Fallback to rule-based classification
            return { ...activity, ...this.fallbackClassification(activity) };
        }
    }
    
    private generateCacheKey(activity: ActivityData): string {
        return `${activity.activeWindow}_${Math.floor(activity.keyboardActivity / 10)}_${Math.floor(activity.mouseActivity / 10)}`;
    }
    
    private async classifyWithAI(activity: ActivityData): Promise<Partial<ActivityData>> {
        // In a real implementation, this would call an AI service
        // For now, use rule-based classification
        return this.fallbackClassification(activity);
    }
    
    private fallbackClassification(activity: ActivityData): Partial<ActivityData> {
        const productivityKeywords = ['github', 'stackoverflow', 'docs', 'code', 'work', 'project', 'task'];
        const distractingKeywords = ['youtube', 'facebook', 'twitter', 'instagram', 'reddit', 'news'];
        const deepWorkKeywords = ['code', 'editor', 'ide', 'development', 'programming'];
        
        const activeWindow = activity.activeWindow.toLowerCase();
        
        let category: ActivityData['category'] = 'NEUTRAL';
        let productivityScore = 0.5;
        let focusIntensity = 0.5;
        
        // Classify based on window content and activity levels
        if (deepWorkKeywords.some(keyword => activeWindow.includes(keyword)) && activity.keyboardActivity > 60) {
            category = 'DEEP_WORK';
            productivityScore = 0.9;
            focusIntensity = 0.9;
        } else if (productivityKeywords.some(keyword => activeWindow.includes(keyword))) {
            category = 'PRODUCTIVE';
            productivityScore = 0.7;
            focusIntensity = 0.7;
        } else if (distractingKeywords.some(keyword => activeWindow.includes(keyword))) {
            category = 'DISTRACTING';
            productivityScore = 0.2;
            focusIntensity = 0.3;
        } else if (activity.keyboardActivity < 10 && activity.mouseActivity < 20) {
            category = 'NEUTRAL';
            productivityScore = 0.4;
            focusIntensity = 0.2;
        } else {
            category = 'ADMINISTRATIVE';
            productivityScore = 0.6;
            focusIntensity = 0.5;
        }
        
        return {
            category,
            productivityScore,
            focusIntensity
        };
    }
}

class PatternAnalyzer {
    async analyzePatterns(activities: ActivityData[]): Promise<any> {
        if (activities.length === 0) return {};
        
        const avgProductivity = activities.reduce((sum, a) => sum + a.productivityScore, 0) / activities.length;
        const categoryDistribution = this.getCategoryDistribution(activities);
        const mostProductiveTime = this.findMostProductiveTime(activities);
        
        return {
            avgProductivity,
            categoryDistribution,
            mostProductiveTime,
            totalActivities: activities.length,
            timespan: activities[activities.length - 1].timestamp - activities[0].timestamp
        };
    }
    
    private getCategoryDistribution(activities: ActivityData[]): Record<string, number> {
        const distribution: Record<string, number> = {};
        
        activities.forEach(activity => {
            distribution[activity.category] = (distribution[activity.category] || 0) + 1;
        });
        
        // Convert to percentages
        const total = activities.length;
        Object.keys(distribution).forEach(key => {
            distribution[key] = distribution[key] / total;
        });
        
        return distribution;
    }
    
    private findMostProductiveTime(activities: ActivityData[]): string | null {
        const hourlyProductivity: Record<number, number[]> = {};
        
        activities.forEach(activity => {
            const hour = new Date(activity.timestamp).getHours();
            if (!hourlyProductivity[hour]) {
                hourlyProductivity[hour] = [];
            }
            hourlyProductivity[hour].push(activity.productivityScore);
        });
        
        let bestHour = -1;
        let bestScore = 0;
        
        Object.keys(hourlyProductivity).forEach(hour => {
            const scores = hourlyProductivity[parseInt(hour)];
            const avgScore = scores.reduce((sum, score) => sum + score, 0) / scores.length;
            
            if (avgScore > bestScore) {
                bestScore = avgScore;
                bestHour = parseInt(hour);
            }
        });
        
        return bestHour >= 0 ? `${bestHour}:00` : null;
    }
}

// Export classes for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        UniversalActivityTracker,
        AIActivityClassifier,
        PatternAnalyzer
    };
}

// Global instance for browser usage
if (typeof window !== 'undefined') {
    (window as any).UniversalActivityTracker = UniversalActivityTracker;
    (window as any).AIActivityClassifier = AIActivityClassifier;
    (window as any).PatternAnalyzer = PatternAnalyzer;
}