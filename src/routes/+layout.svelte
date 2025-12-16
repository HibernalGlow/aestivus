<script lang="ts">
	import '../app.css';
	import ThemeImportDialog from '$lib/components/layout/ThemeImportDialog.svelte';
	import SettingsOverlay from '$lib/components/settings/SettingsOverlay.svelte';
	
	let { children } = $props();
</script>

<div class="h-screen flex flex-col overflow-hidden">
	<div class="flex-1 overflow-hidden">
		{@render children()}
	</div>
</div>

<ThemeImportDialog />
<SettingsOverlay />
