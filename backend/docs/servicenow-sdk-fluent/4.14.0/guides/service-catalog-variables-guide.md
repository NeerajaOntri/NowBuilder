Version: 4.14.0

# Service Catalog Variables

Servicenow guide to create Service Catalog Variables and Variable Sets. Creates a Variable(`item_option_new`) - single variable and Variable Set(`item_option_new_set`) - reusable collection of variables that can
be attached to one or more catalog items.

## Catalog Variables Reference

### Common Variable Properties

Properties like `question`, `order`, `mandatory`, `readOnly`, `hidden`, `defaultValue`, and role-based access (`readRoles`, `writeRoles`, `createRoles`) are shared across all variable types. Each variable type also has its own additional properties — see the individual API docs in `api/service-catalog/variables/` for the complete property reference.

### Variable Types

Text Variables

- SingleLineTextVariable -- Single line text input

- MultiLineTextVariable -- Multi-line text area

- WideSingleLineTextVariable -- Full-width single line

- EmailVariable -- Email address input

- UrlVariable -- URL input

- IpAddressVariable -- IPv4/IPv6 input

- MaskedVariable -- Masked/password input (supports `useEncryption`, `useConfirmation`)

Choice Variables

- SelectBoxVariable -- Dropdown choice list. Requires `choices` object with `{ label, sequence }`.

- MultipleChoiceVariable -- Radio buttons. Supports `choiceDirection: 'down'` or `'across'`.

- YesNoVariable -- Yes/No choice list.

- CheckboxVariable -- Checkbox. Use `selectionRequired: true` for mandatory.

- NumericScaleVariable -- Likert scale radio buttons.

Lookup Variables

- LookupSelectBoxVariable -- Dropdown from table data.

- LookupMultipleChoiceVariable -- Radio buttons from table data.

Reference Variables

- ReferenceVariable -- References a record in another table. Key properties: `referenceTable`, `referenceQualCondition`, `useReferenceQualifier`.

- RequestedForVariable -- Specifies who the request is for.

- ListCollectorVariable -- Select multiple records from a table.

Dynamic Default Values

Variables support dynamic default values that auto-populate based on another variable's referenced record:

- dependentQuestion -- The name of a `RequestedForVariable` or `ReferenceVariable` whose selected record is used as the source for the dynamic default.

- dotWalkPath -- The dot-walk path from the dependent question's referenced record to get the default value.

- useDynamicDefault -- Must be `true` to enable dynamic default behavior.

Note: The `dependentQuestion` must reference a `RequestedForVariable` or `ReferenceVariable` since it requires a referenced record to dot-walk from.

Date/Time Variables

- DateVariable -- Date picker.

- DateTimeVariable -- Date and time picker.

- DurationVariable -- Duration input.

Layout Variables

- ContainerStartVariable / ContainerSplitVariable / ContainerEndVariable -- Multi-column layout containers. Must be properly paired.

- LabelVariable -- Display-only label.

- BreakVariable -- Horizontal line separator.

Special Variables

- AttachmentVariable -- File upload.

- HtmlVariable -- Rich content display.

- RichTextLabelVariable -- Formatted label.

- CustomVariable / CustomWithLabelVariable -- Custom UI component embedding a UI Macro, Service Portal Widget, Macroponent, or Virtual Agent Topic Block. Use `CustomVariable` for label-less rendering; use `CustomWithLabelVariable` when the question text should display as a label. Neither supports `mandatory`, `hidden`, or `readOnly`.

- UIPageVariable -- UI page insertion.

Custom Variable Rendering Contexts

Custom and CustomWithLabel variables support multiple rendering contexts — set the property for each context the item is ordered in. Every context property is optional and defaults to empty (the build does not require or diagnose at least one being set), but a variable with none set renders blank in every context. See the `customvariable-api` topic for the per-context property table.

A single variable can set both `macro` and `widget` so the correct component renders in each context. Reference a project-defined `UiMacro` by importing it, or use a sys_id string for an existing platform macro. Use `summaryMacro` to provide a read-only rendering on the request confirmation and summary pages — without it, a custom variable backed by a rich interactive macro shows blank or a sys_id on those pages. See the `ui-macro-guide` topic for the full `summaryMacro` and `customCart` patterns.

XML-safe script content: The Jelly XML parser treats the entire `<script>` body as element text — including JavaScript comments. A comment like `/* avoids < and & */` contains bare XML-reserved characters, which the build flags with a malformed-XML warning (the content is still written as-is). Never use `<` or `&` anywhere in a `<script>` block, whether in code or comments — including once past the build, an XML entity that decodes back to one of these characters between Jelly passes can still cause a render-time `SAXParseException`. See the "XML-Safe JavaScript Across Jelly Passes" section in the `jelly-guide` topic.

Catalog client script isolation: scoped catalog client scripts run with `window`, `document`, `jQuery`, and `prototype` as `null`, so a catalog client script that reaches through `window` to a function the macro registered fails with a `TypeError`. See the `ui-macro-guide` topic for the pattern to use instead.

## Variable Set Reference

### Properties

For the complete property reference including all properties, types, and detailed descriptions, see the `variableset-api` documentation.

### Attaching to Catalog Items

Attach variable sets via `variableSets: [{ variableSet, order }]` on a Catalog Item or Record Producer. Item-specific variables can be added alongside variable sets.

### Multi-Row Variable Set (MRVS)

Use `type: "multiRow"` for grid/table data entry (e.g., multiple team members). Configure with `setAttributes` for row limits and collapsibility.

### MRVS Unsupported Variable Types

- AttachmentVariable

- ContainerStartVariable / ContainerEndVariable / ContainerSplitVariable

- HtmlVariable

- CustomVariable / CustomWithLabelVariable

- RichTextLabelVariable

- UIPageVariable

### MRVS Limitations

- "Assign to Field" not supported

- Cannot add variables with read roles

- Set row limits using `max_rows` attribute

- Will not display if added to a container

### Role-Based Access

- `readRoles`: Roles that can view the variable set

- `writeRoles`: Roles that can modify values

- `createRoles`: Roles that can create instances (multiRow)

Set-level permissions override variable-level permissions when access is denied at the set level.

## Modifying Existing Variables

When the requirement is to change a variable that already exists on a catalog
item (update properties, change its type, or modify its choices), follow the steps
below. Do not create a new variable alongside the old one — this leaves
duplicate fields on the form.

### Step 1 — Query Before Acting

Before writing any code, check whether the variable exists. Query the
`item_option_new` table filtering by `cat_item` (the catalog item sys_id) and
`name` (the variable's programmatic key):

Query table: item_option_new
Filter: cat_item=^name=
Fields: sys_id, name, type, active

Use the result to confirm the variable exists and identify its current type.

### Step 2 — Add to Working Set

Add the parent catalog item (`sc_cat_item`) to the working set using
`add_to_working_set`. This generates the Fluent file containing the full catalog
item definition, including all its variables.

### Step 3 — Choose the Correct Modification Path

| Scenario | Action |
| Changing properties only (label, mandatory, order, etc.) — same type | Update properties in-place on the same variable key. |
| Changing the variable type (e.g., `SingleLineTextVariable` → `SelectBoxVariable` ) | Swap the constructor function on the same key. Add type-specific properties, remove incompatible ones. |
| Narrowing choices on an existing SelectBox/MultipleChoice | Keep all existing choices; set `inactive: true` on removed ones. Do NOT delete choice keys. |
| Adding choices to an existing SelectBox/MultipleChoice | Add new choice keys with appropriate `sequence` values. |

### In-Place Type Change (Correct Pattern)

The Fluent build system tracks variables by their key in the `variables` object.
That key IS the variable's `name` field. When you change the constructor on the
same key, the build system updates the existing record's type — it does NOT
create a new record.

Before — Single line text:

```
import { CatalogItem, SingleLineTextVariable } from '@servicenow/sdk/core'

export const hardwareRequest = CatalogItem({
    $id: Now.ID['hardware_request'],
    name: 'Hardware Request',
    shortDescription: 'Request hardware procurement for your team',
    variables: {
        hardware_type: SingleLineTextVariable({
            question: 'Hardware Type',
            order: 100,
            mandatory: true,
            exampleText: 'e.g. Laptop, Desktop, Monitor',
        }),
    },
})
```

**After — Select box with choices:

```
import { CatalogItem, SelectBoxVariable } from '@servicenow/sdk/core'

export const hardwareRequest = CatalogItem({
    $id: Now.ID['hardware_request'],
    name: 'Hardware Request',
    shortDescription: 'Request hardware procurement for your team',
    variables: {
        // Same key = same record, type is updated in-place
        hardware_type: SelectBoxVariable({
            question: 'Hardware Type',
            order: 100,
            mandatory: true,
            choices: {
                laptop: { label: 'Laptop', sequence: 1 },
                desktop: { label: 'Desktop', sequence: 2 },
                monitor: { label: 'Monitor', sequence: 3 },
            },
            includeNone: true,
        }),
    },
})
```

Managing Choices on Existing Variables
When reducing the available options on a SelectBox or MultipleChoice variable,
never delete choice keys from the source. This triggers deletedRecordWarnings
requiring manual cleanup.

✅ Correct — deactivate unwanted choices:

```
hardware_type: SelectBoxVariable({
    question: 'Hardware Type',
    order: 100,
    mandatory: true,
    choices: {
        // Active choices — visible to users
        laptop: { label: 'Laptop', sequence: 1 },
        desktop: { label: 'Desktop', sequence: 2 },
        monitor: { label: 'Monitor', sequence: 3 },
        // Retired choices — hidden but preserved for historical data
        docking_station: { label: 'Docking Station', sequence: 4, inactive: true },
        keyboard_mouse: { label: 'Keyboard/Mouse', sequence: 5, inactive: true },
        mobile_phone: { label: 'Mobile Phone', sequence: 6, inactive: true },
    },
    includeNone: true,
})
```

❌ Wrong — removing choice keys entirely:

```
// Causes deletedRecordWarnings and breaks historical data
hardware_type: SelectBoxVariable({
    question: 'Hardware Type',
    choices: {
        laptop: { label: 'Laptop', sequence: 1 },
        desktop: { label: 'Desktop', sequence: 2 },
        monitor: { label: 'Monitor', sequence: 3 },
        // docking_station, keyboard_mouse, mobile_phone REMOVED — BAD
    },
})
```

## Examples

### Variable Examples

Text variables:

```
import { SingleLineTextVariable, MultiLineTextVariable, EmailVariable, MaskedVariable } from '@servicenow/sdk/core'

SingleLineTextVariable({ question: "Employee Name", order: 100, mandatory: true, exampleText: "John Smith" });
MultiLineTextVariable({ question: "Description", order: 200, mandatory: true, width: 100 });
EmailVariable({ question: "Email Address", order: 300, mandatory: true });
MaskedVariable({ question: "Enter Password", order: 400, useEncryption: true });
```

Choice variables:

```
import { SelectBoxVariable, MultipleChoiceVariable, CheckboxVariable } from '@servicenow/sdk/core'

SelectBoxVariable({
  question: "Priority Level",
  order: 100,
  choices: {
    high: { label: "High", sequence: 1 },
    medium: { label: "Medium", sequence: 2 },
    low: { label: "Low", sequence: 3 }
  },
  includeNone: true
});

MultipleChoiceVariable({
  question: "Services Required",
  choiceDirection: "down",
  choices: {
    install: { label: "Installation", sequence: 1 },
    config: { label: "Configuration", sequence: 2 },
    training: { label: "Training", sequence: 3 }
  },
  order: 200
});

CheckboxVariable({ question: "I agree to the terms", order: 400, selectionRequired: true });
```

Reference variables:

```
import { ReferenceVariable, ListCollectorVariable } from '@servicenow/sdk/core'

ReferenceVariable({
  question: "Point of Contact",
  referenceTable: "sys_user",
  referenceQualCondition: "active=true",
  order: 100
});

ListCollectorVariable({
  question: "Team Members",
  listTable: "sys_user",
  referenceQual: "active=true",
  order: 300,
  mandatory: true
});
```

Dynamic defaults with dependentQuestion:

Use `dependentQuestion` to auto-populate reference variables based on another variable's value. When the source variable changes, the dependent variable automatically updates by following the `dotWalkPath` from the source record.

This is commonly used with `RequestedForVariable` to auto-fill organizational context (manager, department, location, cost center) when the user selects who the request is for.

| Property | Type | Description |
| `dependentQuestion` | string | Name of the source variable (must be `RequestedForVariable` or `ReferenceVariable` ). |
| `dotWalkPath` | string | Dot-walk path from the source record to get the value (e.g., `'manager'` , `'department'` , `'location.building'` ). |
| `useDynamicDefault` | boolean | Must be `true` to enable dynamic defaults. |

```
import { CatalogItem, RequestedForVariable, ReferenceVariable } from '@servicenow/sdk/core'

export const accessRequest = CatalogItem({
    $id: Now.ID['access_request'],
    name: 'Access Request',
    shortDescription: 'Request system access for a user',
    variables: {
        // Source variable — user selects who needs access
        requestedFor: RequestedForVariable({
            question: 'Who needs access?',
            order: 100,
            mandatory: true,
            referenceQualCondition: 'active=true',
        }),

        // Auto-populated from requestedFor.manager
        manager: ReferenceVariable({
            question: 'Manager (auto-filled)',
            order: 200,
            referenceTable: 'sys_user',
            referenceQualCondition: 'active=true',
            useDynamicDefault: true,
            dotWalkPath: 'manager',
            dependentQuestion: 'requestedFor',
        }),

        // Auto-populated from requestedFor.department
        department: ReferenceVariable({
            question: 'Department (auto-filled)',
            order: 300,
            referenceTable: 'cmn_department',
            referenceQualCondition: 'active=true',
            useDynamicDefault: true,
            dotWalkPath: 'department',
            dependentQuestion: 'requestedFor',
        }),

        // Auto-populated from requestedFor.location
        location: ReferenceVariable({
            question: 'Location (auto-filled)',
            order: 400,
            referenceTable: 'cmn_location',
            referenceQualCondition: 'active=true',
            useDynamicDefault: true,
            dotWalkPath: 'location',
            dependentQuestion: 'requestedFor',
        }),
    },
})
```

Dynamic defaults with text variables:

`dependentQuestion` also works with non-reference variables to auto-populate string fields by dot-walking from the source record:

```
import { CatalogItem, RequestedForVariable, SingleLineTextVariable, ReferenceVariable } from '@servicenow/sdk/core'

export const employeeOnboarding = CatalogItem({
    $id: Now.ID['employee_onboarding'],
    name: 'Employee Onboarding',
    variables: {
        requestedFor: RequestedForVariable({
            question: 'Requested For',
            order: 100,
            mandatory: true,
        }),

        // Auto-populate first name from the selected user
        firstName: SingleLineTextVariable({
            question: 'First Name',
            order: 200,
            useDynamicDefault: true,
            dependentQuestion: 'requestedFor',
            dotWalkPath: 'first_name',
        }),

        // Auto-populate location reference
        location: ReferenceVariable({
            question: 'Location',
            order: 300,
            referenceTable: 'cmn_location',
            useDynamicDefault: true,
            dependentQuestion: 'requestedFor',
            dotWalkPath: 'location',
        }),
    },
})
```

dependentQuestion rules:

- The source variable (`dependentQuestion`) must be either `RequestedForVariable` or `ReferenceVariable`

- The source variable must be declared before the dependent variable in the `variables` object

- `useDynamicDefault` must be `true` on the dependent variable

- `dotWalkPath` specifies the field path from the source record (supports dot-walking like `'location.building'`)

- The dependent variable's `referenceTable` should match the type returned by the dot-walk path

Container layout (multi-column):

Container variables must follow the exact triplet order: ContainerStartVariable → variables → ContainerSplitVariable → variables → ContainerEndVariable. Every start must have exactly one split and one end. Containers are not supported in multiRow variable sets.

```
import { ContainerStartVariable, ContainerSplitVariable, ContainerEndVariable, SingleLineTextVariable, EmailVariable } from '@servicenow/sdk/core'

const variables = {
  contact_container_start: ContainerStartVariable({
    question: "Contact Information",
    layout: "2across",
    displayTitle: true,
    order: 100
  }),
  first_name: SingleLineTextVariable({
    question: "First Name",
    mandatory: true,
    order: 110
  }),
  contact_split: ContainerSplitVariable({ order: 200 }),
  email: EmailVariable({
    question: "Email Address",
    mandatory: true,
    order: 210
  }),
  contact_container_end: ContainerEndVariable({ order: 300 })
}
```

Variables with pricing:

```
import { CheckboxVariable, SelectBoxVariable } from '@servicenow/sdk/core'

premiumSupport: CheckboxVariable({
  question: "Premium Support (+$150)",
  pricingDetails: [
    { amount: 150, currencyType: "USD", field: "price_if_checked" },
    { amount: 30, currencyType: "USD", field: "rec_price_if_checked" }
  ],
  order: 500
});

hardwareType: SelectBoxVariable({
  question: "Hardware Type",
  choices: {
    laptop: {
      label: "Business Laptop (Base)",
      sequence: 1,
      pricingDetails: [{ amount: 0, currencyType: "USD", field: "misc" }]
    },
    workstation: {
      label: "Developer Workstation (+$800)",
      sequence: 2,
      pricingDetails: [{ amount: 800, currencyType: "USD", field: "misc" }]
    }
  },
  mandatory: true,
  order: 600
});
```

Custom variables with UI Macros:

Define a `UiMacro` and reference it from a `CustomVariable` or `CustomWithLabelVariable` to embed a custom UI component on a catalog form. `CustomVariable` renders the component without a label; `CustomWithLabelVariable` displays the `question` text as a label above the component.

```
import { CatalogItem, CustomVariable, UiMacro, SingleLineTextVariable } from '@servicenow/sdk/core'

const searchPanelMacro = UiMacro({
    $id: Now.ID['catalog-search-panel'],
    name: 'catalog_search_panel',
    description: 'Renders an inline contextual search panel. Parameters: none.',
    category: 'catalog',
    xml: Now.include('./catalog-search-panel.jelly.xml'),
})

export const incidentRequest = CatalogItem({
    $id: Now.ID['incident-request'],
    name: 'Create Incident',
    shortDescription: 'Submit a new incident',
    variables: {
        // CustomVariable — no label, macro renders directly
        search_results: CustomVariable({
            question: 'Contextual Search Results',
            macro: searchPanelMacro,
            order: 100,
        }),
        short_description: SingleLineTextVariable({
            question: 'Short Description',
            order: 200,
            mandatory: true,
        }),
    },
})
```

`CustomWithLabelVariable` follows the same pattern, with the `question` text shown as a label above the macro. For a full walkthrough — including a `summaryMacro` for a separate read-only rendering on confirmation pages, and `customCart` to replace the default cart/checkout buttons — see the "Catalog Variable Using a Macro" and "Custom Cart Macro" sections of the `ui-macro-guide` topic.

### Single-Row Variable Set

```
import { VariableSet, EmailVariable, SingleLineTextVariable, ReferenceVariable } from "@servicenow/sdk/core";

export const contactInfoSet = VariableSet({
  $id: Now.ID["contact_info_set"],
  title: "Contact Information",
  description: "Standard contact information fields",
  type: "singleRow",
  layout: "2across",
  order: 100,
  displayTitle: true,
  variables: {
    email: EmailVariable({ question: "Email Address", mandatory: true, order: 100 }),
    phone: SingleLineTextVariable({ question: "Phone Number", mandatory: true, order: 200 }),
    department: ReferenceVariable({
      question: "Department",
      referenceTable: "cmn_department",
      referenceQualCondition: "active=true",
      order: 300
    })
  }
});
```

### Multi-Row Variable Set (MRVS)

```
import { VariableSet, ReferenceVariable, SelectBoxVariable, DateVariable } from '@servicenow/sdk/core'

export const teamMembersSet = VariableSet({
  $id: Now.ID["team_members_set"],
  title: "Team Members",
  description: "Add multiple team members who need access",
  type: "multiRow",
  layout: "2across",
  displayTitle: true,
  setAttributes: "max_rows=10,collapsible=true",

  readRoles: ["admin", "manager"],
  writeRoles: ["admin"],

  variables: {
    user: ReferenceVariable({
      question: "User",
      referenceTable: "sys_user",
      referenceQualCondition: "active=true",
      mandatory: true,
      order: 100
    }),
    accessLevel: SelectBoxVariable({
      question: "Access Level",
      choices: {
        read: { label: "Read Only", sequence: 1 },
        write: { label: "Write", sequence: 2 },
        admin: { label: "Admin", sequence: 3 }
      },
      mandatory: true,
      order: 200
    }),
    startDate: DateVariable({ question: "Access Start Date", mandatory: true, order: 300 })
  }
});
```

### Attaching Variable Sets to a Catalog Item

```
import { CatalogItem, MultiLineTextVariable } from '@servicenow/sdk/core'
import { contactInfoSet } from './variable-sets/contact-info-set'
import { teamMembersSet } from './variable-sets/team-members-set'
import { serviceCatalog } from './catalogs/service-catalog'
import { itServicesCategory } from './categories/it-services'

export const accessRequest = CatalogItem({
  $id: Now.ID["access_request"],
  name: "Team Access Request",
  shortDescription: "Request access for team members",
  catalogs: [serviceCatalog],
  categories: [itServicesCategory],

  variableSets: [
    { variableSet: contactInfoSet, order: 100 },
    { variableSet: teamMembersSet, order: 200 }
  ],

  variables: {
    notes: MultiLineTextVariable({ question: "Additional Notes", order: 100 })
  },

  flow: "523da512c611228900811a37c97c2014"
});
```

## Related Topics

- For service catalog items and record producers: service-catalog-guide.md

- For catalog ui policies: service-catalog-ui-policy-guide.md

- For catalog client scripts: service-catalog-client-script-guide.md

- For UI Macros (used with Custom/CustomWithLabel variables): ui-macro-guide.md

- For the UiMacro API reference: uimacro-api
