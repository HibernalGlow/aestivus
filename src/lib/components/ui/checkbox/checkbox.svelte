<script lang="ts">
  import { cn } from "$lib/utils";
  import { Check } from "@lucide/svelte";

  interface Props {
    checked?: boolean;
    disabled?: boolean;
    id?: string;
    class?: string;
    onchange?: (checked: boolean) => void;
  }

  let {
    checked = $bindable(false),
    disabled = false,
    id,
    class: className,
    onchange,
  }: Props = $props();

  function handleClick() {
    if (!disabled) {
      checked = !checked;
      onchange?.(checked);
    }
  }
</script>

<button
  type="button"
  role="checkbox"
  aria-checked={checked}
  {disabled}
  {id}
  class={cn(
    "peer h-4 w-4 shrink-0 rounded-sm border border-primary ring-offset-background",
    "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
    "disabled:cursor-not-allowed disabled:opacity-50",
    "data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground",
    className
  )}
  data-state={checked ? "checked" : "unchecked"}
  onclick={handleClick}
>
  {#if checked}
    <span class="flex items-center justify-center text-current">
      <Check class="h-3.5 w-3.5" />
    </span>
  {/if}
</button>
