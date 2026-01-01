# React Migration Evaluation

**Date:** 2026-01-01
**Target:** Migrate from Svelte/SvelteKit to React (Vite or Next.js)

## 1. Executive Summary
The migration of `aestivus` from Svelte to React is **feasible but high-effort**. The project is not a simple CRUD app; it relies heavily on `@xyflow/svelte` (Svelte Flow) for its core functionality. While the backend interaction (Tauri) and styling (Tailwind) are highly portable, the 170+ components and intricate state management logic will require a significant rewrite rather than a simple syntax translation.

**Estimated Effort:** High (Weeks to Months depending on team size)
**Risk Level:** Medium-High (Risk of regression in Flow Editor interactions)

## 2. Dependency Mapping & Strategy

### Core Framework
| Current (Svelte) | Target (React) | Notes |
| :--- | :--- | :--- |
| **SvelteKit** | **Vite + React Router** or **Next.js** | Since this is a Tauri app, **Vite + React Router** is recommended for a pure SPA experience (Single Page Application) which aligns better with Tauri's distribution model than Next.js server features. |
| **Svelte 5** | **React 19** | |

### Critical Libraries
| Feature | Svelte Library | React Replacement | Complexity |
| :--- | :--- | :--- | :--- |
| **Flow/Node Editor** | `@xyflow/svelte` | `@xyflow/react` | **High**. This is the core logic. While concepts share an origin, the implementation details of nodes, handles, and event propagation differ. |
| **UI Components** | `bits-ui` | `Radix UI` / `shadcn/ui` | **Medium**. `bits-ui` is a port of Radix, so the API concepts are similar, but every component template must be rewritten. |
| **Animations** | `svelte-motion` | `framer-motion` | **Low**. `svelte-motion` is a direct port of `framer-motion`, so API compatibility is high. |
| **Icons** | `@lucide/svelte` | `@lucide/react` | **Low**. Direct drop-in replacement. |
| **Drag & Drop** | `svelte-dnd-action` | `dnd-kit` or `react-beautiful-dnd` | **Medium**. Logic will need adaptation. |

## 3. Architecture & State Management

### State Migration
*   **Current:** Svelte Stores (`writable`, `derived`) and Svelte 5 Runes (`.svelte.ts`).
*   **Target:** **Zustand** is strongly recommended over generic React Context for this application.
    *   Zustand's store model closely mimics Svelte's global stores.
    *   It avoids the "provider hell" of Context and performance issues with frequent updates (crucial for a canvas/node editor).

### Backend Integration (Tauri)
*   **Current:** `@tauri-apps/api`.
*   **Target:** Unchanged. The Tauri API is framework-agnostic. You can reuse the logic in `src/lib/api` or `src/lib/services` with minimal changes, wrapping them in React Hooks (e.g., `useQuery` from TanStack Query) for better lifecycle management.

## 4. Migration Roadmap

### Phase 1: Foundation Setup
1.  Initialize a new React + Vite project structure alongside the existing one (or in a separate branch).
2.  Install `tailwindcss`, `shadcn/ui`, `@xyflow/react`, and `zustand`.
3.  Port global styles (`app.css`) and Tailwind config.

### Phase 2: Utilities & Services
1.  Port `src/lib/utils.ts` and helper functions.
2.  Port API services (Tauri wrappers). Since these are likely pure TS, they might be copy-paste compatible.

### Phase 3: The Flow Editor (The Hard Part)
1.  Re-implement the main `FlowCanvas` using `@xyflow/react`.
2.  Port custom Node components one by one. **This is where 60% of the effort will go.**
3.  Ensure state synchronization between the React Flow instance and the global application state.

### Phase 4: UI Shell & Pages
1.  Port the layout (`Sidebar`, `Header`).
2.  Port the simplified pages (Settings, etc.).

## 5. Pros & Cons

### Pros
*   **Ecosystem:** React has a vastly larger ecosystem of components and libraries.
*   **Hiring:** Easier to find React developers than Svelte developers.
*   **Tooling:** Mature tooling for everything from testing to visualization.

### Cons
*   **Performance:** Svelte's compilation approach often yields better performance for complex DOM interactions (like a node editor) out-of-the-box compared to React's Virtual DOM diffing, though React 19 and proper memoization minimize this gap.
*   **Verbosity:** React components will likely be more verbose (hooks, imports, JSX wrappers) than their Svelte equivalents.
*   **Lost Work:** The current codebase seems modern (Svelte 5). Rewriting it is throwing away working, high-quality code.

## 6. Recommendation
Only proceed if:
1.  The team struggles to maintain the Svelte codebase due to lack of familiarity.
2.  There is a critical library required that *only* exists in React (unlikely given the current stack).

If the current application is stable and performant, the ROI (Return on Investment) of a rewrite is low.
