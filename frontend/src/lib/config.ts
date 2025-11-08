/**
 * Environment configuration with automatic domain detection
 */

/**
 * Get API base URL based on current hostname
 * - localhost: http://localhost:8000
 * - production: https://api-farbrain.easyrec.app
 * - Can be overridden by VITE_API_URL environment variable
 */
export function getApiUrl(): string {
  // Environment variable takes precedence (for flexibility)
  if (import.meta.env.VITE_API_URL) {
    return import.meta.env.VITE_API_URL;
  }

  // Auto-detect based on hostname
  const hostname = window.location.hostname;

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }

  // Production environment
  return 'https://api-farbrain.easyrec.app';
}

/**
 * Get WebSocket URL based on current hostname
 * - localhost: ws://localhost:8000
 * - production: wss://api-farbrain.easyrec.app
 * - Can be overridden by VITE_WS_URL environment variable
 */
export function getWebSocketUrl(): string {
  // Environment variable takes precedence (for flexibility)
  if (import.meta.env.VITE_WS_URL) {
    return import.meta.env.VITE_WS_URL;
  }

  // Auto-detect based on hostname
  const hostname = window.location.hostname;

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'ws://localhost:8000';
  }

  // Production environment (wss for secure WebSocket)
  return 'wss://api-farbrain.easyrec.app';
}
