import { type FilterConfig, FILE_TYPE_PRESETS } from "./FilterTypes";

/**
 * 根据配置生成 SQL 查询语句
 */
export function generateSql(config: FilterConfig): string {
  const conditions: string[] = [];

  // 文件类型（包含）
  const allExts: string[] = [];
  for (const typeId of config.fileTypes) {
    const preset = FILE_TYPE_PRESETS.find((p) => p.id === typeId);
    if (preset) allExts.push(...preset.exts);
  }
  allExts.push(...config.customExts);

  if (allExts.length > 0) {
    const extList = allExts.map((e) => `"${e}"`).join(", ");
    conditions.push(`ext IN (${extList})`);
  }

  // 文件类型（排除）
  if (config.excludeExts.length > 0) {
    const excludeList = config.excludeExts.map((e) => `"${e}"`).join(", ");
    conditions.push(`ext NOT IN (${excludeList})`);
  }

  // 大小
  if (config.sizeEnabled) {
    if (config.sizeMin && config.sizeMax) {
      conditions.push(`size BETWEEN ${config.sizeMin} AND ${config.sizeMax}`);
    } else if (config.sizeMin) {
      conditions.push(`size >= ${config.sizeMin}`);
    } else if (config.sizeMax) {
      conditions.push(`size <= ${config.sizeMax}`);
    }
  }

  // 日期
  if (config.dateEnabled && config.datePreset !== "any") {
    if (config.datePreset === "today") {
      conditions.push("date = today");
    } else if (config.datePreset === "week") {
      conditions.push("date >= mo");
    } else if (config.datePreset === "month") {
      // 获取本月第一天
      const now = new Date();
      const firstDay = new Date(now.getFullYear(), now.getMonth(), 1);
      conditions.push(`date >= "${firstDay.toISOString().split("T")[0]}"`);
    } else if (config.datePreset === "year") {
      const year = new Date().getFullYear();
      conditions.push(`date >= "${year}-01-01"`);
    } else if (config.datePreset === "custom") {
      if (config.dateStart && config.dateEnd) {
        conditions.push(
          `date BETWEEN "${config.dateStart}" AND "${config.dateEnd}"`,
        );
      } else if (config.dateStart) {
        conditions.push(`date >= "${config.dateStart}"`);
      } else if (config.dateEnd) {
        conditions.push(`date <= "${config.dateEnd}"`);
      }
    }
  }

  // 名称匹配
  if (config.nameEnabled && config.namePattern) {
    const pattern = config.namePattern;
    switch (config.nameMode) {
      case "contains":
        conditions.push(`name ILIKE "%${pattern}%"`);
        break;
      case "starts":
        conditions.push(`name ILIKE "${pattern}%"`);
        break;
      case "ends":
        conditions.push(`name ILIKE "%${pattern}"`);
        break;
      case "regex":
        conditions.push(`name RLIKE "${pattern}"`);
        break;
    }
  }

  // 位置（是否在压缩包内）
  if (config.locationEnabled && config.inArchive !== "any") {
    if (config.inArchive === "yes") {
      conditions.push('archive <> ""');
    } else {
      conditions.push('archive = ""');
    }
  }

  // 类型
  if (config.itemType !== "any") {
    conditions.push(`type = "${config.itemType}"`);
  }

  // 图片元数据
  if (config.imageMetaEnabled) {
    // 宽度
    if (config.widthMin && config.widthMax) {
      conditions.push(
        `width BETWEEN ${config.widthMin} AND ${config.widthMax}`,
      );
    } else if (config.widthMin) {
      conditions.push(`width >= ${config.widthMin}`);
    } else if (config.widthMax) {
      conditions.push(`width <= ${config.widthMax}`);
    }

    // 高度
    if (config.heightMin && config.heightMax) {
      conditions.push(
        `height BETWEEN ${config.heightMin} AND ${config.heightMax}`,
      );
    } else if (config.heightMin) {
      conditions.push(`height >= ${config.heightMin}`);
    } else if (config.heightMax) {
      conditions.push(`height <= ${config.heightMax}`);
    }

    // 分辨率预设
    if (config.resolutionPreset && config.resolutionPreset !== "any") {
      const presets: Record<string, string> = {
        "1080p": 'resolution = "1920x1080"',
        "4k": 'resolution = "3840x2160"',
        "8k": 'resolution = "7680x4320"',
        "social-cover": 'resolution IN ("1200x630", "630x1200")',
      };
      if (presets[config.resolutionPreset]) {
        conditions.push(presets[config.resolutionPreset]);
      }
    }
  }

  // 容器平均大小
  if (config.avgSizeEnabled) {
    let field = "avg_img_size";
    if (config.avgSizeFormat === "videos") {
      field = "avg_vid_size";
    } else if (config.avgSizeFormat === "custom" && config.avgSizeCustomExts) {
      const exts = config.avgSizeCustomExts
        .split(/[,，\s]+/)
        .map((e) => e.trim().replace(/^\./, ""))
        .filter((e) => e);
      if (exts.length > 0) {
        field = `avg_size_${exts.join("_")}`;
      }
    }

    if (config.avgSizeMin && config.avgSizeMax) {
      conditions.push(
        `${field} BETWEEN ${config.avgSizeMin} AND ${config.avgSizeMax}`,
      );
    } else if (config.avgSizeMin) {
      conditions.push(`${field} >= ${config.avgSizeMin}`);
    } else if (config.avgSizeMax) {
      conditions.push(`${field} <= ${config.avgSizeMax}`);
    }
  }

  // 重新排序条件以优化性能
  const cheapConditions: string[] = [];
  const expensiveConditions: string[] = [];

  for (const cond of conditions) {
    if (
      cond.includes("width") ||
      cond.includes("height") ||
      cond.includes("resolution") ||
      cond.includes("megapixels") ||
      cond.includes("aspect") ||
      cond.includes("RLIKE")
    ) {
      expensiveConditions.push(cond);
    } else {
      cheapConditions.push(cond);
    }
  }

  const finalConditions = [...cheapConditions, ...expensiveConditions];
  return finalConditions.length > 0 ? finalConditions.join(" AND ") : "1";
}

/**
 * 根据配置生成 JSON 结构化的查询配置
 */
export function generateJsonConfig(config: FilterConfig): object {
  const conditions: object[] = [];

  // 文件类型（包含）
  const allExts: string[] = [];
  for (const typeId of config.fileTypes) {
    const preset = FILE_TYPE_PRESETS.find((p) => p.id === typeId);
    if (preset) allExts.push(...preset.exts);
  }
  allExts.push(...config.customExts);

  if (allExts.length > 0) {
    conditions.push({ field: "ext", op: "in", value: allExts });
  }

  // 文件类型（排除）
  if (config.excludeExts.length > 0) {
    conditions.push({
      field: "ext",
      op: "not_in",
      value: config.excludeExts,
    });
  }

  // 大小
  if (config.sizeEnabled) {
    if (config.sizeMin && config.sizeMax) {
      conditions.push({
        field: "size",
        op: "between",
        value: [config.sizeMin, config.sizeMax],
      });
    } else if (config.sizeMin) {
      conditions.push({ field: "size", op: ">=", value: config.sizeMin });
    } else if (config.sizeMax) {
      conditions.push({ field: "size", op: "<=", value: config.sizeMax });
    }
  }

  // 日期
  if (config.dateEnabled && config.datePreset !== "any") {
    if (config.datePreset === "today") {
      conditions.push({ field: "date", op: "=", value: "today" });
    } else if (config.datePreset === "week") {
      conditions.push({ field: "date", op: ">=", value: "mo" });
    } else if (config.datePreset === "custom") {
      if (config.dateStart && config.dateEnd) {
        conditions.push({
          field: "date",
          op: "between",
          value: [config.dateStart, config.dateEnd],
        });
      } else if (config.dateStart) {
        conditions.push({ field: "date", op: ">=", value: config.dateStart });
      } else if (config.dateEnd) {
        conditions.push({ field: "date", op: "<=", value: config.dateEnd });
      }
    }
  }

  // 名称
  if (config.nameEnabled && config.namePattern) {
    const opMap = {
      contains: "ilike",
      starts: "ilike",
      ends: "ilike",
      regex: "rlike",
    };
    const patternMap = {
      contains: `%${config.namePattern}%`,
      starts: `${config.namePattern}%`,
      ends: `%${config.namePattern}`,
      regex: config.namePattern,
    };
    conditions.push({
      field: "name",
      op: opMap[config.nameMode],
      value: patternMap[config.nameMode],
    });
  }

  // 位置
  if (config.locationEnabled && config.inArchive !== "any") {
    conditions.push({
      field: "archive",
      op: config.inArchive === "yes" ? "!=" : "=",
      value: "",
    });
  }

  // 类型
  if (config.itemType !== "any") {
    conditions.push({ field: "type", op: "=", value: config.itemType });
  }

  return { op: "and", conditions };
}
