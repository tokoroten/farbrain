import React from 'react';
import theme from '../../styles/theme';

interface CardProps {
  children: React.ReactNode;
  style?: React.CSSProperties;
  onClick?: () => void;
  hoverable?: boolean;
}

export const Card: React.FC<CardProps> = ({
  children,
  style,
  onClick,
  hoverable = false,
}) => {
  const cardStyle: React.CSSProperties = {
    ...theme.components.card,
    ...(hoverable && {
      cursor: 'pointer',
      transition: 'all 0.2s ease',
    }),
    ...style,
  };

  const hoverStyle: React.CSSProperties = hoverable
    ? {
        transform: 'translateY(-2px)',
        boxShadow: theme.shadows.lg,
      }
    : {};

  const [isHovered, setIsHovered] = React.useState(false);

  return (
    <div
      style={isHovered ? { ...cardStyle, ...hoverStyle } : cardStyle}
      onClick={onClick}
      onMouseEnter={() => hoverable && setIsHovered(true)}
      onMouseLeave={() => hoverable && setIsHovered(false)}
    >
      {children}
    </div>
  );
};
