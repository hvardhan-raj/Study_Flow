import QtQuick 2.15

// Global design tokens — import this file anywhere with:
//
//   Theme { id: theme }
QtObject {
    // ── Background / Surface ─────────────────────────────────────
    readonly property color bg:           "#F0F4F9"
    readonly property color surface:      "#FFFFFF"
    readonly property color surfaceAlt:   "#F8FAFC"
    readonly property color border:       "#E2E8F0"
    readonly property color borderLight:  "#F1F5F9"

    // ── Sidebar ──────────────────────────────────────────────────
    readonly property color sidebarBg:    "#111827"
    readonly property color sidebarText:  "#8FA3B8"
    readonly property color sidebarActive:"#FFFFFF"
    readonly property color sidebarAccent:"#3B82F6"

    // ── Text ─────────────────────────────────────────────────────
    readonly property color textPrimary:  "#0F172A"
    readonly property color textSecondary:"#475569"
    readonly property color textMuted:    "#94A3B8"
    readonly property color textDisabled: "#CBD5E1"

    // ── Accent / Brand ───────────────────────────────────────────
    readonly property color accent:       "#3B82F6"
    readonly property color accentHover:  "#2563EB"
    readonly property color accentLight:  "#EFF6FF"
    readonly property color accentBorder: "#BFDBFE"

    // ── Status ───────────────────────────────────────────────────
    readonly property color success:      "#10B981"
    readonly property color successLight: "#ECFDF5"
    readonly property color warning:      "#F59E0B"
    readonly property color warningLight: "#FFFBEB"
    readonly property color danger:       "#EF4444"
    readonly property color dangerLight:  "#FEF2F2"
    readonly property color purple:       "#8B5CF6"
    readonly property color purpleLight:  "#F5F3FF"

    // ── Typography ───────────────────────────────────────────────
    readonly property string fontFamily:  "Segoe UI"
    readonly property int    fontXs:      9
    readonly property int    fontSm:      11
    readonly property int    fontBase:    13
    readonly property int    fontMd:      15
    readonly property int    fontLg:      18
    readonly property int    fontXl:      22

    // ── Spacing ──────────────────────────────────────────────────
    readonly property int    spaceXs:     4
    readonly property int    spaceSm:     8
    readonly property int    space:       16
    readonly property int    spaceLg:     24
    readonly property int    spaceXl:     32

    // ── Radius ───────────────────────────────────────────────────
    readonly property int    radiusSm:    6
    readonly property int    radiusMd:    12
    readonly property int    radiusLg:    18
    readonly property int    radiusXl:    24

    // ── Animation ────────────────────────────────────────────────
    readonly property int    animFast:    120
    readonly property int    animNormal:  200
    readonly property int    animSlow:    350

    // ── Sidebar width ────────────────────────────────────────────
    readonly property int sidebarW: 220

    // ── Header height ────────────────────────────────────────────
    readonly property int headerH: 62
}
