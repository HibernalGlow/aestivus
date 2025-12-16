"""
文件服务 API - 提供本地文件访问
用于在前端显示本地图片等资源
"""

from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
import mimetypes

router = APIRouter(tags=["files"])


@router.get("/file")
async def serve_file(path: str = Query(..., description="本地文件路径")):
    """
    提供本地文件访问
    
    用于前端显示本地图片、视频等资源
    例如: /v1/file?path=E:/SteamLibrary/.../preview.gif
    """
    file_path = Path(path)
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"文件不存在: {path}")
    
    if not file_path.is_file():
        raise HTTPException(status_code=400, detail=f"不是文件: {path}")
    
    # 获取 MIME 类型
    mime_type, _ = mimetypes.guess_type(str(file_path))
    if mime_type is None:
        mime_type = "application/octet-stream"
    
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        filename=file_path.name
    )


@router.get("/preview/{workshop_id}")
async def get_wallpaper_preview(
    workshop_id: str,
    workshop_path: str = Query(..., description="工坊根目录路径")
):
    """
    获取壁纸预览图
    
    根据 workshop_id 和工坊路径，自动查找预览图文件
    支持 gif, jpg, png 等格式
    """
    workshop_dir = Path(workshop_path)
    wallpaper_dir = workshop_dir / workshop_id
    
    if not wallpaper_dir.exists():
        raise HTTPException(status_code=404, detail=f"壁纸目录不存在: {workshop_id}")
    
    # 尝试查找预览图文件（按优先级）
    preview_names = ["preview.gif", "preview.jpg", "preview.png", "preview.webp"]
    
    for name in preview_names:
        preview_path = wallpaper_dir / name
        if preview_path.exists():
            mime_type, _ = mimetypes.guess_type(str(preview_path))
            return FileResponse(
                path=preview_path,
                media_type=mime_type or "image/gif"
            )
    
    # 如果没有找到预览图，返回 404
    raise HTTPException(status_code=404, detail=f"未找到预览图: {workshop_id}")
