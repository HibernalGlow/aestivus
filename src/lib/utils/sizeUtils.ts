/**
 * 尺寸工具模块 - Container Query 版本
 * 
 * 迁移状态：
 * - FindzNode: ✅ 已迁移到 Container Query
 * - 其他节点: ⏳ 待迁移，仍使用旧版 getSizeClasses
 * 
 * 新版使用方式：
 * 1. 容器添加 class="@container" 声明 container context
 * 2. 子元素使用 cq-* 类名，如 cq-input, cq-button, cq-text
 * 3. 条件显示使用 cq-compact-only / cq-wide-only
 * 4. 样式定义在 container-responsive.css
 */

/** 尺寸模式类型 */
export type SizeMode = 'compact' | 'normal';

/**
 * Container Query 类名映射（新版推荐）
 */
export const CQ_CLASSES = {
  input: 'cq-input',
  button: 'cq-button',
  buttonIcon: 'cq-button-icon',
  buttonSm: 'cq-button-sm',
  icon: 'cq-icon',
  iconSm: 'cq-icon-sm',
  iconLg: 'cq-icon-lg',
  gap: 'cq-gap',
  gapSm: 'cq-gap-sm',
  gapLg: 'cq-gap-lg',
  mb: 'cq-mb',
  text: 'cq-text',
  textSm: 'cq-text-sm',
  textLg: 'cq-text-lg',
  padding: 'cq-padding',
  paddingSm: 'cq-padding-sm',
  px: 'cq-px',
  py: 'cq-py',
  rounded: 'cq-rounded',
  roundedLg: 'cq-rounded-lg',
  maxHeight: 'cq-max-h',
  maxHeightSm: 'cq-max-h-sm',
  statCard: 'cq-stat-card',
  statValue: 'cq-stat-value',
  statLabel: 'cq-stat-label',
} as const;

export type CQClasses = typeof CQ_CLASSES;

/** 获取 CQ 类名对象 */
export function getCQClasses(): CQClasses {
  return CQ_CLASSES;
}

// ========== 兼容层（其他节点迁移前保留） ==========

/** 旧版样式类映射（其他节点迁移前保留） */
export const SIZE_CLASSES = {
  compact: {
    input: 'h-7 text-xs',
    select: 'h-6 text-xs',
    button: 'h-7 text-xs',
    buttonIcon: 'h-7 w-7',
    buttonSm: 'h-6 text-xs',
    icon: 'h-3 w-3',
    iconSm: 'h-2.5 w-2.5',
    iconLg: 'h-4 w-4',
    gap: 'gap-1',
    gapSm: 'gap-0.5',
    gapLg: 'gap-2',
    space: 'space-y-2',
    spaceSm: 'space-y-1',
    spaceLg: 'space-y-3',
    mb: 'mb-2',
    mbSm: 'mb-1',
    text: 'text-xs',
    textSm: 'text-[10px]',
    textLg: 'text-sm',
    padding: 'p-1.5',
    paddingSm: 'p-1',
    paddingLg: 'p-2',
    px: 'px-2',
    py: 'py-1',
    rounded: 'rounded',
    roundedLg: 'rounded-lg',
    maxHeight: 'max-h-40',
    maxHeightSm: 'max-h-16',
    gridCols: 'grid-cols-2',
  },
  normal: {
    input: 'h-10',
    select: 'h-9 text-sm',
    button: 'h-12',
    buttonIcon: 'h-10 w-10',
    buttonSm: 'h-8',
    icon: 'h-4 w-4',
    iconSm: 'h-3 w-3',
    iconLg: 'h-5 w-5',
    gap: 'gap-2',
    gapSm: 'gap-1',
    gapLg: 'gap-3',
    space: 'space-y-3',
    spaceSm: 'space-y-2',
    spaceLg: 'space-y-4',
    mb: 'mb-4',
    mbSm: 'mb-2',
    text: 'text-sm',
    textSm: 'text-xs',
    textLg: 'text-base',
    padding: 'p-2',
    paddingSm: 'p-1.5',
    paddingLg: 'p-3',
    px: 'px-3',
    py: 'py-2',
    rounded: 'rounded-lg',
    roundedLg: 'rounded-xl',
    maxHeight: 'max-h-80',
    maxHeightSm: 'max-h-40',
    gridCols: 'grid-cols-3',
  }
} as const;

export type SizeClasses = typeof SIZE_CLASSES[SizeMode];

/** 
 * 获取指定模式的样式类
 * @deprecated 迁移到 Container Query 后可删除
 */
export function getSizeClasses(size: SizeMode): SizeClasses {
  return SIZE_CLASSES[size];
}

/** 
 * 根据 isFullscreen 获取对应的 SizeMode
 * @deprecated 迁移到 Container Query 后可删除
 */
export function getSizeMode(isFullscreen: boolean): SizeMode {
  return isFullscreen ? 'normal' : 'compact';
}

/** 
 * 快捷辅助：根据 isFullscreen 直接获取样式类
 * @deprecated 迁移到 Container Query 后可删除
 */
export function getClasses(isFullscreen: boolean): SizeClasses {
  return SIZE_CLASSES[getSizeMode(isFullscreen)];
}
