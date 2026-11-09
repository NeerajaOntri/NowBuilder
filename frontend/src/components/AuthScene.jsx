import { useEffect, useRef } from 'react';
import gsap from 'gsap';

/**
 * Sign-in showcase: nowBuilder's own characters, animated with GSAP.
 * - Nimbus: a cloud-shaped helper bot that reads the requirement and builds the plan.
 * - Pip: a small delivery drone that carries the checked changes to the instance.
 * Respects prefers-reduced-motion (everything is shown in its final state, no motion).
 */
const ROWS = [
  { api: 'Set VIP priority', type: 'Business rule' },
  { api: 'CallerUtils', type: 'Script include' },
  { api: 'Show VIP banner', type: 'Client script' },
  { api: 'Category on resolve', type: 'UI policy' },
];
const SAYS = ['Reading your requirement…', 'Reading incident fields', 'Checking existing business rules', 'Fixed one with AI', 'All checked. Ready for review!'];

export function AuthScene() {
  const root = useRef(null);
  const said = useRef(null);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    const ctx = gsap.context(() => {
      if (reduced) {
        gsap.set('.sc-row-state', { opacity: 1 });
        gsap.set('.sc-row .ok', { opacity: 1 });
        gsap.set('.sc-row .err', { opacity: 0 });
        gsap.set('.sc-bubble', { opacity: 1, scale: 1 });
        if (said.current) said.current.textContent = SAYS[SAYS.length - 1];
        return;
      }
      // entrance
      gsap.from('.sc-copy > *', { y: 18, opacity: 0, duration: 0.7, stagger: 0.12, delay: 0.15, ease: 'power3.out' });
      gsap.from('.nimbus', { y: 60, scale: 0.85, opacity: 0, duration: 1, delay: 0.3, ease: 'back.out(1.6)', transformOrigin: '50% 100%' });
      gsap.from('.pip', { x: 160, y: -80, opacity: 0, duration: 1.1, delay: 0.7, ease: 'power2.out' });
      gsap.from('.sc-card', { y: 30, opacity: 0, duration: 0.8, delay: 0.55, ease: 'power3.out' });
      gsap.from('.sc-chip', { scale: 0, opacity: 0, duration: 0.5, stagger: 0.12, delay: 1, ease: 'back.out(2)' });

      // idle life
      gsap.to('.nimbus', { y: -12, duration: 2.2, ease: 'sine.inOut', yoyo: true, repeat: -1 });
      gsap.to('.nimbus-shadow', { scaleX: 0.82, opacity: 0.35, duration: 2.2, ease: 'sine.inOut', yoyo: true, repeat: -1, transformOrigin: '50% 50%' });
      gsap.to('.nimbus-antenna-tip', { opacity: 0.35, duration: 0.8, yoyo: true, repeat: -1, ease: 'sine.inOut' });
      gsap.to('.nimbus-arm-wave', { rotate: -28, duration: 0.35, yoyo: true, repeat: 5, delay: 1.4, ease: 'sine.inOut', transformOrigin: '10% 90%' });
      const blink = gsap.timeline({ repeat: -1, repeatDelay: 2.6 });
      blink.to('.nimbus-eye', { scaleY: 0.1, duration: 0.08, transformOrigin: '50% 50%' }).to('.nimbus-eye', { scaleY: 1, duration: 0.12 });
      gsap.to('.pip', { x: '+=26', y: '-=18', rotate: 6, duration: 1.8, ease: 'sine.inOut', yoyo: true, repeat: -1, delay: 1.8 });
      gsap.to('.pip-prop', { scaleX: 0.15, duration: 0.07, yoyo: true, repeat: -1, transformOrigin: '50% 50%', ease: 'none' });
      gsap.to('.sc-cloud', { x: (i) => (i % 2 ? -40 : 40), duration: (i) => 9 + i * 3, ease: 'sine.inOut', yoyo: true, repeat: -1 });
      gsap.to('.sc-chip', { y: (i) => (i % 2 ? 8 : -8), duration: (i) => 2 + i * 0.4, ease: 'sine.inOut', yoyo: true, repeat: -1 });

      // the story: Nimbus checks each row, one fails, gets fixed, Pip flies off to deploy
      const story = gsap.timeline({ repeat: -1, repeatDelay: 1.6, delay: 1.6 });
      const say = (i) => () => { if (said.current) said.current.textContent = SAYS[i]; };
      story.call(say(0)).set('.sc-row-state', { opacity: 0 }).set('.sc-row .ok, .sc-row .err', { opacity: 0 })
        .set('.sc-row', { backgroundColor: 'rgba(255,255,255,0)' })
        .to('.sc-bubble', { scale: 1, opacity: 1, duration: 0.3, ease: 'back.out(2)' })
        .call(say(1), undefined, '+=1.1');
      ROWS.forEach((_, i) => {
        const row = `.sc-row:nth-child(${i + 1})`;
        story.to(row, { backgroundColor: 'rgba(29,95,214,0.08)', duration: 0.2 }, i === 0 ? '+=0.6' : '+=0.25')
          .to(`${row} .sc-row-state`, { opacity: 1, duration: 0.2 })
          .to(`${row} ${i === 3 ? '.err' : '.ok'}`, { opacity: 1, scale: 1, duration: 0.3, ease: 'back.out(3)' }, '<')
          .to(row, { backgroundColor: 'rgba(29,95,214,0)', duration: 0.3 });
        if (i === 0) story.call(say(2));
      });
      story.call(say(3), undefined, '+=0.5')
        .to('.nimbus-arm-wave', { rotate: -40, duration: 0.25, yoyo: true, repeat: 1, transformOrigin: '10% 90%' })
        .to('.sc-row:nth-child(4) .err', { opacity: 0, duration: 0.2 })
        .to('.sc-row:nth-child(4) .ok', { opacity: 1, duration: 0.3, ease: 'back.out(3)' })
        .call(say(4), undefined, '+=0.3')
        .to('.sc-card', { boxShadow: '0 0 0 3px rgba(18,128,90,0.35), 0 18px 40px rgba(21,35,59,0.12)', duration: 0.4, yoyo: true, repeat: 1 })
        .to('.pip-box', { y: -6, duration: 0.2, yoyo: true, repeat: 1 }, '+=0.2')
        .to('.pip', { x: '+=240', y: '-=140', opacity: 0, duration: 1, ease: 'power2.in' }, '+=0.4')
        .set('.pip', { x: -200, y: 60 })
        .to('.pip', { x: 0, y: 0, opacity: 1, duration: 1.2, ease: 'power2.out' }, '+=1');
    }, el);
    return () => ctx.revert();
  }, []);

  return (
    <div className="sc" ref={root} aria-hidden="true">
      <svg className="sc-cloud c1" viewBox="0 0 120 50"><path d="M20 45a18 18 0 0 1 4-35 24 24 0 0 1 45-4 20 20 0 0 1 32 16 14 14 0 0 1-3 23z" /></svg>
      <svg className="sc-cloud c2" viewBox="0 0 120 50"><path d="M20 45a18 18 0 0 1 4-35 24 24 0 0 1 45-4 20 20 0 0 1 32 16 14 14 0 0 1-3 23z" /></svg>
      <svg className="sc-cloud c3" viewBox="0 0 120 50"><path d="M20 45a18 18 0 0 1 4-35 24 24 0 0 1 45-4 20 20 0 0 1 32 16 14 14 0 0 1-3 23z" /></svg>

      <div className="sc-copy">
        <h2>From requirement to deployed, with a helper at every step.</h2>
        <p>Describe what you need. nowBuilder reads your instance, designs business rules, script includes and UI logic the ServiceNow way, and checks them before anything changes.</p>
      </div>

      <div className="sc-stage">
        <span className="sc-chip k1">GlideRecord</span>
        <span className="sc-chip k2">Business rules</span>
        <span className="sc-chip k3">UI policies</span>
        <span className="sc-chip k4">Validated</span>

        {/* Nimbus, the cloud helper */}
        <div className="nimbus-wrap">
          <div className="sc-bubble"><span ref={said}>{SAYS[0]}</span></div>
          <svg className="nimbus" viewBox="0 0 260 230" width="260" height="230">
            <defs>
              <linearGradient id="nb-body" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0" stopColor="#ffffff" />
                <stop offset="1" stopColor="#e3eeff" />
              </linearGradient>
              <radialGradient id="nb-glow"><stop offset="0" stopColor="#ffd27a" /><stop offset="1" stopColor="#ffb547" stopOpacity="0" /></radialGradient>
            </defs>
            <line x1="130" y1="38" x2="130" y2="16" stroke="#9fb4d6" strokeWidth="4" strokeLinecap="round" />
            <circle className="nimbus-antenna-tip" cx="130" cy="12" r="14" fill="url(#nb-glow)" />
            <circle cx="130" cy="12" r="6" fill="#ffb547" />
            {/* arms */}
            <g className="nimbus-arm-hold">
              <path d="M58 150c-18 6-26 20-22 32" stroke="#cfdcf2" strokeWidth="16" strokeLinecap="round" fill="none" />
            </g>
            <g className="nimbus-arm-wave">
              <path d="M204 140c18-6 28-24 26-40" stroke="#cfdcf2" strokeWidth="16" strokeLinecap="round" fill="none" />
              <circle cx="230" cy="96" r="11" fill="#ffffff" stroke="#cfdcf2" strokeWidth="3" />
            </g>
            {/* body */}
            <g fill="url(#nb-body)" stroke="#cfdcf2" strokeWidth="3">
              <circle cx="82" cy="120" r="50" />
              <circle cx="178" cy="122" r="46" />
              <circle cx="130" cy="96" r="60" />
              <rect x="56" y="118" width="148" height="66" rx="33" />
            </g>
            <rect x="57" y="120" width="146" height="60" rx="30" fill="url(#nb-body)" />
            {/* face */}
            <rect x="80" y="92" width="100" height="60" rx="28" fill="#15233b" />
            <ellipse className="nimbus-eye" cx="112" cy="120" rx="8" ry="11" fill="#6fe3ff" />
            <ellipse className="nimbus-eye" cx="148" cy="120" rx="8" ry="11" fill="#6fe3ff" />
            <path d="M118 136q12 9 24 0" stroke="#6fe3ff" strokeWidth="4" strokeLinecap="round" fill="none" />
            <circle cx="92" cy="138" r="5" fill="#ff9fb0" opacity="0.55" />
            <circle cx="168" cy="138" r="5" fill="#ff9fb0" opacity="0.55" />
            {/* tablet */}
            <g transform="translate(14 168) rotate(-8)">
              <rect width="58" height="40" rx="7" fill="#1d5fd6" />
              <rect x="7" y="8" width="30" height="4" rx="2" fill="#bcd3ff" />
              <rect x="7" y="17" width="40" height="4" rx="2" fill="#bcd3ff" />
              <rect x="7" y="26" width="22" height="4" rx="2" fill="#5fd3a1" />
            </g>
          </svg>
          <div className="nimbus-shadow" />
        </div>

        {/* Pip, the delivery drone */}
        <svg className="pip" viewBox="0 0 120 120" width="110" height="110">
          <ellipse className="pip-prop" cx="60" cy="18" rx="34" ry="5" fill="#9fb4d6" />
          <rect x="57" y="18" width="6" height="12" rx="3" fill="#6b7890" />
          <circle cx="60" cy="50" r="22" fill="#1d5fd6" />
          <path d="M40 50a20 20 0 0 1 40 0" fill="#3b7bf0" />
          <circle cx="52" cy="50" r="6" fill="#fff" /><circle cx="68" cy="50" r="6" fill="#fff" />
          <circle cx="53" cy="51" r="3" fill="#15233b" /><circle cx="69" cy="51" r="3" fill="#15233b" />
          <path d="M54 61q6 4 12 0" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" fill="none" />
          <path d="M52 71l-4 12M68 71l4 12" stroke="#6b7890" strokeWidth="2.5" strokeLinecap="round" />
          <g className="pip-box">
            <rect x="42" y="82" width="36" height="28" rx="5" fill="#ffb547" />
            <path d="M42 92h36M60 82v28" stroke="#e0932a" strokeWidth="3" />
          </g>
        </svg>

        {/* what they're working on */}
        <div className="sc-card">
          <div className="sc-card-head"><strong>VIP incident handling</strong><span>Demo instance</span></div>
          <ul>
            {ROWS.map((r) => (
              <li className="sc-row" key={r.api}>
                <span className="api">{r.api}</span>
                <span className="type">{r.type}</span>
                <span className="sc-row-state">
                  <svg className="ok" viewBox="0 0 20 20" width="18" height="18"><circle cx="10" cy="10" r="9" /><path d="M6 10.4l2.7 2.6L14 7.6" /></svg>
                  <svg className="err" viewBox="0 0 20 20" width="18" height="18"><circle cx="10" cy="10" r="9" /><path d="M7 7l6 6M13 7l-6 6" /></svg>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
