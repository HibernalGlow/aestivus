<script lang="ts">
  import { goto } from '$app/navigation';
  import { onMount } from 'svelte';

  // 直接跳转到流程编辑器
  onMount(() => {
    goto('/flow/new', { replaceState: true });
  });
</script>

<div class="min-h-screen w-full bg-background flex items-center justify-center">
  <p class="text-muted-foreground">加载中...</p>
</div>
