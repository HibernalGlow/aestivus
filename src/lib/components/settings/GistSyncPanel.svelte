<script lang="ts">
	/**
	 * Aestivus - GitHub Gist 同步设置面板
	 */
	import { Button } from '$lib/components/ui/button';
	import { Input } from '$lib/components/ui/input';
	import { Label } from '$lib/components/ui/label';
	import { gistSyncStore } from '$lib/stores/gistSync.svelte';
	import { autoBackupStore } from '$lib/stores/autoBackup.svelte';

	let tokenInput = $state('');
	let loginError = $state('');
	let loginLoading = $state(false);

	// 响应式获取状态
	let config = $derived(gistSyncStore.config);
	let status = $derived(gistSyncStore.status);
	let statusMessage = $derived(gistSyncStore.statusMessage);
	let user = $derived(gistSyncStore.user);
	let isLoggedIn = $derived(gistSyncStore.isLoggedIn);

	async function handleLogin() {
		if (!tokenInput.trim()) {
			loginError = '请输入 GitHub Token';
			return;
		}
		loginLoading = true;
		loginError = '';
		
		const result = await gistSyncStore.login(tokenInput.trim());
		
		if (result.success) {
			tokenInput = '';
		} else {
			loginError = result.message;
		}
		loginLoading = false;
	}

	function handleLogout() {
		gistSyncStore.logout();
	}

	async function handleUpload() {
		// 构建备份数据
		const payload = autoBackupStore.buildFullBackupPayload('manual');
		const content = JSON.stringify(payload, null, 2);
		await gistSyncStore.updateGist(content);
	}

	async function handleDownload() {
		const result = await gistSyncStore.downloadFromGist();
		if (result.success && result.content) {
			try {
				const payload = JSON.parse(result.content);
				// 恢复 localStorage 数据
				if (payload.rawLocalStorage && typeof window !== 'undefined') {
					for (const [key, value] of Object.entries(payload.rawLocalStorage)) {
						try {
							localStorage.setItem(key, value as string);
						} catch (e) {
							console.error(`恢复 localStorage 键失败: ${key}`, e);
						}
					}
				}
				alert('同步成功！部分设置可能需要刷新页面生效。');
			} catch (e) {
				console.error('解析 Gist 内容失败:', e);
			}
		}
	}
</script>

<div class="space-y-6 p-6">
	<!-- 登录状态 -->
	<div class="space-y-4">
		<div>
			<h3 class="text-lg font-semibold">☁️ GitHub Gist 同步</h3>
			<p class="text-sm text-muted-foreground">将设置同步到 GitHub Gist，实现跨设备同步</p>
		</div>

		{#if isLoggedIn}
			<!-- 已登录状态 -->
			<div class="rounded-lg border p-4 space-y-3">
				<div class="flex items-center gap-3">
					{#if user?.avatar_url}
						<img src={user.avatar_url} alt={user.login} class="w-10 h-10 rounded-full" />
					{/if}
					<div>
						<p class="font-medium">{user?.login}</p>
						<p class="text-sm text-muted-foreground">已登录</p>
					</div>
				</div>
				<Button variant="outline" size="sm" onclick={handleLogout}>
					退出登录
				</Button>
			</div>
		{:else}
			<!-- 未登录状态 -->
			<div class="space-y-3">
				<div class="space-y-2">
					<Label>GitHub Personal Access Token</Label>
					<p class="text-xs text-muted-foreground">
						需要 <code class="bg-muted px-1 rounded">gist</code> 权限。
						<a href="https://github.com/settings/tokens/new?scopes=gist" target="_blank" class="text-primary underline">
							创建 Token
						</a>
					</p>
					<Input
						type="password"
						bind:value={tokenInput}
						placeholder="ghp_xxxxxxxxxxxx"
						onkeydown={(e) => e.key === 'Enter' && handleLogin()}
					/>
				</div>
				{#if loginError}
					<p class="text-sm text-destructive">{loginError}</p>
				{/if}
				<Button onclick={handleLogin} disabled={loginLoading}>
					{loginLoading ? '验证中...' : '登录'}
				</Button>
			</div>
		{/if}
	</div>

	{#if isLoggedIn}
		<hr class="border-border" />

		<!-- 同步操作 -->
		<div class="space-y-4">
			<div>
				<h3 class="text-lg font-semibold">同步操作</h3>
				<p class="text-sm text-muted-foreground">
					{#if config.gistId}
						已关联 Gist: <code class="bg-muted px-1 rounded text-xs">{config.gistId}</code>
					{:else}
						尚未创建 Gist，首次上传将自动创建
					{/if}
				</p>
			</div>

			<!-- 状态消息 -->
			{#if statusMessage}
				<div class="rounded-lg p-3 text-sm {status === 'error' ? 'bg-destructive/10 text-destructive' : status === 'success' ? 'bg-green-500/10 text-green-600' : 'bg-muted'}">
					{statusMessage}
				</div>
			{/if}

			<div class="flex gap-2">
				<Button 
					variant="default" 
					onclick={handleUpload}
					disabled={status === 'syncing'}
				>
					⬆️ 上传到 Gist
				</Button>
				<Button 
					variant="outline" 
					onclick={handleDownload}
					disabled={status === 'syncing' || !config.gistId}
				>
					⬇️ 从 Gist 下载
				</Button>
			</div>
		</div>

		<hr class="border-border" />

		<!-- 同步设置 -->
		<div class="space-y-4">
			<div>
				<h3 class="text-lg font-semibold">同步设置</h3>
			</div>

			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<div>
						<Label>自动同步</Label>
						<p class="text-xs text-muted-foreground">定时自动上传到 Gist</p>
					</div>
					<input
						type="checkbox"
						checked={config.autoSync}
						onchange={(e) => gistSyncStore.updateConfig({ autoSync: (e.target as HTMLInputElement).checked })}
						class="h-4 w-4"
					/>
				</div>

				{#if config.autoSync}
					<div class="flex items-center justify-between">
						<Label>同步间隔（分钟）</Label>
						<Input
							type="number"
							min="5"
							max="1440"
							value={config.syncInterval}
							onchange={(e) => gistSyncStore.updateConfig({ syncInterval: parseInt((e.target as HTMLInputElement).value) || 60 })}
							class="w-24"
						/>
					</div>
				{/if}

				<div class="flex items-center justify-between">
					<div>
						<Label>公开 Gist</Label>
						<p class="text-xs text-muted-foreground">设为公开后任何人都可以查看</p>
					</div>
					<input
						type="checkbox"
						checked={config.isPublic}
						onchange={(e) => gistSyncStore.updateConfig({ isPublic: (e.target as HTMLInputElement).checked })}
						class="h-4 w-4"
					/>
				</div>
			</div>
		</div>
	{/if}
</div>
