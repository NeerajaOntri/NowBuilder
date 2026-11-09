import { useEffect, useRef, useState } from 'react';

/** Modal dialog: focus moves inside, Escape and the backdrop close it, focus returns on close. */
export function Dialog({ title, onClose, children, wide, labelledBy = 'dialog-title' }

) {
  const box = useRef(null);
  useEffect(() => {
    const before = document.activeElement;
    const first = box.current?.querySelector('[data-autofocus], input, button.btn-primary, button');
    first?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
      if (e.key === 'Tab' && box.current) {  // keep focus inside
        const f = [...box.current.querySelectorAll('button:not([disabled]), input, a[href], [tabindex="0"]')];
        if (!f.length) return;
        if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f[f.length - 1].focus(); }
        else if (!e.shiftKey && document.activeElement === f[f.length - 1]) { e.preventDefault(); f[0].focus(); }
      }
    };
    document.addEventListener('keydown', onKey);
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.removeEventListener('keydown', onKey); document.body.style.overflow = overflow; before?.focus(); };
  }, [onClose]);
  return (
    <div className="dialog-backdrop" onMouseDown={(e) => { if (e.target === e.currentTarget) onClose(); }}>
      <div ref={box} className={`dialog${wide ? ' dialog-wide' : ''}`} role="dialog" aria-modal="true" aria-labelledby={labelledBy}>
        <div className="dialog-head">
          <h2 id={labelledBy}>{title}</h2>
          <button type="button" className="icon-btn" aria-label="Close" onClick={onClose}>
            <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true"><path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" /></svg>
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

/** Simple yes / no confirmation. */
export function ConfirmDialog({ title, children, confirmLabel, danger, onCancel, onConfirm }

) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const go = async () => {
    setBusy(true); setError(null);
    try { await onConfirm(); } catch (e) { setError(e.message); setBusy(false); }
  };
  return (
    <Dialog title={title} onClose={busy ? () => {} : onCancel}>
      <div className="dialog-body">{children}{error && <div className="alert alert-error small" role="alert">{error}</div>}</div>
      <div className="dialog-actions">
        <button type="button" className="btn" disabled={busy} onClick={onCancel}>Cancel</button>
        <button type="button" className={`btn ${danger ? 'btn-danger-solid' : 'btn-primary'}`} disabled={busy} onClick={go}>{busy ? 'Working…' : confirmLabel}</button>
      </div>
    </Dialog>
  );
}
