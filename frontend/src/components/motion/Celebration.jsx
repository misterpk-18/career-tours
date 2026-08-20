import React, { useEffect, useRef } from 'react';
import { useReducedMotion } from '../../hooks/useReducedMotion';

/**
 * A confetti burst for a good score.
 *
 * Canvas rather than a few hundred animated DOM nodes: the browser draws this in
 * one composited layer instead of laying out 140 absolutely positioned divs, and
 * it disappears completely when it finishes rather than leaving a swarm of empty
 * elements behind a result card.
 *
 * No dependency. A confetti library is 15-30KB to do arithmetic that is forty
 * lines, and this bundle already carries a syntax highlighter.
 *
 * Skipped entirely under prefers-reduced-motion — a canvas animation is exactly
 * the kind of thing that setting exists to stop, and the CSS block in index.css
 * cannot reach it.
 */
const COLOURS = ['--brand-solid', '--accent-solid', '--success-solid', '--brand-fg', '--accent-fg'];
const PIECES = 140;
const DRAG = 0.992;

// Velocities are a FRACTION OF THE CONTAINER, not a pixel count.
//
// The first version used fixed pixel speeds — up to 22 device px per frame
// upward against a gravity of 0.28 — which works in a full-window burst and
// fails completely in a result card. Measured in the card this actually lives
// in (219 CSS px tall), every piece cleared the top edge inside 0.3s and the
// remaining 2.3s animated an empty canvas. The burst was invisible and the code
// looked correct.
//
// Solving peak = v0^2 / 2g for a rise of PEAK_RISE * height gives the launch
// speed below, so the arc fits whatever box it is dropped into.
const PEAK_RISE = 0.34;
const GRAVITY_FACTOR = 0.0006;

export const Celebration = ({ active, duration = 2600 }) => {
  const canvas = useRef(null);
  const reduced = useReducedMotion();

  useEffect(() => {
    if (!active || reduced || !canvas.current) return undefined;

    const element = canvas.current;
    const context = element.getContext('2d');
    const scale = window.devicePixelRatio || 1;

    const resize = () => {
      element.width = element.offsetWidth * scale;
      element.height = element.offsetHeight * scale;
    };
    resize();

    // Token colours read once from the resolved stylesheet, so the burst matches
    // whichever theme is active instead of hard-coding two palettes.
    const styles = getComputedStyle(document.documentElement);
    const palette = COLOURS.map((token) => `rgb(${styles.getPropertyValue(token).trim()})`);

    const gravity = element.height * GRAVITY_FACTOR;
    // The launch speed that peaks at PEAK_RISE of the container's height.
    const launch = Math.sqrt(2 * gravity * element.height * PEAK_RISE);

    const pieces = Array.from({ length: PIECES }, () => ({
      x: element.width * (0.5 + (Math.random() - 0.5) * 0.5),
      y: element.height * 0.62,
      vx: (Math.random() - 0.5) * launch * 1.1,
      // 0.55-1.0 of the full launch speed, so the burst has depth instead of a
      // single uniform front.
      vy: -launch * (0.55 + Math.random() * 0.45),
      size: (Math.random() * 5 + 3) * scale,
      spin: (Math.random() - 0.5) * 0.3,
      angle: Math.random() * Math.PI,
      colour: palette[Math.floor(Math.random() * palette.length)],
    }));

    const started = performance.now();
    let frame;

    const tick = (now) => {
      const elapsed = now - started;
      const life = Math.min(1, elapsed / duration);

      context.clearRect(0, 0, element.width, element.height);

      for (const piece of pieces) {
        piece.vy += gravity;
        piece.vx *= DRAG;
        piece.x += piece.vx;
        piece.y += piece.vy;
        piece.angle += piece.spin;

        context.save();
        context.translate(piece.x, piece.y);
        context.rotate(piece.angle);
        // Fade out over the last third rather than vanishing mid-flight.
        context.globalAlpha = life < 0.66 ? 1 : 1 - (life - 0.66) / 0.34;
        context.fillStyle = piece.colour;
        context.fillRect(-piece.size / 2, -piece.size / 2, piece.size, piece.size * 0.62);
        context.restore();
      }

      if (life < 1) {
        frame = requestAnimationFrame(tick);
      } else {
        context.clearRect(0, 0, element.width, element.height);
      }
    };

    frame = requestAnimationFrame(tick);
    window.addEventListener('resize', resize);

    return () => {
      cancelAnimationFrame(frame);
      window.removeEventListener('resize', resize);
    };
  }, [active, duration, reduced]);

  if (!active || reduced) return null;

  return (
    <canvas
      ref={canvas}
      aria-hidden="true"
      className="pointer-events-none absolute inset-0 h-full w-full"
    />
  );
};

export default Celebration;
