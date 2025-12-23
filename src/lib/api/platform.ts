/**
 * 平台 API 封装层
 * 提供统一的接口，支持 Tauri 和浏览器环境
 */

import { getApiBaseUrl } from '$lib/stores/backend';

// Tauri API 类型声明
declare global {
  interface Window {
    __TAURI__?: {
      core: {
        invoke: (cmd: string, args?: Record<string, unknown>) => Promise<unknown>;
      };
    };
  }
}

export interface PlatformAPI {
  /** 打开文件夹选择对话框 */
  openFolderDialog(title?: string): Promise<string | null>;
  /** 打开文件选择对话框 */
  openFileDialog(title?: string, filters?: FileFilter[]): Promise<string | null>;
  /** 读取剪贴板 */
  readClipboard(): Promise<string>;
  /** 写入剪贴板 */
  writeClipboard(text: string): Promise<void>;
  /** 验证路径 */
  validatePath(path: string): Promise<PathValidation>;
  /** 是否为 Tauri 环境 */
  isTauri(): boolean;
}

export interface FileFilter {
  name: string;
  extensions: string[];
}

export interface PathValidation {
  valid: boolean;
  exists: boolean;
  isDir: boolean;
  isFile: boolean;
  message: string;
}

/**
 * Tauri 平台 API 实现
 */
class TauriPlatformAPI implements PlatformAPI {
  isTauri(): boolean {
    return true;
  }

  async openFolderDialog(title?: string): Promise<string | null> {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const result = await open({
        directory: true,
        title: title || '选择文件夹'
      });
      return result as string | null;
    } catch (error) {
      console.error('[TauriPlatformAPI] openFolderDialog error:', error);
      return null;
    }
  }

  async openFileDialog(title?: string, filters?: FileFilter[]): Promise<string | null> {
    try {
      const { open } = await import('@tauri-apps/plugin-dialog');
      const result = await open({
        directory: false,
        title: title || '选择文件',
        filters: filters
      });
      return result as string | null;
    } catch (error) {
      console.error('[TauriPlatformAPI] openFileDialog error:', error);
      return null;
    }
  }

  async readClipboard(): Promise<string> {
    try {
      const { readText } = await import('@tauri-apps/plugin-clipboard-manager');
      return (await readText()) || '';
    } catch (error) {
      console.error('[TauriPlatformAPI] readClipboard error:', error);
      return '';
    }
  }

  async writeClipboard(text: string): Promise<void> {
    try {
      const { writeText } = await import('@tauri-apps/plugin-clipboard-manager');
      await writeText(text);
    } catch (error) {
      console.error('[TauriPlatformAPI] writeClipboard error:', error);
    }
  }

  async validatePath(path: string): Promise<PathValidation> {
    // 通过后端 API 验证路径
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/system/validate-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      if (response.ok) {
        const data = await response.json();
        return {
          valid: data.valid,
          exists: data.exists,
          isDir: data.is_dir,
          isFile: data.is_file,
          message: data.message
        };
      }
    } catch (error) {
      console.error('[TauriPlatformAPI] validatePath error:', error);
    }
    return {
      valid: false,
      exists: false,
      isDir: false,
      isFile: false,
      message: '验证失败'
    };
  }
}

/**
 * 浏览器平台 API 实现
 * 使用原生 input 元素实现文件选择
 */
class BrowserPlatformAPI implements PlatformAPI {
  isTauri(): boolean {
    return false;
  }

  async openFolderDialog(title?: string): Promise<string | null> {
    // 浏览器原生文件夹选择（需要 webkitdirectory 支持）
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.webkitdirectory = true;
      input.style.display = 'none';
      
      input.onchange = () => {
        const files = input.files;
        if (files && files.length > 0) {
          // 返回第一个文件的相对路径的目录部分
          const path = files[0].webkitRelativePath;
          const folderName = path.split('/')[0];
          resolve(folderName);
        } else {
          resolve(null);
        }
        document.body.removeChild(input);
      };
      
      input.oncancel = () => {
        resolve(null);
        document.body.removeChild(input);
      };
      
      document.body.appendChild(input);
      input.click();
    });
  }

  async openFileDialog(title?: string, filters?: FileFilter[]): Promise<string | null> {
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.style.display = 'none';
      
      // 转换 filters 为 accept 属性
      if (filters && filters.length > 0) {
        const accept = filters
          .flatMap(f => f.extensions.map(ext => `.${ext}`))
          .join(',');
        input.accept = accept;
      }
      
      input.onchange = () => {
        const file = input.files?.[0];
        if (file) {
          resolve(file.name);
        } else {
          resolve(null);
        }
        document.body.removeChild(input);
      };
      
      input.oncancel = () => {
        resolve(null);
        document.body.removeChild(input);
      };
      
      document.body.appendChild(input);
      input.click();
    });
  }

  async readClipboard(): Promise<string> {
    try {
      return await navigator.clipboard.readText();
    } catch (error) {
      console.error('[BrowserPlatformAPI] readClipboard error:', error);
      return '';
    }
  }

  async writeClipboard(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
    } catch (error) {
      console.error('[BrowserPlatformAPI] writeClipboard error:', error);
    }
  }

  async validatePath(path: string): Promise<PathValidation> {
    try {
      const response = await fetch(`${getApiBaseUrl()}/api/v1/system/validate-path`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path })
      });
      if (response.ok) {
        const data = await response.json();
        return {
          valid: data.valid,
          exists: data.exists,
          isDir: data.is_dir,
          isFile: data.is_file,
          message: data.message
        };
      }
    } catch (error) {
      console.error('[BrowserPlatformAPI] validatePath error:', error);
    }
    return {
      valid: false,
      exists: false,
      isDir: false,
      isFile: false,
      message: '验证失败'
    };
  }
}

/**
 * 检测当前是否为 Tauri 环境
 */
export function isTauriEnvironment(): boolean {
  return typeof window !== 'undefined' && '__TAURI__' in window;
}

/**
 * 获取平台 API 实例
 * 自动检测环境并返回对应实现
 */
export function getPlatformAPI(): PlatformAPI {
  if (isTauriEnvironment()) {
    return new TauriPlatformAPI();
  }
  return new BrowserPlatformAPI();
}

/** 平台 API 单例 */
export const platform = getPlatformAPI();
