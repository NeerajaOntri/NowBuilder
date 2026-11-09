import { useEffect, useMemo, useRef } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({ gfm: true, breaks: false });

/** Renders the assistant's Markdown safely (the model's output is never trusted as HTML).
 *  Code blocks get a Copy button, since scripts are what people take from the chat. */
export function Markdown({ text }) {
  const ref = useRef(null);
  const html = useMemo(() => {
    const raw = marked.parse(text, { async: false });
    return DOMPurify.sanitize(raw, { USE_PROFILES: { html: true } });
  }, [text]);
  useEffect(() => {
    const root = ref.current;
    if (!root) return;
    root.querySelectorAll('pre').forEach((pre) => {
      if (pre.querySelector('.code-copy')) return;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'code-copy';
      btn.textContent = 'Copy';
      btn.addEventListener('click', async () => {
        try {
          await navigator.clipboard.writeText(pre.querySelector('code')?.textContent ?? pre.textContent ?? '');
          btn.textContent = 'Copied';
        } catch {
          btn.textContent = 'Copy blocked';
        }
        setTimeout(() => { btn.textContent = 'Copy'; }, 1600);
      });
      pre.appendChild(btn);
    });
  }, [html]);
  return <div ref={ref} className="md" dangerouslySetInnerHTML={{ __html: html }} />;
}
