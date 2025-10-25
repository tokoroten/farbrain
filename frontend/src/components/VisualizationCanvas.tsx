/**
 * UMAP visualization canvas with clusters
 */

import { useRef, useEffect, useState } from 'react';
import type { IdeaVisualization, ClusterData } from '../types/api';

interface Props {
  ideas: IdeaVisualization[];
  clusters: ClusterData[];
  selectedIdea: IdeaVisualization | null;
  onSelectIdea: (idea: IdeaVisualization | null) => void;
}

export const VisualizationCanvas = ({ ideas, clusters, selectedIdea, onSelectIdea }: Props) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Resize handler
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setDimensions({ width, height });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  // Draw canvas
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, dimensions.width, dimensions.height);

    // Calculate bounds
    const padding = 50;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    ideas.forEach((idea) => {
      minX = Math.min(minX, idea.x);
      maxX = Math.max(maxX, idea.x);
      minY = Math.min(minY, idea.y);
      maxY = Math.max(maxY, idea.y);
    });

    const dataWidth = maxX - minX || 1;
    const dataHeight = maxY - minY || 1;
    const scaleX = (dimensions.width - 2 * padding) / dataWidth;
    const scaleY = (dimensions.height - 2 * padding) / dataHeight;
    const scale = Math.min(scaleX, scaleY) * transform.scale;

    const centerX = dimensions.width / 2;
    const centerY = dimensions.height / 2;
    const dataCenterX = (minX + maxX) / 2;
    const dataCenterY = (minY + maxY) / 2;

    const toScreenX = (x: number) =>
      (x - dataCenterX) * scale + centerX + transform.x;
    const toScreenY = (y: number) =>
      (y - dataCenterY) * scale + centerY + transform.y;

    // Draw clusters (convex hulls)
    clusters.forEach((cluster) => {
      if (cluster.convex_hull.length < 3) return;

      ctx.beginPath();
      ctx.moveTo(
        toScreenX(cluster.convex_hull[0].x),
        toScreenY(cluster.convex_hull[0].y)
      );

      cluster.convex_hull.forEach((point, i) => {
        if (i > 0) {
          ctx.lineTo(toScreenX(point.x), toScreenY(point.y));
        }
      });

      ctx.closePath();
      ctx.fillStyle = `hsla(${cluster.id * 60}, 60%, 85%, 0.3)`;
      ctx.fill();
      ctx.strokeStyle = `hsla(${cluster.id * 60}, 60%, 60%, 0.6)`;
      ctx.lineWidth = 2;
      ctx.stroke();

      // Draw cluster label
      const centerX = cluster.convex_hull.reduce((sum, p) => sum + toScreenX(p.x), 0) / cluster.convex_hull.length;
      const centerY = cluster.convex_hull.reduce((sum, p) => sum + toScreenY(p.y), 0) / cluster.convex_hull.length;

      ctx.font = 'bold 14px sans-serif';
      ctx.fillStyle = '#333';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(cluster.label, centerX, centerY);
    });

    // Draw ideas
    ideas.forEach((idea) => {
      const x = toScreenX(idea.x);
      const y = toScreenY(idea.y);
      const radius = 6;
      const isSelected = selectedIdea?.id === idea.id;

      // Draw circle
      ctx.beginPath();
      ctx.arc(x, y, radius + (isSelected ? 3 : 0), 0, Math.PI * 2);
      ctx.fillStyle = `hsl(${idea.novelty_score * 1.2}, 70%, 60%)`;
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 3;
        ctx.stroke();
      }

      // Draw border
      ctx.strokeStyle = 'white';
      ctx.lineWidth = 2;
      ctx.stroke();
    });

  }, [ideas, clusters, dimensions, transform, selectedIdea]);

  // Mouse handlers
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    setDragStart({ x: e.clientX - transform.x, y: e.clientY - transform.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging) {
      setTransform({
        ...transform,
        x: e.clientX - dragStart.x,
        y: e.clientY - dragStart.y,
      });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleClick = (e: React.MouseEvent) => {
    if (isDragging) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    // Find clicked idea
    const padding = 50;
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

    ideas.forEach((idea) => {
      minX = Math.min(minX, idea.x);
      maxX = Math.max(maxX, idea.x);
      minY = Math.min(minY, idea.y);
      maxY = Math.max(maxY, idea.y);
    });

    const dataWidth = maxX - minX || 1;
    const dataHeight = maxY - minY || 1;
    const scaleX = (dimensions.width - 2 * padding) / dataWidth;
    const scaleY = (dimensions.height - 2 * padding) / dataHeight;
    const scale = Math.min(scaleX, scaleY) * transform.scale;

    const centerX = dimensions.width / 2;
    const centerY = dimensions.height / 2;
    const dataCenterX = (minX + maxX) / 2;
    const dataCenterY = (minY + maxY) / 2;

    const toScreenX = (x: number) =>
      (x - dataCenterX) * scale + centerX + transform.x;
    const toScreenY = (y: number) =>
      (y - dataCenterY) * scale + centerY + transform.y;

    for (const idea of ideas) {
      const x = toScreenX(idea.x);
      const y = toScreenY(idea.y);
      const distance = Math.sqrt((clickX - x) ** 2 + (clickY - y) ** 2);

      if (distance < 10) {
        onSelectIdea(idea);
        return;
      }
    }

    onSelectIdea(null);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setTransform({
      ...transform,
      scale: Math.max(0.1, Math.min(5, transform.scale * delta)),
    });
  };

  return (
    <div
      ref={containerRef}
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        cursor: isDragging ? 'grabbing' : 'grab',
      }}
    >
      <canvas
        ref={canvasRef}
        width={dimensions.width}
        height={dimensions.height}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
        onClick={handleClick}
        onWheel={handleWheel}
        style={{
          display: 'block',
          width: '100%',
          height: '100%',
        }}
      />

      <div style={{
        position: 'absolute',
        bottom: '1rem',
        right: '1rem',
        background: 'rgba(255,255,255,0.9)',
        padding: '0.5rem',
        borderRadius: '0.5rem',
        fontSize: '0.875rem',
        color: '#666',
      }}>
        ドラッグで移動 | ホイールでズーム
      </div>
    </div>
  );
};
