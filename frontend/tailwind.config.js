/** @type {import('tailwindcss').Config} */

// Tokens are stored in index.css as space-separated RGB channels
// (`--surface: 255 255 255`) so Tailwind's opacity modifiers keep working:
// `bg-surface/70` becomes `rgb(255 255 255 / 0.7)`.
const ch = (name) => `rgb(var(${name}) / <alpha-value>)`;

export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  // No darkMode variant. There is one palette — Solarized Dark — so `dark:`
  // would be a class that can never match, and its absence means a stray one is
  // a build-time nothing rather than a style that silently never applies.
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
        // Semantic aliases only. The raw 50-950 indigo ramp was removed: it had
        // zero users, and its presence invited `bg-brand-400` in place of a token
        // that means something. `accent` (purple) is gone entirely — see the
        // colour contract at the top of index.css.
        brand: {
          solid: ch('--brand-solid'),
          'solid-hover': ch('--brand-solid-hover'),
          fg: ch('--brand-fg'),
          subtle: ch('--brand-subtle'),
          'subtle-fg': ch('--brand-subtle-fg'),
        },
        // ACHIEVEMENT ONLY — XP, levels, streaks, badges, celebration. See the
        // revised colour contract at the top of index.css. Kept narrow so amber
        // never stops meaning "you earned something".
        accent: {
          solid: ch('--accent-solid'),
          'solid-hover': ch('--accent-solid-hover'),
          fg: ch('--accent-fg'),
          subtle: ch('--accent-subtle'),
          'subtle-fg': ch('--accent-subtle-fg'),
        },
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
      // Two structural radii plus pills. `md`, `2xl` and `3xl` are deliberately
      // absent: a card previously nested 3xl -> 2xl -> xl -> lg -> full, and
      // dropping the keys means `rounded-2xl` compiles to nothing rather than
      // quietly creeping back in.
      borderRadius: {
        none: '0',
        sm: '0.25rem',
        DEFAULT: '0.5rem',
        lg: '0.5rem',
        xl: '0.75rem',
        // Presentation surfaces only — the result hero, the level card. `md` and
        // `3xl` stay absent on purpose so they compile to nothing instead of
        // quietly reintroducing a five-radius nest.
        '2xl': '1rem',
        full: '9999px',
      },
      boxShadow: {
        e1: 'var(--shadow-e1)',
        e2: 'var(--shadow-e2)',
        e3: 'var(--shadow-e3)',
      },
      ringColor: { DEFAULT: 'rgb(var(--focus))' },
      ringOffsetColor: { DEFAULT: 'rgb(var(--canvas))' },
      // `float` was dead code and `pulse-slow` drove a decorative 2px dot on
      // every skill-gap chip. `fade-in` is the app's only animation now, and it
      // is covered by the prefers-reduced-motion block in index.css.
      // MOTION
      //
      // Every entry below is covered by the prefers-reduced-motion block in
      // index.css, which flattens animation and transition durations to 0.01ms
      // globally — so adding motion here cannot override a user's stated
      // preference. That block is why these are `animation` utilities rather
      // than inline JS tweens.
      //
      // One easing curve for everything that enters (a decelerating cubic) and
      // one springy overshoot for things that CONFIRM (a press landing, a tick
      // appearing). Two curves, used consistently, read as one system; five
      // curves read as five people.
      transitionTimingFunction: {
        enter: 'cubic-bezier(0.16, 1, 0.3, 1)',
        spring: 'cubic-bezier(0.34, 1.56, 0.64, 1)',
      },
      animation: {
        'fade-in': 'fade-in 0.18s cubic-bezier(0.16, 1, 0.3, 1) both',
        // Entrances. `rise-in` is the workhorse; the stagger comes from
        // animation-delay applied per item by the Reveal component.
        'rise-in': 'rise-in 0.34s cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-in-right': 'slide-in-right 0.28s cubic-bezier(0.16, 1, 0.3, 1) both',
        'slide-in-left': 'slide-in-left 0.28s cubic-bezier(0.16, 1, 0.3, 1) both',
        // Confirmations — something the student did just landed.
        pop: 'pop 0.32s cubic-bezier(0.34, 1.56, 0.64, 1) both',
        'pop-tick': 'pop-tick 0.4s cubic-bezier(0.34, 1.56, 0.64, 1) both',
        // A wrong answer in PRACTICE only. Never in a graded run, where no
        // verdict is revealed at all.
        shake: 'shake 0.36s ease-in-out both',
        // The last minute of a timed sitting.
        'pulse-urgent': 'pulse-urgent 1s ease-in-out infinite',
        // Achievement surfaces.
        'flame-flicker': 'flame-flicker 2.4s ease-in-out infinite',
        'sheen': 'sheen 2.2s ease-in-out infinite',
        'ring-in': 'ring-in 0.9s cubic-bezier(0.16, 1, 0.3, 1) both',
      },
      keyframes: {
        'fade-in': {
          from: { opacity: '0', transform: 'translateY(4px) scale(0.985)' },
          to: { opacity: '1', transform: 'none' },
        },
        'rise-in': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'none' },
        },
        'slide-in-right': {
          from: { opacity: '0', transform: 'translateX(16px)' },
          to: { opacity: '1', transform: 'none' },
        },
        'slide-in-left': {
          from: { opacity: '0', transform: 'translateX(-16px)' },
          to: { opacity: '1', transform: 'none' },
        },
        pop: {
          '0%': { opacity: '0', transform: 'scale(0.9)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        'pop-tick': {
          '0%': { opacity: '0', transform: 'scale(0.4) rotate(-12deg)' },
          '70%': { opacity: '1', transform: 'scale(1.12) rotate(2deg)' },
          '100%': { opacity: '1', transform: 'scale(1) rotate(0)' },
        },
        shake: {
          '0%, 100%': { transform: 'translateX(0)' },
          '20%': { transform: 'translateX(-5px)' },
          '40%': { transform: 'translateX(5px)' },
          '60%': { transform: 'translateX(-3px)' },
          '80%': { transform: 'translateX(3px)' },
        },
        'pulse-urgent': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.45' },
        },
        'flame-flicker': {
          '0%, 100%': { transform: 'scale(1) rotate(-1deg)', opacity: '1' },
          '50%': { transform: 'scale(1.08) rotate(1.5deg)', opacity: '0.92' },
        },
        sheen: {
          '0%': { transform: 'translateX(-120%)' },
          '60%, 100%': { transform: 'translateX(220%)' },
        },
        'ring-in': {
          from: { 'stroke-dashoffset': 'var(--ring-empty)' },
          to: { 'stroke-dashoffset': 'var(--ring-offset-target)' },
        },
      },
      backgroundImage: {
        // EARNED surfaces only, per the revised contract. Theme-aware via the
        // token, because light and dark need genuinely different tints here — an
        // alpha wash disappears on white and an opaque tint looks pasted-on over
        // dark. See --gradient-earned in index.css.
        'earned': 'var(--gradient-earned)',
        'earned-strong': 'linear-gradient(135deg, rgb(var(--brand-solid)), rgb(var(--accent-solid)))',
        'xp': 'linear-gradient(90deg, rgb(var(--brand-solid)), rgb(var(--accent-solid)))',
        'sheen': 'linear-gradient(100deg, transparent, rgb(255 255 255 / 0.28), transparent)',
      },
    },
  },
  plugins: [],
};
