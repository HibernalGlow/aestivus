/**
 * Findz 节点共享 hooks
 */

/** 
 * 复制到剪贴板并显示反馈
 * @returns [copied 状态, copy 函数]
 */
export function createCopyFeedback(timeout = 2000) {
  let copied = $state(false);
  
  async function copy(text: string): Promise<boolean> {
    try {
      await navigator.clipboard.writeText(text);
      copied = true;
      setTimeout(() => { copied = false; }, timeout);
      return true;
    } catch (e) {
      console.error('复制失败:', e);
      return false;
    }
  }
  
  return {
    get copied() { return copied; },
    copy
  };
}

/**
 * 格式化文件大小
 */
export function formatSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

/**
 * 解析大小字符串为字节数
 */
export function parseSize(str: string): number | null {
  if (!str.trim()) return null;
  const match = str.trim().match(/^([\d.]+)\s*(B|KB|MB|GB)?$/i);
  if (!match) return null;
  const num = parseFloat(match[1]);
  if (isNaN(num)) return null;
  const unit = (match[2] || 'B').toUpperCase();
  const multipliers: Record<string, number> = { 
    B: 1, KB: 1024, MB: 1024 * 1024, GB: 1024 * 1024 * 1024 
  };
  return num * (multipliers[unit] || 1);
}

/**
 * 解析数字字符串
 */
export function parseNumber(str: string): number | null {
  if (!str.trim()) return null;
  const num = parseInt(str, 10);
  return isNaN(num) ? null : num;
}
