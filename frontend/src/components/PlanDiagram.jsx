// Flowcharts of a plan, like Now Assist's flow view, drawn from the plan itself (nothing assumed):
// 1. how nowBuilder built it, step by step (request → read the instance → design → checks → deploy);
// 2. what each component does at run time: start, decisions (diamonds, Yes / No), actions, loops
//    drawn back to where they repeat, and the end.

const TYPE = {
  flow: 'Flow', business_rule: 'Business rule', script_include: 'Script include', client_script: 'Client script',
  ui_policy: 'UI policy', ui_action: 'UI action', notification: 'Notification', data_policy: 'Data policy',
  scheduled_job: 'Scheduled job', system_property: 'System property', event: 'Event', script_action: 'Script action',
  table: 'Table', field: 'Field', catalog_item: 'Catalog item', record_producer: 'Record producer',
};

const yes = (v) => String(v) === 'true';
// An encoded query in words: ownerISNOTEMPTY^state!=7 -> "owner is not empty AND state ≠ 7".
const OPS = [['ISNOTEMPTY', ' is not empty'], ['ISEMPTY', ' is empty'], ['VALCHANGES', ' changes'],
  ['CHANGESTO', ' changes to '], ['CHANGESFROM', ' changes from '], ['NOT IN', ' is not one of '], ['NOT LIKE', " doesn't contain "],
  ['STARTSWITH', ' starts with '], ['ENDSWITH', ' ends with '], ['LIKE', ' contains '], ['IN', ' is one of '],
  ['!=', ' ≠ '], ['>=', ' ≥ '], ['<=', ' ≤ '], ['=', ' = '], ['>', ' > '], ['<', ' < ']];
const term = (t) => {
  const pill = t.replace(/\{\{\s*(?:trigger\.current|step\d+\.Record)\.([^}]+)\}\}/g, '$1');
  for (const [op, words] of OPS) {
    const i = pill.indexOf(op);
    if (i > 0) return pill.slice(0, i) + words + pill.slice(i + op.length).replace(/,/g, ', ');
  }
  return pill;
};
const cond = (q) => (q ? String(q).replace(/\^EQ$/, '').split('^OR').map((o) => o.split('^').map(term).join(' AND ')).join(' OR ') : '');

function ordered(components) {
  const byId = new Map(components.map((c) => [c.id, c]));
  const seen = new Set();
  const out = [];
  const visit = (c) => {
    if (!c || seen.has(c.id)) return;
    seen.add(c.id);
    (c.dependsOn ?? []).forEach((d) => visit(byId.get(d)));
    out.push(c);
  };
  components.forEach(visit);
  return out;
}

// ---------- what each component does, as chart items ----------
// item: { kind: 'start'|'process'|'decision'|'end', text, no?: text, back?: index of the item a "No" loops to }

function flowItems(gen) {
  const rec = gen?.record ?? {};
  const steps = gen?.steps ?? [];
  const items = [{ kind: 'start', text: `${rec.trigger || 'Trigger'}${rec.table ? ` on ${rec.table}` : ''}` }];
  if (rec.trigger_condition) items.push({ kind: 'decision', text: `${cond(rec.trigger_condition)}?`, no: "Flow doesn't run" });
  const kids = (n) => steps.filter((s) => Number(s.inside) === Number(n));
  const walk = (list) => list.forEach((s) => {
    const name = String(s.name ?? '');
    const inner = kids(s.step);
    if (/until/i.test(name)) {
      const first = items.length;
      walk(inner);
      items.push({ kind: 'decision', text: `${cond(s.condition)}?`, no: 'Repeat', back: first });
    } else if (/^(if|else if)$/i.test(name.trim())) {
      items.push({ kind: 'decision', text: `${cond(s.condition)}?`, no: 'Skip these steps' });
      walk(inner);
    } else if (/^else$/i.test(name.trim())) {
      items.push({ kind: 'process', text: 'Otherwise:' });
      walk(inner);
    } else if (/for each/i.test(name)) {
      items.push({ kind: 'process', text: `For each ${String(s.items ?? 'record').replace(/[{}]/g, '')}` });
      walk(inner);
    } else if (/wait/i.test(name)) {
      const d = typeof s.duration === 'object' ? Object.entries(s.duration).map(([k, v]) => `${v} ${k}`).join(' ') : s.duration;
      items.push({ kind: 'process', text: `Wait ${d ?? ''}`.trim() });
    } else {
      items.push({ kind: 'process', text: s.detail ? `${name}: ${s.detail}` : name });
    }
  });
  walk(steps.filter((s) => !s.inside));
  items.push({ kind: 'end', text: 'End' });
  return items;
}

function componentItems(c) {
  const r = c.generated?.record ?? {};
  const what = c.purpose || c.name;
  switch (c.type) {
    case 'flow': return flowItems(c.generated);
    case 'business_rule': {
      const ops = ['insert', 'update', 'delete', 'query'].filter((o) => yes(r[`action_${o}`])).join(' / ');
      return [{ kind: 'start', text: `${r.when || 'before'} ${ops || 'save'} on ${r.collection || c.table}` },
        ...(r.filter_condition || r.condition ? [{ kind: 'decision', text: `${cond(r.filter_condition) || r.condition}?`, no: "Rule doesn't run" }] : []),
        { kind: 'process', text: what }, { kind: 'end', text: 'Record saved' }];
    }
    case 'client_script': {
      const start = r.type === 'onChange' ? `${r.field_name || r.field} changes on the form` : `${r.type || 'Form'} on ${r.table || c.table}`;
      return [{ kind: 'start', text: start },
        ...(r.type === 'onChange' ? [{ kind: 'decision', text: 'Form still loading?', yesText: 'No', noText: 'Yes', no: 'Do nothing' }] : []),
        { kind: 'process', text: what }, { kind: 'end', text: 'Done' }];
    }
    case 'ui_policy': {
      const acts = (c.generated?.actions ?? []).map((a) => [a.field, yes(a.mandatory) || a.mandatory === 'true' ? 'mandatory' : '',
        a.visible === 'false' ? 'hidden' : '', a.disabled === 'true' ? 'read-only' : ''].filter(Boolean).join(' '));
      return [{ kind: 'start', text: `Form ${yes(r.on_load) ? 'loads or ' : ''}changes on ${r.table || c.table}` },
        { kind: 'decision', text: `${cond(r.conditions)}?`, no: yes(r.reverse_if_false) ? 'Undo the actions' : 'No change' },
        { kind: 'process', text: acts.length ? `Make ${acts.join(', ')}` : what }, { kind: 'end', text: 'Done' }];
    }
    case 'notification':
      return [{ kind: 'start', text: r.event_name ? `Event ${r.event_name}` : yes(r.triggered_by_flow) ? 'A flow sends it' : `Record ${[yes(r.action_insert) && 'inserted', yes(r.action_update) && 'updated'].filter(Boolean).join(' or ')} on ${r.collection || c.table}` },
        ...(r.condition ? [{ kind: 'decision', text: `${cond(r.condition)}?`, no: 'No email' }] : []),
        { kind: 'process', text: `Email ${[r.recipient_fields, r.recipient_groups, r.recipient_users].filter(Boolean).join(', ') || 'recipients'}: ${r.subject || ''}` },
        { kind: 'end', text: 'Sent' }];
    case 'scheduled_job':
      return [{ kind: 'start', text: `Runs ${r.run_type || ''} ${r.run_time ? `at ${String(r.run_time).slice(-8)}` : ''}`.trim() },
        { kind: 'process', text: what }, { kind: 'end', text: 'Done' }];
    case 'ui_action':
      return [{ kind: 'start', text: `User clicks “${r.name || c.name}”` },
        ...(r.condition ? [{ kind: 'decision', text: `${r.condition}?`, no: 'Button hidden' }] : []),
        { kind: 'process', text: what }, { kind: 'end', text: 'Done' }];
    case 'script_action':
      return [{ kind: 'start', text: `Event ${r.event_name || ''} fires` }, { kind: 'process', text: what }, { kind: 'end', text: 'Done' }];
    default:
      return [{ kind: 'start', text: `${TYPE[c.type] ?? c.type} ${c.table ? `on ${c.table}` : ''}`.trim() },
        { kind: 'process', text: what }, { kind: 'end', text: 'Ready to use' }];
  }
}

// ---------- SVG flowchart ----------

const W = 560, CX = 220, BOX = 250, SIDE_X = 430, SIDE_W = 120, LINE = 15, GAP = 30;

function wrap(text, max) {
  const words = String(text ?? '').split(/\s+/).filter(Boolean);
  const lines = [];
  let cur = '';
  words.forEach((w) => {
    if ((cur + ' ' + w).trim().length > max && cur) { lines.push(cur); cur = w; } else cur = (cur + ' ' + w).trim();
  });
  if (cur) lines.push(cur);
  return lines.slice(0, 5).map((l, i, a) => (i === 4 && a.length === 5 && words.join(' ').length > l.length * 5 ? `${l}…` : l));
}

function Chart({ items, label }) {
  let y = 10;
  const laid = items.map((it) => {
    const lines = wrap(it.text, it.kind === 'decision' ? 22 : 34);
    const h = it.kind === 'decision' ? Math.max(70, lines.length * LINE + 40) : lines.length * LINE + 22;
    const node = { ...it, lines, y, h };
    y += h + GAP;
    return node;
  });
  const height = y - GAP + 14;
  const backs = laid.filter((n) => n.back !== undefined);
  return (
    <svg className="fc" viewBox={`0 0 ${W} ${height}`} role="img" aria-label={label}>
      <defs>
        <marker id="fc-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
          <path d="M0 0L10 5L0 10z" fill="#7a8aa3" />
        </marker>
      </defs>
      {laid.map((n, i) => {
        const next = laid[i + 1];
        const midY = n.y + n.h / 2;
        return (
          <g key={i}>
            {next && <line x1={CX} y1={n.y + n.h} x2={CX} y2={next.y} className="fc-edge" markerEnd="url(#fc-arrow)" />}
            {next && n.kind === 'decision' && <text x={CX + 8} y={n.y + n.h + 18} className="fc-label">{n.back !== undefined ? 'Yes, done' : (n.yesText ?? 'Yes')}</text>}
            {n.kind === 'decision' && n.no && n.back === undefined && (
              <>
                <line x1={CX + 100} y1={midY} x2={SIDE_X} y2={midY} className="fc-edge" markerEnd="url(#fc-arrow)" />
                <text x={CX + 108} y={midY - 6} className="fc-label">{n.noText ?? 'No'}</text>
                <rect x={SIDE_X} y={midY - 18} width={SIDE_W} height={36} rx="18" className="fc-side" />
                {wrap(n.no, 16).slice(0, 2).map((l, k, a) => (
                  <text key={k} x={SIDE_X + SIDE_W / 2} y={midY + 4 + (k - (a.length - 1) / 2) * 13} className="fc-text small" textAnchor="middle">{l}</text>
                ))}
              </>
            )}
            {n.kind === 'decision'
              ? <polygon points={`${CX},${n.y} ${CX + 100},${midY} ${CX},${n.y + n.h} ${CX - 100},${midY}`} className="fc-decision" />
              : <rect x={CX - BOX / 2} y={n.y} width={BOX} height={n.h} rx={n.kind === 'process' ? 6 : n.h / 2}
                  className={n.kind === 'process' ? 'fc-process' : 'fc-terminal'} />}
            {n.lines.map((l, k) => (
              <text key={k} x={CX} y={midY + 5 + (k - (n.lines.length - 1) / 2) * LINE} textAnchor="middle"
                className={`fc-text${n.kind === 'start' || n.kind === 'end' ? ' strong' : ''}`}>{l}</text>
            ))}
          </g>
        );
      })}
      {backs.map((n, i) => {
        const to = laid[n.back];
        const x = CX - BOX / 2 - 22 - i * 8;
        const fromY = n.y + n.h / 2;
        const toY = to.y + to.h / 2;
        return (
          <g key={`b${i}`}>
            <path d={`M${CX - 100} ${fromY} H${x} V${toY} H${CX - (to.kind === 'decision' ? 100 : BOX / 2)}`} className="fc-edge loop" markerEnd="url(#fc-arrow)" />
            <text x={x + 4} y={fromY - 6} className="fc-label loop">{n.no ?? 'No'}</text>
          </g>
        );
      })}
    </svg>
  );
}

// ---------- how nowBuilder built it ----------

function buildSteps(plan, comps) {
  const tables = [...new Set(comps.map((c) => c.table).filter(Boolean))];
  const errors = comps.reduce((n, c) => n + (c.problems ?? []).filter((p) => p.severity === 'error').length, 0);
  const deployed = comps.filter((c) => c.deploy?.status === 'deployed').length;
  return [
    { kind: 'start', text: `Request: ${plan.title}` },
    { kind: 'process', text: `Read the instance${tables.length ? `: ${tables.join(', ')}` : ''} and what already runs there` },
    { kind: 'process', text: `Designed ${comps.length} component${comps.length === 1 ? '' : 's'} in ${plan.application && plan.application !== 'global' ? plan.application : 'Global'}: ${comps.map((c) => TYPE[c.type] ?? c.type).join(', ')}` },
    { kind: 'decision', text: 'Checks against the instance passed?', no: errors ? `${errors} to fix (Fix with AI)` : 'Fix with AI' },
    ...(plan.deployment?.update_set
      ? [{ kind: 'process', text: `Deployed ${deployed} of ${comps.length} into update set ${plan.deployment.update_set.name}` },
        { kind: 'end', text: plan.deployment.status === 'deployed' ? 'Live in the instance' : `Deployment: ${plan.deployment.status}` }]
      : [{ kind: 'end', text: 'Ready: Approve, then Deploy' }]),
  ];
}

export function PlanDiagram({ plan }) {
  const comps = ordered(plan.components ?? []);
  return (
    <div className="diagram" aria-label="Plan diagrams">
      <section className="fc-card">
        <h4>How nowBuilder built it</h4>
        <Chart items={buildSteps(plan, comps)} label="How nowBuilder built this plan" />
      </section>
      {comps.map((c) => (
        <section key={c.id} className="fc-card">
          <h4><span className="dg-type">{TYPE[c.type] ?? c.type}</span> {c.name}
            {c.deploy?.status === 'deployed' && <span className="dg-status ok"> · deployed</span>}</h4>
          <Chart items={componentItems(c)} label={`What ${c.name} does`} />
        </section>
      ))}
    </div>
  );
}
