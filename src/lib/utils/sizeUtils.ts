/**
 * 尺寸工具模块 - 统一管理节点模式和全屏模式的尺寸样式类
 * 消除节点组件中的 isFullscreenRender 条件判断
 */

/** 尺寸模式类型 */
export type SizeMode = 'compact' | 'normal';

/** 尺寸样式类映射 */
export const SIZE_CLASSES = {
  compact: {
    // 输入框
    input: 'h-7 text-xs',
    select: 'h-6 text-xs',
    // 按钮
    button: 'h-7 text-xs',
    buttonIcon: 'h-7 w-7',
    buttonSm: 'h-6 text-xs',
    // 图标
    icon: 'h-3 w-3',
    iconSm: 'h-2.5 w-2.5',
    iconLg: 'h-4 w-4',
    // 间距
    gap: 'gap-1',
    gapSm: 'gap-0.5',
    gapLg: 'gap-2',
    space: 'space-y-2',
    spaceSm: 'space-y-1',
    spaceLg: 'space-y-3',
    mb: 'mb-2',
    mbSm: 'mb-1',
    // 文字
    text: 'text-xs',
    textSm: 'text-[10px]',
    textLg: 'text-sm',
    // 内边距
    padding: 'p-1.5',
    paddingSm: 'p-1',
    paddingLg: 'p-2',
    px: 'px-2',
    py: 'py-1',
    // 圆角
    rounded: 'rounded',
    roundedLg: 'rounded-lg',
    // 高度限制
    maxHeight: 'max-h-40',
    maxHeightSm: 'max-h-16',
    // Grid
    gridCols: 'grid-cols-2',
  },
  normal: {
    // 输入框
    input: 'h-10',
    select: 'h-9 text-sm',
    // 按钮
    button: 'h-12',
    buttonIcon: 'h-10 w-10',
    buttonSm: 'h-8',
    // 图标
    icon: 'h-4 w-4',
    iconSm: 'h-3 w-3',
    iconLg: 'h-5 w-5',
    // 间距
    gap: 'gap-2',
    gapSm: 'gap-1',
    gapLg: 'gap-3',
    space: 'space-y-3',
    spaceSm: 'space-y-2',
    spaceLg: 'space-y-4',
    mb: 'mb-4',
    mbSm: 'mb-2',
    // 文字
    text: 'text-sm',
    textSm: 'text-xs',
    textLg: 'text-base',
    // 内边距
    padding: 'p-2',
    paddingSm: 'p-1.5',
    paddingLg: 'p-3',
    px: 'px-3',
    py: 'py-2',
    // 圆角
    rounded: 'rounded-lg',
    roundedLg: 'rounded-xl',
    // 高度限制
    maxHeight: 'max-h-80',
    maxHeightSm: 'max-h-40',
    // Grid
    gridCols: 'grid-cols-3',
  }
} as const;

/** 样式类类型 */
export type SizeClasses = typeof SIZE_CLASSES[SizeMode];

/** 获取指定模式的样式类 */
export function getSizeClasses(size: SizeMode): SizeClasses {
  return SIZE_CLASSES[size];
}

/** 根据 isFullscreen 获取对应的 SizeMode */
export function getSizeMode(isFullscreen: boolean): SizeMode {
  return isFullscreen ? 'normal' : 'compact';
}

/** 快捷辅助：根据 isFullscreen 直接获取样式类 */
export function getClasses(isFullscreen: boolean): SizeClasses {
  return SIZE_CLASSES[getSizeMode(isFullscreen)];
}
