Version: 4.14.0

# UI Actions

Guide for creating ServiceNow UI Actions using the Fluent API. UI Actions are buttons, links, or context menu items that execute server-side or client-side logic on forms and lists.

## When to Use

- Adding buttons to a form (e.g., "Approve", "Mark Resolved", "Save & Close")

- Adding buttons or links to a list view (banner buttons, row-level actions)

- Adding context menu items (right-click options) on forms or lists

- Executing server-side scripts on button click (update records, trigger workflows)

- Executing client-side scripts (confirmations, field validation, redirects)

- Creating workspace-compatible actions with V2 button rendering

## Instructions

- Decide applicability first: Choose whether the action can be used on forms, lists, or both using the `form` and `list` nested objects.

- Choose client vs server: Set `client.isClient: true` for client-side scripts (confirmations, redirects). Leave unset or `false` for server-side scripts (record updates, GlideRecord queries). Server module scripts (`import`/`export`) only work with server-side actions.

- For client-side actions: Use `client.onClick` to call the function, and define the function in `script`. Example: `client.onClick: 'myFunction()'` and `script: 'function myFunction() { ... }'`

- Set visibility: Use `showInsert` and `showUpdate` to control when the action appears (new records vs existing records). Use `condition` for dynamic visibility based on record state.

- Restrict by role: Use the `roles` array to limit which users see the action.

- Style appropriately: Use `'primary'` for main actions, `'destructive'` for dangerous operations (delete, cancel), `'unstyled'` for secondary actions.

- Workspace compatibility: For workspace-enabled actions, set `workspace.isConfigurableWorkspace: true` and if creating a client-side script, additionally provide `workspace.clientScriptV2`. Whenever `workspace.isConfigurableWorkspace` is `true`, also set `workspace.showFormButtonV2` or `workspace.showFormMenuButtonV2` to `true` — otherwise the action has no visible entry point in Workspace.

- Workspace integration records: When `workspace.isConfigurableWorkspace: true`, Two additional records: `sys_ux_form_action`, `sys_ux_form_action_layout_item`must be created

## API Reference

For the complete property reference including all `form`, `list`, `client`, and `workspace` nested objects with their types and descriptions, see the `uiaction-api` topic.

## Key Concepts

### Form vs List Applicability

| Property | Type | Description |
| `form` | `true | Object` | Set to `true` for the action to be executable in a form via programmatic calls without appearing in the UI (only available in UI26). When set as an object, you can configure its display options on a form. |
| `form.showButton` | `boolean` | Adds a button to the form header |
| `form.showLink` | `boolean` | Adds a link below the form |
| `form.showContextMenu` | `boolean` | Adds to the right-click menu on form |
| `form.style` | `string` | `'primary'` , `'destructive'` , or `'unstyled'` |
| `list` | `true | Object` | Set to `true` for the action to be executable in a list via programmatic calls without appearing in the UI (only available in UI26). When set as an object, you can configure its display options on a list. |
| `list.showButton` | `boolean` | Adds a button at the bottom of the list |
| `list.showBannerButton` | `boolean` | Adds a button in the list banner |
| `list.showLink` | `boolean` | Adds a link in the list |
| `list.showContextMenu` | `boolean` | Adds to the right-click menu on list rows |
| `list.showListChoice` | `boolean` | Adds to dropdown menus of choice fields |
| `list.showSaveWithFormButton` | `boolean` | Shows the button when saving the form from a related list |
| `list.style` | `string` | `'primary'` , `'destructive'` , or `'unstyled'` |

### Client-Side vs Server-Side

| Aspect | Server-Side (default) | Client-Side ( `client.isClient: true` ) |
| Script runs | On the server | In the browser |
| `current` access | Full GlideRecord | Not available (use `g_form` ) |
| Module support | Yes ( `import` / `export` ) | No — string scripts only |
| Script property | `script` (string or module function) | `script` (function definition) + `client.onClick` (function call) |
| Use for | Record updates, GlideRecord queries | Confirmations, redirects, form validation |

Client-side pattern: Define the function in `script`, call it in `client.onClick`:

```
client: { isClient: true, onClick: 'myFunction()' },
script: `function myFunction() { /* logic here */ }`
```

Function naming: Use unique, descriptive function names for each UI Action on a table. In UI16, multiple actions with the same function name on the same form can conflict (e.g., two actions both defining `function validate()`). While Workspace/Lit UI handles this correctly with closures, UI16 may execute the wrong function. Use specific names like `validateIncidentForm()` or `approveRequestAction()` instead of generic names.

### Visibility Controls

| Property | Description |
| `showInsert` | Show on new records (insert mode) |
| `showUpdate` | Show on existing records (update mode) |
| `showQuery` | Show when a list filter is applied |
| `showMultipleUpdate` | Show when multiple records are selected (bulk edit) |
| `condition` | Script/condition controlling dynamic visibility (e.g., `"current.state == 'new'"` ) |
| `roles` | Array of role names restricting who sees the action |
| `includeInViews` | Only show in these specific views |
| `excludeFromViews` | Hide from these specific views |

### Additional Properties

| Property | Description |
| `isolateScript` | Run the script in an isolated scope (prevents global variable conflicts) |
| `messages` | Array of user-facing messages accessible via `getMessage()` or `getMessages()` in client scripts |
| `comments` | Internal developer notes (not visible to end users) |
| `overrides` | Reference to another UI Action for domain separation - used when a UI Action on a subdomain overrides a UI Action on a parent domain |
| `order` | Numeric value controlling button position (lower numbers appear first, default is 100) |
| `hint` | Tooltip text shown when user hovers over the button |

### Workspace Compatibility

For actions to work in ServiceNow Workspace, set workspace properties:

```
workspace: {
    isConfigurableWorkspace: true,
    showFormButtonV2: true,
    showFormMenuButtonV2: true,
    clientScriptV2: `function onClick(g_form) {
        // V2 client script
    }`,
}
```

When `workspace.isConfigurableWorkspace: true` is set on a UI Action, Additional integration records should be created in `sys_ux_form_action` and `sys_ux_form_action_layout_item`. Button in workspace will not be visible unless these records are created.

Required: whenever `workspace.isConfigurableWorkspace` is `true`, at least one of `workspace.showFormButtonV2` or `workspace.showFormMenuButtonV2` must also be `true`. If both are left `false`/unset, the UI Action is enabled for Workspace but has no button or menu entry rendered, so it becomes unreachable.

#### Creating Workspace Integration Records

Before creating these records: Query the instance for an existing `sys_ux_form_action` record matching the target `ui_action` (sys_id) and `table`. Only create the `sys_ux_form_action` (and its corresponding `sys_ux_form_action_layout_item`) if no matching record is found.

- 
sys_ux_form_action - Links the UI action to workspace

| Property | Type | Description |
| `table` | `string` | Table the UI action belongs to |
| `ui_action` | `string` | Reference to the UI action record |
| `action_type` | `string` | Fixed value: `'ui_action'` |
| `active` | `boolean` | Fixed value: `true` |
| `name` | `string` | From UI action's `name` field |

- 
sys_ux_form_action_layout_item - Defines how the action appears in workspace

| Property | Type | Description |
| `table` | `string` | Table the UI action belongs to |
| `name` | `string` | From UI action's `name` field |
| `label` | `string` | From UI action's `name` field |
| `color` | `string` | Mapped from UI action's `form_style` |
| `overflow` | `boolean` | From UI action's `form_menu_button_v2` |
| `order` | `number` | From UI action's `order` |
| `active` | `boolean` | Fixed value: `true` |
| `item_type` | `string` | Fixed value: `'action'` |
| `action` | `string` | Reference to the `sys_ux_form_action` record |

Color mapping (from UI action `form_style` to workspace `color`):

- `'primary'` → `'primary'`

- `'primary-ai'` → `'primary-ai'`

- `'secondary-ai'` → `'secondary-ai'`

- `'destructive'` → `'primary-negative'`

- `'unstyled'` → `'secondary'`

### Table Inheritance and Overrides

UI Actions use table inheritance and deduplication to determine what gets shown to users:

Inheritance:

- UI Actions defined on a parent table (e.g., `task`) automatically appear on child tables (e.g., `incident`, `problem`)

- Child tables inherit all parent UI Actions unless explicitly overridden

Deduplication:

- By action name: If a child table defines a UI Action with the same `actionName` as a parent action, the child action overrides the parent

- By name AND action name: If two actions have the same `name` and `actionName`, ServiceNow displays only the one with the lower `order` value

Override pattern (table inheritance):

- Identify the parent action's `actionName` (query `sys_ui_action` table filtered by `table` and `name` if needed)

- Create a child action with the same `actionName` as the parent — this automatically overrides the parent action

- Set a lower `order` value if you want your action to take precedence over siblings with matching `name` and `actionName`

## Examples

### Combined Form and List Button with Client-Side Confirmation

UI Action with both form and list placement, including client-side confirmation before server-side processing:

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['confirm-delete'],
    table: 'x_myapp_request', // custom table
    name: 'Delete',
    actionName: 'confirm_delete',
    showUpdate: true,
    showMultipleUpdate: true,
    form: {
        showButton: true,
        style: 'primary',
    },
    list: {
        showBannerButton: true,
        style: 'primary',
    },
    condition: "current.state == '4'",
    client: {
        isClient: true,
        onClick: 'confirmAndDelete()',
    },
    script: `
var viewType;
var selectedSysId;

function confirmAndDelete() {
    selectedSysId = typeof g_list != 'undefined' ? g_list.getChecked() : g_form.getUniqueValue();
    viewType = typeof g_list != 'undefined' ? 'list' : 'form';
    if(!selectedSysId || selectedSysId.length ==0)
        return;
    deleteListEntryRecords();
}

function deleteListEntryRecords() {
    var dialogClass = typeof GlideModal != 'undefined' ? GlideModal : GlideDialogWindow;
    var dlg = new dialogClass('delete_document_list_entry');
    dlg.setTitle(new GwtMessage().getMessage('Confirmation'));
    dlg.setWidth(300);
    dlg.setPreference('sysparm_list_view', viewType);
    if (viewType == 'list') {
        dlg.setPreference('sysparm_document_list_entry_sys_id_list', selectedSysId);
    } else
        dlg.setPreference('sysparm_document_list_entry_sys_id', selectedSysId);
    dlg.render();
}
    `,
})
```

### Form Button with Server-Side Script

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['mark-resolved'],
    table: 'x_myapp_request',
    name: 'Mark as Resolved',
    actionName: 'mark_resolved',
    showUpdate: true,
    form: {
        showButton: true,
        style: 'primary',
    },
    condition: "current.state != 'resolved'",
    script: `current.state = 'resolved';
current.resolution_code = 'Solved (Permanently)';
current.update();
action.setRedirectURL(current);`,
})
```

### List Banner Button with Role Restriction

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['bulk-assign'],
    table: 'x_myapp_task',
    name: 'Assign to Me',
    actionName: 'bulk_assign',
    showUpdate: true,
    showMultipleUpdate: true,
    list: {
        showBannerButton: true,
        showButton: true,
        style: 'primary',
    },
    roles: ['itil'],
    script: `current.assigned_to = gs.getUserID();
current.update();`,
})
```

### Client-Side Confirmation with Workspace Support

```
import { UiAction, Record } from '@servicenow/sdk/core'

// UI Action definition
const deleteRequest = UiAction({
    $id: Now.ID['confirm-delete'],
    table: 'x_myapp_request',
    name: 'Delete Request',
    actionName: 'confirm_delete',
    showUpdate: true,
    form: {
        showButton: true,
        style: 'destructive',
    },
    client: {
        isClient: true,
        onClick: 'confirmDelete()', // call the function defined in script
    },
    workspace: {
        isConfigurableWorkspace: true,
        showFormButtonV2: true,
        clientScriptV2: `function onClick(g_form) {
            if (confirm('Are you sure you want to delete this request?')) {
                g_form.submit();
            }
        }`,
    },
    script: `function confirmDelete() {
        if (confirm('Are you sure you want to delete this request?')) {
            gsftSubmit(null, g_form.getFormElement(), 'confirm_delete');
        }
    }`,
})

// Workspace integration records (required — must be created explicitly)

// 1. sys_ux_form_action - Links UI action to workspace
const deleteFormAction = Record({
    $id: Now.ID['confirm-delete-form-action'],
    table: 'sys_ux_form_action',
    data: {
        table: 'x_myapp_request',
        ui_action: deleteRequest, // reference to UI action above
        action_type: 'ui_action',
        active: true,
        name: 'Delete Request' // UI Action name
    }
})

// 2. sys_ux_form_action_layout_item - Defines workspace appearance
Record({
    $id: Now.ID['confirm-delete-layout-item'],
    table: 'sys_ux_form_action_layout_item',
    data: {
        table: 'x_myapp_request',
        name: 'Delete Request',
        label: 'Delete Request',              // from action's name
        color: 'primary-negative',            // mapped from style: 'destructive'
        overflow: false,                      // depends on UI Action showFormMenuButtonV2
        order: 100,                          // default order
        active: true,
        item_type: 'action',
        action: deleteFormAction
    }
})
```

### Server-Side Module Script

```
import { UiAction } from '@servicenow/sdk/core'
import { escalateRequest } from '../../server/actions/escalate-request'

UiAction({
    $id: Now.ID['escalate'],
    table: 'x_myapp_request',
    name: 'Escalate',
    actionName: 'escalate_request',
    showUpdate: true,
    form: {
        showButton: true,
        style: 'destructive',
    },
    roles: ['itil', 'admin'],
    order: 200,
    script: escalateRequest,
})
```

### Workspace-Enabled Approval Action with Complete Integration

```
import { UiAction, Record } from '@servicenow/sdk/core'

// UI Action with workspace support
UiAction({
    $id: Now.ID['approve-request'],
    table: 'x_myapp_approval',
    name: 'Approve',
    actionName: 'approve_request',
    showUpdate: true,
    form: {
        showButton: true,
        style: 'primary',
    },
    workspace: {
        isConfigurableWorkspace: true,
        showFormButtonV2: true,
        clientScriptV2: `function onClick(g_form) {
            var comments = prompt('Enter approval comments (optional):');
            if (comments !== null) {
                g_form.setValue('approval_comments', comments);
                g_form.submit();
            }
        }`,
    },
    condition: "current.state == 'pending'",
    roles: ['approver_user'],
    order: 100,
    script: `
        current.state = 'approved';
        current.approved_by = gs.getUserID();
        current.approved_date = new GlideDateTime();
        current.update();
        gs.addInfoMessage('Request approved successfully');
        action.setRedirectURL(current);
    `,
})

// Workspace integration records

// 1. Form Action - links UI action to workspace
Record({
    $id: Now.ID['approve-request-form-action'],
    table: 'sys_ux_form_action',
    data: {
        table: 'x_myapp_approval',
        ui_action: Now.ID['approve-request'],
        action_type: 'ui_action',
        active: true,
        name: 'Approve'
    }
})

// 2. Layout Item - defines appearance and behavior
Record({
    $id: Now.ID['approve-request-layout-item'],
    table: 'sys_ux_form_action_layout_item',
    data: {
        table: 'x_myapp_approval',
        name: 'approve_request_item', // Form Action name
        label: 'Approve',
        color: 'primary',   // mapped from UI Action form style: 'primary'
        overflow: false,    // depends on UI Action showFormMenuButtonV2
        order: 100,         // from UI action order
        active: true,
        item_type: 'action',
        action: Now.ID['approve-request-form-action']
    }
})
```

### Client-Side with Messages and onClick

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['notify-user'],
    table: 'x_myapp_request',
    name: 'Notify User',
    actionName: 'notify_user',
    showUpdate: true,
    form: {
        showButton: true,
        style: 'primary',
    },
    client: {
        isClient: true,
        onClick: 'notifyUser()', // call the function defined in script
    },
    messages: ['User has been notified successfully'],
    hint: 'Send notification to the assigned user',
    isolateScript: true,
    order: 150,
    script: `function notifyUser() {
        var msg = getMessage('User has been notified successfully');
        alert(msg);
        g_form.addInfoMessage(msg);
    }`
})
```

### Context Menu with Server-Side Script

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['close-task'],
    table: 'task',
    name: 'Close Task',
    actionName: 'close_task',
    showUpdate: true,
    form: {
        showContextMenu: true,
    },
    condition: "current.state != 3",
    roles: ['itil'],
    script: `current.state = 3;
current.close_notes = 'Closed via context menu action';
current.closed_at = new GlideDateTime();
current.closed_by = gs.getUserID();
current.update();
gs.addInfoMessage('Task closed successfully');
action.setRedirectURL(current);`,
})
```

### Client-Side Redirect Action

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['view-related-items'],
    table: 'x_myapp_request',
    name: 'View Related Items',
    actionName: 'view_related_items',
    showUpdate: true,
    form: {
        showLink: true,
    },
    client: {
        isClient: true,
        onClick: 'viewRelatedItems()',
    },
    script: `function viewRelatedItems() {
        var requestId = g_form.getUniqueValue();
        var url = 'x_myapp_related_items_list.do?sysparm_query=request=' + requestId;
        window.location.href = url;
    }`,
})
```

### List Banner Button with Client-Side Confirmation

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['bulk-delete-items'],
    table: 'x_myapp_inventory',
    name: 'Delete Selected Items',
    actionName: 'bulk_delete_items',
    showUpdate: true,
    showMultipleUpdate: true,
    list: {
        showBannerButton: true,
        style: 'destructive',
    },
    roles: ['admin'],
    client: {
        isClient: true,
        onClick: 'confirmBulkDelete()',
    },
    script: `function confirmBulkDelete() {
        var count = g_list.getChecked().length;
        if (count === 0) {
            alert('Please select at least one item to delete');
            return;
        }
        if (confirm('Are you sure you want to delete ' + count + ' item(s)? This action cannot be undone.')) {
            gsftSubmit(null, g_form.getFormElement(), 'bulk_delete_items');
        }
    }`,
})
```

### Server-Side GlideRecord Query with Multiple Updates

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['assign-related-tasks'],
    table: 'x_myapp_project',
    name: 'Assign All Tasks to Me',
    actionName: 'assign_related_tasks',
    showUpdate: true,
    form: {
        showButton: true,
        style: 'primary',
    },
    condition: "current.state == 'in_progress'",
    script: `var taskGr = new GlideRecord('x_myapp_task');
taskGr.addQuery('project', current.sys_id);
taskGr.addQuery('assigned_to', '');
taskGr.query();
var assignedCount = 0;
while (taskGr.next()) {
    taskGr.assigned_to = gs.getUserID();
    taskGr.assigned_date = new GlideDateTime();
    taskGr.update();
    assignedCount++;
}
gs.addInfoMessage('Assigned ' + assignedCount + ' tasks to you');
action.setRedirectURL(current);`,
})
```

### Combined Client and Server Script - Confirmation with Server Processing

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['approve-with-confirmation'],
    table: 'x_myapp_approval_request',
    name: 'Approve Request',
    actionName: 'approve_request',
    showUpdate: true,
    form: {
        showButton: true,
        style: 'primary',
    },
    condition: "current.state == 'pending'",
    client: {
        isClient: true,
        onClick: 'approveWithConfirmation()',
    },
    script: `
// Client-side: Confirmation dialog
function approveWithConfirmation() {
    var comments = prompt('Please enter approval comments (optional):');
    if (comments !== null) {
        g_form.setValue('approval_comments', comments);
        gsftSubmit(null, g_form.getFormElement(), 'approve_request');
    }
}

// Guard ensures server-side code only runs on the server, not in the browser

if (typeof window == 'undefined') {
    processApproval();
}
function processApproval() {

// Server-side: Process approval
current.state = 'approved';
current.approved_by = gs.getUserID();
current.approved_date = new GlideDateTime();
current.update();

// Send notification
var approver = gs.getUser();
gs.eventQueue('approval.granted', current, approver.getDisplayName(), current.approval_comments);

gs.addInfoMessage('Request approved successfully');
action.setRedirectURL(current);
}`,
})
```

### Combined Client and Server Script - Validation with Complex Server Logic

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['submit-for-review'],
    table: 'x_myapp_document',
    name: 'Submit for Review',
    actionName: 'submit_for_review',
    showUpdate: true,
    form: {
        showButton: true,
        style: 'primary',
    },
    condition: "current.state == 'draft'",
    client: {
        isClient: true,
        onClick: 'validateAndSubmit()',
    },
    script: `
// Client-side: Validate required fields before submission
function validateAndSubmit() {
    var errors = [];

    if (!g_form.getValue('title')) {
        errors.push('Title is required');
    }
    if (!g_form.getValue('category')) {
        errors.push('Category must be selected');
    }
    if (!g_form.getValue('assigned_reviewer')) {
        errors.push('Reviewer must be assigned');
    }
    if (errors.length > 0) {
        alert('Please fix the following errors:\\n\\n' + errors.join('\\n'));
        return;
    }
    if (confirm('Submit this document for review? You will not be able to edit it until review is complete.')) {
        gsftSubmit(null, g_form.getFormElement(), 'submit_for_review');
    }
}

// Guard ensures server-side code only runs on the server, not in the browser
if (typeof window == 'undefined') {
    processReview();
}
function processReview() {
    // Server-side: Create review task and update document state
    current.state = 'in_review';
    current.submitted_date = new GlideDateTime();
    current.submitted_by = gs.getUserID();
    current.update();

    // Create review task
    var reviewTask = new GlideRecord('x_myapp_review_task');
    reviewTask.initialize();
    reviewTask.document = current.sys_id;
    reviewTask.assigned_to = current.assigned_reviewer;
    reviewTask.due_date = new GlideDateTime();
    reviewTask.due_date.addDaysLocalTime(3); // 3 day SLA
    reviewTask.state = 'open';
    reviewTask.insert();
    action.setRedirectURL(current);
}`,
})
```

### Override existing Form Button in child table

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['custom-resolve-form'],
    table: 'custom_incident', // custom incident table
    name: 'Resolve',
    actionName: 'resolve_incident', // must match parent action name
    showUpdate: true,
    form: {
        showButton: true,
        style: 'primary',
    },
    condition: "current.state != 6",
    client: {
        isClient: true,
        onClick: 'customResolveValidation()',
    },
    script: `
// Client-side: Validate required fields
function customResolveValidation() {
    if (!g_form.getValue('close_notes') || !g_form.getValue('close_code')) {
        alert('Close Notes and Close Code are required');
        return;
    }
    if (confirm('Resolve this incident?')) {
        gsftSubmit(null, g_form.getFormElement(), 'resolve');
    }
}

// Guard ensures server-side code only runs on the server, not in the browser
if (typeof window == 'undefined') {
    // Server-side: Process resolution
    current.state = 6;
    current.resolved_at = new GlideDateTime();
    current.resolved_by = gs.getUserID();
    current.update();
    gs.addInfoMessage('Incident resolved successfully');
    action.setRedirectURL(current);
}`,
})
```

### Override List Context Menu

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['custom-resolve-list'],
    table: 'custom_incident', // custom incident table
    name: 'Resolve',
    actionName: 'resolve_incident', // must match parent action - automatically overrides parent due to same actionName
    showUpdate: true,
    list: {
        showContextMenu: true, // right-click menu on list
    },
    condition: "current.state != 6",
    script: `
// Validate before resolving
if (!current.close_notes || !current.close_code) {
    gs.addErrorMessage('Close Notes and Close Code required');
    action.setRedirectURL(current);
    return;
}
current.state = 6;
current.resolved_at = new GlideDateTime();
current.resolved_by = gs.getUserID();
current.update();
gs.addInfoMessage('Incident resolved successfully');
action.setRedirectURL(current);
`,
})
```

### Hidden Action - Executable Only from Forms

```
import { UiAction } from '@servicenow/sdk/core'

UiAction({
    $id: Now.ID['hidden-resolve-form'],
    table: 'incident',
    name: 'Resolve',
    actionName: 'resolve_incident',
    showUpdate: true,
    form: true, // all display options are false by default
    condition: "current.state != 6",
    script: `
// Validate before resolving
if (!current.close_notes || !current.close_code) {
    gs.addErrorMessage('Close Notes and Close Code required');
    action.setRedirectURL(current);
    return;
}
current.state = 6;
current.resolved_at = new GlideDateTime();
current.resolved_by = gs.getUserID();
current.update();
gs.addInfoMessage('Incident resolved successfully');
action.setRedirectURL(current);
`,
})
```

## Avoidance

- Never use module scripts for client-side actions — modules only work on server-side. Client actions require string scripts. If the build reports a type mismatch, the action is client-side and must use string scripts or `Now.include()`.

- Never put inline code in `client.onClick` — define the function in `script` and call it from `onClick`. Example: `client.onClick: 'myFunction()'` with `script: 'function myFunction() { ... }'`

- Never set both `form` and `list` properties without intentional design — decide whether the action applies to forms, lists, or both. Setting both without purpose creates confusing UX.

- Never create UI Actions for view switching — always use View Rules (`sysrule_view`) for automatic view routing based on conditions or device type.

- Never use `showMultipleUpdate` without testing — bulk actions run on every selected record and can be expensive. Ensure the script handles bulk operations efficiently.

- Never hardcode record states in scripts — use constants or choice values that match the table's state model.

- Never omit `condition` for destructive actions — always gate dangerous operations behind a condition (e.g., state check) and role restriction.

- Never forget `action.setRedirectURL(current)` — server-side scripts that update the current record should redirect back to the form to show the updated state.

- Never use `client.onClick` for server-side scripts — `onClick` is for client-side logic only. Use `script` property for server-side actions.

- Never rely on `isolateScript` as a security measure — it prevents variable pollution, not malicious code execution. Use proper ACLs and role restrictions for security.

- Never use workspace properties without testing in Configurable Workspace — workspace V2 rendering (`showFormButtonV2`, `clientScriptV2`) only applies in workspace environments; test both classic and workspace UIs.

- Never set `workspace.isConfigurableWorkspace: true` without creating the two required integration records — UI actions won't appear in workspace unless `sys_ux_form_action` and `sys_ux_form_action_layout_item` records are created

## See Also

- For view switching and automatic view routing → use View Rules (`sysrule_view`). See the `view-rule-guide`

- For client-side field validation and dynamic behavior → use Client Scripts or UI Policies

- For securing UI Actions by role → see the `roles` property and ACL configuration

- For programmatic action invocation → use the `actionName` property as a reference in scripts

- For full API property reference and type signatures → see the `uiaction-api` topic
