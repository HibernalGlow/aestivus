/**
 * 平台服务 - 提供跨平台的系统功能访问
 * 
 * 支持两种模式：
 * - pywebview 模式：通过 window.pywebview.api 调用 Python 桥接
 * - Web 模式：通过 FastAPI 后端或 Web API 实现
 */

// pywebview API 类型定义
declare global {
  interface Window {
    pywebview?: {
      api: {
        open_folder_dialog: (title?: string) => Promise<string | null>;
        open_file_dialog: (title?: string, fileTypes?: string[], allowMultiple?: boolean) => Promise<string[] | null>;
        read_clipboard: () => Promise<string>;
        write_clipboard: (text: string) => Promise<boolean>;
        validate_path: (path: string) => Promise<{
          valid: boolean;
          exists: boolean;
          is_dir: boolean;
          is_file: boolean;
          message: string;
        }>;
        get_clipboard_path: () => Promise<{
          path: string | null;
          valid: boolean;
          message: string;
        }>;
      };
    };
  }
}

/**
 * 检查是否在 pywebview 环境中运行
 */
export function isPywebviewMode(): boolean {
  return typeof window !== 'undefined' && 
         'pywebview' in window && 
         !!window.pywebview?.api;
}

/**
 * 平台服务接口
 */
export interface PlatformService {
  openFolderDialog(title?: string): Promise<string | null>;
  openFileDialog(title?: string, fileTypes?: string[], allowMultiple?: boolean): Promise<string[] | null>;
  readClipboard(): Promise<string>;
  writeClipboard(text: string): Promise<boolean>;
  validatePath(path: string): Promise<{
    valid: boolean;
    exists: boolean;
    is_dir: boolean;
    is_file: boolean;
    message: string;
  }>;
  getClipboardPath(): Promise<{
    path: string | null;
    valid: boolean;
    message: string;
  }>;
}

/**
 * pywebview 平台实现
 */
class PywebviewPlatform implements PlatformService {
  async openFolderDialog(title = '选择文件夹'): Promise<string | null> {
    if (!window.pywebview?.api) return null;
    return window.pywebview.api.open_folder_dialog(title);
  }

  async openFileDialog(title = '选择文件', fileTypes?: string[], allowMultiple = false): Promise<string[] | null> {
    if (!window.pywebview?.api) return null;
    return window.pywebview.api.open_file_dialog(title, fileTypes, allowMultiple);
  }

  async readClipboard(): Promise<string> {
    if (!window.pywebview?.api) return '';
    return window.pywebview.api.read_clipboard();
  }

  async writeClipboard(text: string): Promise<boolean> {
    if (!window.pywebview?.api) return false;
    return window.pywebview.api.write_clipboard(text);
  }

  async validatePath(path: string) {
    if (!window.pywebview?.api) {
      return { valid: false, exists: false, is_dir: false, is_file: false, message: 'pywebview 不可用' };
    }
    return window.pywebview.api.validate_path(path);
  }

  async getClipboardPath() {
    if (!window.pywebview?.api) {
      return { path: null, valid: false, message: 'pywebview 不可用' };
    }
    return window.pywebview.api.get_clipboard_path();
  }
}

/**
 * Web 平台实现（通过后端 API 或 Web API）
 */
class WebPlatform implements PlatformService {
  async openFolderDialog(): Promise<string | null> {
    // Web 模式下无法直接打开系统对话框
    // 可以通过后端 API 实现（如果后端运行在本地）
    console.warn('Web 模式不支持文件夹选择对话框');
    return null;
  }

  async openFileDialog(): Promise<string[] | null> {
    // 使用 HTML5 File API
    return new Promise((resolve) => {
      const input = document.createElement('input');
      input.type = 'file';
      input.multiple = true;
      input.onchange = () => {
        const files = Array.from(input.files || []).map(f => f.name);
        resolve(files.length > 0 ? files : null);
      };
      input.click();
    });
  }

  async readClipboard(): Promise<string> {
    try {
      return await navigator.clipboard.readText();
    } catch {
      return '';
    }
  }

  async writeClipboard(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      return false;
    }
  }

  async validatePath(path: string) {
    // Web 模式下无法验证本地路径
    // 假设路径有效（实际验证在后端执行时进行）
    return {
      valid: !!path && path.trim().length > 0,
      exists: true,
      is_dir: true,
      is_file: false,
      message: path ? '路径将在执行时验证' : '路径为空'
    };
  }

  async getClipboardPath() {
    const content = await this.readClipboard();
    if (!content || !content.trim()) {
      return { path: null, valid: false, message: '剪贴板为空' };
    }
    // 简单验证是否看起来像路径
    const trimmed = content.trim();
    const looksLikePath = trimmed.includes('/') || trimmed.includes('\\') || trimmed.match(/^[A-Z]:/i);
    return {
      path: looksLikePath ? trimmed : null,
      valid: looksLikePath,
      message: looksLikePath ? '路径将在执行时验证' : '剪贴板内容不像路径'
    };
  }
}

/**
 * 获取当前平台服务实例
 */
export function getPlatformService(): PlatformService {
  if (isPywebviewMode()) {
    return new PywebviewPlatform();
  }
  return new WebPlatform();
}

/**
 * 默认导出的平台服务实例
 */
export const platform = getPlatformService();
