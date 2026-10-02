/** Case Pulse mark: a gold ring with a pulse line. Pure SVG, themed through currentColor. */
export function Logo({ className = "size-6" }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" className={`text-primary ${className}`} aria-hidden>
      <circle cx="12" cy="12" r="10.25" stroke="currentColor" strokeWidth="1.5" opacity="0.55" />
      <path d="M4.5 12.5h3.2l2-5 3.4 9.5 2.1-4.5h4.3" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
