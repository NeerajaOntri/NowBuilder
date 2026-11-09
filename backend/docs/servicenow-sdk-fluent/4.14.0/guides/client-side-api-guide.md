Version: 4.14.0

# Client-Side APIs

Reference for ServiceNow client-side APIs available in the browser. These APIs are shared across all Fluent APIs that execute client-side scripts — Client Scripts, UI Policy scripts (`scriptTrue`/`scriptFalse`), UI Actions (client-side), Catalog Client Scripts, and Catalog UI Policies.

Client-side scripts run in the browser and do not support JavaScript module imports (`import`/`export`). Use string scripts wrapped in the appropriate function signature (e.g., `function onCondition() { }` for UI Policies, `function onLoad() { }` for Client Scripts).

## g_form (GlideForm)

The `g_form` object provides methods to interact with the current form — reading and setting field values, controlling visibility and mandatory state, and displaying messages.

### Field Values

| Method | Description |
| `getValue(field)` | Get the current value of a field |
| `setValue(field, value)` | Set a field's value |
| `clearValue(field)` | Clear a field's value |

### Field Display

| Method | Description |
| `setVisible(field, bool)` | Show ( `true` ) or hide ( `false` ) a field |
| `setDisplay(field, bool)` | Show/hide a field (alternative to `setVisible` ) |
| `setReadOnly(field, bool)` | Make a field read-only ( `true` ) or editable ( `false` ) |
| `setMandatory(field, bool)` | Make a field required ( `true` ) or optional ( `false` ) |

### Choice Fields

| Method | Description |
| `addOption(field, value, label)` | Add an option to a choice/dropdown field |
| `clearOptions(field)` | Remove all options from a choice/dropdown field |

### Field Messages

| Method | Description |
| `showFieldMsg(field, message, type)` | Display a message next to a field ( `type` : `'error'` , `'info'` , `'warning'` ) |
| `hideFieldMsg(field)` | Remove the message next to a field |

### Form Messages

| Method | Description |
| `addInfoMessage(message)` | Display an info banner at the top of the form |
| `addErrorMessage(message)` | Display an error banner at the top of the form |
| `addWarningMessage(message)` | Display a warning banner at the top of the form |
| `clearMessages()` | Remove all banner messages from the form |

### Form State

| Method | Description |
| `isNewRecord()` | Returns `true` if the form is for a new (unsaved) record |
| `getUniqueValue()` | Get the sys_id of the current record |
| `hasField(field)` | Check if a field exists on the form |
| `submit()` | Programmatically submit the form |
| `getFormElement()` | Get the underlying DOM form element |
| `flash(field, color, count)` | Flash a field to draw user attention |

### References

| Method | Description |
| `getReference(field, callback)` | Get the referenced GlideRecord for a reference field. Legacy — prefer `GlideAjax` for complex lookups |

## g_user (GlideUser)

The `g_user` object provides information about the currently logged-in user.

| Method | Description |
| `hasRole(role)` | Check if the user has a specific role |
| `getFullName()` | Get the user's full display name |
| `getUserID()` | Get the user's sys_id |
| `getName()` | Get the user's username |

## Additional Client APIs

| API | Description |
| `g_scratchpad` | Object containing data passed from server-side Display Business Rules to the client. Use this to share server-computed values with client scripts without making additional AJAX calls |
| `g_modal` | Modal dialog controls (available in workspace context) |
| `g_service_catalog` | Service catalog form methods (available only in catalog item / record producer context) |

## Where client-side scripts appear in Fluent

| Fluent API | Script property | Function signature |
| Client Script ( `onLoad` ) | `script` | `function onLoad() { }` |
| Client Script ( `onChange` ) | `script` | `function onChange(control, oldValue, newValue, isLoading) { }` |
| Client Script ( `onSubmit` ) | `script` | `function onSubmit() { }` — return `false` to cancel |
| Client Script ( `onCellEdit` ) | `script` | `function onCellEdit(sysIDs, table, oldValues, newValue, callback) { }` |
| UI Policy | `scriptTrue` / `scriptFalse` | `function onCondition() { }` |
| UI Action (client-side) | `script` + `client.onClick` | Custom function name |
| Catalog Client Script | `script` | Same signatures as Client Script |
| Catalog UI Policy | `scriptTrue` / `scriptFalse` | `function onCondition() { }` |

## Constraints

- No module imports — `import`/`export` are not available in the browser. Use `Now.include()` to reference external `.js` files (see the `now-include-guide` topic)

- No third-party libraries — only platform-provided APIs (`g_form`, `g_user`, `GlideAjax`, etc.) are available

- Avoid synchronous server calls — use `GlideAjax` with async callbacks. `getXMLWait()` freezes the UI and is deprecated in scoped apps

- Guard `onChange` against initial load — always check `if (isLoading) return;` at the start of `onChange` scripts to prevent execution during form load
