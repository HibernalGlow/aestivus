import {
  Image,
  Video,
  Music,
  FileText,
  Archive,
  FileCode,
} from "@lucide/svelte";

// 过滤器配置类型
export interface FilterConfig {
  // 文件类型快捷选择
  fileTypes: string[];
  // 大小范围
  sizeEnabled: boolean;
  sizeMin: string;
  sizeMax: string;
  // 日期范围
  dateEnabled: boolean;
  datePreset: string; // today, week, month, year, custom
  dateStart: string;
  dateEnd: string;
  // 名称匹配
  nameEnabled: boolean;
  namePattern: string;
  nameMode: "contains" | "starts" | "ends" | "regex";
  // 位置
  locationEnabled: boolean;
  inArchive: "any" | "yes" | "no";
  // 类型
  itemType: "any" | "file" | "dir";
  // 自定义扩展名（包含）
  customExts: string[];
  // 排除的扩展名
  excludeExts: string[];
  // 图片元数据
  imageMetaEnabled: boolean;
  widthMin: string;
  widthMax: string;
  heightMin: string;
  heightMax: string;
  resolutionPreset: string; // any, 1080p, 4k, social-cover, custom
  // 容器平均大小
  avgSizeEnabled: boolean;
  avgSizeFormat: "images" | "videos" | "custom";
  avgSizeCustomExts: string;
  avgSizeMin: string;
  avgSizeMax: string;
}

export const defaultConfig: FilterConfig = {
  fileTypes: [],
  sizeEnabled: false,
  sizeMin: "",
  sizeMax: "",
  dateEnabled: false,
  datePreset: "any",
  dateStart: "",
  dateEnd: "",
  nameEnabled: false,
  namePattern: "",
  nameMode: "contains",
  locationEnabled: false,
  inArchive: "any",
  itemType: "file",
  customExts: [],
  excludeExts: [],
  imageMetaEnabled: false,
  widthMin: "",
  widthMax: "",
  heightMin: "",
  heightMax: "",
  resolutionPreset: "any",
  avgSizeEnabled: false,
  avgSizeFormat: "images",
  avgSizeCustomExts: "",
  avgSizeMin: "",
  avgSizeMax: "",
};

export interface Preset {
  id: string;
  name: string;
  config: FilterConfig;
  isBuiltin?: boolean;
}

export const STORAGE_KEY = "findz-filter-presets";

export const BUILTIN_PRESETS: Preset[] = [
  {
    id: "all-files",
    name: "所有文件",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      itemType: "file",
    },
  },
  {
    id: "jxl-in-archive",
    name: "压缩包内JXL",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      customExts: ["jxl"],
      locationEnabled: true,
      inArchive: "yes",
      itemType: "file",
    },
  },
  {
    id: "archive-no-avif",
    name: "压缩包内(无AVIF/WEBP)",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      excludeExts: ["avif", "webp"],
      locationEnabled: true,
      inArchive: "yes",
      itemType: "file",
    },
  },
  {
    id: "height-630-archive",
    name: "压缩包内高度630",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      fileTypes: ["images"],
      locationEnabled: true,
      inArchive: "yes",
      itemType: "file",
      imageMetaEnabled: true,
      heightMin: "630",
      heightMax: "630",
    },
  },
  {
    id: "large-files",
    name: "大文件 (>100MB)",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      sizeEnabled: true,
      sizeMin: "100M",
      sizeMax: "",
      itemType: "file",
    },
  },
  {
    id: "recent-images",
    name: "本周图片",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      fileTypes: ["images"],
      dateEnabled: true,
      datePreset: "week",
      itemType: "file",
    },
  },
  {
    id: "nested-archives",
    name: "嵌套压缩包",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      fileTypes: ["archives"],
      locationEnabled: true,
      inArchive: "yes",
      itemType: "file",
    },
  },
  {
    id: "dirs-only",
    name: "仅目录",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      itemType: "dir",
    },
  },
  {
    id: "ad-images",
    name: "广告/宣传图",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      nameEnabled: true,
      nameMode: "regex",
      namePattern:
        "招募|credit|广告|宣传|招新|绅士快乐|粉丝群|無邪気|[Cc]redit[s]|ver\\.\\d+\\.\\d+|YZv\\.\\d+\\.\\d+|z{3,}",
      itemType: "file",
    },
  },
  {
    id: "social-cover",
    name: "封面图 (1200x630)",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      fileTypes: ["images"],
      imageMetaEnabled: true,
      resolutionPreset: "social-cover",
      sizeEnabled: true,
      sizeMax: "320K",
      itemType: "file",
    },
  },
  {
    id: "high-quality-archives",
    name: "高质量图片档 (平均 > 500K)",
    isBuiltin: true,
    config: {
      ...defaultConfig,
      avgSizeEnabled: true,
      avgSizeFormat: "images",
      avgSizeMin: "500K",
      itemType: "file",
      inArchive: "yes",
    },
  },
];

export const FILE_TYPE_PRESETS = [
  {
    id: "images",
    label: "图片",
    icon: Image,
    exts: [
      "jpg",
      "jpeg",
      "png",
      "gif",
      "webp",
      "bmp",
      "svg",
      "ico",
      "jxl",
      "avif",
    ],
  },
  {
    id: "videos",
    label: "视频",
    icon: Video,
    exts: ["mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v"],
  },
  {
    id: "audio",
    label: "音频",
    icon: Music,
    exts: ["mp3", "wav", "flac", "aac", "ogg", "m4a", "wma"],
  },
  {
    id: "docs",
    label: "文档",
    icon: FileText,
    exts: [
      "pdf",
      "doc",
      "docx",
      "xls",
      "xlsx",
      "ppt",
      "pptx",
      "txt",
      "md",
      "rtf",
    ],
  },
  {
    id: "archives",
    label: "压缩包",
    icon: Archive,
    exts: ["zip", "rar", "7z", "tar", "gz", "bz2", "xz"],
  },
  {
    id: "code",
    label: "代码",
    icon: FileCode,
    exts: [
      "py",
      "js",
      "ts",
      "java",
      "c",
      "cpp",
      "h",
      "go",
      "rs",
      "rb",
      "php",
      "html",
      "css",
      "json",
      "xml",
      "yaml",
      "yml",
    ],
  },
  { id: "jxl", label: "JXL", icon: Image, exts: ["jxl"] },
];

export const DATE_PRESETS = [
  { value: "any", label: "不限" },
  { value: "today", label: "今天" },
  { value: "week", label: "本周" },
  { value: "month", label: "本月" },
  { value: "year", label: "今年" },
  { value: "custom", label: "自定义" },
];

export const SIZE_PRESETS = [
  { label: "微小 (<10KB)", min: "", max: "10K" },
  { label: "小 (<1MB)", min: "", max: "1M" },
  { label: "中 (1-100MB)", min: "1M", max: "100M" },
  { label: "大 (100MB-1GB)", min: "100M", max: "1G" },
  { label: "超大 (>1GB)", min: "1G", max: "" },
];
