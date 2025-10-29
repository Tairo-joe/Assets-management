// Service Worker for ITAM Mobile Offline Capability
const CACHE_NAME = 'itam-mobile-v1';
const OFFLINE_URL = '/offline.html';

// Assets to cache for offline functionality
const CACHE_ASSETS = [
    '/',
    '/static/css/mobile.css',
    '/static/css/styles.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css',
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js'
];

// Install event - cache assets
self.addEventListener('install', event => {
    console.log('Service Worker: Installing...');
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => {
                console.log('Service Worker: Caching assets');
                return cache.addAll(CACHE_ASSETS);
            })
            .then(() => {
                console.log('Service Worker: Assets cached');
                return self.skipWaiting();
            })
            .catch(error => {
                console.error('Service Worker: Cache failed', error);
            })
    );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
    console.log('Service Worker: Activating...');
    event.waitUntil(
        caches.keys().then(cacheNames => {
            return Promise.all(
                cacheNames.map(cache => {
                    if (cache !== CACHE_NAME) {
                        console.log('Service Worker: Deleting old cache', cache);
                        return caches.delete(cache);
                    }
                })
            );
        }).then(() => {
            console.log('Service Worker: Activated');
            return self.clients.claim();
        })
    );
});

// Fetch event - serve cached content when offline
self.addEventListener('fetch', event => {
    // Skip non-GET requests
    if (event.request.method !== 'GET') return;

    // Skip requests to external domains (except CDNs we want to cache)
    const url = new URL(event.request.url);
    if (url.origin !== location.origin && !isCDNRequest(url)) return;

    event.respondWith(
        caches.match(event.request)
            .then(response => {
                // Return cached version if available
                if (response) {
                    console.log('Service Worker: Serving from cache', event.request.url);
                    return response;
                }

                // Otherwise fetch from network
                return fetch(event.request)
                    .then(response => {
                        // Don't cache non-successful responses
                        if (!response || response.status !== 200 || response.type !== 'basic') {
                            return response;
                        }

                        // Clone the response for caching
                        const responseToCache = response.clone();

                        // Cache the response for future use
                        caches.open(CACHE_NAME)
                            .then(cache => {
                                console.log('Service Worker: Caching new asset', event.request.url);
                                cache.put(event.request, responseToCache);
                            });

                        return response;
                    })
                    .catch(error => {
                        console.log('Service Worker: Network fetch failed, serving offline content');

                        // If it's a navigation request, serve offline page
                        if (event.request.mode === 'navigate') {
                            return caches.match(OFFLINE_URL);
                        }

                        // For other requests, return a generic offline response
                        return new Response('Offline', {
                            status: 503,
                            statusText: 'Service Unavailable',
                            headers: new Headers({
                                'Content-Type': 'text/plain'
                            })
                        });
                    });
            })
    );
});

// Helper function to determine if request is from a CDN we want to cache
function isCDNRequest(url) {
    const cdnDomains = [
        'cdn.jsdelivr.net',
        'cdnjs.cloudflare.com',
        'stackpath.bootstrapcdn.com'
    ];

    return cdnDomains.some(domain => url.hostname.includes(domain));
}

// Background sync for offline actions
self.addEventListener('sync', event => {
    if (event.tag === 'background-sync') {
        console.log('Service Worker: Background sync triggered');
        event.waitUntil(syncOfflineData());
    }
});

// Sync offline data when back online
async function syncOfflineData() {
    try {
        // Get offline actions from IndexedDB or localStorage
        const offlineActions = await getOfflineActions();

        for (const action of offlineActions) {
            try {
                await syncAction(action);
                await removeOfflineAction(action.id);
                console.log('Service Worker: Synced offline action', action.id);
            } catch (error) {
                console.error('Service Worker: Failed to sync action', action.id, error);
            }
        }

        // Notify clients that sync is complete
        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'SYNC_COMPLETE',
                message: 'Offline data synchronized successfully'
            });
        });
    } catch (error) {
        console.error('Service Worker: Background sync failed', error);
    }
}

// Placeholder functions for offline data management
async function getOfflineActions() {
    // In a real implementation, this would read from IndexedDB
    return [];
}

async function syncAction(action) {
    // In a real implementation, this would send the action to the server
    return Promise.resolve();
}

async function removeOfflineAction(actionId) {
    // In a real implementation, this would remove the action from IndexedDB
    return Promise.resolve();
}

// Push notifications for important updates
self.addEventListener('push', event => {
    if (!event.data) return;

    const data = event.data.json();
    const options = {
        body: data.body,
        icon: '/static/images/icon-192x192.png',
        badge: '/static/images/badge-72x72.png',
        vibrate: [100, 50, 100],
        data: data.url,
        actions: [
            {
                action: 'open',
                title: 'Open',
                icon: '/static/images/checkmark.png'
            },
            {
                action: 'close',
                title: 'Close',
                icon: '/static/images/xmark.png'
            }
        ]
    };

    event.waitUntil(
        self.registration.showNotification(data.title, options)
    );
});

// Handle notification clicks
self.addEventListener('notificationclick', event => {
    event.notification.close();

    if (event.action === 'open') {
        const url = event.notification.data;
        event.waitUntil(
            clients.openWindow(url || '/')
        );
    }
});

// Periodic background sync for data updates
self.addEventListener('periodicsync', event => {
    if (event.tag === 'asset-updates') {
        event.waitUntil(updateAssetData());
    }
});

async function updateAssetData() {
    try {
        // In a real implementation, this would fetch latest asset data
        console.log('Service Worker: Updating asset data in background');

        const clients = await self.clients.matchAll();
        clients.forEach(client => {
            client.postMessage({
                type: 'DATA_UPDATED',
                message: 'Asset data updated in background'
            });
        });
    } catch (error) {
        console.error('Service Worker: Background update failed', error);
    }
}
