/**
 * PassiveTracker - Frontend service for passive activity tracking
 * RescueTime killer that tracks everything automatically
 */

interface ActivityData {
    activeTab: string;
    windowFocus: boolean;
    mouseMovements: number;
    keystrokePatterns: KeystrokeData;
    scrollBehavior: ScrollMetrics;
    timestamp: number;
}

interface KeystrokeData {
    wordsPerMinute: number;
    typingRhythm: 'steady' | 'burst' | 'irregular';
    activityLevel: number;
}

interface ScrollMetrics {
    scrollDistance: number;
    scrollSpeed: number;
    scrollDirection: 'up' | 'down' | 'both';
}

interface TrackingPermissions {
    granted: boolean;
    screenTime: boolean;
    applicationAccess: boolean;
    keyboardMouse: boolean;
    websiteTracking: boolean;
}

interface TrackingConfig {
    intervalSeconds: number;
    enableKeyboardTracking: boolean;
    enableMouseTracking: boolean;
    enableWebTracking: boolean;
    privacyMode: boolean;
}

class ApiClient {
    private baseUrl: string;

    constructor(baseUrl: string = '/api') {
        this.baseUrl = baseUrl;
    }

    async post(endpoint: string, data: any): Promise<any> {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data)
        });

        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }

        return response.json();
    }

    async get(endpoint: string): Promise<any> {
        const response = await fetch(`${this.baseUrl}${endpoint}`);
        
        if (!response.ok) {
            throw new Error(`API request failed: ${response.statusText}`);
        }

        return response.json();
    }
}

export class PassiveTracker {
    private trackingInterval: NodeJS.Timeout | null = null;
    private api: ApiClient;
    private config: TrackingConfig;
    private isTracking: boolean = false;
    private activityBuffer: ActivityData[] = [];
    
    // Activity monitoring variables
    private mouseActivity: number = 0;
    private keystrokeData: KeystrokeData = {
        wordsPerMinute: 0,
        typingRhythm: 'steady',
        activityLevel: 0
    };
    private scrollMetrics: ScrollMetrics = {
        scrollDistance: 0,
        scrollSpeed: 0,
        scrollDirection: 'both'
    };
    
    // Event listeners for cleanup
    private eventListeners: Array<() => void> = [];

    constructor(config: Partial<TrackingConfig> = {}) {
        this.api = new ApiClient();
        this.config = {
            intervalSeconds: 30,
            enableKeyboardTracking: true,
            enableMouseTracking: true,
            enableWebTracking: true,
            privacyMode: false,
            ...config
        };
    }

    async startTracking(userId: string): Promise<void> {
        console.log('🔍 Starting passive tracking for user:', userId);

        // Request permissions first
        const permissions = await this.requestTrackingPermissions();
        if (!permissions.granted) {
            console.warn('⚠️ Tracking permissions not granted');
            return;
        }

        this.isTracking = true;
        this.setupEventListeners();

        // Start periodic tracking
        this.trackingInterval = setInterval(async () => {
            if (this.isTracking) {
                try {
                    const activityData = await this.collectActivityData();
                    
                    // Add to buffer
                    this.activityBuffer.push(activityData);
                    
                    // Send data if buffer is full or enough time has passed
                    if (this.activityBuffer.length >= 5) {
                        await this.sendTrackingData(userId);
                    }
                } catch (error) {
                    console.error('❌ Failed to collect activity data:', error);
                }
            }
        }, this.config.intervalSeconds * 1000);

        console.log('✅ Passive tracking started successfully');
    }

    async stopTracking(): Promise<void> {
        console.log('🛑 Stopping passive tracking');
        
        this.isTracking = false;
        
        if (this.trackingInterval) {
            clearInterval(this.trackingInterval);
            this.trackingInterval = null;
        }

        // Clean up event listeners
        this.eventListeners.forEach(cleanup => cleanup());
        this.eventListeners = [];

        // Send any remaining buffered data
        if (this.activityBuffer.length > 0) {
            // Note: Would need userId here in real implementation
            console.log('📤 Sending final buffered data');
        }

        console.log('✅ Passive tracking stopped');
    }

    private async requestTrackingPermissions(): Promise<TrackingPermissions> {
        console.log('🔑 Requesting tracking permissions');
        
        const permissions: TrackingPermissions = {
            granted: false,
            screenTime: false,
            applicationAccess: false,
            keyboardMouse: false,
            websiteTracking: false
        };

        try {
            // Check for basic permissions
            if ('permissions' in navigator) {
                // Note: Real implementation would check specific permissions
                permissions.websiteTracking = true;
            }

            // Request notification permission (as a proxy for user consent)
            if ('Notification' in window) {
                const permission = await Notification.requestPermission();
                permissions.granted = permission === 'granted';
            } else {
                // Fallback - assume granted for demo
                permissions.granted = true;
            }

            permissions.screenTime = true; // Browser can track this
            permissions.keyboardMouse = true; // Can track within page
            permissions.applicationAccess = false; // Limited by browser security

            console.log('🔑 Permissions result:', permissions);
            return permissions;

        } catch (error) {
            console.error('❌ Failed to request permissions:', error);
            return permissions;
        }
    }

    private setupEventListeners(): void {
        console.log('📡 Setting up activity event listeners');

        // Mouse movement tracking
        if (this.config.enableMouseTracking) {
            const mouseHandler = (event: MouseEvent) => {
                this.mouseActivity += Math.abs(event.movementX) + Math.abs(event.movementY);
            };
            document.addEventListener('mousemove', mouseHandler);
            this.eventListeners.push(() => document.removeEventListener('mousemove', mouseHandler));
        }

        // Keyboard activity tracking
        if (this.config.enableKeyboardTracking) {
            let keystrokeCount = 0;
            let lastKeystroke = Date.now();
            
            const keyHandler = (event: KeyboardEvent) => {
                const now = Date.now();
                const timeDiff = now - lastKeystroke;
                
                keystrokeCount++;
                
                // Calculate typing rhythm
                if (timeDiff < 100) {
                    this.keystrokeData.typingRhythm = 'burst';
                } else if (timeDiff > 2000) {
                    this.keystrokeData.typingRhythm = 'irregular';
                } else {
                    this.keystrokeData.typingRhythm = 'steady';
                }
                
                // Update WPM (rough calculation)
                const timeWindow = 60000; // 1 minute
                this.keystrokeData.wordsPerMinute = (keystrokeCount / 5) * (timeWindow / timeDiff);
                this.keystrokeData.activityLevel = Math.min(1, keystrokeCount / 100);
                
                lastKeystroke = now;
            };
            
            document.addEventListener('keydown', keyHandler);
            this.eventListeners.push(() => document.removeEventListener('keydown', keyHandler));
        }

        // Scroll tracking
        const scrollHandler = (event: Event) => {
            const scrollY = window.scrollY;
            const scrollDelta = scrollY - (this.scrollMetrics.scrollDistance || 0);
            
            this.scrollMetrics.scrollDistance = scrollY;
            this.scrollMetrics.scrollSpeed = Math.abs(scrollDelta);
            this.scrollMetrics.scrollDirection = scrollDelta > 0 ? 'down' : 'up';
        };
        
        window.addEventListener('scroll', scrollHandler, { passive: true });
        this.eventListeners.push(() => window.removeEventListener('scroll', scrollHandler));

        // Page visibility tracking
        const visibilityHandler = () => {
            if (document.hidden) {
                console.log('📱 Page hidden - reduced tracking');
            } else {
                console.log('👁️ Page visible - full tracking');
            }
        };
        
        document.addEventListener('visibilitychange', visibilityHandler);
        this.eventListeners.push(() => document.removeEventListener('visibilitychange', visibilityHandler));

        // Window focus tracking
        const focusHandler = () => console.log('🎯 Window focused');
        const blurHandler = () => console.log('😴 Window blurred');
        
        window.addEventListener('focus', focusHandler);
        window.addEventListener('blur', blurHandler);
        this.eventListeners.push(() => {
            window.removeEventListener('focus', focusHandler);
            window.removeEventListener('blur', blurHandler);
        });
    }

    private async collectActivityData(): Promise<ActivityData> {
        const data: ActivityData = {
            activeTab: document.title,
            windowFocus: document.hasFocus(),
            mouseMovements: this.mouseActivity,
            keystrokePatterns: { ...this.keystrokeData },
            scrollBehavior: { ...this.scrollMetrics },
            timestamp: Date.now()
        };

        // Reset counters
        this.mouseActivity = 0;

        return data;
    }

    private async sendTrackingData(userId: string): Promise<void> {
        if (this.activityBuffer.length === 0) return;

        try {
            console.log(`📤 Sending ${this.activityBuffer.length} activity records`);
            
            await this.api.post('/tracking/activity', {
                userId,
                activities: this.activityBuffer,
                timestamp: Date.now(),
                config: this.config
            });

            console.log('✅ Activity data sent successfully');
            this.activityBuffer = []; // Clear buffer

        } catch (error) {
            console.error('❌ Failed to send tracking data:', error);
            
            // Keep data in buffer for retry, but limit buffer size
            if (this.activityBuffer.length > 50) {
                this.activityBuffer = this.activityBuffer.slice(-25); // Keep last 25
                console.warn('⚠️ Buffer overflow - discarded old data');
            }
        }
    }

    // Public methods for manual data collection
    async getInstantActivitySnapshot(): Promise<ActivityData> {
        return this.collectActivityData();
    }

    async getTrackingSummary(userId: string, hours: number = 24): Promise<any> {
        try {
            return await this.api.get(`/tracking/summary/${userId}?hours=${hours}`);
        } catch (error) {
            console.error('❌ Failed to get tracking summary:', error);
            return null;
        }
    }

    // Configuration methods
    updateConfig(newConfig: Partial<TrackingConfig>): void {
        this.config = { ...this.config, ...newConfig };
        console.log('⚙️ Tracking config updated:', this.config);
    }

    getConfig(): TrackingConfig {
        return { ...this.config };
    }

    isCurrentlyTracking(): boolean {
        return this.isTracking;
    }

    // Privacy methods
    async enablePrivacyMode(): Promise<void> {
        console.log('🔒 Enabling privacy mode');
        this.config.privacyMode = true;
        
        // In privacy mode, reduce tracking granularity
        this.config.enableKeyboardTracking = false;
        this.config.intervalSeconds = Math.max(this.config.intervalSeconds, 60);
    }

    async disablePrivacyMode(): Promise<void> {
        console.log('🔓 Disabling privacy mode');
        this.config.privacyMode = false;
        this.config.enableKeyboardTracking = true;
        this.config.intervalSeconds = 30;
    }

    // Analytics methods
    getLocalActivityStats(): any {
        return {
            totalMouseMovements: this.mouseActivity,
            currentWPM: this.keystrokeData.wordsPerMinute,
            typingRhythm: this.keystrokeData.typingRhythm,
            scrollDistance: this.scrollMetrics.scrollDistance,
            isActive: this.isTracking,
            bufferSize: this.activityBuffer.length
        };
    }
}

export default PassiveTracker;