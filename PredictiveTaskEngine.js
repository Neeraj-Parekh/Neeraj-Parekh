/**
 * Predictive Task Generation Engine for FocusFlow
 * Implements autonomous task creation based on user patterns and AI predictions
 */

interface TaskPrediction {
    title: string;
    description: string;
    priority: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    estimatedDuration: number;
    confidence: number;
    reasoning: string;
    suggestedTime: Date;
    project: string;
    tags: string[];
    subtasks?: string[];
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
    workingHours: { start: number; end: number };
    preferences: {
        breakFrequency: number;
        preferredTaskLength: number;
        focusTimePreference: number[];
    };
}

interface HistoricalData {
    tasks: Task[];
    sessions: Session[];
    timeEntries: TimeEntry[];
}

interface Task {
    id: string;
    title: string;
    description: string;
    project: string;
    priority: string;
    duration: number;
    completedAt: Date;
    tags: string[];
    source: string;
    confidence?: number;
    userId: string;
    status: string;
    estimatedPomodoros: number;
    dueDate?: Date;
    createdAt: Date;
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

class PredictiveTaskEngine {
    private patternAnalyzer: PatternAnalyzer;
    private aiTaskGenerator: AITaskGenerator;
    
    constructor() {
        this.patternAnalyzer = new PatternAnalyzer();
        this.aiTaskGenerator = new AITaskGenerator();
    }
    
    async generatePredictedTasks(userId: string, horizon: number = 24): Promise<TaskPrediction[]> {
        // Analyze user patterns
        const patterns = await this.patternAnalyzer.analyzeUserPatterns(userId);
        
        // Get current context
        const context = await this.getCurrentContext(userId);
        
        // Generate predictions using multiple strategies
        const predictions = await Promise.all([
            this.generateTimeBasedPredictions(patterns, context, horizon),
            this.generatePatternBasedPredictions(patterns, context),
            this.generateContextBasedPredictions(context),
            this.generateAIPoweredPredictions(patterns, context)
        ]);
        
        // Combine and rank predictions
        const allPredictions = predictions.flat();
        const rankedPredictions = this.rankPredictions(allPredictions);
        
        // Auto-create high-confidence predictions
        await this.autoCreateHighConfidenceTasks(userId, rankedPredictions);
        
        return rankedPredictions.slice(0, 10); // Top 10
    }
    
    private async generateTimeBasedPredictions(
        patterns: UserPatterns, 
        context: UserContext, 
        horizon: number
    ): Promise<TaskPrediction[]> {
        const predictions: TaskPrediction[] = [];
        const now = new Date();
        
        // Check each hour in the prediction horizon
        for (let hour = 0; hour < horizon; hour++) {
            const targetTime = new Date(now.getTime() + (hour * 60 * 60 * 1000));
            const hourOfDay = targetTime.getHours();
            const dayOfWeek = targetTime.getDay();
            
            // Check if user typically does specific tasks at this time
            const historicalTasks = patterns.timeBasedTasks[hourOfDay] || [];
            
            for (const taskPattern of historicalTasks) {
                if (taskPattern.frequency > 0.6 && taskPattern.dayOfWeek === dayOfWeek) {
                    predictions.push({
                        title: this.generateTaskTitle(taskPattern),
                        description: `Predicted based on your typical ${this.formatTime(hourOfDay)} routine`,
                        priority: taskPattern.avgPriority,
                        estimatedDuration: taskPattern.avgDuration,
                        confidence: taskPattern.frequency,
                        reasoning: `You typically do this type of task on ${this.getDayName(dayOfWeek)} at ${this.formatTime(hourOfDay)}`,
                        suggestedTime: targetTime,
                        project: taskPattern.commonProject,
                        tags: taskPattern.commonTags
                    });
                }
            }
        }
        
        return predictions;
    }
    
    private async generatePatternBasedPredictions(
        patterns: UserPatterns, 
        context: UserContext
    ): Promise<TaskPrediction[]> {
        const predictions: TaskPrediction[] = [];
        
        // Analyze project patterns
        for (const projectPattern of patterns.projectPatterns) {
            const currentHour = context.currentTime.getHours();
            
            if (projectPattern.optimalTimes.includes(currentHour)) {
                predictions.push({
                    title: `Continue work on ${projectPattern.name}`,
                    description: `Based on your productivity patterns, now is an optimal time for ${projectPattern.name} work`,
                    priority: 'MEDIUM',
                    estimatedDuration: projectPattern.averageSessionLength,
                    confidence: projectPattern.productivityScore,
                    reasoning: `Your productivity score for ${projectPattern.name} is highest at this time`,
                    suggestedTime: context.currentTime,
                    project: projectPattern.name,
                    tags: ['pattern-based', 'optimal-time']
                });
            }
        }
        
        // Check for break patterns
        if (this.shouldSuggestBreak(context, patterns)) {
            predictions.push({
                title: 'Take a productive break',
                description: 'Based on your patterns, a break now will improve your next focus session',
                priority: 'MEDIUM',
                estimatedDuration: 15,
                confidence: 0.8,
                reasoning: 'Your productivity typically improves after breaks at this time',
                suggestedTime: context.currentTime,
                project: 'Personal',
                tags: ['break', 'wellness']
            });
        }
        
        return predictions;
    }
    
    private async generateContextBasedPredictions(context: UserContext): Promise<TaskPrediction[]> {
        const predictions: TaskPrediction[] = [];
        
        // High energy suggestions
        if (context.energyLevel > 0.7) {
            predictions.push({
                title: 'Tackle a challenging task',
                description: 'Your energy level is high - perfect time for complex work',
                priority: 'HIGH',
                estimatedDuration: 50,
                confidence: 0.75,
                reasoning: 'High energy level detected, optimal for difficult tasks',
                suggestedTime: context.currentTime,
                project: context.currentProject,
                tags: ['high-energy', 'challenging']
            });
        }
        
        // Low energy suggestions
        if (context.energyLevel < 0.4) {
            predictions.push({
                title: 'Handle routine administrative tasks',
                description: 'Energy is low - good time for simple, repetitive tasks',
                priority: 'LOW',
                estimatedDuration: 25,
                confidence: 0.65,
                reasoning: 'Low energy level, administrative tasks are manageable',
                suggestedTime: context.currentTime,
                project: 'Admin',
                tags: ['low-energy', 'routine']
            });
        }
        
        // Deadline-based predictions
        for (const deadline of context.upcomingDeadlines) {
            const timeUntilDeadline = deadline.dueDate.getTime() - context.currentTime.getTime();
            const urgency = this.calculateUrgency(timeUntilDeadline);
            
            if (urgency > 0.5) {
                predictions.push({
                    title: `Work on ${deadline.title}`,
                    description: `Deadline approaching - ${this.formatTimeUntil(timeUntilDeadline)} remaining`,
                    priority: urgency > 0.8 ? 'CRITICAL' : 'HIGH',
                    estimatedDuration: Math.min(deadline.estimatedTime, 90),
                    confidence: urgency,
                    reasoning: `Deadline in ${this.formatTimeUntil(timeUntilDeadline)}`,
                    suggestedTime: context.currentTime,
                    project: deadline.project,
                    tags: ['deadline', 'urgent']
                });
            }
        }
        
        return predictions;
    }
    
    private async generateAIPoweredPredictions(
        patterns: UserPatterns, 
        context: UserContext
    ): Promise<TaskPrediction[]> {
        const aiPrompt = `
        Based on this user's productivity patterns and current context, predict tasks they should work on:
        
        Patterns: ${JSON.stringify(patterns, null, 2)}
        Context: ${JSON.stringify(context, null, 2)}
        
        Generate 5 specific, actionable tasks with:
        - Clear titles
        - Realistic time estimates
        - Appropriate priorities
        - Reasoning for each prediction
        
        Consider:
        - User's work schedule and habits
        - Current projects and deadlines
        - Productivity patterns
        - Seasonal/temporal factors
        
        Return as JSON array of TaskPrediction objects.
        `;
        
        try {
            const aiPredictions = await this.aiTaskGenerator.generate(aiPrompt);
            return aiPredictions;
        } catch (error) {
            console.error('AI task generation failed:', error);
            return [];
        }
    }
    
    private rankPredictions(predictions: TaskPrediction[]): TaskPrediction[] {
        return predictions.sort((a, b) => {
            // Prioritize by confidence, urgency, and timeliness
            const scoreA = this.calculatePredictionScore(a);
            const scoreB = this.calculatePredictionScore(b);
            
            return scoreB - scoreA;
        });
    }
    
    private calculatePredictionScore(prediction: TaskPrediction): number {
        let score = prediction.confidence * 0.4; // Base confidence weight
        
        // Priority boost
        const priorityWeights = { 'CRITICAL': 0.4, 'HIGH': 0.3, 'MEDIUM': 0.2, 'LOW': 0.1 };
        score += priorityWeights[prediction.priority] || 0.1;
        
        // Time relevance (prefer tasks suggested for soon)
        const timeUntilSuggested = prediction.suggestedTime.getTime() - Date.now();
        const timeRelevance = Math.max(0, 1 - (timeUntilSuggested / (4 * 60 * 60 * 1000))); // 4 hour window
        score += timeRelevance * 0.2;
        
        // Duration preference (medium length tasks preferred)
        const durationScore = 1 - Math.abs(prediction.estimatedDuration - 35) / 100;
        score += Math.max(0, durationScore) * 0.1;
        
        return score;
    }
    
    private async autoCreateHighConfidenceTasks(
        userId: string, 
        predictions: TaskPrediction[]
    ): Promise<void> {
        const highConfidenceTasks = predictions.filter(p => 
            p.confidence > 0.85 && 
            p.priority !== 'LOW'
        );
        
        for (const prediction of highConfidenceTasks) {
            try {
                // Create task in database
                await this.createPredictedTask(userId, prediction);
                
                // Notify user about auto-created task
                await this.notifyTaskCreated(userId, prediction);
                
            } catch (error) {
                console.error('Failed to auto-create task:', error);
            }
        }
    }
    
    private async createPredictedTask(userId: string, prediction: TaskPrediction): Promise<void> {
        const taskData: Task = {
            id: this.generateTaskId(),
            title: prediction.title,
            description: `${prediction.description}\n\nAI Reasoning: ${prediction.reasoning}`,
            project: prediction.project,
            priority: prediction.priority,
            estimatedPomodoros: Math.ceil(prediction.estimatedDuration / 25),
            dueDate: prediction.suggestedTime,
            tags: [...prediction.tags, 'ai-generated'],
            source: 'ai_prediction',
            confidence: prediction.confidence,
            status: 'pending',
            createdAt: new Date(),
            userId: userId,
            duration: prediction.estimatedDuration
        };
        
        // Save to storage
        await this.saveTask(taskData);
    }
    
    private async saveTask(task: Task): Promise<void> {
        // Save to local storage or send to backend
        if (typeof localStorage !== 'undefined') {
            const existingTasks = JSON.parse(localStorage.getItem('predicted_tasks') || '[]');
            existingTasks.push(task);
            localStorage.setItem('predicted_tasks', JSON.stringify(existingTasks));
        }
        
        console.log('✨ Auto-created task:', task.title);
    }
    
    private async notifyTaskCreated(userId: string, prediction: TaskPrediction): Promise<void> {
        if (typeof window !== 'undefined' && 'Notification' in window) {
            if (Notification.permission === 'granted') {
                new Notification('New Task Created', {
                    body: `AI suggested: ${prediction.title}`,
                    icon: '/icons/task-icon.png'
                });
            }
        }
        
        // Also dispatch custom event
        if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('task-auto-created', {
                detail: { task: prediction, userId }
            }));
        }
    }
    
    private async getCurrentContext(userId: string): Promise<UserContext> {
        // Get current context from various sources
        const now = new Date();
        
        // Mock context for demo - in real app, this would come from actual data
        return {
            currentTime: now,
            recentTasks: await this.getRecentTasks(userId),
            currentProject: await this.getCurrentProject(userId),
            energyLevel: await this.estimateEnergyLevel(userId),
            environmentScore: await this.getEnvironmentScore(),
            upcomingDeadlines: await this.getUpcomingDeadlines(userId),
            workingHours: { start: 9, end: 17 },
            preferences: {
                breakFrequency: 4, // Every 4 pomodoros
                preferredTaskLength: 25,
                focusTimePreference: [9, 10, 14, 15] // Preferred hours
            }
        };
    }
    
    private async getRecentTasks(userId: string): Promise<any[]> {
        // Mock implementation
        return [
            { title: 'Review code', project: 'Development', completed: true },
            { title: 'Update documentation', project: 'Development', completed: false }
        ];
    }
    
    private async getCurrentProject(userId: string): Promise<string> {
        // Mock implementation
        return 'FocusFlow Development';
    }
    
    private async estimateEnergyLevel(userId: string): Promise<number> {
        // Simple time-based energy estimation
        const hour = new Date().getHours();
        
        if (hour >= 9 && hour <= 11) return 0.9; // Morning peak
        if (hour >= 14 && hour <= 16) return 0.8; // Afternoon peak
        if (hour >= 19 || hour <= 7) return 0.3; // Low energy
        
        return 0.6; // Default
    }
    
    private async getEnvironmentScore(): Promise<number> {
        // Mock implementation - could integrate with environment sensors
        return 0.75;
    }
    
    private async getUpcomingDeadlines(userId: string): Promise<any[]> {
        // Mock implementation
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        
        return [
            {
                title: 'Complete project milestone',
                dueDate: tomorrow,
                project: 'FocusFlow Development',
                estimatedTime: 120
            }
        ];
    }
    
    private generateTaskTitle(pattern: TaskPattern): string {
        const templates = [
            `Work on ${pattern.type}`,
            `Continue ${pattern.type} tasks`,
            `Focus on ${pattern.type}`,
            `${pattern.type} session`
        ];
        
        return templates[Math.floor(Math.random() * templates.length)];
    }
    
    private formatTime(hour: number): string {
        const period = hour >= 12 ? 'PM' : 'AM';
        const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour;
        return `${displayHour}:00 ${period}`;
    }
    
    private getDayName(dayOfWeek: number): string {
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        return days[dayOfWeek];
    }
    
    private shouldSuggestBreak(context: UserContext, patterns: UserPatterns): boolean {
        // Simple heuristic for break suggestion
        const hour = context.currentTime.getHours();
        const workingHours = hour >= context.workingHours.start && hour <= context.workingHours.end;
        
        // Suggest break if it's working hours and user typically takes breaks
        return workingHours && (hour % context.preferences.breakFrequency === 0);
    }
    
    private calculateUrgency(timeUntilDeadline: number): number {
        const hoursUntilDeadline = timeUntilDeadline / (1000 * 60 * 60);
        
        if (hoursUntilDeadline <= 6) return 1.0; // Critical
        if (hoursUntilDeadline <= 24) return 0.8; // High
        if (hoursUntilDeadline <= 72) return 0.6; // Medium
        
        return 0.3; // Low urgency
    }
    
    private formatTimeUntil(milliseconds: number): string {
        const hours = Math.floor(milliseconds / (1000 * 60 * 60));
        const days = Math.floor(hours / 24);
        
        if (days > 0) return `${days} day${days > 1 ? 's' : ''}`;
        if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
        
        return 'less than an hour';
    }
    
    private generateTaskId(): string {
        return `task_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

class PatternAnalyzer {
    async analyzeUserPatterns(userId: string): Promise<UserPatterns> {
        const historicalData = await this.getHistoricalData(userId, 90); // 90 days
        
        return {
            timeBasedTasks: this.analyzeTimePatterns(historicalData),
            projectPatterns: this.analyzeProjectPatterns(historicalData),
            priorityPatterns: this.analyzePriorityPatterns(historicalData),
            durationPatterns: this.analyzeDurationPatterns(historicalData),
            contextPatterns: this.analyzeContextPatterns(historicalData),
            seasonalPatterns: this.analyzeSeasonalPatterns(historicalData)
        };
    }
    
    private async getHistoricalData(userId: string, days: number): Promise<HistoricalData> {
        // Mock implementation - in real app, fetch from database
        return {
            tasks: this.generateMockTasks(),
            sessions: this.generateMockSessions(),
            timeEntries: this.generateMockTimeEntries()
        };
    }
    
    private generateMockTasks(): Task[] {
        // Generate sample historical tasks for pattern analysis
        const projects = ['Development', 'Design', 'Research', 'Admin'];
        const priorities = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
        const tasks: Task[] = [];
        
        for (let i = 0; i < 50; i++) {
            const daysAgo = Math.floor(Math.random() * 90);
            const date = new Date();
            date.setDate(date.getDate() - daysAgo);
            
            tasks.push({
                id: `task_${i}`,
                title: `Sample task ${i}`,
                description: `Description for task ${i}`,
                project: projects[Math.floor(Math.random() * projects.length)],
                priority: priorities[Math.floor(Math.random() * priorities.length)] as any,
                duration: Math.floor(Math.random() * 120) + 15,
                completedAt: date,
                tags: ['mock', 'historical'],
                source: 'manual',
                userId: 'demo_user',
                status: 'completed',
                estimatedPomodoros: Math.ceil((Math.floor(Math.random() * 120) + 15) / 25),
                createdAt: new Date(date.getTime() - (24 * 60 * 60 * 1000))
            });
        }
        
        return tasks;
    }
    
    private generateMockSessions(): Session[] {
        const sessions: Session[] = [];
        
        for (let i = 0; i < 100; i++) {
            const startTime = new Date();
            startTime.setHours(startTime.getHours() - Math.floor(Math.random() * 720)); // Last 30 days
            
            const duration = Math.floor(Math.random() * 60) + 15;
            const endTime = new Date(startTime.getTime() + (duration * 60 * 1000));
            
            sessions.push({
                duration,
                focusScore: Math.random(),
                startTime,
                endTime,
                taskId: `task_${Math.floor(Math.random() * 50)}`
            });
        }
        
        return sessions;
    }
    
    private generateMockTimeEntries(): TimeEntry[] {
        const activities = ['coding', 'meetings', 'email', 'research', 'planning'];
        const entries: TimeEntry[] = [];
        
        for (let i = 0; i < 200; i++) {
            const timestamp = new Date();
            timestamp.setHours(timestamp.getHours() - Math.floor(Math.random() * 720));
            
            entries.push({
                activity: activities[Math.floor(Math.random() * activities.length)],
                duration: Math.floor(Math.random() * 120) + 5,
                timestamp,
                productivityScore: Math.random()
            });
        }
        
        return entries;
    }
    
    private analyzeTimePatterns(data: HistoricalData): Record<number, TaskPattern[]> {
        const patterns: Record<number, TaskPattern[]> = {};
        
        // Group tasks by hour of day
        for (let hour = 0; hour < 24; hour++) {
            const hourTasks = data.tasks.filter(task => 
                new Date(task.completedAt).getHours() === hour
            );
            
            if (hourTasks.length > 0) {
                patterns[hour] = this.extractTaskPatterns(hourTasks);
            }
        }
        
        return patterns;
    }
    
    private analyzeProjectPatterns(data: HistoricalData): ProjectPattern[] {
        const projectGroups = this.groupTasksByProject(data.tasks);
        const patterns: ProjectPattern[] = [];
        
        Object.keys(projectGroups).forEach(projectName => {
            const projectTasks = projectGroups[projectName];
            const optimalTimes = this.findOptimalTimesForProject(projectTasks);
            const avgSessionLength = this.calculateAverageSessionLength(projectTasks);
            const productivityScore = this.calculateProjectProductivityScore(projectTasks, data.sessions);
            
            patterns.push({
                name: projectName,
                optimalTimes,
                averageSessionLength,
                productivityScore
            });
        });
        
        return patterns;
    }
    
    private analyzePriorityPatterns(data: HistoricalData): PriorityPattern[] {
        const priorityGroups = this.groupTasksByPriority(data.tasks);
        const patterns: PriorityPattern[] = [];
        
        Object.keys(priorityGroups).forEach(priority => {
            const priorityTasks = priorityGroups[priority];
            const preferredTimes = this.findPreferredTimesForPriority(priorityTasks);
            const completionRate = this.calculateCompletionRate(priorityTasks);
            
            patterns.push({
                priority,
                preferredTimes,
                completionRate
            });
        });
        
        return patterns;
    }
    
    private analyzeDurationPatterns(data: HistoricalData): DurationPattern[] {
        // Analyze how accurate duration estimates are by task type
        const taskTypes = this.extractTaskTypes(data.tasks);
        const patterns: DurationPattern[] = [];
        
        taskTypes.forEach(taskType => {
            const typeTasks = data.tasks.filter(task => 
                task.title.toLowerCase().includes(taskType.toLowerCase())
            );
            
            if (typeTasks.length > 2) {
                const avgDuration = typeTasks.reduce((sum, task) => sum + task.duration, 0) / typeTasks.length;
                const accuracy = this.calculateDurationAccuracy(typeTasks);
                
                patterns.push({
                    taskType,
                    averageDuration: avgDuration,
                    accuracy
                });
            }
        });
        
        return patterns;
    }
    
    private analyzeContextPatterns(data: HistoricalData): ContextPattern[] {
        // Mock context patterns - in real app, analyze environmental/contextual factors
        return [
            {
                context: 'morning',
                productivityMultiplier: 1.2,
                preferredActivities: ['coding', 'planning']
            },
            {
                context: 'afternoon',
                productivityMultiplier: 0.9,
                preferredActivities: ['meetings', 'admin']
            }
        ];
    }
    
    private analyzeSeasonalPatterns(data: HistoricalData): SeasonalPattern[] {
        // Mock seasonal patterns
        return [
            {
                period: 'weekday',
                productivityTrend: 1.1,
                preferredTaskTypes: ['development', 'meetings']
            },
            {
                period: 'weekend',
                productivityTrend: 0.8,
                preferredTaskTypes: ['learning', 'planning']
            }
        ];
    }
    
    private extractTaskPatterns(tasks: Task[]): TaskPattern[] {
        // Group similar tasks and extract patterns
        const taskGroups = this.groupSimilarTasks(tasks);
        
        return taskGroups.map(group => ({
            type: group.type,
            frequency: group.tasks.length / tasks.length,
            avgDuration: this.calculateAverage(group.tasks.map(t => t.duration)),
            avgPriority: this.calculateMostCommonPriority(group.tasks),
            commonProject: this.calculateMostCommonProject(group.tasks),
            commonTags: this.calculateMostCommonTags(group.tasks),
            dayOfWeek: this.calculateMostCommonDay(group.tasks)
        }));
    }
    
    private groupSimilarTasks(tasks: Task[]): { type: string; tasks: Task[] }[] {
        // Simple grouping by project and priority
        const groups: Record<string, Task[]> = {};
        
        tasks.forEach(task => {
            const key = `${task.project}_${task.priority}`;
            if (!groups[key]) {
                groups[key] = [];
            }
            groups[key].push(task);
        });
        
        return Object.keys(groups).map(key => ({
            type: key,
            tasks: groups[key]
        }));
    }
    
    private groupTasksByProject(tasks: Task[]): Record<string, Task[]> {
        return tasks.reduce((groups, task) => {
            if (!groups[task.project]) {
                groups[task.project] = [];
            }
            groups[task.project].push(task);
            return groups;
        }, {} as Record<string, Task[]>);
    }
    
    private groupTasksByPriority(tasks: Task[]): Record<string, Task[]> {
        return tasks.reduce((groups, task) => {
            if (!groups[task.priority]) {
                groups[task.priority] = [];
            }
            groups[task.priority].push(task);
            return groups;
        }, {} as Record<string, Task[]>);
    }
    
    private extractTaskTypes(tasks: Task[]): string[] {
        const types = new Set<string>();
        
        tasks.forEach(task => {
            // Extract type from title (simple keyword extraction)
            const words = task.title.toLowerCase().split(' ');
            const keywords = ['code', 'review', 'design', 'meeting', 'research', 'plan', 'admin'];
            
            words.forEach(word => {
                if (keywords.includes(word)) {
                    types.add(word);
                }
            });
        });
        
        return Array.from(types);
    }
    
    private findOptimalTimesForProject(tasks: Task[]): number[] {
        const hourCounts: Record<number, number> = {};
        
        tasks.forEach(task => {
            const hour = new Date(task.completedAt).getHours();
            hourCounts[hour] = (hourCounts[hour] || 0) + 1;
        });
        
        // Return hours with above-average activity
        const avgCount = Object.values(hourCounts).reduce((sum, count) => sum + count, 0) / 24;
        return Object.keys(hourCounts)
            .map(Number)
            .filter(hour => hourCounts[hour] > avgCount);
    }
    
    private calculateAverageSessionLength(tasks: Task[]): number {
        return tasks.reduce((sum, task) => sum + task.duration, 0) / tasks.length;
    }
    
    private calculateProjectProductivityScore(tasks: Task[], sessions: Session[]): number {
        // Mock calculation - in real app, correlate task completion with focus scores
        return Math.random() * 0.4 + 0.6; // Random score between 0.6-1.0
    }
    
    private findPreferredTimesForPriority(tasks: Task[]): number[] {
        // Similar to optimal times calculation
        return this.findOptimalTimesForProject(tasks);
    }
    
    private calculateCompletionRate(tasks: Task[]): number {
        const completedTasks = tasks.filter(task => task.status === 'completed');
        return completedTasks.length / tasks.length;
    }
    
    private calculateDurationAccuracy(tasks: Task[]): number {
        // Mock calculation - compare estimated vs actual duration
        return Math.random() * 0.3 + 0.7; // Random accuracy between 0.7-1.0
    }
    
    private calculateAverage(numbers: number[]): number {
        return numbers.reduce((sum, num) => sum + num, 0) / numbers.length;
    }
    
    private calculateMostCommonPriority(tasks: Task[]): 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' {
        const counts: Record<string, number> = {};
        tasks.forEach(task => {
            counts[task.priority] = (counts[task.priority] || 0) + 1;
        });
        
        const mostCommon = Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
        return mostCommon as 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
    }
    
    private calculateMostCommonProject(tasks: Task[]): string {
        const counts: Record<string, number> = {};
        tasks.forEach(task => {
            counts[task.project] = (counts[task.project] || 0) + 1;
        });
        
        return Object.keys(counts).reduce((a, b) => counts[a] > counts[b] ? a : b);
    }
    
    private calculateMostCommonTags(tasks: Task[]): string[] {
        const tagCounts: Record<string, number> = {};
        tasks.forEach(task => {
            task.tags.forEach(tag => {
                tagCounts[tag] = (tagCounts[tag] || 0) + 1;
            });
        });
        
        return Object.keys(tagCounts)
            .sort((a, b) => tagCounts[b] - tagCounts[a])
            .slice(0, 3); // Top 3 tags
    }
    
    private calculateMostCommonDay(tasks: Task[]): number {
        const dayCounts: Record<number, number> = {};
        tasks.forEach(task => {
            const day = new Date(task.completedAt).getDay();
            dayCounts[day] = (dayCounts[day] || 0) + 1;
        });
        
        const mostCommonDay = Object.keys(dayCounts).reduce((a, b) => 
            dayCounts[parseInt(a)] > dayCounts[parseInt(b)] ? a : b
        );
        
        return parseInt(mostCommonDay);
    }
}

class AITaskGenerator {
    async generate(prompt: string): Promise<TaskPrediction[]> {
        // Mock AI task generation - in real implementation, would call AI service
        console.log('🤖 AI Task Generator called with prompt:', prompt.substring(0, 100) + '...');
        
        // Return mock predictions for demo
        return [
            {
                title: 'Review AI integration code',
                description: 'AI suggests reviewing the recent activity tracker integration for optimization opportunities',
                priority: 'HIGH',
                estimatedDuration: 45,
                confidence: 0.87,
                reasoning: 'Based on your coding patterns and current project momentum',
                suggestedTime: new Date(Date.now() + 60 * 60 * 1000), // 1 hour from now
                project: 'FocusFlow Development',
                tags: ['ai-generated', 'code-review', 'optimization']
            },
            {
                title: 'Update project documentation',
                description: 'AI detected missing documentation for recent features',
                priority: 'MEDIUM',
                estimatedDuration: 30,
                confidence: 0.75,
                reasoning: 'Documentation typically follows after major feature implementations',
                suggestedTime: new Date(Date.now() + 2 * 60 * 60 * 1000), // 2 hours from now
                project: 'FocusFlow Development',
                tags: ['ai-generated', 'documentation', 'maintenance']
            }
        ];
    }
}

// Export classes for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        PredictiveTaskEngine,
        PatternAnalyzer,
        AITaskGenerator
    };
}

// Global instance for browser usage
if (typeof window !== 'undefined') {
    (window as any).PredictiveTaskEngine = PredictiveTaskEngine;
    (window as any).PatternAnalyzer = PatternAnalyzer;
    (window as any).AITaskGenerator = AITaskGenerator;
}