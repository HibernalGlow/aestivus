<script lang="ts">
  /**
   * CircularProgress - 圆形进度条组件
   * 类似电量小组件的圆环显示，中间显示数值
   */
  import { cn } from '$lib/utils';

  interface Props {
    /** 最大值 */
    max?: number;
    /** 最小值 */
    min?: number;
    /** 当前值 */
    value: number;
    /** 主色（进度条颜色） */
    primaryColor?: string;
    /** 次色（背景轨道颜色） */
    secondaryColor?: string;
    /** 尺寸 class，如 size-10, size-12 */
    size?: string;
    /** 显示的文本（默认显示百分比） */
    label?: string;
    /** 文字大小 class */
    textSize?: string;
    /** 自定义类名 */
    class?: string;
  }

  let {
    max = 100,
    min = 0,
    value = 0,
    primaryColor = 'hsl(var(--primary))',
    secondaryColor = 'hsl(var(--muted))',
    size = 'size-10',
    label,
    textSize = 'text-xs',
    class: className = ''
  }: Props = $props();

  // 计算百分比
  let percent = $derived(Math.min(100, Math.max(0, ((value - min) / (max - min)) * 100)));
  
  // SVG 圆环参数
  const radius = 45;
  const circumference = 2 * Math.PI * radius;
  let strokeDasharray = $derived(`${(percent / 100) * circumference} ${circumference}`);
</script>

<div class={cn('relative', size, className)}>
  <svg class="size-full -rotate-90" viewBox="0 0 100 100">
    <!-- 背景轨道 -->
    <circle
      cx="50"
      cy="50"
      r={radius}
      fill="none"
      stroke={secondaryColor}
      stroke-width="8"
    />
    <!-- 进度条 -->
    <circle
      cx="50"
      cy="50"
      r={radius}
      fill="none"
      stroke={primaryColor}
      stroke-width="8"
      stroke-linecap="round"
      stroke-dasharray={strokeDasharray}
      class="transition-all duration-500 ease-out"
    />
  </svg>
  <!-- 中间文字 -->
  <span class={cn('absolute inset-0 flex items-center justify-center font-medium', textSize)}>
    {label ?? Math.round(percent)}
  </span>
</div>
