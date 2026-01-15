"""
Test progress callback chain
"""
import asyncio
import sys

sys.path.insert(0, r"d:\1VSCODE\Projects\aestivus\src-python")
sys.path.insert(0, r"d:\1VSCODE\Projects\PackU\AutoRepack\src")

async def test():
    from adapters.repacku_adapter import RepackuAdapter, RepackuInput
    from pathlib import Path
    import tempfile
    import json
    
    test_dir = Path(tempfile.mkdtemp())
    sub_dir = test_dir / "folder1"
    sub_dir.mkdir()
    (sub_dir / "a.txt").write_text("test")
    
    config = {
        "folder_tree": {
            "path": str(test_dir),
            "name": test_dir.name,
            "compress_mode": "skip",
            "total_files": 0,
            "children": [{
                "path": str(sub_dir),
                "name": "folder1",
                "compress_mode": "entire",
                "total_files": 1,
                "children": []
            }]
        },
        "config": {"target_file_types": []}
    }
    
    config_path = test_dir / "_config.json"
    config_path.write_text(json.dumps(config, ensure_ascii=False))
    
    progress_calls = []
    loop = asyncio.get_running_loop()
    
    async def async_progress(p, m):
        progress_calls.append((p, m))
        print(f"ASYNC_PROGRESS: {p}% - {m}")
    
    def sync_progress(p, m):
        print(f"SYNC_PROGRESS: {p}% - {m}")
        asyncio.run_coroutine_threadsafe(async_progress(p, m), loop)
    
    def on_log(m):
        print(f"LOG: {m}")
    
    adapter = RepackuAdapter()
    input_data = RepackuInput(
        action="compress",
        config_path=str(config_path),
        delete_after=False
    )
    
    print("Starting compress...")
    result = await adapter.execute(input_data, sync_progress, on_log)
    
    # Wait a bit for threadsafe callbacks
    await asyncio.sleep(0.5)
    
    print(f"\nResult: success={result.success}")
    print(f"Progress calls: {len(progress_calls)}")
    for p, m in progress_calls:
        print(f"  {p}% - {m}")
    
    import shutil
    shutil.rmtree(test_dir, ignore_errors=True)
    
    return len(progress_calls)

if __name__ == "__main__":
    count = asyncio.run(test())
    print(f"\nTotal progress callbacks: {count}")
    if count >= 3:
        print("PASS")
    else:
        print("FAIL - expected at least 3 callbacks")
