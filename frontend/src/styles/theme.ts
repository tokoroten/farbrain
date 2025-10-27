/**
 * Theme configuration for consistent styling across the application
 */

export const colors = {
  // Primary colors
  primary: '#667eea',
  primaryLight: '#a5b4fc',
  primaryDark: '#4c51bf',

  // Secondary colors
  secondary: '#764ba2',

  // Neutral colors
  white: '#ffffff',
  background: '#f5f5f5',
  backgroundLight: '#fafafa',
  text: '#333',
  textLight: '#666',
  textMuted: '#999',

  // Border colors
  border: '#e0e0e0',
  borderLight: '#f0f0f0',

  // Status colors
  success: '#10b981',
  error: '#ef4444',
  warning: '#f59e0b',
  info: '#3b82f6',

  // Special colors
  cyan: '#06b6d4',
  gold: '#fbbf24',
};

export const spacing = {
  xs: '0.25rem',
  sm: '0.5rem',
  md: '0.75rem',
  lg: '1rem',
  xl: '1.5rem',
  '2xl': '2rem',
  '3xl': '3rem',
};

export const fontSize = {
  xs: '0.7rem',
  sm: '0.875rem',
  base: '1rem',
  lg: '1.1rem',
  xl: '1.25rem',
  '2xl': '1.5rem',
  '3xl': '1.875rem',
};

export const borderRadius = {
  sm: '0.25rem',
  md: '0.5rem',
  lg: '0.75rem',
  xl: '1rem',
  full: '9999px',
};

export const shadows = {
  sm: '0 1px 2px rgba(0, 0, 0, 0.05)',
  base: '0 1px 3px rgba(0, 0, 0, 0.1)',
  md: '0 2px 8px rgba(0, 0, 0, 0.1)',
  lg: '0 4px 12px rgba(0, 0, 0, 0.15)',
  xl: '0 10px 25px rgba(0, 0, 0, 0.2)',
};

/**
 * Common component styles
 */
export const components = {
  card: {
    background: colors.white,
    borderRadius: borderRadius.md,
    boxShadow: shadows.md,
    padding: spacing.lg,
    border: `1px solid ${colors.border}`,
  },

  button: {
    base: {
      padding: `${spacing.md} ${spacing.lg}`,
      borderRadius: borderRadius.md,
      border: 'none',
      cursor: 'pointer',
      fontWeight: '600',
      fontSize: fontSize.base,
      transition: 'all 0.2s ease',
    },
    primary: {
      background: colors.primary,
      color: colors.white,
    },
    secondary: {
      background: colors.white,
      color: colors.primary,
      border: `2px solid ${colors.primary}`,
    },
    disabled: {
      background: colors.borderLight,
      color: colors.textMuted,
      cursor: 'not-allowed',
    },
  },

  input: {
    base: {
      padding: spacing.md,
      border: `1px solid ${colors.border}`,
      borderRadius: borderRadius.md,
      fontSize: fontSize.base,
      width: '100%',
      boxSizing: 'border-box' as const,
    },
    focus: {
      outline: 'none',
      borderColor: colors.primary,
      boxShadow: `0 0 0 3px rgba(102, 126, 234, 0.1)`,
    },
  },

  container: {
    maxWidth: '1200px',
    margin: '0 auto',
    padding: spacing.lg,
  },

  section: {
    background: colors.white,
    borderRadius: borderRadius.lg,
    boxShadow: shadows.md,
    padding: spacing.xl,
    marginBottom: spacing.xl,
  },

  header: {
    background: colors.white,
    borderBottom: `1px solid ${colors.border}`,
    padding: spacing.lg,
    boxShadow: shadows.sm,
  },
};

/**
 * Layout utilities
 */
export const layout = {
  flexCenter: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  flexBetween: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  flexColumn: {
    display: 'flex',
    flexDirection: 'column' as const,
  },
};

/**
 * Typography utilities
 */
export const typography = {
  heading1: {
    fontSize: fontSize['3xl'],
    fontWeight: '700',
    color: colors.text,
    marginBottom: spacing.lg,
  },
  heading2: {
    fontSize: fontSize['2xl'],
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.md,
  },
  heading3: {
    fontSize: fontSize.xl,
    fontWeight: '600',
    color: colors.text,
    marginBottom: spacing.md,
  },
  body: {
    fontSize: fontSize.base,
    color: colors.text,
    lineHeight: '1.5',
  },
  small: {
    fontSize: fontSize.sm,
    color: colors.textLight,
  },
};

export const theme = {
  colors,
  spacing,
  fontSize,
  borderRadius,
  shadows,
  components,
  layout,
  typography,
};

export default theme;
