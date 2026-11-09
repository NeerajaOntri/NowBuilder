Version: 4.14.0

# Service Portal OOTB Reference (Gold Standard)

This file contains reference OOTB patterns from ServiceNow's global scope records, useful as a gold-standard starting point when creating custom headers, footers, or themes.

The live records are the source of truth. The snippets here can drift across releases and instances. Query the current record from your target instance (e.g. `now-sdk query sp_header_footer -q 'name=Stock Header' -f 'template,script,css' -o json`, `now-sdk query sp_theme -q 'name=Coral' -f 'css_variables' -o json`) and use it as your reference. Use the snippets below to understand structure and required patterns.

Related Guides:

- service-portal-guide.md — Portal, pages, widgets, scripts

- service-portal-components-guide.md — Theme, header/footer, menu API

- service-portal-advanced-guide.md — Route maps, troubleshooting

Source of Truth:

- Stock Header: `sp_header_footer` sys_id `bf5ec2f2cb10120000f8d856634c9c0c`

- Coral Theme: `sp_theme` sys_id `281507c44317d210ca4c1f425db8f2fd`

These sys_ids are from a baseline ServiceNow instance and may differ by release or per-instance customization. Query the live records on your target instance to get the authoritative sys_id and content — the patterns below are structural references, not guaranteed copies.

## Stock Header Template

Query the live record — do not treat the snippet below as authoritative. The Stock Header lives in an `sp_header_footer` record (global scope, queryable on any instance). Its markup can differ across releases, and the copy embedded in this guide has drifted from the baseline (e.g. inline comment wording). Always pull the current template from your target instance and use it as your reference:

```
now-sdk query sp_header_footer -q 'name=Stock Header' -f 'sys_id,template,script,css' -o json
```

The snippet below is a structural reference for understanding the template — the menu placeholder, logo `ng-if`, login/avatar blocks, and required flags — not a byte-for-byte source of truth.

Scope & menu wiring check before using:

- Scoped apps: Remove the "Language selector" block from the server script (`pm.isActive(...)`). `pm` is global-scope-only and breaks scoped apps.

- Menus: The header expects `data.menu` and `data.hasMenuItems` populated by the server script, and the portal must set `mainMenu` in `ServicePortal`.

```
<!-- Structural reference — OOTB Stock Header (query the live sp_header_footer record for current markup) -->
<div>
  <nav id="responsiveNav" class="navbar-inverse" ng-class="::{'navbar':!isViewNative, 'is-native': isViewNative}"
       role="navigation" aria-label="${Primary}">
    <div ng-show="::!isViewNative" class="navbar-header">
      <a class="navbar-brand" ng-if="::!portal.logo" href="?id={{::portal.homepage_dv}}"><span ng-bind="portal.title"></span></a>
      <a class="navbar-brand navbar-brand-logo" ng-if="::portal.logo" ng-href="?id={{::portal.homepage_dv}}" ng-click="collapse()" aria-label="{{::logoText}}">
        <img ng-src="{{::portal.logo}}" title="{{::portal.title}}" alt="{{::portal.logo_alt_text || portal.title}} ${Logo}" />
      </a>
      <button ng-if="data.hasMenuItems || (!user.logged_in && page.id != portal.login_page_dv && !data.hasLogin) || user.logged_in" type="button" class="navbar-toggle collapsed" data-toggle="collapse" data-placement="bottom" data-toggle-second="tooltip" data-original-title="{{::data.toggleMsg}}" data-target="#sp-nav-bar" aria-haspopup="menu">
        <span class="sr-only">${Toggle navigation}</span>
        <span class="icon-bar"></span>
        <span class="icon-bar"></span>
        <span class="icon-bar"></span>
      </button>
    </div>

    <div sp-navbar-toggle="" class="collapse navbar-right" id="sp-nav-bar" role="navigation">
      <!-- Menu Widget -->
      <sp-widget widget="::data.menu"></sp-widget>
      <!-- Language Selector (i18n) -->
      <sp-widget widget="::data.langSelector"></sp-widget>
      <!-- Login link (only if not logged in, not on login page, and menu doesn't have login) -->
      <ul ng-if="(!user.logged_in && page.id != portal.login_page_dv && !data.hasLogin)" class="nav navbar-nav" role="presentation">
        <li role="presentation"><a href ng-click="::openLogin()">${Login}</a></li>
      </ul>
      <!-- Logged-in user menu -->
      <ul ng-if="user.logged_in" class="nav navbar-nav">
        <!-- Live Chat (optional) -->
        <li ng-if="::(data.connect_support_queue_id && !isAgentChatConfigured)"><a href ng-click="openPopUp()" role="button">${Live Chat}</a></li>
        <!-- Desktop avatar dropdown -->
        <li ng-if="showAvatar" class="hidden-xs hidden-sm dropdown">
          <a href class="toggle-dropdown" data-toggle="dropdown" aria-expanded="false" aria-label="{{::data.profileBtnMsg}}: {{::user.name}}" id="profile-dropdown" role="button" aria-haspopup="true">
            <span class="navbar-avatar" aria-hidden="true"><sn-avatar class="avatar-small-medium" primary="avatarProfile" /></span>
            <span class="visible-lg-inline">{{::user.name}}</span>
          </a>
          <ul class="dropdown-menu" aria-label="{{::data.profileBtnMsg}}">
            <li><a tabindex="-1" ng-href="?id=user_profile&sys_id={{::user.sys_id}}">${Profile}</a></li>
            <li ng-if="::!(isViewNative || isViewNativeTablet)"><a tabindex="-1" href="{{::portal.logoutUrl}}">${Logout}</a></li>
          </ul>
        </li>
        <!-- Mobile/tablet avatar (visible only on small screens) -->
        <li ng-if="showSMAvatar" class="visible-xs-block visible-sm-block"><a ng-href="?id=user_profile&sys_id={{::user.sys_id}}" ng-click="collapse()">
          <span class="navbar-avatar"><sn-avatar class="avatar-small-medium" primary="avatarProfile" /></span>{{::user.name}}</a>
        </li>
        <li ng-if="::!(isViewNative || isViewNativeTablet)" class="visible-xs-block visible-sm-block"><a ng-href="{{::portal.logoutUrl}}" ng-click="collapse()">${Logout}</a></li>
      </ul>
    </div>
  </nav>
</div>
```

## Stock Header Server Script

Reference only — query the live `sp_header_footer` `script` field and use it as your reference. The snippet below shows the structure, not the current source of truth.

```
// Structural reference — OOTB Stock Header server script (query the live sp_header_footer record for current source)
//
// EXCEPTION for scoped apps: remove the "Language selector" block below (the
// pm.isActive(...) line). `pm` is a global-scope-only object — it throws
// `"pm" is not defined"` in a scoped application and will fail on every page load.
// Every other line in this script is scoped-safe and can be used as-is.
//
// CRITICAL: Header/footer server scripts must NOT use IIFE wrapper!
// WRONG: (function() { data.menu = ...; })();
// RIGHT: data.menu = ...;
// Unlike widgets, headers/footers execute in a context where IIFE breaks data binding.

// Live Chat support queue (optional)
data.connect_support_queue_id = $sp.getValue('sp_chat_queue');

// Portal config
data.login_page = $sp.getValue('login_page');
data.profileBtnMsg = gs.getMessage("User options");
data.toggleMsg = gs.getMessage("Toggle navigation");

// Get menu widget from portal's sp_rectangle_menu field
var menu = $sp.getValue("sp_rectangle_menu");
data.menu = $sp.getWidgetFromInstance(menu);

// Language selector (i18n support) — GLOBAL SCOPE ONLY, see exception note above.
// In a scoped app, omit this line entirely (leave data.langSelector unset, or set to "").
data.langSelector = pm.isActive('com.glide.i18n') ? $sp.getWidget('sp-lang-selector') : "";

// CRITICAL: Menu flags control visibility and prevent duplication
if (data.menu && data.menu.data) {
    data.menu.data.replace = true;  // REQUIRED — prevents menu duplication
    // Check if menu already has login link
    data.hasLogin = false;
    if (data.menu.data.menu.items) {
        data.hasMenuItems = data.menu.data.menu.items.length > 0;  // REQUIRED — controls toggle button
        for (var i in data.menu.data.menu.items) {
            var item = data.menu.data.menu.items[i];
            if (item.type == 'page' && item.sp_page == data.login_page)
                data.hasLogin = true;
        }
    }
}

// Login modal widget
data.loginWidget = $sp.getWidgetFromInstance('login-modal');
```

Required variables:

| Variable | Purpose | If Missing |
| `data.menu` | Menu widget instance | No menu rendered |
| `data.menu.data.replace` | Prevents duplication | Menu items appear twice |
| `data.hasMenuItems` | Toggle button visibility | Toggle always hidden |
| `data.hasLogin` | Hide login link if menu has one | Duplicate login links |
| `data.langSelector` | i18n language selector | No language switching |
| `data.profileBtnMsg` | Accessibility label | Missing aria-label |
| `data.toggleMsg` | Tooltip text | Missing tooltip |

## Stock Header Client Script

Reference only — query the live `sp_header_footer` `client_script` field and use it as your reference. The snippet below shows the structure, not the current source of truth.

```
// Structural reference — OOTB Stock Header client script (query the live sp_header_footer record for current source)
// REQUIRED for avatar display — without this, sn-avatar shows nothing

api.controller = function ($rootScope, $scope, snRecordWatcher, spUtil, $location, $uibModal, cabrillo, $timeout, $window, i18n, spAriaUtil, $element) {

    $scope.logoText = i18n.format(i18n.getMessage('Go to {0} Homepage'), $scope.portal.title);
    
    $scope.collapse = function() {
        $rootScope.$emit('sp-navbar-collapse');
    }

    // CRITICAL: Avatar initialization — sn-avatar requires this object
    $scope.avatarProfile = {
        userID: $scope.user.sys_id,
        name: $scope.user.name,
        initials: $window.NOW.user_initials
    };

    // Set user image if available
    if ($window.NOW.user_avatar) {
        $scope.avatarProfile.userImage = $window.NOW.user_avatar;
    }

    // Show avatar only when user is logged in
    $scope.showAvatar = $scope.user.logged_in;
    $scope.showSMAvatar = $scope.user.logged_in;

    // Login modal handler
    $scope.openLogin = function() {
        $uibModal.open({
            templateUrl: 'login-modal-template',
            controller: 'LoginModalController',
            size: 'sm'
        });
    };
}
```

Required avatar variables:

| Variable | Purpose | If Missing |
| `$scope.avatarProfile.userID` | User sys_id for avatar lookup | Avatar shows nothing |
| `$scope.avatarProfile.name` | Fallback display name | No name shown |
| `$scope.avatarProfile.initials` | Fallback initials circle | No initials |
| `$scope.avatarProfile.userImage` | Profile image URL | Shows initials instead |
| `$scope.showAvatar` | Controls avatar visibility | Avatar hidden |

## Stock Header CSS

Reference only — query the live `sp_header_footer` `css` field and use it as your reference. The snippet below shows the structure, not the current source of truth.

Theme variable dependency: This CSS uses `$sp-navbar-*` and `$sp-logo-*` variables that must be defined in the theme. If you use this CSS in a custom theme that does not define them, SCSS compilation fails. Either use the Coral theme or use the required variables from the live `sp_theme` record.

```
// Structural reference — OOTB Stock Header CSS (query the live sp_header_footer record for current source)

.navbar {
  transition: 250ms opacity ease-in-out;
  -webkit-transition: 250ms opacity ease-in-out;
  border: 0;
  border-bottom: $sp-navbar-bottom-width solid $sp-navbar-divider-color;
}

.navbar-fade {
  opacity: 0.4;
}

.navbar-inverse .navbar-toggle {
  border-color: $sp-navbar-toggle-border-color;
}

header[role="banner"],
.nav > li > a {
  max-height: 60px;
}

.nav > li > a span.fa {
  margin-left: 0.2rem;
}

.responsive-tablet {
  .nav > li > a {
    padding-right: 0.5rem;
    padding-left: 0.5rem;
  }
}

.navbar-brand {
  max-height: 60px;
  padding: 0;
  padding-bottom: 0.5rem;
}

.navbar-brand img, .navbar-brand span {
  margin-left: $sp-logo-margin-x;
  margin-right: $sp-logo-margin-x;
  margin-top: $sp-logo-margin-y;
  margin-bottom: $sp-logo-margin-y;
  display: block;
  max-height: $sp-logo-max-height;
  max-width: $sp-logo-max-width;
  position: relative;
  top: 50%;
  -webkit-transform: translateY(-50%);
  -ms-transform: translateY(-50%);
  transform: translateY(-50%);
  overflow: hidden;
  width: calc(100% - 3rem);
}

.responsive-tablet {
  .navbar-brand img, .navbar-brand span {
    max-width: $sp-logo-mobile-max-width;
  }
}

.breadcrumb-container {
  background-color: $panel-bg;
}

/* for mobile app */
.navbar-inverse.is-native {
  background-color: #405060;
}

nav {
  margin-bottom: 0px;
  border-radius: 0px;

  .toggle-dropdown {
    height: 60px;
  }
}

.navbar-right {
  padding-right: 0px;
  padding-left: 7px;
}

.navbar-nav {
  margin: 0px;
}

// Dropdown menu scrollable when too many items
.scrollable-dropdown {
  max-height: 80vh;
  overflow: auto;
  height: auto;
}

.is-native {
  .scrollable-dropdown {
    max-height: 100vh;
    overflow: scroll;
    height: auto;
  }
}

/* CRITICAL: Media query fallbacks for responsive behavior */
/* The .responsive-desktop class is added dynamically by SP framework, */
/* but media queries are REQUIRED as fallbacks or menu will be hidden! */
@media (min-width: 993px) {
  .navbar-right {
    display: flex !important;
    height: auto !important;
  }
}

@media (max-width: 992px) {
  .navbar-toggle {
    display: block;
  }
  .navbar-header {
    float: none;
  }
  .navbar-left, .navbar-right {
    float: none !important;
  }
  .navbar-nav {
    float: none !important;
  }
  .navbar-nav > li {
    float: none;
  }
  .navbar-nav > li > a {
    padding-top: 1rem;
    padding-bottom: 1rem;
  }
}

/* Safari alignment fix (framework class - secondary to media queries) */
.responsive-desktop {
  .navbar-right {
    display: flex !important;
    height: auto !important;
  }
}

.responsive-tablet {
  .navbar-toggle {
    display: block;
  }
  .navbar-header {
    float: none;
  }
  .navbar-left, .navbar-right {
    float: none !important;
  }
  .navbar-nav {
    float: none !important;
  }
  .navbar-nav > li {
    float: none;
  }
  .navbar-nav > li > a {
    padding-top: 1rem;
    padding-bottom: 1rem;
  }
}

/* High contrast mode accessibility */
@media screen and (-ms-high-contrast: active), (forced-colors: active) {
  .navbar-brand,
  .navbar-nav > li > a,
  .skip-link,
  .btn.btn-primary,
  .btn.btn-danger,
  .navbar-inverse .navbar-toggle {
    &:focus {
      outline-offset: -4px !important;
    }
  }
}
```

## Coral Theme SCSS Variables

Reference only — query the live `sp_theme` `css_variables` field and use it as your reference. The snippet below shows the structure, not the current source of truth.

All color variables use `sp-rgb()` UXF tokens with fallbacks:

```
// Structural reference — Coral Theme variables (query the live sp_theme record for current source)

// Grays
$gray-base: #000000;
$gray-dark: sp-rgb(--now-color--neutral-16, #1D272B) !default;
$gray-darker: sp-rgb(--now-color--neutral-18, #10171A) !default;
$gray-light: sp-rgb(--now-color--neutral-9, #616D74) !default;
$gray-lighter: sp-rgb(--now-color--neutral-1, #F5F6F7) !default;
$gray: sp-rgb(--now-color--neutral-11, #3D4A50) !default;

// Brand colors
$brand-primary: sp-rgb(--now-color--primary-1, #0080A3) !default;
$brand-success: sp-rgb(--now-color_alert--positive-3, #3E8600) !default;
$brand-warning: sp-rgb(--now-color_alert--warning-3, #B29800) !default;
$brand-danger: sp-rgb(--now-color_alert--critical-3, #E52239) !default;
$brand-info: sp-rgb(--now-color_alert--info-3, #007AC9) !default;

// Background
$body-bg: sp-rgb(--now-color_background--primary, #FFFFFF) !default;
$background-primary: sp-rgb(--now-color_background--primary, #FFFFFF);
$background-secondary: sp-rgb(--now-color_background--secondary, #F5F6F7);
$background-tertiary: sp-rgb(--now-color_background--tertiary, #E2E5E7);

// Text
$text-color: sp-rgb(--now-color_text--primary, #10171A) !default;
$text-primary: sp-rgb(--now-color_text--primary, #10171A);
$text-secondary: sp-rgb(--now-color_text--secondary, #232E33) !default;
$text-tertiary: sp-rgb(--now-color_text--tertiary, #37444A);
$text-muted: sp-rgb(--now-color_text--tertiary, #37444A) !default;

// Links
$link-color: sp-rgb(--now-color--link-2, #1955BE);
$link-hover-color: sp-rgb(--now-color--link-3, #113A82);

// Navbar
$navbar-inverse-bg: sp-rgb(--now-color_background--primary, #FFFFFF) !default;
$navbar-inverse-link-color: sp-rgb(--now-color_text--primary, #10171A) !default;
$navbar-inverse-link-hover-color: sp-rgb(--now-color_text--primary, #10171A) !default;
$navbar-inverse-link-hover-bg: sp-rgb(--now-color--primary-0, #BDDEE7) !default;
$navbar-inverse-link-active-bg: sp-rgb(--now-color_background--secondary, #F5F6F7) !default;
$sp-navbar-divider-color: sp-rgb(--now-color_divider--tertiary, #CFD5D7) !default;
$sp-navbar-bottom-width: 0.125rem !default;

// Borders
$border-primary: sp-rgb(--now-color_border--primary, #737F84);
$border-secondary: sp-rgb(--now-color_border--secondary, #AAB2B6);
$border-tertiary: sp-rgb(--now-color_border--tertiary, #CFD5D7);
$input-border: sp-rgb(--now-color_border--primary, #737F84) !default;
$input-border-focus: sp-rgb(--now-color--focus-ring, #359325) !default;

// Buttons
$btn-primary-color: sp-rgb(--now-color_text--primary-actionable, #FFFFFF) !default;
$btn-primary-bg: sp-rgb(--now-color--primary-2, #00566E);
$btn-primary-border: sp-rgb(--now-color--primary-2, #00566E);
$btn-default-bg: sp-rgb(--now-color_background--primary, #FFFFFF);
$btn-default-border: sp-rgb(--now-color_border--tertiary, #CFD5D7) !default;

// Panels
$panel-bg: sp-rgb(--now-color_background--primary, #FFFFFF);
$panel-default-border: sp-rgb(--now-color_border--tertiary, #CFD5D7);
$panel-primary-heading-bg: sp-rgb(--now-color--primary-1, #0080A3);
$panel-primary-text: sp-rgb(--now-color_text--primary-actionable, #FFFFFF) !default;

// Alerts/States
$state-success-bg: sp-rgb(--now-color_alert--positive-0, #C7DCB5) !default;
$state-warning-bg: sp-rgb(--now-color_alert--warning-0, #ECE5BF) !default;
$state-danger-bg: sp-rgb(--now-color_alert--critical-0, #F9C8CE) !default;
$state-info-bg: sp-rgb(--now-color_alert--info-0, #BDDCF1) !default;
```

## Critical Rules Summary

| Rule | Why | Common Mistake |
| NO IIFE in server scripts | Headers/footers don't use IIFE context | Wrapping in `(function() { ... })();` |
| Include `@media` query CSS | Framework class may not apply; fallback required | Only using `.responsive-desktop` class |
| Wrap template in outer `<div>` | Framework expects single root | Starting with `<nav>` directly |
| NO `navbar-fixed-top` class | Framework handles via `body.fixed-header` | Adding positioning classes |
| Use `sp-navbar-toggle=""` directive | Framework handles collapse | Using only Bootstrap collapse |
| Collapse target must be `#sp-nav-bar` | Framework expects this ID | Custom IDs like `#my-nav` |
| Use `data.menu` NOT `c.data.menu` | Headers don't use controller alias | Using `c.data.*` |
| Use `sp-rgb()` for all colors | UXF/dark mode support | Raw hex values |
| All variables end with `!default` | Allow theme override | Missing `!default` |

## MANDATORY: Header/Footer Prevention Checklist

BEFORE creating ANY custom header or footer, the agent MUST verify ALL items below. Skipping any item will cause silent failures.

### Server Script Checklist

-  NO IIFE wrapper — Script starts with bare statements, NOT `(function() {`

-  Menu fetch present — Contains `var menu = $sp.getValue("sp_rectangle_menu");`

-  Menu widget loaded — Contains `data.menu = $sp.getWidgetFromInstance(menu);`

-  Replace flag set — Contains `data.menu.data.replace = true;`

-  Menu items flag set — Contains `data.hasMenuItems = ...`

-  Login page fetched — Contains `data.login_page = $sp.getValue('login_page');`

### Client Script Checklist

-  Avatar profile initialized — Contains `$scope.avatarProfile = { userID: ..., name: ..., initials: ... }`

-  User image set — Contains `if ($window.NOW.user_avatar) { $scope.avatarProfile.userImage = ... }`

-  Show avatar flags set — Contains `$scope.showAvatar = $scope.user.logged_in`

-  Collapse handler present — Contains `$scope.collapse = function() { $rootScope.$emit('sp-navbar-collapse'); }`

### CSS Checklist

- 
 NO `!important` on background-color — Blocks `ng-style` from setting avatar image

- 
 Desktop media query present — Contains `@media (min-width: 993px) { .navbar-right { display: flex !important; } }`

- 
 Mobile media query present — Contains `@media (max-width: 992px) { ... }`

- 
 Uses theme variables — Uses `$sp-navbar-*`, `$sp-logo-*`, `$brand-*` variables, NOT raw hex

- 
 All variables have `!default` — Every `$variable:` ends with `!default`

### Template Checklist

-  Wrapped in outer `<div>` — Template starts with `<div>`, not `<nav>`

-  Menu widget rendered — Contains `<sp-widget widget="::data.menu"></sp-widget>`

-  Collapse target is `#sp-nav-bar` — Uses `data-target="#sp-nav-bar"`, NOT custom ID

-  Has `sp-navbar-toggle=""` directive — On the collapsible div

-  NO `navbar-fixed-top` class — Framework handles positioning

-  User controls present — Has `ng-if="user.logged_in"` section with profile/logout

### Portal Wiring Checklist

-  Theme has header — `SPTheme({ header: portalHeader, ... })`

-  Portal has theme — `ServicePortal({ theme: enterpriseTheme, ... })`

-  Portal has menu — `ServicePortal({ mainMenu: portalMenu, ... })`

## Related Guides

This reference provides OOTB patterns as a starting point — always verify against the live record before using it. Load the guides below for implementation details:

| When you need to… | Load this guide |
| Build a portal, pages, widgets, server/client scripts | `service-portal-guide` |
| Create custom theme, header/footer, menu, providers | `service-portal-components-guide` |
| Add route maps, troubleshoot issues, verify deployment | `service-portal-advanced-guide` |
