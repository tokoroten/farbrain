/**
 * File download utilities
 */

import type { AxiosResponse } from 'axios';

/**
 * Extract filename from Content-Disposition header
 */
function extractFilenameFromHeader(
  contentDisposition: string | undefined,
  defaultFilename: string
): string {
  if (!contentDisposition) {
    return defaultFilename;
  }

  // Try RFC 5987 encoding first (filename*=UTF-8''encoded-name)
  const filenameStarMatch = contentDisposition.match(/filename\*=UTF-8''(.+)/i);
  if (filenameStarMatch) {
    try {
      return decodeURIComponent(filenameStarMatch[1]);
    } catch (e) {
      console.warn('Failed to decode filename*:', e);
    }
  }

  // Fall back to regular filename="name" or filename=name
  const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/i);
  if (filenameMatch && filenameMatch[1]) {
    return filenameMatch[1].replace(/['"]/g, '');
  }

  return defaultFilename;
}

/**
 * Download file from axios response
 * Handles filename extraction from Content-Disposition header
 */
export async function downloadFile(
  response: AxiosResponse,
  defaultFilename: string,
  mimeType?: string
): Promise<void> {
  // Create blob with appropriate MIME type
  const blob = mimeType
    ? new Blob([response.data], { type: mimeType })
    : new Blob([response.data]);

  // Create download URL
  const url = window.URL.createObjectURL(blob);

  // Create temporary link element
  const link = document.createElement('a');
  link.href = url;

  // Extract filename from response headers or use default
  const filename = extractFilenameFromHeader(
    response.headers['content-disposition'],
    defaultFilename
  );
  link.setAttribute('download', filename);

  // Trigger download
  document.body.appendChild(link);
  link.click();

  // Cleanup
  link.remove();
  window.URL.revokeObjectURL(url);
}

/**
 * Download text content as file
 */
export function downloadTextFile(
  content: string,
  filename: string,
  mimeType: string = 'text/plain'
): void {
  const blob = new Blob([content], { type: mimeType });
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
