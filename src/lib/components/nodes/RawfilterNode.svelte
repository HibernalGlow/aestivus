<script lang="ts">
  import BaseNode from './BaseNode.svelte';
  import { Checkbox } from '$lib/components/ui/checkbox';
  import { Label } from '$lib/components/ui/label';
  import { api } from '$lib/services/api';
  
  // Props from SvelteFlow
  export let id: string;
  export let data: {
    config: {
      path: string;
      name_only_mode: boolean;
      create_shortcuts: boolean;
      trash_only: boolean;
    };
    status: 'idle' | 'running' | 'completed' | 'error';
    hasInputConnection: boolean;
    logs: string[];
  };
  
  // 执行节点
  async function handleExecute() {
    data.status = 'running';
    data.logs = [...data.logs, `开始执行 rawfilter...`];
    
    try {
      const result = await api.executeNode('rawfilter', {
        path: data.config.path,
        name_only_mode: data.config.name_only_mode,
        create_shortcuts: data.config.create_shortcuts,
        trash_only: data.config.trash_only
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
  icon="🔍"
  displayName="相似文件过滤"
  bind:status={data.status}
  bind:hasInputConnection={data.hasInputConnection}
  bind:path={data.config.path}
  bind:logs={data.logs}
  onExecute={handleExecute}
>
  <div slot="config" class="space-y-2">
    <!-- 仅名称模式 -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="name-only-{id}" 
        bind:checked={data.config.name_only_mode}
        disabled={data.status === 'running'}
      />
      <Label for="name-only-{id}" class="text-xs cursor-pointer">
        仅名称模式（跳过内部分析）
      </Label>
    </div>
    
    <!-- 创建快捷方式 -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="shortcuts-{id}" 
        bind:checked={data.config.create_shortcuts}
        disabled={data.status === 'running'}
      />
      <Label for="shortcuts-{id}" class="text-xs cursor-pointer">
        创建快捷方式而非移动
      </Label>
    </div>
    
    <!-- 仅移动到 trash -->
    <div class="flex items-center gap-2">
      <Checkbox 
        id="trash-only-{id}" 
        bind:checked={data.config.trash_only}
        disabled={data.status === 'running'}
      />
      <Label for="trash-only-{id}" class="text-xs cursor-pointer">
        仅移动到 trash
      </Label>
    </div>
  </div>
</BaseNode>
