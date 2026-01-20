<script lang="ts">
  import { ContextMenu as ContextMenuPrimitive } from "bits-ui";

  let {
    ref = $bindable(null),
    children,
    ...restProps
  }: ContextMenuPrimitive.TriggerProps = $props();
</script>

<ContextMenuPrimitive.Trigger
  bind:ref
  data-slot="context-menu-trigger"
  {...restProps}
>
  {@render children?.()}
</ContextMenuPrimitive.Trigger>
