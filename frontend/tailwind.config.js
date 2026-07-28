/** @type {import('tailwindcss').Config} */

// Tokens are stored in index.css as space-separated RGB channels
// (`--surface: 255 255 255`) so Tailwind's opacity modifiers keep working:
// `bg-surface/70` becomes `rgb(255 255 255 / 0.7)`.
const ch = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // The resolved theme lives on <html data-theme="light|dark">. Pointing
  // Tailwind's `dark:` variant at the same attribute keeps one source of truth
  // while leaving an escape hatch for genuinely asymmetric cases.
  darkMode: ['selector', '[data-theme="dark"]'],
  theme: {
    extend: {
      colors: {
        canvas: ch('--canvas'),
        surface: {
          DEFAULT: ch('--surface'),
          2: ch('--surface-2'),
          3: ch('--surface-3'),
          inverse: ch('--surface-inverse'),
        },
        overlay: ch('--overlay'),
        line: {
          // Decorative dividers and panel edges (exempt from the 3:1 minimum).
          DEFAULT: ch('--line'),
          // Interactive boundaries — inputs, focusable cards. Meets 3:1 in both
          // themes, replacing the old rgba(255,255,255,0.12) at ~1.2:1.
          strong: ch('--line-strong'),
        },
        fg: {
          DEFAULT: ch('--fg'),
          secondary: ch('--fg-secondary'),
          muted: ch('--fg-muted'),
          'on-solid': ch('--fg-on-solid'),
        },
        brand: {
          // The full indigo ramp stays available for gradients and one-offs.
          50: '#f0f3ff',
          100: '#e0e7ff',
          200: '#c7d2fe',
          300: '#a5b4fc',
          400: '#818cf8',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
          800: '#3730a3',
          900: '#312e81',
          950: '#1e1b4b',
          // Semantic aliases — prefer these in components.
          solid: ch('--brand-solid'),
          'solid-hover': ch('--brand-solid-hover'),
          fg: ch('--brand-fg'),
          subtle: ch('--brand-subtle'),
          'subtle-fg': ch('--brand-subtle-fg'),
        },
        accent: { solid: ch('--accent-solid'), fg: ch('--accent-fg'), subtle: ch('--accent-subtle') },
        success: { solid: ch('--success-solid'), fg: ch('--success-fg'), subtle: ch('--success-subtle') },
        warning: { solid: ch('--warning-solid'), fg: ch('--warning-fg'), subtle: ch('--warning-subtle') },
        danger: { solid: ch('--danger-solid'), fg: ch('--danger-fg'), subtle: ch('--danger-subtle') },
        focus: ch('--focus'),
        // NOTE: the previous partial `emerald` override (only 50/500/600/700)
        // has been removed. `extend` merges per-key, so it shadowed 4 shades and
        // left 100-400/800-950 on Tailwind's defaults — a half-custom ramp.
        // Use the success-* tokens instead; Tailwind's own emerald is intact.
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      // Full scale override so line-height and tracking travel with each size.
      // Ratio is ~1.13 through the UI range (11-22px), widening for display.
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem', letterSpacing: '0.02em' }], // 11px - uppercase eyebrows/badges ONLY
        xs: ['0.75rem', { lineHeight: '1.125rem', letterSpacing: '0.01em' }], // 12px - metadata, timestamps
        sm: ['0.875rem', { lineHeight: '1.375rem' }], // 14px - dense UI, buttons
        base: ['0.9375rem', { lineHeight: '1.5rem' }], // 15px - DEFAULT BODY COPY
        lg: ['1.0625rem', { lineHeight: '1.625rem' }], // 17px - lead paragraphs
        xl: ['1.1875rem', { lineHeight: '1.75rem', letterSpacing: '-0.005em' }], // 19px - card titles
        '2xl': ['1.375rem', { lineHeight: '1.875rem', letterSpacing: '-0.01em' }], // 22px - section headings
        '3xl': ['1.75rem', { lineHeight: '2.125rem', letterSpacing: '-0.015em' }], // 28px - page h1
        '4xl': ['2.125rem', { lineHeight: '2.375rem', letterSpacing: '-0.02em' }], // 34px - hero h1
        '5xl': ['2.625rem', { lineHeight: '2.875rem', letterSpacing: '-0.025em' }],
        '6xl': ['3.25rem', { lineHeight: '3.5rem', letterSpacing: '-0.03em' }],
      },
      boxShadow: {
        glass: 'var(--glass-shadow)',
        'glass-hover': 'var(--glass-shadow-hover)',
        e1: 'var(--shadow-e1)',
        e2: 'var(--shadow-e2)',
        e3: 'var(--shadow-e3)',
      },
      ringColor: { DEFAULT: 'rgb(var(--focus))' },
      ringOffsetColor: { DEFAULT: 'rgb(var(--canvas))' },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        float: 'float 6s ease-in-out infinite',
        // The three modals already referenced `animate-fade-in`; without this
        // entry the class was a silent no-op and they appeared instantly.
        'fade-in': 'fade-in 0.18s cubic-bezier(0.16, 1, 0.3, 1) both',
      },
      keyframes: {
        float: {
          '0%, 100%': { transform: 'translateY(0px)' },
          '50%': { transform: 'translateY(-8px)' },
        },
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px) scale(0.985)' },
          to: { opacity: '1', transform: 'none' },
        },
      },
    },
  },
  plugins: [],
};
