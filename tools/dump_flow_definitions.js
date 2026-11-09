/* Reads the SDK's own built-in flow action definitions (declarative .now.ts files that ship in
   @servicenow/sdk-core) and prints them as JSON. The column helpers are stubbed: each records
   its own name as the input's type. */
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const base = process.argv[2];                       // extracted package root
const dirs = {
  action: path.join(base, 'src/external/flow/built-ins/actions/core'),
  logic: path.join(base, 'src/external/flow/built-ins/flow-logic'),
  trigger: path.join(base, 'src/external/flow/built-ins/triggers'),
};

function evaluate(file) {
  const src = fs.readFileSync(file, 'utf8')
    .replace(/^\s*import\s[\s\S]*?from\s+'[^']*'\s*$/gm, '')   // single- and multi-line imports
    .replace(/\s+as\s+(Record<[^>]*>|[\w.]+(<[^>]*>)?)/g, '')   // TypeScript casts
    .replace(/^export const (\w+) = /m, 'captured.$1 = ');
  const captured = {};
  const helper = (name) => (opts = {}) => ({ type: name.replace(/Column$/, ''), ...opts });
  const scope = new Proxy({ captured }, {
    has: () => true,
    get: (t, k) => (k === 'captured' ? captured : (k === Symbol.unscopables ? undefined : helper(String(k)))),
  });
  vm.runInNewContext(`with (scope) { ${src} }`, { scope });
  return captured;
}

const shape = (io) => Object.fromEntries(Object.entries(io || {}).map(([k, v]) => [k, {
  label: v.label ?? null, type: v.type, mandatory: Boolean(v.mandatory),
  ...(v.referenceTable ? { reference: v.referenceTable } : {}),
  ...(v.choices ? { choices: v.choices } : {}),
  ...(v.dependent ? { dependent: v.dependent } : {}),
}]));

const out = {};
for (const [kind, dir] of Object.entries(dirs)) {
  if (!fs.existsSync(dir)) continue;
  out[kind] = {};
  for (const f of fs.readdirSync(dir).filter((f) => f.endsWith('.now.ts'))) {
    const key = f.replace('.now.ts', '');
    try {
      const got = evaluate(path.join(dir, f));
      const def = got[key] ?? Object.values(got)[0];
      out[kind][key] = { name: def?.name, sys_id: def?.$id, description: def?.description,
                         inputs: shape(def?.inputs), outputs: shape(def?.outputs) };
    } catch (e) { out[kind][key] = { error: String(e.message).slice(0, 160) }; }
  }
}
process.stdout.write(JSON.stringify(out, null, 1));
