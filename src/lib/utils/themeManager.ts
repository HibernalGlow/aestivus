/**
 * Aestivus - 主题管理工具
 * 用于从 tweakcn.com 导入和应用主题 (从 neoview-tauri 移植)
 */

export interface TweakcnTheme {
    name: string;
    cssVars: {
        light: Record<string, string>;
        dark: Record<string, string>;
        theme?: Record<string, string>;
    };
}

/**
 * 从 tweakcn JSON 生成 CSS 变量
 */
export function generateCSSFromTheme(theme: TweakcnTheme): string {
    const { light, dark, theme: themeVars } = theme.cssVars;

    // 生成 :root 变量
    let css = ':root {\n';
    if (themeVars?.radius) {
        css += `\t--radius: ${themeVars.radius};\n`;
    }
    for (const [key, value] of Object.entries(light)) {
        css += `\t--${key}: ${value};\n`;
    }
    css += '}\n\n';

    // 生成 .dark 变量
    css += '.dark {\n';
    for (const [key, value] of Object.entries(dark)) {
        css += `\t--${key}: ${value};\n`;
    }
    css += '}\n';

    return css;
}

/**
 * 应用主题到 DOM（运行时）
 */
export function applyThemeToDOM(theme: TweakcnTheme, isDark: boolean) {
    if (typeof document === 'undefined') return;
    
    const root = document.documentElement;
    const colors = isDark ? theme.cssVars.dark : theme.cssVars.light;
    
    // 应用 radius
    if (theme.cssVars.theme?.radius) {
        root.style.setProperty('--radius', theme.cssVars.theme.radius);
    }
    
    // 应用颜色变量
    for (const [key, value] of Object.entries(colors)) {
        root.style.setProperty(`--${key}`, value);
    }
    
    console.log('✅ 主题已应用:', theme.name);
}

/**
 * 保存主题到 localStorage
 */
export function saveTheme(theme: TweakcnTheme) {
    if (typeof localStorage === 'undefined') return;
    try {
        const customThemes = JSON.parse(localStorage.getItem('custom-themes') || '[]');
        const filtered = customThemes.filter((t: TweakcnTheme) => t.name !== theme.name);
        filtered.push(theme);
        localStorage.setItem('custom-themes', JSON.stringify(filtered));
        console.log('✅ 主题已保存:', theme.name);
    } catch (error) {
        console.error('❌ 保存主题失败:', error);
    }
}

/**
 * 从 URL 获取主题
 */
export async function fetchThemeFromURL(url: string): Promise<TweakcnTheme> {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const theme = await response.json();
        return theme;
    } catch (error) {
        console.error('❌ 获取主题失败:', error);
        throw error;
    }
}

/**
 * 预设主题列表
 */
export const PRESET_THEMES = [
    {
        name: 'Amethyst Haze',
        url: 'https://tweakcn.com/r/themes/amethyst-haze.json',
        description: '优雅的紫色调主题'
    },
    {
        name: 'Ocean Breeze',
        url: 'https://tweakcn.com/r/themes/ocean-breeze.json',
        description: '清新的海洋蓝主题'
    },
    {
        name: 'Forest Mist',
        url: 'https://tweakcn.com/r/themes/forest-mist.json',
        description: '自然的森林绿主题'
    },
    {
        name: 'Sunset Glow',
        url: 'https://tweakcn.com/r/themes/sunset-glow.json',
        description: '温暖的日落橙主题'
    }
];
