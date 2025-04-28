#!/usr/bin/env python
"""
Run mesh_segmentation_pipeline.py on every mesh under a split folder
-------------------------------------------------------------------
Example
-------
python batch_mesh_segmentation.py \
    --split-dir ../assets/CustomDataset_Completed/000-000 \
    --config    ../configs/mesh_segmentation.yaml \
    --output    ../outputs/mesh_segmentation_output \
    --clear-dir \
    --max-workers 4
"""
from __future__ import annotations
import argparse, subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List

PIPELINE = Path(__file__).resolve().parent / "../src/ys/mesh_segmentation_pipeline.py"

def run_one(mesh_dir: Path, args: argparse.Namespace) -> int:
    mesh_id = mesh_dir.name
    cmd: List[str] = [
        sys.executable, str(PIPELINE),
        "--config",   args.config,
        "--mesh-id",  mesh_id,
        "--assets-dir", str(mesh_dir),          # <─ 포인트
        "--output-dir", args.output,
        "--prefixes", *args.prefixes,
        "--resolution", *map(str, args.resolution),
    ]
    if args.clear_dir:
        cmd.append("--clear-dir")
    if args.visualize:
        cmd.append("--visualize")

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode:
        print(f"❌ {mesh_id} failed\n{proc.stdout}\n{proc.stderr}")
    else:
        print(f"✅ {mesh_id} done")
    return proc.returncode

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--split-dir", required=True, help="e.g. 000-000 폴더 경로")
    p.add_argument("--config",    required=True)
    p.add_argument("--output",    required=True)
    p.add_argument("--prefixes",  nargs="+", default=["matte_", "segmented_"])
    p.add_argument("--resolution", type=int, nargs=2, default=[2048, 2048])
    p.add_argument("--clear-dir", action="store_true")
    p.add_argument("--visualize", action="store_true")
    p.add_argument("--max-workers", type=int, default=os.cpu_count())
    return p.parse_args()

def main() -> None:
    args = parse_args()
    split_path = Path(args.split_dir)
    mesh_dirs = [d for d in split_path.iterdir() if d.is_dir()]
    print(f"{len(mesh_dirs)} meshes found in {split_path}")

    # 병렬 실행 ─ ThreadPoolExecutor → I/O 비중이 큰 파이프라인에 무리 없도록
    with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futs = {ex.submit(run_one, mdir, args): mdir.name for mdir in mesh_dirs}
        for fut in as_completed(futs):
            fut.result()   # 예외 발생 시 여기서 print

if __name__ == "__main__":
    main()
