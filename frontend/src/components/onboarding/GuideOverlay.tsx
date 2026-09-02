import { useEffect, useState } from 'react';
import type { Tour } from './tours';
import './GuideOverlay.css';

interface GuideOverlayProps {
  tour: Tour;
  onDone: () => void;
}

/** The tour's guide card: bottom-center, one short step at a time,
 *  Next/Done and an always-present skip. Highlights the current
 *  step's [data-guide] element with a glow ring, polling briefly so
 *  targets inside not-yet-open modals light up when they appear. */
export default function GuideOverlay({ tour, onDone }: GuideOverlayProps) {
  const [index, setIndex] = useState(0);
  const step = tour.steps[index];
  const last = index === tour.steps.length - 1;

  useEffect(() => {
    if (!step?.target) return;
    let ringed: Element | null = null;
    const tryRing = () => {
      const el = document.querySelector(`[data-guide="${step.target}"]`);
      if (el && el !== ringed) {
        ringed?.classList.remove('guide-ring');
        el.classList.add('guide-ring');
        ringed = el;
      }
    };
    tryRing();
    const interval = window.setInterval(tryRing, 400);
    return () => {
      window.clearInterval(interval);
      ringed?.classList.remove('guide-ring');
    };
  }, [step?.target, index, tour.id]);

  if (!step) return null;

  return (
    <div className="guide-card" role="dialog" aria-label="Quick guide">
      <div className="guide-card__text">{step.text}</div>
      <div className="guide-card__controls">
        <span className="guide-card__progress">
          {index + 1} / {tour.steps.length}
        </span>
        <button
          className="guide-card__skip"
          onClick={onDone}
          title="End the guide"
        >
          Skip
        </button>
        <button
          className="guide-card__next primary"
          onClick={() => (last ? onDone() : setIndex(index + 1))}
        >
          {last ? 'Done' : 'Next'}
        </button>
      </div>
    </div>
  );
}
