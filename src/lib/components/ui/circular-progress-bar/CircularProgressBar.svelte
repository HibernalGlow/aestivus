<script lang="ts">
  /**
   * 动画圆形进度条组件
   * 支持平滑动画过渡
   */
  import { cn } from '$lib/utils';

  interface Props {
    max?: number;
    value?: number;
    min?: number;
    gaugePrimaryColor?: string;
    gaugeSecondaryColor?: string;
    class?: string;
  }

  let {
    max = 100,
    value = 0,
    min = 0,
    gaugePrimaryColor = 'hsl(var(--primary))',
    gaugeSecondaryColor = 'hsl(var(--muted))',
    class: className = ''
  }: Props = $props();

  const circumference = 2 * Math.PI * 45;
  const percentPx = circumference / 100;
  let currentPercent = $derived(((value - min) / (max - min)) * 100);
</script>

<div
  class={cn('relative size-24 text-2xl font-semibold', className)}
  style:--circle-size="100px"
  style:--circumference={circumference}
  style:--percent-to-px="{percentPx}px"
  style:--gap-percent="5"
  style:--offset-factor="0"
  style:--transition-length="0.3s"
  style:--transition-step="200ms"
  style:--delay="0s"
  style:--percent-to-deg="3.6deg"
  style="transform: translateZ(0);"
>
  <svg fill="none" class="size-full" stroke-width="2" viewBox="0 0 100 100">
    {#if currentPercent <= 90 && currentPercent >= 0}
      <circle
        cx="50"
        cy="50"
        r="45"
        stroke-width="10"
        stroke-dashoffset="0"
        stroke-linecap="round"
        stroke-linejoin="round"
        class="opacity-100"
        style="
          stroke:{gaugeSecondaryColor};
          stroke-dasharray: calc(var(--stroke-percent) * var(--percent-to-px)) var(--circumference);
          transform: rotate(calc(1turn - 90deg - (var(--gap-percent) * var(--percent-to-deg) * var(--offset-factor-secondary)))) scaleY(-1);
          transition: all var(--transition-length) ease var(--delay);
          transform-origin:calc(var(--circle-size) / 2) calc(var(--circle-size) / 2);
        "
        style:--stroke-percent={90 - currentPercent}
        style:--offset-factor-secondary="calc(1 - var(--offset-factor))"
      />
    {/if}
    <circle
      cx="50"
      cy="50"
      r="45"
      stroke-width="10"
      stroke-dashoffset="0"
      stroke-linecap="round"
      stroke-linejoin="round"
      class="opacity-100"
      style="
        stroke:{gaugePrimaryColor};
        stroke-dasharray:calc(var(--stroke-percent) * var(--percent-to-px)) var(--circumference);
        transition:var(--transition-length) ease var(--delay),stroke var(--transition-length) ease var(--delay);
        transition-property: stroke-dasharray,transform;
        transform:rotate(calc(-90deg + var(--gap-percent) * var(--offset-factor) * var(--percent-to-deg)));
        transform-origin:calc(var(--circle-size) / 2) calc(var(--circle-size) / 2);
      "
      style:--stroke-percent={currentPercent}
    />
  </svg>
  <span
    class="absolute inset-0 m-auto size-fit flex flex-col items-center justify-center"
  >
    <slot>
      {currentPercent.toFixed(0)}
    </slot>
  </span>
</div>
