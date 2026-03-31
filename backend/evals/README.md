# Repo Analysis Golden Set

`golden_repo_analysis.json` is a lightweight benchmark set for regression testing the GitHub AI analysis pipeline.

## Run

```powershell
cd backend
python scripts/eval_repo_analysis.py --min-score 0.75
```

## Dataset shape

Each case defines:

- `repo_prompt`: synthetic repository context fed to AI analyzer
- `expected.recommended_any`: at least one required stack item
- `expected.forbidden_all`: stack items that must not appear
- `expected.ec2_max`: upper bound for EC2 count
- `expected.rds_enabled`: expected RDS enable state
- `expected.architecture_services_any`: at least one required `additional_services` value
- `expected.must_be_korean`: require Korean report text output

Adjust `--min-score` to tighten release gates.
