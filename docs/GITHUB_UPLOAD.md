# Safe GitHub integration procedure

The prepared working directory intentionally has no local `.git` directory.
Preserve the remote repository's history by cloning it into a separate sibling
directory and creating a review branch. Do not initialize a new history here.

```bash
cd /home2/cohent59/subgraph_filter_suit
git clone git@github.com:TalCohenYosef/most-informative-subgraph.git most-informative-subgraph-publish
cd most-informative-subgraph-publish
git switch -c reproducibility-reorganization-2026-10-19
```

Copy the prepared tree without deleting remote files, replacing the remote
README, or copying ignored environments, unpublished raw inputs, or generated
GNP payloads. The generator under `data/generation_code/gnp/` is included by
this command because it is outside the excluded payload directories:

```bash
rsync -a \
  --exclude='.git/' \
  --exclude='/README.md' \
  --exclude='.conda-env/' \
  --exclude='.conda-pkgs/' \
  --exclude='.validation/' \
  --exclude='.external/' \
  --exclude='__pycache__/' \
  --exclude='*.py[cod]' \
  --exclude='.pytest_cache/' \
  --exclude='.mypy_cache/' \
  --exclude='.venv/' \
  --exclude='.env' \
  --exclude='.idea/' \
  --exclude='.vscode/' \
  --exclude='*.swp' \
  --exclude='*.log' \
  --exclude='caches/' \
  --exclude='miner_batches/' \
  --exclude='checkpoints/' \
  --exclude='.DS_Store' \
  --exclude='Thumbs.db' \
  --include='/data/generated/gnp/references/' \
  --include='/data/generated/gnp/references/.gitkeep' \
  --exclude='/data/generated/gnp/references/***' \
  --include='/data/generated/gnp/queries/' \
  --include='/data/generated/gnp/queries/.gitkeep' \
  --exclude='/data/generated/gnp/queries/***' \
  --include='data/raw/realworld/*/' \
  --include='data/raw/realworld/*/.gitkeep' \
  --exclude='data/raw/realworld/*/*' \
  ../most-informative-subgraph/ ./

cp ../most-informative-subgraph/README.md README.reproducibility.md
git diff --no-index -- README.md README.reproducibility.md || true
git status --short
git diff --check
git diff --stat
```

Before staging, confirm the intended exclusions and additions:

```bash
git check-ignore -v \
  data/generated/gnp/references/graphs_deg_5/G_average_deg_3.json \
  data/generated/gnp/queries/input_color_average_deg_3/S_1.json \
  data/raw/realworld/bookchild/processed_data.pt
git status --short
```

Merge the two README files only after reviewing the displayed differences.
Also review any pre-existing remote files that the non-deleting `rsync` command
leaves in place. After approval, stage and inspect the proposed commit:

```bash
git add -A
git status --short
git diff --cached --check
git diff --cached --stat
git commit -m "Organize paper reproducibility materials"
```

The eventual non-force upload command is:

```bash
git push -u origin reproducibility-reorganization-2026-10-19
```

Do not use `git init`, `git push --force`, `git reset --hard`, or copy a new
`.git` directory into the prepared working tree.
