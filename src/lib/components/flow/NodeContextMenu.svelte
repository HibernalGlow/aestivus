<script lang="ts">
  import { onMount } from "svelte";

  interface Props {
    id: string;
    x: number;
    y: number;
    onClose: () => void;
    onDelete: (id: string) => void;
    onDuplicate: (id: string) => void;
  }

  let { id, x, y, onClose, onDelete, onDuplicate }: Props = $props();

  function handleOutsideClick(e: MouseEvent) {
    onClose();
  }
</script>

<svelte:window
  onclick={handleOutsideClick}
  oncontextmenu={(e) => {
    e.preventDefault();
    onClose();
  }}
/>

<div
  class="node-context-menu"
  style="left: {x}px; top: {y}px;"
  onclick={(e) => e.stopPropagation()}
  role="menu"
  tabindex="-1"
>
  <button
    class="menu-item"
    onclick={() => {
      onDelete(id);
      onClose();
    }}
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      ><path d="M3 6h18" /><path
        d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6"
      /><path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" /><line
        x1="10"
        y1="11"
        x2="10"
        y2="17"
      /><line x1="14" y1="11" x2="14" y2="17" /></svg
    >
    <span>删除节点</span>
  </button>

  <button
    class="menu-item"
    onclick={() => {
      onDuplicate(id);
      onClose();
    }}
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      ><rect width="14" height="14" x="8" y="8" rx="2" ry="2" /><path
        d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2"
      /></svg
    >
    <span>复制节点</span>
  </button>

  <div class="menu-divider"></div>

  <button
    class="menu-item"
    onclick={() => {
      onClose();
    }}
  >
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
      stroke-linecap="round"
      stroke-linejoin="round"
      ><path d="M15 3h6v6" /><path d="M10 14 21 3" /><path
        d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"
      /></svg
    >
    <span>更多属性</span>
  </button>
</div>

<style>
  .node-context-menu {
    position: fixed;
    z-index: 2000;
    min-width: 160px;
    background: color-mix(in srgb, var(--card) 90%, transparent);
    backdrop-filter: blur(16px);
    border: 1px solid color-mix(in srgb, var(--border) 40%, transparent);
    border-radius: 0.75rem;
    padding: 0.5rem;
    box-shadow:
      0 10px 15px -3px rgb(0 0 0 / 0.1),
      0 4px 6px -4px rgb(0 0 0 / 0.1);
    animation: menu-in 0.15s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @keyframes menu-in {
    from {
      opacity: 0;
      transform: scale(0.95) translateY(-5px);
    }
    to {
      opacity: 1;
      transform: scale(1) translateY(0);
    }
  }

  .menu-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    border-radius: 0.5rem;
    color: var(--foreground);
    font-size: 0.875rem;
    transition: all 0.2s;
    background: transparent;
    border: none;
    cursor: pointer;
  }

  .menu-item:hover {
    background: color-mix(in srgb, var(--accent) 15%, transparent);
    color: var(--accent-foreground);
  }

  .menu-divider {
    height: 1px;
    background: color-mix(in srgb, var(--border) 30%, transparent);
    margin: 0.4rem 0.5rem;
  }

  .menu-item svg {
    opacity: 0.8;
  }
</style>
