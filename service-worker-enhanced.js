/**
 * Enhanced Service Worker for FocusFlow PWA
 * Implements advanced caching, background sync, and performance optimizations
 */

const CACHE_VERSION = 'focusflow-v3.0';
const STATIC_CACHE = `${CACHE_VERSION}-static`;
const DYNAMIC_CACHE = `${CACHE_VERSION}-dynamic`;
const API_CACHE = `${CACHE_VERSION}-api`;
const IMAGE_CACHE = `${CACHE_VERSION}-images`;

// Comprehensive caching strategy
const STATIC_ASSETS = [
    '/',
    '/index.html',
    '/intelligence-demo.html',
    '/styles/main.css',
    '/js/app.js',
    '/js/timer.js',
    '/js/tasks.js',
    '/js/analytics.js',
    '/ActivityTracker.js',
    '/PredictiveTaskEngine.js',
    '/EnvironmentController.js',
    '/manifest.json',
    '/icons/icon-192.png',
    '/icons/icon-512.png',
    '/icons/task-icon.png',
    '/icons/environment-icon.png'
];

const API_ENDPOINTS = [
    '/api/tasks',
    '/api/sessions',
    '/api/analytics',
    '/api/predictions',
    '/api/environment'
];

const MAX_CACHE_SIZE = 50; // Maximum number of items per cache
const CACHE_EXPIRY_TIME = 24 * 60 * 60 * 1000; // 24 hours

class EnhancedServiceWorker {
    constructor() {
        this.setupEventListeners();
        this.pendingRequests = new Map();
        this.offlineQueue = [];
        this.analyticsQueue = [];
        this.lastCleanup = Date.now();
    }

    setupEventListeners() {
        self.addEventListener('install', this.handleInstall.bind(this));
        self.addEventListener('activate', this.handleActivate.bind(this));
        self.addEventListener('fetch', this.handleFetch.bind(this));
        self.addEventListener('sync', this.handleBackgroundSync.bind(this));
        self.addEventListener('message', this.handleMessage.bind(this));
        self.addEventListener('push', this.handlePush.bind(this));
        self.addEventListener('notificationclick', this.handleNotificationClick.bind(this));
    }

    async handleInstall(event) {
        console.log('🔧 Service Worker: Installing...');
        
        event.waitUntil(
            Promise.all([
                this.cacheStaticAssets(),
                this.preloadCriticalResources(),
                self.skipWaiting()
            ])
        );
    }

    async handleActivate(event) {
        console.log('✅ Service Worker: Activating...');
        
        event.waitUntil(
            Promise.all([
                this.cleanupOldCaches(),
                this.initializeBackground(),
                self.clients.claim()
            ])
        );
    }

    async cacheStaticAssets() {
        try {
            const cache = await caches.open(STATIC_CACHE);
            
            // Cache assets with retry logic
            for (const asset of STATIC_ASSETS) {
                try {
                    await cache.add(asset);
                } catch (error) {
                    console.warn(`Failed to cache asset: ${asset}`, error);
                }
            }
            
            console.log(`📦 Cached ${STATIC_ASSETS.length} static assets`);
        } catch (error) {
            console.error('Failed to cache static assets:', error);
        }
    }

    async preloadCriticalResources() {
        // Preload critical JavaScript modules
        const criticalResources = [
            '/ActivityTracker.js',
            '/PredictiveTaskEngine.js',
            '/EnvironmentController.js'
        ];

        try {
            const cache = await caches.open(STATIC_CACHE);
            await Promise.all(
                criticalResources.map(resource => cache.add(resource))
            );
            console.log('🎯 Critical resources preloaded');
        } catch (error) {
            console.error('Failed to preload critical resources:', error);
        }
    }

    async cleanupOldCaches() {
        const cacheNames = await caches.keys();
        const oldCaches = cacheNames.filter(name => 
            name.startsWith('focusflow-') && name !== STATIC_CACHE && 
            name !== DYNAMIC_CACHE && name !== API_CACHE && name !== IMAGE_CACHE
        );

        await Promise.all(
            oldCaches.map(cacheName => caches.delete(cacheName))
        );

        if (oldCaches.length > 0) {
            console.log(`🗑️ Cleaned up ${oldCaches.length} old caches`);
        }

        // Clean up oversized caches
        await this.enforceCacheLimits();
    }

    async enforceCacheLimits() {
        const cacheNames = [DYNAMIC_CACHE, API_CACHE, IMAGE_CACHE];
        
        for (const cacheName of cacheNames) {
            try {
                const cache = await caches.open(cacheName);
                const keys = await cache.keys();
                
                if (keys.length > MAX_CACHE_SIZE) {
                    // Remove oldest entries
                    const entriesToRemove = keys.slice(0, keys.length - MAX_CACHE_SIZE);
                    await Promise.all(
                        entriesToRemove.map(key => cache.delete(key))
                    );
                    console.log(`🧹 Cleaned ${entriesToRemove.length} entries from ${cacheName}`);
                }
            } catch (error) {
                console.error(`Failed to enforce cache limits for ${cacheName}:`, error);
            }
        }
    }

    async handleFetch(event) {
        const request = event.request;
        const url = new URL(request.url);

        // Skip non-GET requests for caching
        if (request.method !== 'GET') {
            if (request.method === 'POST' || request.method === 'PUT') {
                event.respondWith(this.handleMutatingRequest(request));
            }
            return;
        }

        // Route based on request type
        if (this.isStaticAsset(url)) {
            event.respondWith(this.handleStaticAsset(request));
        } else if (this.isAPIRequest(url)) {
            event.respondWith(this.handleAPIRequest(request));
        } else if (this.isImageRequest(url)) {
            event.respondWith(this.handleImageRequest(request));
        } else {
            event.respondWith(this.handleDynamicRequest(request));
        }
    }

    isStaticAsset(url) {
        return STATIC_ASSETS.some(asset => url.pathname.endsWith(asset)) ||
               url.pathname.endsWith('.js') ||
               url.pathname.endsWith('.css') ||
               url.pathname.endsWith('.html');
    }

    isAPIRequest(url) {
        return url.pathname.startsWith('/api/') ||
               API_ENDPOINTS.some(endpoint => url.pathname.startsWith(endpoint));
    }

    isImageRequest(url) {
        return /\.(jpg|jpeg|png|gif|webp|svg|ico)$/i.test(url.pathname);
    }

    async handleStaticAsset(request) {
        try {
            // Cache first strategy for static assets
            const cachedResponse = await caches.match(request);
            if (cachedResponse) {
                return cachedResponse;
            }

            // If not in cache, fetch and cache
            const response = await fetch(request);
            if (response.ok) {
                const cache = await caches.open(STATIC_CACHE);
                cache.put(request, response.clone());
            }
            return response;

        } catch (error) {
            console.error('Static asset fetch failed:', error);
            return this.createOfflineResponse(request);
        }
    }

    async handleAPIRequest(request) {
        try {
            // Network first strategy for API requests
            const response = await fetch(request);
            
            if (response.ok) {
                // Cache successful responses
                const cache = await caches.open(API_CACHE);
                cache.put(request, response.clone());
                
                // Store timestamp for expiry checking
                this.setCacheTimestamp(request.url);
            }
            
            return response;

        } catch (error) {
            console.error('API request failed, trying cache:', error);
            
            // Try to serve from cache if network fails
            const cachedResponse = await caches.match(request);
            if (cachedResponse && this.isCacheValid(request.url)) {
                return cachedResponse;
            }

            // Queue for background sync if it's a mutation
            if (this.isMutatingRequest(request)) {
                this.queueForBackgroundSync(request);
            }

            return this.createOfflineAPIResponse(request);
        }
    }

    async handleImageRequest(request) {
        try {
            // Cache first with network fallback for images
            const cachedResponse = await caches.match(request);
            if (cachedResponse) {
                return cachedResponse;
            }

            const response = await fetch(request);
            if (response.ok) {
                const cache = await caches.open(IMAGE_CACHE);
                cache.put(request, response.clone());
            }
            
            return response;

        } catch (error) {
            console.error('Image request failed:', error);
            return this.createPlaceholderImage();
        }
    }

    async handleDynamicRequest(request) {
        try {
            // Stale while revalidate strategy for dynamic content
            const cachedResponse = await caches.match(request);
            
            const fetchPromise = fetch(request).then(response => {
                if (response.ok) {
                    const cache = caches.open(DYNAMIC_CACHE);
                    cache.then(c => c.put(request, response.clone()));
                }
                return response;
            }).catch(() => cachedResponse);

            return cachedResponse || await fetchPromise;

        } catch (error) {
            console.error('Dynamic request failed:', error);
            return this.createOfflineResponse(request);
        }
    }

    async handleMutatingRequest(request) {
        try {
            // Try network first for mutations
            const response = await fetch(request);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            return response;

        } catch (error) {
            console.error('Mutating request failed, queueing for sync:', error);
            
            // Queue for background sync
            await this.queueForBackgroundSync(request);
            
            // Return synthetic success response
            return new Response(
                JSON.stringify({ 
                    success: true, 
                    queued: true, 
                    message: 'Request queued for sync when online' 
                }),
                {
                    status: 202,
                    headers: { 'Content-Type': 'application/json' }
                }
            );
        }
    }

    async handleBackgroundSync(event) {
        console.log('🔄 Background sync triggered:', event.tag);

        if (event.tag === 'background-sync') {
            event.waitUntil(this.performBackgroundSync());
        } else if (event.tag === 'analytics-sync') {
            event.waitUntil(this.syncAnalytics());
        } else if (event.tag === 'predictions-sync') {
            event.waitUntil(this.syncPredictions());
        }
    }

    async performBackgroundSync() {
        try {
            console.log('📤 Performing background sync...');
            
            // Process offline queue
            const offlineData = await this.getOfflineData();
            
            if (offlineData.length > 0) {
                await this.syncOfflineData(offlineData);
                await this.clearOfflineData();
                console.log(`✅ Synced ${offlineData.length} offline operations`);
            }

            // Sync analytics data
            await this.syncAnalytics();

            // Update predictions cache
            await this.updatePredictionsCache();

            // Clean up expired cache entries
            await this.cleanupExpiredCache();

        } catch (error) {
            console.error('Background sync failed:', error);
            throw error; // Retry sync later
        }
    }

    async syncOfflineData(offlineData) {
        const results = [];
        
        for (const item of offlineData) {
            try {
                const response = await fetch(item.request);
                if (response.ok) {
                    results.push({ success: true, item });
                } else {
                    results.push({ success: false, item, error: `HTTP ${response.status}` });
                }
            } catch (error) {
                results.push({ success: false, item, error: error.message });
            }
        }

        // Notify clients of sync results
        this.notifyClients('sync-completed', results);
        
        return results;
    }

    async syncAnalytics() {
        try {
            const analyticsData = await this.getQueuedAnalytics();
            
            if (analyticsData.length > 0) {
                const response = await fetch('/api/analytics/batch', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(analyticsData)
                });

                if (response.ok) {
                    await this.clearAnalyticsQueue();
                    console.log(`📊 Synced ${analyticsData.length} analytics events`);
                }
            }
        } catch (error) {
            console.error('Analytics sync failed:', error);
        }
    }

    async updatePredictionsCache() {
        try {
            const response = await fetch('/api/predictions/latest');
            if (response.ok) {
                const cache = await caches.open(API_CACHE);
                cache.put('/api/predictions/latest', response.clone());
                console.log('🔮 Updated predictions cache');
            }
        } catch (error) {
            console.error('Failed to update predictions cache:', error);
        }
    }

    async cleanupExpiredCache() {
        const now = Date.now();
        
        // Only cleanup once per hour
        if (now - this.lastCleanup < 60 * 60 * 1000) {
            return;
        }

        try {
            const cache = await caches.open(API_CACHE);
            const requests = await cache.keys();
            
            for (const request of requests) {
                if (!this.isCacheValid(request.url)) {
                    await cache.delete(request);
                }
            }
            
            this.lastCleanup = now;
            console.log('🧹 Cleaned expired cache entries');
            
        } catch (error) {
            console.error('Cache cleanup failed:', error);
        }
    }

    async handleMessage(event) {
        const { type, data } = event.data;

        switch (type) {
            case 'SKIP_WAITING':
                self.skipWaiting();
                break;
                
            case 'QUEUE_ANALYTICS':
                await this.queueAnalytics(data);
                break;
                
            case 'FORCE_SYNC':
                await this.performBackgroundSync();
                break;
                
            case 'CLEAR_CACHE':
                await this.clearAllCaches();
                break;
                
            case 'GET_CACHE_STATUS':
                const status = await this.getCacheStatus();
                event.ports[0].postMessage(status);
                break;
        }
    }

    async handlePush(event) {
        const options = {
            body: 'You have new productivity insights available!',
            icon: '/icons/icon-192.png',
            badge: '/icons/badge-icon.png',
            tag: 'productivity-update',
            data: {
                url: '/',
                timestamp: Date.now()
            },
            actions: [
                {
                    action: 'view',
                    title: 'View Insights'
                },
                {
                    action: 'dismiss',
                    title: 'Dismiss'
                }
            ]
        };

        if (event.data) {
            const payload = event.data.json();
            options.body = payload.body || options.body;
            options.data = { ...options.data, ...payload.data };
        }

        event.waitUntil(
            self.registration.showNotification('FocusFlow', options)
        );
    }

    async handleNotificationClick(event) {
        event.notification.close();

        if (event.action === 'view') {
            const url = event.notification.data?.url || '/';
            
            event.waitUntil(
                clients.openWindow(url)
            );
        }
    }

    // Utility methods
    async queueForBackgroundSync(request) {
        const requestData = {
            url: request.url,
            method: request.method,
            headers: Object.fromEntries(request.headers.entries()),
            body: request.method !== 'GET' ? await request.text() : null,
            timestamp: Date.now()
        };

        this.offlineQueue.push(requestData);
        await this.saveOfflineData();

        // Register for background sync
        try {
            await self.registration.sync.register('background-sync');
        } catch (error) {
            console.error('Failed to register background sync:', error);
        }
    }

    async queueAnalytics(data) {
        this.analyticsQueue.push({
            ...data,
            timestamp: Date.now()
        });

        await this.saveAnalyticsData();

        // Register for analytics sync
        try {
            await self.registration.sync.register('analytics-sync');
        } catch (error) {
            console.error('Failed to register analytics sync:', error);
        }
    }

    isMutatingRequest(request) {
        return ['POST', 'PUT', 'DELETE', 'PATCH'].includes(request.method);
    }

    setCacheTimestamp(url) {
        const timestamps = this.getCacheTimestamps();
        timestamps[url] = Date.now();
        this.saveCacheTimestamps(timestamps);
    }

    isCacheValid(url) {
        const timestamps = this.getCacheTimestamps();
        const timestamp = timestamps[url];
        
        if (!timestamp) return false;
        
        return (Date.now() - timestamp) < CACHE_EXPIRY_TIME;
    }

    getCacheTimestamps() {
        try {
            return JSON.parse(localStorage.getItem('sw-cache-timestamps') || '{}');
        } catch {
            return {};
        }
    }

    saveCacheTimestamps(timestamps) {
        try {
            localStorage.setItem('sw-cache-timestamps', JSON.stringify(timestamps));
        } catch (error) {
            console.error('Failed to save cache timestamps:', error);
        }
    }

    async getOfflineData() {
        try {
            const data = await this.getFromIDB('offline-queue');
            return data || this.offlineQueue;
        } catch {
            return this.offlineQueue;
        }
    }

    async saveOfflineData() {
        try {
            await this.saveToIDB('offline-queue', this.offlineQueue);
        } catch (error) {
            console.error('Failed to save offline data:', error);
        }
    }

    async clearOfflineData() {
        this.offlineQueue = [];
        try {
            await this.deleteFromIDB('offline-queue');
        } catch (error) {
            console.error('Failed to clear offline data:', error);
        }
    }

    async getQueuedAnalytics() {
        try {
            const data = await this.getFromIDB('analytics-queue');
            return data || this.analyticsQueue;
        } catch {
            return this.analyticsQueue;
        }
    }

    async saveAnalyticsData() {
        try {
            await this.saveToIDB('analytics-queue', this.analyticsQueue);
        } catch (error) {
            console.error('Failed to save analytics data:', error);
        }
    }

    async clearAnalyticsQueue() {
        this.analyticsQueue = [];
        try {
            await this.deleteFromIDB('analytics-queue');
        } catch (error) {
            console.error('Failed to clear analytics queue:', error);
        }
    }

    async notifyClients(type, data) {
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({ type, data });
        });
    }

    async getCacheStatus() {
        const cacheNames = await caches.keys();
        const status = {};

        for (const cacheName of cacheNames) {
            const cache = await caches.open(cacheName);
            const keys = await cache.keys();
            status[cacheName] = keys.length;
        }

        return {
            caches: status,
            offlineQueue: this.offlineQueue.length,
            analyticsQueue: this.analyticsQueue.length,
            version: CACHE_VERSION
        };
    }

    async clearAllCaches() {
        const cacheNames = await caches.keys();
        await Promise.all(cacheNames.map(name => caches.delete(name)));
        
        this.offlineQueue = [];
        this.analyticsQueue = [];
        
        console.log('🗑️ All caches cleared');
    }

    createOfflineResponse(request) {
        if (request.url.endsWith('.html') || request.headers.get('accept')?.includes('text/html')) {
            return new Response(`
                <!DOCTYPE html>
                <html>
                <head>
                    <title>FocusFlow - Offline</title>
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body { font-family: sans-serif; text-align: center; padding: 50px; }
                        .offline { color: #666; }
                    </style>
                </head>
                <body>
                    <h1>🔌 You're Offline</h1>
                    <p class="offline">FocusFlow is working offline. Your data will sync when you're back online.</p>
                    <button onclick="location.reload()">Try Again</button>
                </body>
                </html>
            `, {
                headers: { 'Content-Type': 'text/html' }
            });
        }

        return new Response('Offline', { status: 503 });
    }

    createOfflineAPIResponse(request) {
        return new Response(
            JSON.stringify({
                error: 'Offline',
                message: 'This request will be synced when online',
                queued: true
            }),
            {
                status: 503,
                headers: { 'Content-Type': 'application/json' }
            }
        );
    }

    createPlaceholderImage() {
        // Create a simple SVG placeholder
        const svg = `
            <svg width="400" height="300" xmlns="http://www.w3.org/2000/svg">
                <rect width="100%" height="100%" fill="#f0f0f0"/>
                <text x="50%" y="50%" font-family="sans-serif" font-size="18" 
                      text-anchor="middle" fill="#999">Image Offline</text>
            </svg>
        `;

        return new Response(svg, {
            headers: { 'Content-Type': 'image/svg+xml' }
        });
    }

    // IndexedDB utilities for persistent storage
    async openIDB() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open('FocusFlowSW', 1);
            
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
            
            request.onupgradeneeded = () => {
                const db = request.result;
                if (!db.objectStoreNames.contains('data')) {
                    db.createObjectStore('data');
                }
            };
        });
    }

    async saveToIDB(key, data) {
        const db = await this.openIDB();
        const transaction = db.transaction(['data'], 'readwrite');
        const store = transaction.objectStore('data');
        
        return new Promise((resolve, reject) => {
            const request = store.put(data, key);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    async getFromIDB(key) {
        const db = await this.openIDB();
        const transaction = db.transaction(['data'], 'readonly');
        const store = transaction.objectStore('data');
        
        return new Promise((resolve, reject) => {
            const request = store.get(key);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve(request.result);
        });
    }

    async deleteFromIDB(key) {
        const db = await this.openIDB();
        const transaction = db.transaction(['data'], 'readwrite');
        const store = transaction.objectStore('data');
        
        return new Promise((resolve, reject) => {
            const request = store.delete(key);
            request.onerror = () => reject(request.error);
            request.onsuccess = () => resolve();
        });
    }

    async initializeBackground() {
        // Initialize background tasks
        console.log('🔄 Initializing background services...');
        
        // Set up periodic cache cleanup
        setInterval(() => {
            this.cleanupExpiredCache();
        }, 60 * 60 * 1000); // Every hour

        // Set up cache size enforcement
        setInterval(() => {
            this.enforceCacheLimits();
        }, 30 * 60 * 1000); // Every 30 minutes
    }
}

// Initialize the enhanced service worker
const enhancedSW = new EnhancedServiceWorker();

console.log('🚀 Enhanced Service Worker loaded and ready');

// Debug logging for development
if (self.location.hostname === 'localhost') {
    console.log('🐛 Service Worker in development mode');
    
    // Log all fetch requests in development
    const originalHandleFetch = enhancedSW.handleFetch.bind(enhancedSW);
    enhancedSW.handleFetch = function(event) {
        console.log('📥 Fetch:', event.request.method, event.request.url);
        return originalHandleFetch(event);
    };
}