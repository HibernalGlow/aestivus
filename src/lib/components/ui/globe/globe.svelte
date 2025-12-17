<script lang="ts">
	/**
	 * Globe 组件 - 基于 cobe 的 3D 地球动画
	 * 参考: https://animation-svelte.vercel.app/magic/globe
	 * 支持与主题同步
	 */
	import { onMount, onDestroy } from 'svelte';
	import createGlobe from 'cobe';

	interface Props {
		class?: string;
		width?: number;
		height?: number;
	}

	let { class: className = '', width = 400, height = 400 }: Props = $props();

	let canvasRef: HTMLCanvasElement;
	let phi = 0;
	let globe: ReturnType<typeof createGlobe> | null = null;

	/**
	 * 从 CSS 变量解析 HSL 颜色并转换为 RGB [0-1] 数组
	 */
	function parseHSLToRGB(cssVar: string, fallback: [number, number, number]): [number, number, number] {
		if (typeof document === 'undefined') return fallback;
		
		const value = getComputedStyle(document.documentElement).getPropertyValue(cssVar).trim();
		if (!value) return fallback;

		// 解析 "h s% l%" 格式
		const parts = value.split(/\s+/);
		if (parts.length < 3) return fallback;

		const h = parseFloat(parts[0]) / 360;
		const s = parseFloat(parts[1]) / 100;
		const l = parseFloat(parts[2]) / 100;

		// HSL to RGB 转换
		const hue2rgb = (p: number, q: number, t: number) => {
			if (t < 0) t += 1;
			if (t > 1) t -= 1;
			if (t < 1 / 6) return p + (q - p) * 6 * t;
			if (t < 1 / 2) return q;
			if (t < 2 / 3) return p + (q - p) * (2 / 3 - t) * 6;
			return p;
		};

		if (s === 0) {
			return [l, l, l];
		}

		const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
		const p = 2 * l - q;
		return [hue2rgb(p, q, h + 1 / 3), hue2rgb(p, q, h), hue2rgb(p, q, h - 1 / 3)];
	}

	function initGlobe() {
		if (globe) {
			globe.destroy();
		}

		// 从主题获取颜色
		const baseColor = parseHSLToRGB('--muted', [0.3, 0.3, 0.3]);
		const markerColor = parseHSLToRGB('--primary', [0.1, 0.8, 1]);
		const glowColor = parseHSLToRGB('--background', [0.1, 0.1, 0.1]);

		globe = createGlobe(canvasRef, {
			devicePixelRatio: 2,
			width: width * 2,
			height: height * 2,
			phi: 0,
			theta: 0.3,
			dark: 1,
			diffuse: 1.2,
			mapSamples: 16000,
			mapBrightness: 6,
			baseColor,
			markerColor,
			glowColor,
			markers: [
				{ location: [37.7595, -122.4367], size: 0.03 }, // San Francisco
				{ location: [40.7128, -74.006], size: 0.03 }, // New York
				{ location: [51.5074, -0.1278], size: 0.03 }, // London
				{ location: [35.6762, 139.6503], size: 0.03 }, // Tokyo
				{ location: [31.2304, 121.4737], size: 0.03 }, // Shanghai
				{ location: [39.9042, 116.4074], size: 0.03 } // Beijing
			],
			onRender: (state) => {
				state.phi = phi;
				phi += 0.005;
			}
		});
	}

	onMount(() => {
		initGlobe();

		// 监听主题变化（class 变化）
		const observer = new MutationObserver((mutations) => {
			for (const mutation of mutations) {
				if (mutation.attributeName === 'class' || mutation.attributeName === 'style') {
					// 主题变化时重新初始化
					initGlobe();
					break;
				}
			}
		});

		observer.observe(document.documentElement, {
			attributes: true,
			attributeFilter: ['class', 'style']
		});

		return () => observer.disconnect();
	});

	onDestroy(() => {
		if (globe) {
			globe.destroy();
		}
	});
</script>

<div class="flex items-center justify-center {className}">
	<canvas
		bind:this={canvasRef}
		style="width: {width}px; height: {height}px; aspect-ratio: 1;"
		class="opacity-90"
	></canvas>
</div>
