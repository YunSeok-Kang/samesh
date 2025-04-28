#!/usr/bin/env python
"""
batch_mesh_segmentation.py
──────────────────────────
‣ 각 mesh 디렉터리에 대해 mesh_segmentation_pipeline.py 실행
‣ 실행 결과를 CSV(logs/batch_report.csv)로 저장
‣ 실패한 mesh 의 stdout/stderr 를 logs/errors/<mesh_id>.log 로 보존
"""

from __future__ import annotations
import argparse, subprocess, sys, os, csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple

PIPELINE = Path(__file__).resolve().parent / "../src/ys/mesh_segmentation_pipeline.py"

# ──────────────────────────────────────────────────────────────────────────────
# 1) 개별 mesh 실행 함수
# ──────────────────────────────────────────────────────────────────────────────
def run_one(mesh_dir: Path, args: argparse.Namespace, log_dir: Path) -> Tuple[str, bool, str]:
    mesh_id = mesh_dir.name
    cmd: List[str] = [
        sys.executable, str(PIPELINE),
        "--config",       args.config,
        "--mesh-id",      mesh_id,
        "--assets-dir",   str(mesh_dir),
        "--output-dir",   args.output,
        "--prefixes",    *args.prefixes,
        "--resolution",  *map(str, args.resolution),
    ]
    if args.clear_dir:
        cmd.append("--clear-dir")
    if args.visualize:
        cmd.append("--visualize")

    proc = subprocess.run(cmd, capture_output=True, text=True)

    # ---------- 성공 ----------
    if proc.returncode == 0:
        print(f"✅ {mesh_id} done")
        return mesh_id, True, ""

    # ---------- 실패 ----------
    err_file = log_dir / "errors" / f"{mesh_id}.log"
    err_file.parent.mkdir(parents=True, exist_ok=True)
    err_file.write_text(proc.stdout + "\n" + proc.stderr)
    print(f"❌ {mesh_id} failed  →  {err_file.relative_to(log_dir.parent)}")
    return mesh_id, False, str(err_file)

# ──────────────────────────────────────────────────────────────────────────────
# 2) 인자 파서
# ──────────────────────────────────────────────────────────────────────────────
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--split-dir",  required=True, help="e.g. 000-000 폴더 경로")
    p.add_argument("--config",     required=True)
    p.add_argument("--output",     required=True)
    p.add_argument("--prefixes",   nargs="+", default=["matte_", "segmented_"])
    p.add_argument("--resolution", type=int,  nargs=2, default=[2048, 2048])
    p.add_argument("--clear-dir",  action="store_true")
    p.add_argument("--visualize",  action="store_true")
    p.add_argument("--max-workers",type=int,  default=os.cpu_count())
    p.add_argument("--log-dir",    default="logs", help="CSV와 에러 로그를 저장할 폴더")
    return p.parse_args()

# ──────────────────────────────────────────────────────────────────────────────
# 3) 메인
# ──────────────────────────────────────────────────────────────────────────────
def main() -> None:
    args = parse_args()
    split_path = Path(args.split_dir)
    mesh_dirs   = [d for d in split_path.iterdir() if d.is_dir()]

    log_dir = Path(args.log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    print(f"{len(mesh_dirs)} meshes found in {split_path}")
    results: list[Tuple[str, bool, str]] = []

    # 병렬 실행
    with ThreadPoolExecutor(max_workers=args.max_workers) as ex:
        futs = {ex.submit(run_one, mdir, args, log_dir): mdir.name for mdir in mesh_dirs}
        for fut in as_completed(futs):
            results.append(fut.result())

    # ───── CSV 기록 ─────
    csv_path = log_dir / "batch_report.csv"
    with csv_path.open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["mesh_id", "success", "error_log"])   # 헤더
        writer.writerows(results)

    # ───── 요약 통계 ─────
    total     = len(results)
    succeeded = sum(1 for _, ok, _ in results if ok)
    failed    = total - succeeded
    rate      = succeeded / total * 100 if total else 0
    print(f"\nSummary • total: {total}  success: {succeeded}  fail: {failed}  "
          f"success-rate: {rate:.1f}%")
    print(f"Detailed report → {csv_path.resolve()}")

if __name__ == "__main__":
    main()
