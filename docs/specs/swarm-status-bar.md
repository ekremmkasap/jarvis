# Swarm Status Bar - Design Doc

## Overview
A fixed UI component at the top of the screen displaying real-time agent activity within the Jarvis AI swarm. It continuously polls (`GET /api/swarm-status` every 4s) without breaking the application in case of network failures.

## Agent Layout & Color Palette
- Seda (`seda`): #00ff88
- Mert (`mert`): #ffdd00
- Buse (`buse`): #ff69b4
- Eren (`eren`): #ff8c00
- Luna (`luna`): #9b59b6
- Sabrican (`sab`): #95a5a6
- Sabri (`sbr`): #e74c3c

## Implementation Plan
1. **Component**: `apps/web-ui/src/components/SwarmStatusBar.tsx` (Client component)
   - Uses `useEffect` and `setInterval` for polling.
   - Gracefully handles fetch errors (fallback to empty array).
   - Uses styled HTML elements or inline CSS with keyframe animations.
2. **Integration**: `apps/web-ui/src/app/layout.tsx`
   - Injected directly into the `<body>` element so it persists across all pages.
3. **Validation**: `npm run build` will verify there are no hydration or client-side Next.js issues.
