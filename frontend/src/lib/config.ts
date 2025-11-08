/**
 * Environment configuration
 *
 * Use start-local.ps1 for local development (localhost:8000)
 * Use start-farbrain.ps1 for production hosting (api-farbrain.easyrec.app)
 */

/**
 * Get API base URL from environment variable
 * Defaults to localhost if not set
 */
export function getApiUrl(): string {
  return import.meta.env.VITE_API_URL || 'http://localhost:8000';
}

/**
 * Get WebSocket URL from environment variable
 * Defaults to localhost if not set
 */
export function getWebSocketUrl(): string {
  return import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
}
