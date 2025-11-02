/**
 * Custom hook for coordinate transformation in visualization canvas
 */

import { useMemo } from 'react';
import type { IdeaVisualization } from '../types/api';

interface Dimensions {
  width: number;
  height: number;
}

interface Transform {
  x: number;
  y: number;
  scale: number;
}

interface CoordinateTransform {
  toScreenX: (x: number) => number;
  toScreenY: (y: number) => number;
  bounds: {
    minX: number;
    maxX: number;
    minY: number;
    maxY: number;
    dataWidth: number;
    dataHeight: number;
  };
}

const CANVAS_PADDING = 50;

/**
 * Calculate coordinate transformation functions for canvas rendering
 * This hook calculates the transformation between data coordinates and screen coordinates
 *
 * @param ideas - Array of ideas with x, y coordinates
 * @param dimensions - Canvas dimensions
 * @param transform - Current transform state (pan/zoom)
 * @returns Transformation functions and bounds
 */
export function useCoordinateTransform(
  ideas: IdeaVisualization[],
  dimensions: Dimensions,
  transform: Transform
): CoordinateTransform {
  return useMemo(() => {
    // Calculate data bounds
    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    ideas.forEach((idea) => {
      minX = Math.min(minX, idea.x);
      maxX = Math.max(maxX, idea.x);
      minY = Math.min(minY, idea.y);
      maxY = Math.max(maxY, idea.y);
    });

    // Calculate data dimensions
    const dataWidth = maxX - minX || 1;
    const dataHeight = maxY - minY || 1;

    // Calculate scale to fit data in canvas with padding
    const scaleX = (dimensions.width - 2 * CANVAS_PADDING) / dataWidth;
    const scaleY = (dimensions.height - 2 * CANVAS_PADDING) / dataHeight;
    const scale = Math.min(scaleX, scaleY) * transform.scale;

    // Calculate centers
    const centerX = dimensions.width / 2;
    const centerY = dimensions.height / 2;
    const dataCenterX = (minX + maxX) / 2;
    const dataCenterY = (minY + maxY) / 2;

    // Transformation functions
    const toScreenX = (x: number) =>
      (x - dataCenterX) * scale + centerX + transform.x;

    const toScreenY = (y: number) =>
      (y - dataCenterY) * scale + centerY + transform.y;

    return {
      toScreenX,
      toScreenY,
      bounds: {
        minX,
        maxX,
        minY,
        maxY,
        dataWidth,
        dataHeight,
      },
    };
  }, [ideas, dimensions, transform]);
}
