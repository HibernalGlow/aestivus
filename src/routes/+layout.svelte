<script lang="ts">
	import '../app.css';
	import { onMount } from 'svelte';
	import ThemeImportDialog from '$lib/components/layout/ThemeImportDialog.svelte';
	import SettingsOverlay from '$lib/components/settings/SettingsOverlay.svelte';
	import { initBackend, listenBackendReady, backendReady } from '$lib/stores/backend';
	import { hydrateFromBackend } from '$lib/stores/nodeLayoutStore';
	import { initPresets } from '$lib/stores/layoutPresets';
	
	let { children } = $props();
	
	// 初始化后端连接
	onMount(() => {
		initBackend();
		listenBackendReady();
		
		// 后端就绪后初始化存储
		const unsubscribe = backendReady.subscribe(async (ready) => {
			if (ready) {
				// 从后端加载布局配置（包含 localStorage 迁移）
				await hydrateFromBackend();
				// 初始化预设系统
				await initPresets();
				unsubscribe();
			}
		});
	});
</script>

<div class="h-screen flex flex-col overflow-hidden">
	<div class="flex-1 overflow-hidden">
		{@render children()}
	</div>
</div>

<ThemeImportDialog />
<SettingsOverlay />
