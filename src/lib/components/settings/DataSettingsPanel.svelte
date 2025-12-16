<script lang="ts">
	/**
	 * Aestivus - 数据设置面板
	 * 包含备份和同步两个子标签
	 */
	import { HardDrive, Cloud } from '@lucide/svelte';
	import * as Tabs from '$lib/components/ui/tabs';
	import BackupSettingsPanel from '$lib/components/settings/BackupSettingsPanel.svelte';
	import GistSyncPanel from '$lib/components/settings/GistSyncPanel.svelte';

	let activeTab = $state('backup');
</script>

<div class="h-full flex flex-col">
	<Tabs.Root bind:value={activeTab} class="flex-1 flex flex-col">
		<div class="border-b px-4">
			<Tabs.List class="h-10">
				<Tabs.Trigger value="backup" class="gap-2">
					<HardDrive class="h-4 w-4" />
					备份
				</Tabs.Trigger>
				<Tabs.Trigger value="sync" class="gap-2">
					<Cloud class="h-4 w-4" />
					同步
				</Tabs.Trigger>
			</Tabs.List>
		</div>

		<div class="flex-1 overflow-auto">
			<Tabs.Content value="backup" class="h-full m-0 p-0">
				<BackupSettingsPanel />
			</Tabs.Content>
			<Tabs.Content value="sync" class="h-full m-0 p-0">
				<GistSyncPanel />
			</Tabs.Content>
		</div>
	</Tabs.Root>
</div>
