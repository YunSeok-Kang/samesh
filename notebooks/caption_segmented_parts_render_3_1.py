import subprocess
from pathlib import Path

def run_blender(mesh_dir: str, output_dir: str,
                blender_path: str = "./../../DiffuRank/blender-3.4.1-linux-x64/blender",
                script_relpath: str = "../src/ys/blender_render_script_type1.py"):
    base_dir = Path.cwd()

    # Blender 실행파일 절대경로
    blender_exec = Path(blender_path).resolve()
    # 스크립트 절대경로
    script_path = (base_dir / script_relpath).resolve()

    if not script_path.exists():
        raise FileNotFoundError(f"스크립트를 찾을 수 없습니다: {script_path}")

    # mesh_dir, output_dir 절대경로로 변환
    mesh_abs = Path(mesh_dir).resolve()
    out_abs  = Path(output_dir).resolve()
    if not mesh_abs.exists():
        raise FileNotFoundError(f"메쉬 파일을 찾을 수 없습니다: {mesh_abs}")
    
    print(mesh_abs)
    print(out_abs)
    
    # 출력 디렉토리는 미리 만들어 두는 편이 안전
    out_abs.mkdir(parents=True, exist_ok=True)

    cmd = [
        str(blender_exec),
        "-b",
        "-P", str(script_path),
        "--",
        "--mesh_dir", str(mesh_abs),
        "--output_dir", str(out_abs)
    ]

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            cwd=base_dir
        )
        print("=== Blender stdout ===")
        print(result.stdout)
        print("=== Blender stderr ===")
        print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Blender 실행에 실패했습니다 (return code: {e.returncode})")
        print("stdout:", e.stdout)
        print("stderr:", e.stderr)
        raise

if __name__ == "__main__":
    run_blender(
        mesh_dir="../outputs/mesh_segmentation_output/CustomDataset/000-001/000234d39e684deb80b7b8d028681dc1/000234d39e684deb80b7b8d028681dc1_label_132.glb",
        output_dir="../outputs/mesh_segmentation_output/CustomDataset/000-001/000234d39e684deb80b7b8d028681dc1/renders/label_132"
    )