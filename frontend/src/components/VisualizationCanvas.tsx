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
  hoveredIdeaId?: string | null;
  currentUserId?: string;
}

export const VisualizationCanvas = ({ ideas, clusters, selectedIdea, onSelectIdea, hoveredIdeaId, currentUserId }: Props) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });
  const [transform, setTransform] = useState({ x: 0, y: 0, scale: 1 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [hoveredIdea, setHoveredIdea] = useState<IdeaVisualization | null>(null);
  const [hoveredCluster, setHoveredCluster] = useState<ClusterData | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState({ x: 0, y: 0 });
  const [myLatestIdeaId, setMyLatestIdeaId] = useState<string | null>(null);
  const [othersRecentIdeaIds, setOthersRecentIdeaIds] = useState<string[]>([]);
  const [pulseAnimation, setPulseAnimation] = useState(0);
  const animationFrameRef = useRef<number | null>(null);
  const prevIdeasCountRef = useRef(ideas.length);

  // Track latest ideas and start pulse animation
  useEffect(() => {
    if (ideas.length === 0) return;

    // Only update if new ideas were added (not on every re-render)
    const ideasAdded = ideas.length > prevIdeasCountRef.current;
    prevIdeasCountRef.current = ideas.length;

    if (!ideasAdded) return;

    // Find my most recent idea
    const myIdeas = currentUserId
      ? ideas.filter(idea => idea.user_id === currentUserId)
      : [];

    if (myIdeas.length > 0) {
      const sortedMyIdeas = [...myIdeas].sort((a, b) =>
        new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      );
      const myNewest = sortedMyIdeas[0];

      if (myNewest.id !== myLatestIdeaId) {
        setMyLatestIdeaId(myNewest.id);
        setPulseAnimation(0);

        // Clear after 10 seconds
        const timeout = setTimeout(() => {
          setMyLatestIdeaId(null);
        }, 10000);

        return () => clearTimeout(timeout);
      }
    }

    // Find others' 5 most recent ideas
    const othersIdeas = currentUserId
      ? ideas.filter(idea => idea.user_id !== currentUserId)
      : ideas;

    const sortedOthersIdeas = [...othersIdeas].sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
    const recentOthers = sortedOthersIdeas.slice(0, 5).map(idea => idea.id);

    setOthersRecentIdeaIds(recentOthers);
  }, [ideas, myLatestIdeaId, currentUserId]);

  // Pulse animation loop
  useEffect(() => {
    if (!myLatestIdeaId && othersRecentIdeaIds.length === 0) {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
      return;
    }

    const animate = () => {
      setPulseAnimation((prev) => (prev + 0.05) % (Math.PI * 2));
      animationFrameRef.current = requestAnimationFrame(animate);
    };

    animationFrameRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current);
        animationFrameRef.current = null;
      }
    };
  }, [myLatestIdeaId, othersRecentIdeaIds]);

  // Resize handler using ResizeObserver
  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const { width, height } = containerRef.current.getBoundingClientRect();
        setDimensions({ width, height });
      }
    };

    updateDimensions();

    // Use ResizeObserver to detect container size changes
    const resizeObserver = new ResizeObserver(() => {
      updateDimensions();
    });

    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    // Also listen to window resize as fallback
    window.addEventListener('resize', updateDimensions);

    return () => {
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateDimensions);
    };
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

      // Draw cluster label with background
      const centerX = cluster.convex_hull.reduce((sum, p) => sum + toScreenX(p.x), 0) / cluster.convex_hull.length;
      const centerY = cluster.convex_hull.reduce((sum, p) => sum + toScreenY(p.y), 0) / cluster.convex_hull.length;

      ctx.font = 'bold 16px sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';

      // Measure text for background
      const textMetrics = ctx.measureText(cluster.label);
      const textWidth = textMetrics.width;
      const textHeight = 20;
      const padding = 8;

      // Draw semi-transparent background
      ctx.fillStyle = `hsla(${cluster.id * 60}, 60%, 95%, 0.9)`;
      ctx.fillRect(
        centerX - textWidth / 2 - padding,
        centerY - textHeight / 2 - padding / 2,
        textWidth + padding * 2,
        textHeight + padding
      );

      // Draw border
      ctx.strokeStyle = `hsla(${cluster.id * 60}, 60%, 60%, 0.8)`;
      ctx.lineWidth = 2;
      ctx.strokeRect(
        centerX - textWidth / 2 - padding,
        centerY - textHeight / 2 - padding / 2,
        textWidth + padding * 2,
        textHeight + padding
      );

      // Draw text
      ctx.fillStyle = `hsla(${cluster.id * 60}, 70%, 30%, 1)`;
      ctx.fillText(cluster.label, centerX, centerY);
    });

    // Draw ideas
    ideas.forEach((idea) => {
      const x = toScreenX(idea.x);
      const y = toScreenY(idea.y);
      const radius = 6;
      const isSelected = selectedIdea?.id === idea.id;
      const isMyLatest = myLatestIdeaId === idea.id;
      const isOthersRecent = othersRecentIdeaIds.includes(idea.id);
      const isHovered = hoveredIdeaId === idea.id;
      const isDimmed = hoveredIdeaId && !isHovered;

      // Set global alpha for dimming effect
      if (isDimmed) {
        ctx.globalAlpha = 0.2;
      } else {
        ctx.globalAlpha = 1.0;
      }

      // Draw pulsing glow effect for my latest idea (gold color)
      if (isMyLatest) {
        const pulseValue = Math.sin(pulseAnimation) * 0.5 + 0.5; // 0 to 1
        const glowRadius = radius + 15 + pulseValue * 10;

        // Outer glow (largest) - gold
        const gradient1 = ctx.createRadialGradient(x, y, radius, x, y, glowRadius);
        gradient1.addColorStop(0, `hsla(45, 90%, 60%, 0.7)`);
        gradient1.addColorStop(0.5, `hsla(45, 90%, 60%, ${0.4 * pulseValue})`);
        gradient1.addColorStop(1, `hsla(45, 90%, 60%, 0)`);

        ctx.beginPath();
        ctx.arc(x, y, glowRadius, 0, Math.PI * 2);
        ctx.fillStyle = gradient1;
        ctx.fill();

        // Inner glow (medium) - brighter gold
        const innerGlowRadius = radius + 8 + pulseValue * 5;
        const gradient2 = ctx.createRadialGradient(x, y, radius, x, y, innerGlowRadius);
        gradient2.addColorStop(0, `hsla(45, 100%, 70%, 0.9)`);
        gradient2.addColorStop(1, `hsla(45, 100%, 70%, 0)`);

        ctx.beginPath();
        ctx.arc(x, y, innerGlowRadius, 0, Math.PI * 2);
        ctx.fillStyle = gradient2;
        ctx.fill();
      }

      // Draw pulsing glow effect for others' recent ideas (cyan color)
      if (isOthersRecent) {
        const pulseValue = Math.sin(pulseAnimation) * 0.5 + 0.5; // 0 to 1
        const glowRadius = radius + 10 + pulseValue * 6;

        // Outer glow - cyan
        const gradient1 = ctx.createRadialGradient(x, y, radius, x, y, glowRadius);
        gradient1.addColorStop(0, `hsla(180, 80%, 60%, 0.5)`);
        gradient1.addColorStop(0.5, `hsla(180, 80%, 60%, ${0.3 * pulseValue})`);
        gradient1.addColorStop(1, `hsla(180, 80%, 60%, 0)`);

        ctx.beginPath();
        ctx.arc(x, y, glowRadius, 0, Math.PI * 2);
        ctx.fillStyle = gradient1;
        ctx.fill();

        // Inner glow - brighter cyan
        const innerGlowRadius = radius + 5 + pulseValue * 3;
        const gradient2 = ctx.createRadialGradient(x, y, radius, x, y, innerGlowRadius);
        gradient2.addColorStop(0, `hsla(180, 90%, 70%, 0.7)`);
        gradient2.addColorStop(1, `hsla(180, 90%, 70%, 0)`);

        ctx.beginPath();
        ctx.arc(x, y, innerGlowRadius, 0, Math.PI * 2);
        ctx.fillStyle = gradient2;
        ctx.fill();
      }

      // Draw circle
      ctx.beginPath();
      ctx.arc(x, y, radius + (isSelected || isHovered ? 3 : 0), 0, Math.PI * 2);
      ctx.fillStyle = `hsl(${idea.novelty_score * 1.2}, 70%, ${isMyLatest || isOthersRecent ? 70 : 60}%)`;
      ctx.fill();

      if (isSelected) {
        ctx.strokeStyle = '#333';
        ctx.lineWidth = 3;
        ctx.stroke();
      } else if (isHovered) {
        ctx.strokeStyle = '#667eea';
        ctx.lineWidth = 3;
        ctx.stroke();
      }

      // Draw border (brighter for latest idea)
      if (!isSelected && !isHovered) {
        ctx.strokeStyle = (isMyLatest || isOthersRecent) ? '#fff' : 'white';
        ctx.lineWidth = (isMyLatest || isOthersRecent) ? 3 : 2;
        ctx.stroke();
      }

      // Draw sparkle effect for latest idea
      if (isMyLatest) {
        const sparkleValue = Math.sin(pulseAnimation * 2) * 0.5 + 0.5;
        ctx.fillStyle = `rgba(255, 255, 255, ${sparkleValue})`;
        ctx.beginPath();
        ctx.arc(x, y, radius / 2, 0, Math.PI * 2);
        ctx.fill();
      }
    });

    // Reset global alpha
    ctx.globalAlpha = 1.0;

  }, [ideas, clusters, dimensions, transform, selectedIdea, myLatestIdeaId, othersRecentIdeaIds, pulseAnimation, hoveredIdeaId]);

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
    } else {
      // Check if hovering over an idea
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      // Calculate coordinate transformation (same as click handler)
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

      // Helper function to check if point is inside polygon (ray casting algorithm)
      const isPointInPolygon = (px: number, py: number, polygon: { x: number; y: number }[]) => {
        let inside = false;
        for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
          const xi = polygon[i].x;
          const yi = polygon[i].y;
          const xj = polygon[j].x;
          const yj = polygon[j].y;

          const intersect = ((yi > py) !== (yj > py)) &&
            (px < (xj - xi) * (py - yi) / (yj - yi) + xi);
          if (intersect) inside = !inside;
        }
        return inside;
      };

      // Find hovered idea FIRST (higher priority than clusters)
      let foundIdea: IdeaVisualization | null = null;
      for (const idea of ideas) {
        const x = toScreenX(idea.x);
        const y = toScreenY(idea.y);
        const distance = Math.sqrt((mouseX - x) ** 2 + (mouseY - y) ** 2);

        if (distance < 10) {
          foundIdea = idea;
          setTooltipPosition({ x: e.clientX, y: e.clientY });
          break;
        }
      }

      // Check if hovering over a cluster (only if not hovering over an idea)
      let foundCluster: ClusterData | null = null;
      if (!foundIdea) {
        for (const cluster of clusters) {
          if (cluster.convex_hull.length < 3) continue;

          const screenPolygon = cluster.convex_hull.map(point => ({
            x: toScreenX(point.x),
            y: toScreenY(point.y),
          }));

          if (isPointInPolygon(mouseX, mouseY, screenPolygon)) {
            foundCluster = cluster;
            setTooltipPosition({ x: e.clientX, y: e.clientY });
            break;
          }
        }
      }

      setHoveredCluster(foundCluster);
      setHoveredIdea(foundIdea);
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

      {/* Tooltip for hovered cluster */}
      {hoveredCluster && (
        <div style={{
          position: 'fixed',
          left: `${tooltipPosition.x + 15}px`,
          top: `${tooltipPosition.y + 15}px`,
          background: `hsla(${hoveredCluster.id * 60}, 60%, 95%, 0.98)`,
          color: `hsla(${hoveredCluster.id * 60}, 70%, 20%, 1)`,
          padding: '1rem',
          borderRadius: '0.75rem',
          fontSize: '0.875rem',
          maxWidth: '350px',
          pointerEvents: 'none',
          zIndex: 1000,
          boxShadow: '0 6px 12px rgba(0,0,0,0.2)',
          border: `3px solid hsla(${hoveredCluster.id * 60}, 60%, 60%, 0.8)`,
        }}>
          <div style={{ fontWeight: 'bold', fontSize: '1rem', marginBottom: '0.5rem' }}>
            {hoveredCluster.label}
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.8, marginBottom: '0.25rem' }}>
            📊 アイディア数: {hoveredCluster.idea_count}件
          </div>
          <div style={{ fontSize: '0.75rem', opacity: 0.8 }}>
            ⭐ 平均新規性スコア: {hoveredCluster.avg_novelty_score.toFixed(1)}
          </div>
        </div>
      )}

      {/* Tooltip for hovered idea */}
      {hoveredIdea && !hoveredCluster && (
        <div style={{
          position: 'fixed',
          left: `${tooltipPosition.x + 15}px`,
          top: `${tooltipPosition.y + 15}px`,
          background: 'rgba(0, 0, 0, 0.9)',
          color: 'white',
          padding: '0.75rem',
          borderRadius: '0.5rem',
          fontSize: '0.875rem',
          maxWidth: '300px',
          pointerEvents: 'none',
          zIndex: 1000,
          boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '0.25rem' }}>
            {hoveredIdea.user_name}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#ffd700', marginBottom: '0.25rem' }}>
            クラスタ: {hoveredIdea.cluster_id !== null ? hoveredIdea.cluster_id : 'なし'}
          </div>
          <div style={{ marginBottom: '0.5rem' }}>
            {hoveredIdea.formatted_text}
          </div>
          <div style={{ fontSize: '0.75rem', color: '#aaa' }}>
            新規性スコア: {hoveredIdea.novelty_score.toFixed(1)}
          </div>
        </div>
      )}

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
        ホバーで表示 | クリックで詳細 | ドラッグで移動 | ホイールでズーム
      </div>
    </div>
  );
};
