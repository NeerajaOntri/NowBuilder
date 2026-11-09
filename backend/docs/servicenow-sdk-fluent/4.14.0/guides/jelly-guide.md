Version: 4.14.0

# Jelly

Guide to writing ServiceNow Jelly templates — the XML-based server-side templating language behind UI Macros (`sys_ui_macro`), custom form formatters, and Service Catalog custom variables. Covers the template preamble and namespaces, the two-phase evaluation model and its caching, keeping inline JavaScript XML-safe across passes, server-side `g2:evaluate` script, and conditional rendering.

## When to Use

- Writing the `.jelly.xml` content for a `UiMacro` (see the `ui-macro-guide` topic for the Fluent API, parameters, and formatter wiring)

- Deciding whether a value belongs in phase one (cached) or phase two (per request)

- Debugging a render-time XML parse error such as `The content of elements must consist of well-formed character data or markup.`

## Key Concepts

### Template Structure

Start every `.jelly.xml` file with the standard preamble:

```
<?xml version="1.0" encoding="utf-8" ?>
<j:jelly trim="false" xmlns:j="jelly:core" xmlns:g="glide" xmlns:j2="null" xmlns:g2="null">

    <!-- macro content -->

</j:jelly>
```

The namespaces:

- `j:` / `j2:` — core Jelly tags (`j:if`, `j:choose`, `j:set`, `j:while`)

- `g:` / `g2:` — Glide extensions (`g:evaluate`, `g:macro_invoke`, and every macro's own tag)

The unprefixed (`j:`, `g:`) namespaces run in Jelly's first pass and the `2`-suffixed ones (`j2:`, `g2:`) in the second:

- Phase 1 — `j:`/`g:` tags and `${...}` output: normally compiled and cached outside UI Pages. In formatter macros, use phase one only for stable invocation parameters and static content.

- Phase 2 — `j2:`/`g2:` tags and `$[...]` output: evaluated per request. Required for request-dependent server values.

`dynamic="true"` on phase-one `g:evaluate` is not a cache bypass — do not rely on it to refresh request-dependent values.

### XML-Safe JavaScript Across Jelly Passes

When a UI Macro is rendered through two-phase Jelly, phase-one output is parsed again as XML. XML entities inside inline `<script>` text are decoded during the first pass: `&amp;&amp;` becomes raw `&&`, and `&lt;` becomes raw `<`. The next pass can then reject that output because a bare `&` must begin an entity and `<` begins XML markup.

This failure appears only at render time. The source `.jelly.xml` can be well-formed and the Fluent build can succeed because the invalid characters do not exist until after phase one. The platform commonly reports:

```
The content of elements must consist of well-formed character data or markup.
```

Avoid entity-bearing JavaScript operators in phase-one macro output:

```
<!-- Avoid: entities decode into invalid XML before the next pass. -->
<script type="text/javascript">
    if (control &amp;&amp; index &lt; count) {
        update();
    }
</script>
```

Prefer equivalent control flow that contains no `&` or `<` characters:

```
<script type="text/javascript">
    if (control) {
        if (index >= 0) {
            update();
        }
    }
</script>
```

For loops that would normally use `<`, iterate downward with `i >= 0` when that preserves the intended behavior. Extract shared helpers such as `listen()` when several fields need the same event-binding fallback, rather than duplicating branches that can reintroduce unsafe operators.

JavaScript comments are not exempt. The XML parser sees the entire `<script>` body as element text content — it does not understand JavaScript syntax. A comment that mentions the avoided characters reintroduces them:

```
<!-- BAD: the comment itself contains bare < and & -->
<script type="text/javascript">
    /* Avoids < and & operators. */
    if (count >= 0) { update(); }
</script>
```

Unlike the entity-decoding case above, these are raw characters in the source file, so the build catches them first: it reports an `xml content may be malformed` warning (the content is still written as-is, so the failure appears when the form renders). Rewrite comments to describe intent without using the reserved characters:

```
<!-- GOOD: comment describes the constraint without using the characters -->
<script type="text/javascript">
    /* Avoids XML-reserved characters in operators. */
    if (count >= 0) { update(); }
</script>
```

This applies to single-line comments (`// ...`) as well as block comments (`/* ... */`). Any bare `<` or `&` anywhere in the `<script>` element — code or comment — is a parse error.

Double escaping (`&amp;amp;`, `&amp;lt;`) can preserve an entity through another pass, but it is fragile and should not be the default pattern. The outer CDATA used to store `UiMacro.xml` does not protect text produced between Jelly passes. For labels and other values already on a form, keep legitimate characters such as `&` in the data and write them client-side with `textContent`; do not rename business labels solely to work around Jelly parsing.

### Server-Side Script

`<g2:evaluate jelly="true">` runs server-side JavaScript in phase two, once per request — the right phase for request-dependent values such as a live `GlideAggregate`. Inside the block, parameters arrive as `jelly.jvar_*`, and the `var` attribute receives the value of the block's last expression. Emit the result with `$[...]`:

```
<g2:evaluate var="jvar_count" jelly="true">
    var gr = new GlideAggregate(jelly.jvar_table + '');
    gr.addAggregate('COUNT');
    gr.query();
    var count = 0;
    if (gr.next()) {
        count = parseInt(gr.getAggregate('COUNT'), 10) || 0;
    }
    count;
</g2:evaluate>

<div>$[jvar_count] records</div>
```

Treat any caller-supplied value as untrusted: pass table and field names only, never raw user input that could alter the query.

### Conditional Rendering

```
<j:if test="${!gs.nil(jvar_message)}">
    <div>${jvar_message}</div>
</j:if>

<j:choose>
    <j:when test="${jvar_type == 'danger'}">
        <span style="color: #c00;">Error</span>
    </j:when>
    <j:otherwise>
        <span>Info</span>
    </j:otherwise>
</j:choose>
```

## Avoidance

- Never use phase-one `g:evaluate` for request-dependent formatter data — phase-one output is compiled and cached; use phase two (`g2:evaluate` / `$[...]`) or client rendering.

- Never treat `dynamic="true"` as a phase-one cache bypass — it is not one.

- Never place `&&` or `<` anywhere in an inline `<script>` body — including comments — the XML parser sees the entire element as text content and does not understand JavaScript syntax. Raw `<` or `&` in the source (code or comment) produces a malformed-XML warning at build time and fails at render time; the entity-escaped forms (`&lt;`, `&amp;&amp;`) pass the build but decode back to raw characters between Jelly passes and fail at render time. Prefer nested conditions, `>=`/descending loops, and shared listener helpers, and describe the constraint in comments without using the reserved characters.

- Never pass caller-supplied text into an evaluate block's query beyond table and field names — treat every `jelly.jvar_*` value as untrusted input.

## Related Topics

- `ui-macro-guide` — `UiMacro` API, `jvar_` parameters, client-rendered formatter values, and examples

- `uimacro-api` — full `UiMacro` property reference

- `form-formatters-guide` — placing a macro on a form as a formatter

- `service-catalog-variables-guide` — catalog custom variables backed by a macro
