# Redrock subprocess boundary — evidence record (WP-041, 2026-10-15)

Status: **recording policy chosen and implemented 2026-10-16**. The historical inventory
below describes the pre-change state. The current runner also writes
`redrock_authority.json` beside `rrdetails.h5` for each attempted invocation.

状态：**2026-10-16 决定并实现记录策略**。下文清单是修改前的状态。目前每次尝试调用还会在
`rrdetails.h5` 旁写出 `redrock_authority.json`。

The new record includes the actual argv, resolved `rrdesi` launcher path and SHA-256,
template/archetype directory content hashes, selected environment values, a probe of the
Redrock package visible to FORMA's interpreter, and the subprocess return code. It
excludes the inherited environment because it may contain secrets. The package probe
may differ from the interpreter named by the `rrdesi` shebang. Hashes are taken before
execution, so a file changed during Redrock execution is not covered. No hash is yet
enforced and Redrock's omitted CLI options remain its defaults. Therefore this is an
audit record, **not a reproducibility lock**. The decision owner accepted this boundary:
cross-run comparisons must use both the frozen FORMA digest and this external record;
a changed binary or template is a declared comparability difference, not an automatic
runtime error.

新记录包含实际 argv、`rrdesi` 启动脚本的解析路径和 SHA-256、模板／archetype 目录内容
摘要、选定的环境变量、FORMA 解释器可见的 Redrock 包探测结果及子进程返回码。继承的完整环境
可能包含秘密，故不保存。包探测结果未必对应 `rrdesi` shebang 指定的解释器；摘要在执行前取得，
不能保证执行期间文件不变。目前也不强制比对摘要，未显式指定的选项仍采用 Redrock 默认值。
因此这是审计记录，**不是复现锁**。

## What crosses the boundary

The pipeline builds one command and runs it as an external process
(`src/FORMA/agents/multi_agents/utils/VI.py`, the `rrdesi` runner):

```python
cmd = ["rrdesi", "-i", input_fits, "-o", output_fits, "-d", details_h5,
       "--nminima", str(nminima)]
if use_archetypes:
    cmd += ["--archetypes", archetype_dir, "--archetype-nnearest", str(nnearest),
            "--archetype-legendre-percamera", str(per_camera)]
    cmd += (["--archetypes-no-legendre"] if no_legendre
            else ["--archetype-legendre-degree", str(legendre_degree),
                  "--archetype-legendre-prior", str(legendre_prior)])

env = os.environ.copy()                 # the whole environment is inherited
env["OMP_NUM_THREADS"] = str(omp_num_threads)
env["RR_TEMPLATE_DIR"] = rr_template_dir
subprocess.run(cmd, env=env, text=True, capture_output=True)
```

## What the run records today

`effective_parameters.json` carries a `redrock` section with exactly five numbers —
`nminima`, `nnearest`, `omp_num_threads`, `archetype_legendre_degree`,
`archetype_legendre_prior_sigma` (observed in `.data/runs/legacy-challenge/ELG/3`).

## What is therefore outside the declaration, freeze and authority system

| Input | How it reaches Redrock | Recorded? |
|---|---|---|
| Template set | `RR_TEMPLATE_DIR` path in the environment | path not recorded; **no content digest** |
| Archetype set | `--archetypes` path (only when `USE_ARCHETYPES=true`) | not recorded |
| The binary itself | bare name `rrdesi`, resolved through `PATH` | **no path, no version, no digest** |
| Options we do not pass | Redrock's own defaults (redshift range, priors, polynomial order, template-selection details) | not recorded, version-dependent |
| Environment | `os.environ.copy()` plus two overrides | the inherited set is not recorded |
| Passed options | CLI arguments built from `ParamsConfig` | five numbers only; `use_archetypes`, `per_camera`, `no_legendre` not recorded |

## Why the freeze (WP-041, first increment) does not cover this

The frozen parameter set governs the loaders inside our own process. The subprocess is a
separate authority: it receives materialised arguments and its own environment, and it
re-reads nothing of ours. Evidence for the narrower claim ("the subprocess does not read
the project JSON"): the analysis method is read in the **parent** to build the arguments
(`utils/VI.py` reads `load_analysis_method()` while preparing the run), and no project JSON
path is placed in the child environment or arguments.

Accepted limits of the recording policy:

* the frozen digest cannot be presented as the run's **complete** parameter identity;
* two runs with identical frozen digests can still differ because a template set or binary
  version changed — which bears directly on the re-render reproducibility criterion;
* Redrock's own decisions are attributed to the adjacent external-authority record;
  they are not FORMA declaration values in a prompt manifest.

## Options reviewed and decision

1. **Pin**: resolve `rrdesi` to an absolute path and record its version (or a binary
   digest); record a content digest of the template and archetype directories; pass an
   explicit minimal environment (allowlist) instead of copying the whole one.
2. **Declare**: add an external-authority record to the run artifacts — verbatim `argv`,
   binary identity, template/archetype digests, and the list of options deliberately left to
   Redrock's defaults (stated as external and version-pinned).
3. **Verify**: tests asserting that the `argv` is built solely from declared parameters, that
   the executed `argv` equals the recorded one, and that the child environment is exactly the
   allowlist.

The decision owner chose option 2, recording external authority. A template or launcher
digest change is visible in cross-run comparisons, not a runtime error. Option 1 would
require an explicit new decision. Option 3's exact environment allowlist belongs to the
strict pinning design and was not adopted; the test does verify that the executed argv
equals the recorded argv and that inherited secrets are absent from the artifact.
