/**
 * 共享文件树工具函数
 * 包含树构建和智能展开算法
 * 用于 MvzNode, FindzNode 等多个节点
 */

export interface TreeNode {
  name: string;
  path: string;
  isFolder: boolean;
  isArchive?: boolean;
  children: TreeNode[];
  fileIndex?: number;
  archivePath?: string;
}

/**
 * 构建完整的文件树结构（包括外部路径）
 */
export function buildCompleteFileTree(files: string[]): TreeNode {
  const root: TreeNode = {
    name: 'root',
    path: '',
    isFolder: true,
    children: []
  };

  // 按压缩包分组
  const groupedFiles = new Map<string, string[]>();
  for (const file of files) {
    const parts = file.split('//');
    const archive = parts[0];
    const internal = parts[1] || '';
    if (!groupedFiles.has(archive)) {
      groupedFiles.set(archive, []);
    }
    groupedFiles.get(archive)!.push(internal);
  }

  // 为每个压缩包构建树
  for (const [archivePath, internalFiles] of groupedFiles.entries()) {
    // 解析压缩包的外部路径（支持 Windows 和 Unix 路径）
    const normalizedPath = archivePath.replace(/\\/g, '/');
    const archiveParts = normalizedPath.split('/').filter(p => p);
    
    let current = root;

    // 构建外部路径树（递归创建文件夹节点）
    for (let i = 0; i < archiveParts.length; i++) {
      const part = archiveParts[i];
      const isLastPart = i === archiveParts.length - 1;
      const fullPath = archiveParts.slice(0, i + 1).join('/');

      let child = current.children.find(c => c.name === part);
      if (!child) {
        child = {
          name: part,
          path: fullPath,
          isFolder: !isLastPart,
          isArchive: isLastPart,
          children: [],
          archivePath: isLastPart ? archivePath : undefined
        };
        current.children.push(child);
      }
      current = child;
    }

    // 构建压缩包内部文件树（递归创建文件夹节点）
    for (const internal of internalFiles) {
      if (!internal) continue;
      
      const parts = internal.split('/').filter(p => p);
      let innerCurrent = current;

      for (let i = 0; i < parts.length; i++) {
        const part = parts[i];
        const isLastPart = i === parts.length - 1;
        const fullPath = `${archivePath}//${parts.slice(0, i + 1).join('/')}`;

        let child = innerCurrent.children.find(c => c.name === part);
        if (!child) {
          child = {
            name: part,
            path: fullPath,
            isFolder: !isLastPart,
            children: [],
            fileIndex: isLastPart ? files.findIndex(f => f === `${archivePath}//${internal}`) : undefined
          };
          innerCurrent.children.push(child);
        }
        innerCurrent = child;
      }
    }
  }

  return root;
}

/**
 * 智能展开算法
 * 目标：在视野内展示最重要的压缩包和文件
 * 
 * 策略：
 * 1. 自动展开所有包含文件的压缩包（让用户看到压缩包内容）
 * 2. 自动展开只有单个子节点的中间文件夹（减少层级）
 * 3. 折叠有多个子节点的文件夹（避免信息过载）
 * 4. 优先展开文件数量较少的压缩包（更容易浏览）
 */
export function calculateSmartExpansion(root: TreeNode): Set<string> {
  const expanded = new Set<string>();
  
  // 收集所有压缩包节点及其统计信息
  interface ArchiveInfo {
    node: TreeNode;
    fileCount: number;
    depth: number;
  }
  
  const archives: ArchiveInfo[] = [];
  
  function collectArchives(node: TreeNode, depth: number = 0) {
    if (node.isArchive) {
      const fileCount = countFiles(node);
      archives.push({ node, fileCount, depth });
    }
    
    for (const child of node.children) {
      collectArchives(child, depth + 1);
    }
  }
  
  collectArchives(root);
  
  // 按文件数量排序（文件少的优先展开）
  archives.sort((a, b) => a.fileCount - b.fileCount);
  
  // 展开策略
  const MAX_VISIBLE_FILES = 50; // 最多展示50个文件
  let visibleFileCount = 0;
  
  for (const archiveInfo of archives) {
    const { node, fileCount } = archiveInfo;
    
    // 如果展开这个压缩包不会超过可见文件限制，则展开
    if (visibleFileCount + fileCount <= MAX_VISIBLE_FILES) {
      // 展开压缩包本身
      expanded.add(node.path);
      
      // 展开压缩包到根的路径（确保压缩包可见）
      expandPathToRoot(node.path, expanded);
      
      // 智能展开压缩包内部结构
      expandArchiveContent(node, expanded);
      
      visibleFileCount += fileCount;
    } else {
      // 如果已经达到限制，只展开到压缩包层级（不展开内部）
      expandPathToRoot(node.path, expanded, true);
    }
  }
  
  return expanded;
}

/**
 * 计算节点下的文件总数
 */
function countFiles(node: TreeNode): number {
  if (!node.isFolder && !node.isArchive) {
    return 1;
  }
  
  let count = 0;
  for (const child of node.children) {
    count += countFiles(child);
  }
  return count;
}

/**
 * 展开从节点到根的路径
 */
function expandPathToRoot(path: string, expanded: Set<string>, excludeSelf: boolean = false) {
  const parts = path.split('//')[0].replace(/\\/g, '/').split('/').filter(p => p);
  
  for (let i = 1; i <= parts.length; i++) {
    const parentPath = parts.slice(0, i).join('/');
    if (!excludeSelf || i < parts.length) {
      expanded.add(parentPath);
    }
  }
}

/**
 * 智能展开压缩包内部内容
 * 策略：
 * - 自动展开只有单个子节点的文件夹（减少层级）
 * - 折叠有多个子节点的文件夹（避免混乱）
 */
function expandArchiveContent(archiveNode: TreeNode, expanded: Set<string>) {
  function shouldAutoExpand(node: TreeNode): boolean {
    // 如果只有一个子节点，自动展开
    if (node.children.length === 1) {
      return true;
    }
    
    // 如果所有子节点都是文件（没有文件夹），也展开
    if (node.children.length > 0 && node.children.every(c => !c.isFolder)) {
      return true;
    }
    
    return false;
  }
  
  function expandNode(node: TreeNode) {
    if (!node.isFolder && !node.isArchive) {
      return;
    }
    
    if (shouldAutoExpand(node)) {
      expanded.add(node.path);
      
      // 递归展开子节点
      for (const child of node.children) {
        expandNode(child);
      }
    }
  }
  
  // 从压缩包的子节点开始展开
  for (const child of archiveNode.children) {
    expandNode(child);
  }
}

/**
 * 获取树的统计信息
 */
export function getTreeStats(root: TreeNode): {
  totalFiles: number;
  totalFolders: number;
  totalArchives: number;
  maxDepth: number;
} {
  let totalFiles = 0;
  let totalFolders = 0;
  let totalArchives = 0;
  let maxDepth = 0;
  
  function traverse(node: TreeNode, depth: number = 0) {
    maxDepth = Math.max(maxDepth, depth);
    
    if (node.isArchive) {
      totalArchives++;
    } else if (node.isFolder) {
      totalFolders++;
    } else {
      totalFiles++;
    }
    
    for (const child of node.children) {
      traverse(child, depth + 1);
    }
  }
  
  traverse(root);
  
  return { totalFiles, totalFolders, totalArchives, maxDepth };
}
