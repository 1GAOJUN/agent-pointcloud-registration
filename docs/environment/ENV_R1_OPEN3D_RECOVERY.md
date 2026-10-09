# ENV-R1 — Open3D Runtime Recovery

## Incident

Open3D DLL initialization failure reported when B3A blind test was
about to launch, before Basic Diagnosis had run. B3A was correctly
stopped.

## Root Cause

UNKNOWN / MOST_LIKELY.

The current environment (pointcloud_agh) now imports Open3D successfully
without error. The most likely cause of the original failure is that the
AGH Python tool was invoked with the wrong interpreter (system Python
instead of the conda env Python at
`D:\APP\Anaconda\envs\pointcloud_agh\python.exe`), or the conda env
was not activated before invoking `python`. A direct invocation of the
env Python resolves the issue. No version mismatch or missing DLL was
found.

## Failing Environment

- Python path (assumed failing): system default `python` on PATH,
  which is NOT `D:\APP\Anaconda\envs\pointcloud_agh\python.exe`
- Version: unknown (system Python)
- Environment: not pointcloud_agh

## Known Working Environment

- conda env: pointcloud_agh
- Python path: D:\APP\Anaconda\envs\pointcloud_agh\python.exe
- Python version: 3.11.16 (conda-forge)
- Open3D: 0.20.0
- NumPy: 2.4.6
- matplotlib: 3.11.2
- Entry point (from README):
  `& "D:\APP\Anaconda\envs\pointcloud_agh\python.exe" <script.py>`

## CURRENT vs KNOWN_WORKING

| Item | Failing (assumed) | Working (confirmed) |
|---|---|---|
| Python exe | system python (PATH) | D:\APP\Anaconda\envs\pointcloud_agh\python.exe |
| Python ver | unknown | 3.11.16 |
| conda env | none | pointcloud_agh |
| Open3D | missing / wrong | 0.20.0 |
| NumPy | unknown | 2.4.6 |

## Fix Applied

No installation or version change was needed. The working fix is to
always invoke the absolute path to the conda env Python:

```
& 'D:\APP\Anaconda\envs\pointcloud_agh\python.exe' <script.py>
```

or activate the env first:

```
conda activate pointcloud_agh
python <script.py>
```

No pip install / conda install / version change was performed.

## Verification

| Smoke test | Result |
|---|---|
| SMOKE 1: import + print versions | PASS — Open3D 0.20.0, Python 3.11.16 |
| SMOKE 2: o3d.geometry.PointCloud() | PASS — npts=3 |
| SMOKE 3: o3d.io.read_point_cloud | PASS — L1/seed_001 source.ply, 30000 pts |
| SMOKE 4: agent_diagnose.py | PASS — valid JSON output, all fields present |

## Project Files Modified

NONE (only new docs/environment/ files created under docs/)

## Verdict

ENV_R1_RECOVERED
