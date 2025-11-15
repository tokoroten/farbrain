/**
 * Canvas drawing utilities for visualization
 */

import type { IdeaVisualization, ClusterVisualization, Point2D } from '../types/api';

interface DrawContext {
  ctx: CanvasRenderingContext2D;
  toScreenX: (x: number) => number;
  toScreenY: (y: number) => number;
}

/**
 * Draw cluster convex hulls with labels
 */
export function drawClusters(
  clusters: ClusterVisualization[],
  { ctx, toScreenX, toScreenY }: DrawContext
): void {
  clusters.forEach((cluster) => {
    if (cluster.convex_hull.length < 3) return;

    // Draw convex hull
    ctx.beginPath();
    ctx.moveTo(
      toScreenX(cluster.convex_hull[0].x),
      toScreenY(cluster.convex_hull[0].y)
    );

    cluster.convex_hull.forEach((point: Point2D, i: number) => {
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
    const centerX = cluster.convex_hull.reduce((sum: number, p: Point2D) => sum + toScreenX(p.x), 0) / cluster.convex_hull.length;
    const centerY = cluster.convex_hull.reduce((sum: number, p: Point2D) => sum + toScreenY(p.y), 0) / cluster.convex_hull.length;

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
}

/**
 * Draw connection lines between ideas (when hovering)
 */
export function drawConnectionLines(
  ideas: IdeaVisualization[],
  hoveredIdeaId: string | null,
  { ctx, toScreenX, toScreenY }: DrawContext
): void {
  if (!hoveredIdeaId) return;

  ideas.forEach((idea) => {
    if (!idea.closest_idea_id) return;

    const closestIdea = ideas.find(i => i.id === idea.closest_idea_id);
    if (!closestIdea) return;

    // Only draw line if hovering over this idea or its closest idea
    const isHovered = hoveredIdeaId === idea.id || hoveredIdeaId === closestIdea.id;
    if (!isHovered) return;

    const x1 = toScreenX(idea.x);
    const y1 = toScreenY(idea.y);
    const x2 = toScreenX(closestIdea.x);
    const y2 = toScreenY(closestIdea.y);

    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.strokeStyle = 'rgba(102, 126, 234, 0.8)';
    ctx.lineWidth = 3;
    ctx.stroke();
  });
}

/**
 * Draw pulsing glow effect for an idea
 */
export function drawPulsingGlow(
  x: number,
  y: number,
  radius: number,
  pulseAnimation: number,
  color: { hue: number; saturation: number; lightness: number },
  ctx: CanvasRenderingContext2D
): void {
  const pulseValue = Math.sin(pulseAnimation) * 0.5 + 0.5; // 0 to 1
  const glowRadius = radius + color.lightness / 5 + pulseValue * (color.lightness / 10);

  // Outer glow (largest)
  const gradient1 = ctx.createRadialGradient(x, y, radius, x, y, glowRadius);
  gradient1.addColorStop(0, `hsla(${color.hue}, ${color.saturation}%, ${color.lightness}%, 0.7)`);
  gradient1.addColorStop(0.5, `hsla(${color.hue}, ${color.saturation}%, ${color.lightness}%, ${0.4 * pulseValue})`);
  gradient1.addColorStop(1, `hsla(${color.hue}, ${color.saturation}%, ${color.lightness}%, 0)`);

  ctx.beginPath();
  ctx.arc(x, y, glowRadius, 0, Math.PI * 2);
  ctx.fillStyle = gradient1;
  ctx.fill();

  // Inner glow (medium)
  const innerGlowRadius = radius + (color.lightness / 10) + pulseValue * (color.lightness / 15);
  const gradient2 = ctx.createRadialGradient(x, y, radius, x, y, innerGlowRadius);
  gradient2.addColorStop(0, `hsla(${color.hue}, ${color.saturation + 10}%, ${color.lightness + 10}%, 0.9)`);
  gradient2.addColorStop(1, `hsla(${color.hue}, ${color.saturation + 10}%, ${color.lightness + 10}%, 0)`);

  ctx.beginPath();
  ctx.arc(x, y, innerGlowRadius, 0, Math.PI * 2);
  ctx.fillStyle = gradient2;
  ctx.fill();
}

/**
 * Draw sparkle effect for latest idea
 */
export function drawSparkle(
  x: number,
  y: number,
  radius: number,
  pulseAnimation: number,
  ctx: CanvasRenderingContext2D
): void {
  const sparkleValue = Math.sin(pulseAnimation * 2) * 0.5 + 0.5;
  ctx.fillStyle = `rgba(255, 255, 255, ${sparkleValue})`;
  ctx.beginPath();
  ctx.arc(x, y, radius / 2, 0, Math.PI * 2);
  ctx.fill();
}

interface IdeaDrawConfig {
  selectedIdea: IdeaVisualization | null;
  myLatestIdeaId: string | null;
  othersRecentIdeaIds: string[];
  recentlyVotedIdeaIds: string[];
  pulseAnimation: number;
  hoveredIdeaId: string | null;
  hoveredUserId: string | null;
  filteredUserId: string | null;
  filteredClusterId: number | null;
  getUserColor: (userId: string) => string;
}

/**
 * Draw all ideas on the canvas
 */
export function drawIdeas(
  ideas: IdeaVisualization[],
  config: IdeaDrawConfig,
  { ctx, toScreenX, toScreenY }: DrawContext
): void {
  const {
    selectedIdea,
    myLatestIdeaId,
    othersRecentIdeaIds,
    recentlyVotedIdeaIds,
    pulseAnimation,
    hoveredIdeaId,
    hoveredUserId,
    filteredUserId,
    filteredClusterId,
    getUserColor,
  } = config;

  ideas.forEach((idea) => {
    const x = toScreenX(idea.x);
    const y = toScreenY(idea.y);
    const radius = 6;
    const isSelected = selectedIdea?.id === idea.id;
    const isMyLatest = myLatestIdeaId === idea.id;
    const isOthersRecent = othersRecentIdeaIds.includes(idea.id);
    const isRecentlyVoted = recentlyVotedIdeaIds.includes(idea.id);
    const isHovered = hoveredIdeaId === idea.id;
    const isUserHovered = hoveredUserId ? idea.user_id === hoveredUserId : true;
    const isFilteredUser = filteredUserId ? idea.user_id === filteredUserId : true;
    const isFilteredCluster = filteredClusterId !== null ? idea.cluster_id === filteredClusterId : true;
    const isDimmed = (hoveredIdeaId && !isHovered) || (hoveredUserId && !isUserHovered) ||
                     (filteredUserId && !isFilteredUser) || (filteredClusterId !== null && !isFilteredCluster);

    // Set global alpha for dimming effect
    ctx.globalAlpha = isDimmed ? 0.15 : 1.0;

    // Draw glow effects
    if (isMyLatest) {
      drawPulsingGlow(x, y, radius, pulseAnimation, { hue: 45, saturation: 90, lightness: 60 }, ctx);
    }
    if (isOthersRecent) {
      drawPulsingGlow(x, y, radius, pulseAnimation, { hue: 180, saturation: 80, lightness: 60 }, ctx);
    }
    if (isRecentlyVoted) {
      drawPulsingGlow(x, y, radius, pulseAnimation, { hue: 30, saturation: 90, lightness: 60 }, ctx);
    }

    // Draw circle
    ctx.beginPath();
    ctx.arc(x, y, radius + (isSelected || isHovered ? 3 : 0), 0, Math.PI * 2);

    // Use user-based color
    const userColor = getUserColor(idea.user_id);
    const lightness = isMyLatest || isOthersRecent || isRecentlyVoted ? 70 : 60;
    const hueMatch = userColor.match(/hsl\((\d+)/);
    const hue = hueMatch ? hueMatch[1] : '200';
    ctx.fillStyle = `hsl(${hue}, 70%, ${lightness}%)`;
    ctx.fill();

    // Draw borders
    if (isSelected) {
      ctx.strokeStyle = '#333';
      ctx.lineWidth = 3;
      ctx.stroke();
    } else if (isHovered) {
      ctx.strokeStyle = '#667eea';
      ctx.lineWidth = 3;
      ctx.stroke();
    } else {
      ctx.strokeStyle = (isMyLatest || isOthersRecent || isRecentlyVoted) ? '#fff' : 'white';
      ctx.lineWidth = (isMyLatest || isOthersRecent || isRecentlyVoted) ? 3 : 2;
      ctx.stroke();
    }

    // Draw sparkle effect for latest idea
    if (isMyLatest) {
      drawSparkle(x, y, radius, pulseAnimation, ctx);
    }
  });

  // Reset global alpha
  ctx.globalAlpha = 1.0;
}
