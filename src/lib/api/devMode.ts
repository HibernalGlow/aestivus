/**
 * Dev Mode API
 * 用于在 Release 版本中切换 webview 加载的 URL
 * - Dev 模式：从本地开发服务器加载（如 localhost:1096）
 * - Release 模式：从打包的静态文件加载
 */

import { invoke } from '@tauri-apps/api/core';

/**
 * 切换到 Dev 模式（加载开发服务器）
 * @returns 成功消息
 */
export async function switchToDevMode(): Promise<string> {
	try {
		return await invoke<string>('switch_to_dev_mode');
	} catch (e) {
		console.error('[devMode] Failed to switch to dev mode:', e);
		throw e;
	}
}

/**
 * 切换到 Release 模式（加载打包的静态文件）
 * @returns 成功消息
 */
export async function switchToReleaseMode(): Promise<string> {
	try {
		return await invoke<string>('switch_to_release_mode');
	} catch (e) {
		console.error('[devMode] Failed to switch to release mode:', e);
		throw e;
	}
}

/**
 * 获取当前 Dev Mode 状态
 * @returns 是否处于 Dev 模式
 */
export async function getDevModeStatus(): Promise<boolean> {
	try {
		return await invoke<boolean>('get_dev_mode_status');
	} catch (e) {
		console.error('[devMode] Failed to get dev mode status:', e);
		return false;
	}
}

/**
 * 设置 Dev 服务器 URL
 * @param url 开发服务器 URL（如 http://localhost:1096）
 * @returns 设置的 URL
 */
export async function setDevUrl(url: string): Promise<string> {
	try {
		return await invoke<string>('set_dev_url', { url });
	} catch (e) {
		console.error('[devMode] Failed to set dev URL:', e);
		throw e;
	}
}
