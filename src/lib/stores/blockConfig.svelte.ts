/**
 * 区块配置存储
 * 管理各节点内区块的顺序、展开状态和可见性
 * 从 nodeBlockRegistry 读取支持区块的节点
 */
import type { Component } from 'svelte';
import { nodeBlockRegistry } from '$lib/components/blocks/blockRegistry';

// 区块配置
export interface BlockConfig {
	id: string;
	title: string;
	icon?: Component;
	order: number;
	visible: boolean;
	expanded: boolean;
	canHide: boolean;
	colSpan?: 1 | 2;
}

// 节点区块配置
export interface NodeBlockConfig {
	nodeType: string;
	blocks: BlockConfig[];
}

const STORAGE_KEY = 'aestivus_block_configs_v1';

// 从 registry 生成默认区块配置
function generateDefaultConfigs(): Record<string, BlockConfig[]> {
	const result: Record<string, BlockConfig[]> = {};
	
	for (const [nodeType, layout] of Object.entries(nodeBlockRegistry)) {
		result[nodeType] = layout.blocks.map((block, index) => ({
			id: block.id,
			title: block.title,
			icon: block.icon,
			order: index,
			visible: block.visibleInNormal !== false,
			expanded: block.defaultExpanded !== false,
			canHide: true, // 假设所有区块都可以隐藏，除非 registry 新增字段控制
			colSpan: block.colSpan
		}));
	}
	
	return result;
}

// 默认区块配置
const defaultBlockConfigs = generateDefaultConfigs();

function createBlockConfigStore() {
	// 从 localStorage 加载
	function loadConfigs(): Record<string, BlockConfig[]> {
		try {
			const stored = localStorage.getItem(STORAGE_KEY);
			if (stored) {
				const parsed = JSON.parse(stored) as Record<string, BlockConfig[]>;
				const result: Record<string, BlockConfig[]> = {};

				for (const [nodeType, defaultBlocks] of Object.entries(defaultBlockConfigs)) {
					const storedBlocks = parsed[nodeType] || [];
					
					// 过滤掉 registry 中已不存在的区块
					const validStoredBlocks = storedBlocks.filter(b => 
						defaultBlocks.some(db => db.id === b.id)
					);
					
					const validIds = new Set(validStoredBlocks.map(b => b.id));
					
					// 计算当前最大 order
					const maxOrder = validStoredBlocks.length > 0
						? Math.max(...validStoredBlocks.map(b => b.order))
						: -1;

					// 添加新出现的区块（registry 中有但 storage 中没有）
					const newBlocks = defaultBlocks
						.filter(b => !validIds.has(b.id))
						.map((b, i) => ({
							...b,
							order: maxOrder + 1 + i
						}));

					// 合并：保留存储的配置（顺序、可见性），追加新区块
					// 注意：我们需要从 registry 重新获取 title/icon 等静态属性，但保留用户的 stored 属性 (visible, expanded, order)
					const mergedStored = validStoredBlocks.map(sb => {
						const def = defaultBlocks.find(db => db.id === sb.id);
						return {
							...sb,
							// 更新可能变化的静态属性
							title: def?.title || sb.title,
							icon: def?.icon, 
							colSpan: def?.colSpan
						};
					});

					result[nodeType] = [...mergedStored, ...newBlocks].sort((a, b) => a.order - b.order);
				}
				return result;
			}
		} catch (e) {
			console.warn('Failed to load block configs:', e);
		}
		return defaultBlockConfigs;
	}

	// 保存到 localStorage
	function saveConfigs(data: Record<string, BlockConfig[]>) {
		try {
			// 保存前去掉 icon 组件等非序列化数据，虽然 JSON.stringify 会自动忽略函数/组件，但还是干净点好
			// 实际上直接 stringify 组件对象可能会有问题，最好只存数据字段
			const toSave: Record<string, any[]> = {};
			for (const [k, v] of Object.entries(data)) {
				toSave[k] = v.map(({ icon, ...rest }) => rest);
			}
			localStorage.setItem(STORAGE_KEY, JSON.stringify(toSave));
		} catch (e) {
			console.warn('Failed to save block configs:', e);
		}
	}

	let configs = $state<Record<string, BlockConfig[]>>(loadConfigs());

	// 获取某节点的区块列表
	function getNodeBlocks(nodeType: string): BlockConfig[] {
		return [...(configs[nodeType] || [])].sort((a, b) => a.order - b.order);
	}

	// 设置可见性
	function setBlockVisible(nodeType: string, blockId: string, visible: boolean) {
		const blocks = configs[nodeType];
		if (!blocks) return;
		
		const idx = blocks.findIndex(b => b.id === blockId);
		if (idx !== -1) {
			blocks[idx] = { ...blocks[idx], visible };
			configs = { ...configs, [nodeType]: [...blocks] };
			saveConfigs(configs);
		}
	}

	// 移动区块
	function moveBlock(nodeType: string, blockId: string, newOrder: number) {
		const blocks = configs[nodeType];
		if (!blocks) return;

		const currentIdx = blocks.findIndex(b => b.id === blockId);
		if (currentIdx === -1) return;

		const block = blocks[currentIdx];
		const oldOrder = block.order;
		
		// 简单的重排序逻辑：更新所有受影响区块的 order
		// 这里我们简化处理：直接在数组中移动位置，然后重新分配 order
		const newBlocks = [...blocks];
		newBlocks.splice(currentIdx, 1); // 移除
		newBlocks.splice(newOrder, 0, block); // 插入新位置

		// 重新分配 order 0..N
		const reordered = newBlocks.map((b, i) => ({ ...b, order: i }));

		configs = { ...configs, [nodeType]: reordered };
		saveConfigs(configs);
	}

	// 重置某节点
	function resetNode(nodeType: string) {
		if (defaultBlockConfigs[nodeType]) {
			configs = {
				...configs,
				[nodeType]: defaultBlockConfigs[nodeType].map(b => ({ ...b })) // clone
			};
			saveConfigs(configs);
		}
	}

	return {
		get configs() { return configs; },
		getNodeBlocks,
		setBlockVisible,
		moveBlock,
		resetNode
	};
}

export const blockConfigStore = createBlockConfigStore();
