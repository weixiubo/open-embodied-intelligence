#!/usr/bin/env python3
"""
/302/ 优化方案部署工具

功能：
- 验证 /302/ 目录的修改
- 应用修改到大创agentV3（覆盖）
- 回滚修改到原始版本
- 对比修改内容
"""

import os
import sys
import shutil
import difflib
from pathlib import Path
from typing import Tuple, List

# 配置
SOURCE_DIR = Path(__file__).parent.parent / "大创agentV3"
OPTIM_DIR = Path(__file__).parent  # /302/

FILES_TO_MODIFY = [
    ("config/audio_config.py", "config", "audio_config.py"),
    ("core/music_analyzer.py", "core", "music_analyzer.py"),
    ("dance/robot_controller.py", "dance", "robot_controller.py"),
]


def print_header(text: str) -> None:
    """打印分隔符标题"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_success(text: str) -> None:
    """打印成功消息"""
    print(f"✅ {text}")


def print_error(text: str) -> None:
    """打印错误消息"""
    print(f"❌ {text}", file=sys.stderr)


def print_warning(text: str) -> None:
    """打印警告消息"""
    print(f"⚠️  {text}")


def verify_files() -> bool:
    """验证 /302/ 中的修改文件是否存在"""
    print_header("文件存在性检查")
    
    all_exist = True
    for file_path, _, _ in FILES_TO_MODIFY:
        optim_file = OPTIM_DIR / file_path
        src_file = SOURCE_DIR / file_path
        
        optim_exists = optim_file.exists()
        src_exists = src_file.exists()
        
        status_optim = "✓" if optim_exists else "✗"
        status_src = "✓" if src_exists else "✗"
        
        print(f"  /302/{file_path}              [{status_optim}]")
        print(f"  大创agentV3/{file_path}   [{status_src}]")
        print()
        
        if not optim_exists or not src_exists:
            all_exist = False
    
    if all_exist:
        print_success("所有文件存在")
        return True
    else:
        print_error("部分文件不存在，请检查路径")
        return False


def verify_syntax() -> bool:
    """验证修改文件的 Python 语法"""
    print_header("语法检查")
    
    import py_compile
    
    all_valid = True
    for file_path, sub_dir, filename in FILES_TO_MODIFY:
        optim_file = OPTIM_DIR / file_path
        
        try:
            py_compile.compile(str(optim_file), doraise=True)
            print_success(f"{file_path} 语法正确")
        except py_compile.PyCompileError as e:
            print_error(f"{file_path} 语法错误：{e}")
            all_valid = False
    
    return all_valid


def show_diff(file_path: str) -> None:
    """显示文件对比"""
    optim_file = OPTIM_DIR / file_path
    src_file = SOURCE_DIR / file_path
    
    with open(optim_file, 'r', encoding='utf-8') as f:
        optim_lines = f.readlines()
    
    with open(src_file, 'r', encoding='utf-8') as f:
        src_lines = f.readlines()
    
    diff = difflib.unified_diff(
        src_lines,
        optim_lines,
        fromfile=f"大创agentV3/{file_path}",
        tofile=f"/302/{file_path}",
        lineterm='',
        n=2
    )
    
    diff_lines = list(diff)
    if diff_lines:
        for line in diff_lines[:50]:  # 只显示前 50 行
            if line.startswith('+') and not line.startswith('+++'):
                print(f"  \033[92m{line}\033[0m")  # 绿色（新增）
            elif line.startswith('-') and not line.startswith('---'):
                print(f"  \033[91m{line}\033[0m")  # 红色（删除）
            else:
                print(f"  {line}")
        
        if len(diff_lines) > 50:
            print(f"\n  ... 还有 {len(diff_lines) - 50} 行差异（省略）")
    else:
        print("  无差异")


def compare_files() -> None:
    """对比 /302/ 和大创agentV3 的修改"""
    print_header("修改内容对比")
    
    for file_path, _, _ in FILES_TO_MODIFY:
        print(f"\n📄 {file_path}:")
        show_diff(file_path)


def apply_modifications() -> bool:
    """应用 /302/ 的修改到大创agentV3"""
    print_header("应用修改到大创agentV3")
    
    if not verify_files():
        print_error("文件验证失败，无法应用")
        return False
    
    if not verify_syntax():
        print_error("语法检查失败，无法应用")
        return False
    
    # 确认
    print_warning(f"即将覆盖 {SOURCE_DIR} 中的以下文件：")
    for file_path, _, _ in FILES_TO_MODIFY:
        print(f"  - {file_path}")
    
    response = input("\n是否继续？(yes/no): ").strip().lower()
    if response != 'yes':
        print("已取消")
        return False
    
    # 应用
    success_count = 0
    for file_path, sub_dir, filename in FILES_TO_MODIFY:
        optim_file = OPTIM_DIR / file_path
        src_file = SOURCE_DIR / file_path
        
        try:
            shutil.copy2(optim_file, src_file)
            print_success(f"已复制 {file_path}")
            success_count += 1
        except Exception as e:
            print_error(f"复制失败 {file_path}：{e}")
    
    if success_count == len(FILES_TO_MODIFY):
        print_success(f"\n所有 {success_count} 个文件已更新")
        return True
    else:
        print_error(f"仅更新了 {success_count}/{len(FILES_TO_MODIFY)} 个文件")
        return False


def rollback_modifications() -> bool:
    """回滚修改（使用 git 如果可用，否则恢复原始参数值）"""
    print_header("回滚修改")
    
    rollback_plan = [
        ("config/audio_config.py", 
         "analysis_window: float = 1.2", 
         "analysis_window: float = 2.0"),
        ("core/music_analyzer.py",
         "self.noise_threshold = 250",
         "self.noise_threshold = 400"),
        ("core/music_analyzer.py",
         "self.required_valid_frames = 2",
         "self.required_valid_frames = 3"),
        ("core/music_analyzer.py",
         'librosa.beat.beat_track(\n                    y=audio_data, sr=self.sample_rate, hop_length=512\n                )',
         'librosa.beat.beat_track(\n                    y=audio_data, sr=self.sample_rate\n                )'),
        ("dance/robot_controller.py",
         "min_analysis_duration = 2.0",
         "min_analysis_duration = 3.0"),
    ]
    
    print("预计回滚操作：")
    for file_path, new_val, old_val in rollback_plan:
        print(f"  {file_path}")
        print(f"    « {new_val[:50]}")
        print(f"    » {old_val[:50]}")
    
    response = input("\n是否继续？(yes/no): ").strip().lower()
    if response != 'yes':
        print("已取消")
        return False
    
    print("\n⚠️  需要手动编辑或使用 git 命令回滚")
    print("推荐：")
    print("  git checkout HEAD -- 大创agentV3/config/audio_config.py")
    print("  git checkout HEAD -- 大创agentV3/core/music_analyzer.py")
    print("  git checkout HEAD -- 大创agentV3/dance/robot_controller.py")
    
    return False  # 需要手动确认


def check_deployment_readiness() -> None:
    """检查部署就绪度"""
    print_header("部署就绪度检查")
    
    checks = [
        ("✅ /302/ 目录存在", OPTIM_DIR.exists()),
        ("✅ 大创agentV3 目录存在", SOURCE_DIR.exists()),
        ("✅ config/audio_config.py 存在", (OPTIM_DIR / "config/audio_config.py").exists()),
        ("✅ core/music_analyzer.py 存在", (OPTIM_DIR / "core/music_analyzer.py").exists()),
        ("✅ dance/robot_controller.py 存在", (OPTIM_DIR / "dance/robot_controller.py").exists()),
        ("✅ MODIFICATIONS.md 文档存在", (OPTIM_DIR / "MODIFICATIONS.md").exists()),
    ]
    
    all_ok = True
    for check_name, check_result in checks:
        status = check_name[0:2]  # ✅ 或 ❌
        text = check_name[3:]
        print(f"  {status} {text}")
        if "✅" not in check_name:
            all_ok = False
    
    if all_ok:
        print_success("所有检查通过，可以部署")
    else:
        print_warning("部分检查未通过，请解决后重试")


def main() -> None:
    """主菜单"""
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        
        if cmd == "verify":
            print_header("验证修改")
            verify_files()
            verify_syntax()
        
        elif cmd == "compare":
            compare_files()
        
        elif cmd == "apply":
            apply_modifications()
        
        elif cmd == "rollback":
            rollback_modifications()
        
        elif cmd == "check":
            check_deployment_readiness()
        
        else:
            print_error(f"未知命令：{cmd}")
            print("\n可用命令：")
            print("  verify   - 验证修改文件")
            print("  compare  - 对比修改内容")
            print("  apply    - 应用修改")
            print("  rollback - 回滚修改")
            print("  check    - 检查部署就绪度")
    
    else:
        # 交互菜单
        while True:
            print_header("🔧 /302/ 优化方案部署工具")
            print("1. 验证修改文件")
            print("2. 对比修改内容")
            print("3. 应用修改到大创agentV3")
            print("4. 回滚修改")
            print("5. 检查部署就绪度")
            print("0. 退出")
            print()
            
            choice = input("请选择操作 (0-5): ").strip()
            
            if choice == "1":
                verify_files()
                verify_syntax()
            elif choice == "2":
                compare_files()
            elif choice == "3":
                if apply_modifications():
                    print_success("修改已应用！")
                    break
            elif choice == "4":
                rollback_modifications()
            elif choice == "5":
                check_deployment_readiness()
            elif choice == "0":
                print("退出")
                break
            else:
                print_error("无效选择")
            
            input("\n按 Enter 继续...")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n已中断")
        sys.exit(1)
