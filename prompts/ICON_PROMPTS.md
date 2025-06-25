# Stream Deck Icon Generation Prompts

This file contains all the prompts for generating icons for the Claude Deck Stream Deck plugin.

## Overview

Total: **9 unique icons** across 3 buttons with multiple states each.

## Button 1: OK Button (3 States)

### State 0 - Ready/Normal
```
A clean, bold green checkmark icon on transparent background. Modern flat design, thick stroke weight, rounded corners. The checkmark should be centered and take up about 60% of the canvas. Color: #22c55e (green-500). Optimized for 72x72px display.
```

### State 1 - Thinking/Wait
```
A muted orange checkmark with three small dots (...) positioned to the right on transparent background. Modern flat design indicating processing/wait state. Checkmark color: #f59e0b (amber-500), dots slightly smaller and same color. Shows "wait before pressing". Optimized for 72x72px.
```

### State 2 - Offline
```
A muted gray checkmark icon on transparent background. Same design as active state but desaturated. Color: #6b7280 (gray-500). The icon should appear dimmed/disabled. Optimized for 72x72px display.
```

## Button 2: Escape Button (2 States)

### State 0 - Active
```
A clean, bold red X/cross icon on transparent background. Modern flat design, thick stroke weight, rounded corners. The X should be centered and take up about 60% of the canvas. Color: #ef4444 (red-500). Optimized for 72x72px display.
```

### State 1 - Offline
```
A muted gray X/cross icon on transparent background. Same design as active state but desaturated. Color: #6b7280 (gray-500). The icon should appear dimmed/disabled. Optimized for 72x72px display.
```

## Button 3: Shift+Tab Button (4 States)

### State 0 - Normal/Interactive
```
A clean tab key icon or forward arrow with underline on transparent background. Modern flat design in white/light gray. Color: #f8fafc (slate-50). Bold design representing normal mode. Centered, taking up 60% of canvas. Optimized for 72x72px.
```

### State 1 - Plan Mode
```
A pause symbol (two vertical rectangles) in teal/cyan color on transparent background. Modern flat design, representing planning/pause state. Color: #06b6d4 (cyan-500). Bold, thick strokes. Centered, taking up 60% of canvas. Optimized for 72x72px.
```

### State 2 - Auto-Accept Mode
```
Two forward-pointing chevrons (>>) in bright purple on transparent background. Modern flat design, indicating automatic progression. Color: #a855f7 (purple-500). Bold, thick strokes. Centered, taking up 60% of canvas. Optimized for 72x72px.
```

### State 3 - Offline/Error
```
A circle with a diagonal line through it (prohibited/offline symbol) in gray on transparent background. Modern flat design, representing disconnected state. Color: #6b7280 (gray-500). Bold design. Centered, taking up 60% of canvas. Optimized for 72x72px.
```

## Design Guidelines

- **Size**: Generate for 72x72px (standard) and 144x144px (@2x retina)
- **Style**: Modern flat design, no gradients or shadows
- **Background**: Transparent PNG
- **Stroke weight**: Bold/thick for visibility at small sizes
- **Contrast**: High contrast for visibility on Stream Deck
- **Color scheme**: Use semantic colors (green=ready, red=cancel, orange=wait, gray=offline)

## File Structure

Icons should be saved to:
```
claude-deck-plugin-v2/context/de.co.context.claudedeck.sdPlugin/imgs/actions/
├── ok/
│   ├── icon.png (state 0 - 72x72)
│   ├── icon@2x.png (state 0 - 144x144)
│   ├── thinking/
│   │   ├── icon.png (state 1 - 72x72)
│   │   └── icon@2x.png (state 1 - 144x144)
│   └── offline/
│       ├── icon.png (state 2 - 72x72)
│       └── icon@2x.png (state 2 - 144x144)
├── escape/
│   ├── icon.png (state 0 - 72x72)
│   ├── icon@2x.png (state 0 - 144x144)
│   └── offline/
│       ├── icon.png (state 1 - 72x72)
│       └── icon@2x.png (state 1 - 144x144)
└── shift-tab/
    ├── icon.png (state 0 - 72x72)
    ├── icon@2x.png (state 0 - 144x144)
    ├── plan/
    │   ├── icon.png (state 1 - 72x72)
    │   └── icon@2x.png (state 1 - 144x144)
    ├── auto-accept/
    │   ├── icon.png (state 2 - 72x72)
    │   └── icon@2x.png (state 2 - 144x144)
    └── offline/
        ├── icon.png (state 3 - 72x72)
        └── icon@2x.png (state 3 - 144x144)
```

## Notes

- Current icons exist for some states but may need refreshing
- The OK button thinking/wait state is new and needs to be implemented
- All icons should maintain consistent visual style across the plugin
- Consider testing visibility on both light and dark Stream Deck themes
