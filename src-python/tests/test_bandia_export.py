"""
测试 bandia 路径导出功能
验证解压后的路径映射是否正确
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os


class TestBandiaOutputPath:
    """测试 bandia 输出路径计算"""
    
    def test_get_output_path_single_root_dir(self, tmp_path):
        """测试单个根目录的压缩包 - 应该输出到该目录"""
        from bandia.main import _get_output_path, find_bz_executable
        
        bz_path = find_bz_executable()
        if not bz_path:
            pytest.skip("未找到 Bandizip (bz.exe)")
        
        # 创建测试压缩包（需要实际的压缩包文件）
        # 这里使用 mock 来模拟 bz.exe l 的输出
        mock_output = """
Date      Time    Attr     Size    Compressed  Name
-------  ------  ------  -------  ----------  ------------------------
2024-01-01 12:00           0              0  my_folder/
2024-01-01 12:00       1000            500  my_folder/file1.txt
2024-01-01 12:00       2000            800  my_folder/file2.txt
"""
        
        archive = tmp_path / "test.zip"
        archive.touch()  # 创建空文件用于测试
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )
            
            output_path = _get_output_path(archive, bz_path)
            
            # 单个根目录，应该输出到 my_folder
            assert output_path == tmp_path / "my_folder"
    
    def test_get_output_path_multiple_roots(self, tmp_path):
        """测试多个根项的压缩包 - 应该创建与压缩包同名的目录"""
        from bandia.main import _get_output_path, find_bz_executable
        
        bz_path = find_bz_executable()
        if not bz_path:
            pytest.skip("未找到 Bandizip (bz.exe)")
        
        mock_output = """
Date      Time    Attr     Size    Compressed  Name
-------  ------  ------  -------  ----------  ------------------------
2024-01-01 12:00       1000            500  file1.txt
2024-01-01 12:00       2000            800  file2.txt
2024-01-01 12:00           0              0  some_folder/
"""
        
        archive = tmp_path / "my_archive.zip"
        archive.touch()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout=mock_output,
                stderr=""
            )
            
            output_path = _get_output_path(archive, bz_path)
            
            # 多个根项，应该创建与压缩包同名的目录
            assert output_path == tmp_path / "my_archive"


class TestBandiaAdapter:
    """测试 bandia 适配器的路径映射输出"""
    
    def test_path_mappings_in_output(self):
        """测试适配器返回的 path_mappings 字段"""
        from adapters.bandia_adapter import BandiaOutput
        
        # 验证 BandiaOutput 有 path_mappings 字段
        output = BandiaOutput(
            success=True,
            message="测试",
            path_mappings=[
                {"archive_path": "/path/to/archive.zip", "extracted_path": "/path/to/output"}
            ]
        )
        
        assert len(output.path_mappings) == 1
        assert output.path_mappings[0]["archive_path"] == "/path/to/archive.zip"
        assert output.path_mappings[0]["extracted_path"] == "/path/to/output"
    
    def test_extract_result_has_output_path(self):
        """测试 ExtractResult 数据类包含 output_path 字段"""
        from bandia.main import ExtractResult
        from pathlib import Path
        
        result = ExtractResult(
            path=Path("/test/archive.zip"),
            success=True,
            duration=1.5,
            file_size=1000,
            error="",
            output_path=Path("/test/output_folder")
        )
        
        assert result.output_path == Path("/test/output_folder")


class TestIntegration:
    """集成测试 - 需要实际的压缩包"""
    
    @pytest.mark.skipif(
        not Path("C:/Program Files/Bandizip/bz.exe").exists() and 
        not Path("C:/Program Files (x86)/Bandizip/bz.exe").exists(),
        reason="Bandizip 未安装"
    )
    def test_real_extraction_with_path_mapping(self, tmp_path):
        """使用真实压缩包测试路径映射"""
        import zipfile
        from bandia.main import extract_single, find_bz_executable
        
        bz_path = find_bz_executable()
        if not bz_path:
            pytest.skip("未找到 Bandizip")
        
        # 创建一个测试压缩包
        archive_path = tmp_path / "test_archive.zip"
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "file1.txt").write_text("Hello")
        (content_dir / "file2.txt").write_text("World")
        
        with zipfile.ZipFile(archive_path, 'w') as zf:
            zf.write(content_dir / "file1.txt", "test_folder/file1.txt")
            zf.write(content_dir / "file2.txt", "test_folder/file2.txt")
        
        # 执行解压
        result = extract_single(archive_path, bz_path, delete=False, use_trash=False)
        
        assert result.success
        assert result.output_path is not None
        # 单个根目录应该输出到 test_folder
        assert result.output_path.name == "test_folder"
        assert result.output_path.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
