<script lang="ts">
	/**
	 * 悬停显示/隐藏包装器 - 可复用的悬停逻辑
	 * 支持 pin 固定、延迟显示/隐藏、右键菜单保持
	 */
	import type { Snippet } from 'svelte';

	interface Props {
		isVisible: boolean;
		pinned: boolean;
		onVisibilityChange: (visible: boolean) => void;
		children: Snippet;
		hideDelay?: number;
		showDelay?: number;
	}

	let {
		isVisible = $bindable(false),
		pinned,
		onVisibilityChange,
		children,
		hideDelay = 300,
		showDelay = 0
	}: Props = $props();

	let hideTimer: number | null = null;
	let showTimer: number | null = null;
	let isContextMenuOpen = $state(false);

	// 鼠标进入 - 显示
	function handleMouseEnter() {
		if (!pinned) {
			if (hideTimer) {
				clearTimeout(hideTimer);
				hideTimer = null;
			}
			if (showTimer) {
				clearTimeout(showTimer);
				showTimer = null;
			}
			const delay = showDelay ?? 0;
			if (!isVisible && delay > 0) {
				showTimer = setTimeout(() => {
					isVisible = true;
					onVisibilityChange?.(true);
				}, delay) as unknown as number;
			} else {
				isVisible = true;
				onVisibilityChange?.(true);
			}
		}
	}

	// 鼠标离开 - 隐藏
	function handleMouseLeave() {
		if (!pinned && !isContextMenuOpen) {
			if (showTimer) {
				clearTimeout(showTimer);
				showTimer = null;
			}
			hideTimer = setTimeout(() => {
				if (!isContextMenuOpen) {
					isVisible = false;
					onVisibilityChange?.(false);
				}
			}, hideDelay) as unknown as number;
		}
	}

	// 右键菜单打开时保持显示
	function handleContextMenu() {
		if (!pinned) {
			isContextMenuOpen = true;
			if (hideTimer) {
				clearTimeout(hideTimer);
				hideTimer = null;
			}
			if (showTimer) {
				clearTimeout(showTimer);
				showTimer = null;
			}
		}
	}

	// 右键菜单关闭
	function handleContextMenuClose() {
		if (isContextMenuOpen) {
			isContextMenuOpen = false;
			setTimeout(() => {
				if (!pinned && !document.querySelector(':hover')?.closest('[data-hover-wrapper]')) {
					isVisible = false;
					onVisibilityChange?.(false);
				}
			}, 100);
		}
	}

	// pin 状态变化时强制显示
	$effect(() => {
		if (pinned) {
			isVisible = true;
			if (hideTimer) {
				clearTimeout(hideTimer);
				hideTimer = null;
			}
			if (showTimer) {
				clearTimeout(showTimer);
				showTimer = null;
			}
			onVisibilityChange?.(true);
		}
	});

	// 监听全局点击检测右键菜单关闭
	$effect(() => {
		const handleGlobalClick = () => {
			if (isContextMenuOpen) {
				handleContextMenuClose();
			}
		};

		const handleGlobalContextMenu = (e: MouseEvent) => {
			const target = e.target as HTMLElement | null;
			if (!target?.closest('[data-hover-wrapper="true"]')) {
				isContextMenuOpen = false;
			}
		};

		document.addEventListener('click', handleGlobalClick);
		document.addEventListener('contextmenu', handleGlobalContextMenu);

		return () => {
			document.removeEventListener('click', handleGlobalClick);
			document.removeEventListener('contextmenu', handleGlobalContextMenu);
		};
	});

	// 清理定时器
	$effect(() => {
		return () => {
			if (hideTimer) clearTimeout(hideTimer);
			if (showTimer) clearTimeout(showTimer);
		};
	});
</script>

<div
	class="relative flex w-full h-full"
	data-hover-wrapper="true"
	onmouseenter={handleMouseEnter}
	onmouseleave={handleMouseLeave}
	oncontextmenu={handleContextMenu}
	onclick={handleContextMenuClose}
>
	{@render children?.()}
</div>
