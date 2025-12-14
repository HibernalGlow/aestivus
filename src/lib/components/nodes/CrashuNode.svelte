<script lang="ts">
  import BaseNode from './BaseNode.svelte';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import { Input } from '$lib/components/ui/input';
  import { api } from '$lib/services/api';
  
  // Props from SvelteFlow
  export let id: string;
  export let data: {
    config: {
      path: string;
      target_path: string;
      destination_path: string;
      similarity_threshold: number;
      auto_move: boolean;
    };
    status: 'idle' | 'running' | 'completed' | 'error';
    hasInputConnection: boolean;
    logs: string[];
  };
  
  // 执行节点
  async function handleExecute() {
    data.status = 'running';
    data.logs = [...data.logs, `开始执行 crashu...`];
    
    try {
      const result = await api.executeNode('crashu', {
        path: data.config.path,
        target_path: data.config.target_path,
        destination_path: data.config.destination_path,
        similarity_threshold: data.config.similarity_threshold,
        auto_move: data.config.auto_move
      });
      
      if (result.success) {
        data.status = 'completed';
        data.logs = [...data.logs, result.message];
      } else {
        data.status = 'error';
        data.logs = [...data.logs, `错误: ${result.message}`];
      }
    } catch (error) {
      data.status = 'error';
      data.logs = [...data.logs, `执行失败: ${error}`];
    }
  }
</script>

<BaseNode
  {id}
  icon="💥"
  displayName="相似文件夹检测"
  bind:status={data.status}
  bind:hasInputConnection={data.hasInputConnection}
  bind:path={data.config.path}
  bind:logs={data.logs}
  onExecute={handleExecute}
>
  <div slot="config" class="space-y-3">
    <!-- 相似度阈值 -->
    <div class="space-y-1">
      <Label class="text-xs">相似度阈值: {data.config.similarity_threshold}</Label>
      <Input 
        type="range" 
        min="0" 
        max="1" 
        step="0.1"
        bind:value={data.config.similarity_threshold}
        disabled={data.status === 'running'}
        class="h-2"
      />
    </div>
    
    <!-- 自动移动 -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="auto-move-{id}" 
        bind:checked={data.config.auto_move}
        disabled={data.status === 'running'}
      />
      <Label for="auto-move-{id}" class="text-xs cursor-pointer">
        自动执行移动操作
      </Label>
    </div>
  </div>
</BaseNode>
