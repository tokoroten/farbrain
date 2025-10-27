import React from 'react';
import theme from '../../styles/theme';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  fullWidth?: boolean;
  children: React.ReactNode;
}

export const Button: React.FC<ButtonProps> = ({
  variant = 'primary',
  size = 'md',
  fullWidth = false,
  disabled,
  children,
  style,
  ...props
}) => {
  const getVariantStyles = () => {
    if (disabled) {
      return theme.components.button.disabled;
    }

    switch (variant) {
      case 'secondary':
        return theme.components.button.secondary;
      case 'danger':
        return {
          background: theme.colors.error,
          color: theme.colors.white,
        };
      default:
        return theme.components.button.primary;
    }
  };

  const getSizeStyles = () => {
    switch (size) {
      case 'sm':
        return {
          padding: `${theme.spacing.sm} ${theme.spacing.md}`,
          fontSize: theme.fontSize.sm,
        };
      case 'lg':
        return {
          padding: `${theme.spacing.lg} ${theme.spacing.xl}`,
          fontSize: theme.fontSize.lg,
        };
      default:
        return {};
    }
  };

  const buttonStyle: React.CSSProperties = {
    ...theme.components.button.base,
    ...getVariantStyles(),
    ...getSizeStyles(),
    ...(fullWidth && { width: '100%' }),
    ...style,
  };

  return (
    <button style={buttonStyle} disabled={disabled} {...props}>
      {children}
    </button>
  );
};
