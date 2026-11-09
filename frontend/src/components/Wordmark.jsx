import { Link } from 'react-router-dom';

/** Two connected nodes: a requirement flowing into a component. */
export function Logo({ size = 26 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 26 26" aria-hidden="true">
      <rect x="1" y="1" width="24" height="24" rx="6" fill="#1d5fd6" />
      <circle cx="8.5" cy="9" r="2.6" fill="#fff" />
      <circle cx="17.5" cy="17" r="2.6" fill="#fff" />
      <path d="M8.5 11.6v1.9a3.5 3.5 0 0 0 3.5 3.5h2.9" stroke="#fff" strokeWidth="1.8" fill="none" strokeLinecap="round" />
    </svg>
  );
}

export function Wordmark({ to = '/' }) {
  return (
    <Link to={to} className="wordmark" aria-label="nowBuilder home">
      <Logo /> <span className="wm-text">nowBuilder</span>
    </Link>
  );
}
