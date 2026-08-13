#!/usr/bin/env bash
# Copy migration bootstrap kit from qua-libs-superconducting into a new modality repo.
# Usage: ./scripts/bootstrap_modality_repo.sh MODALITY TARGET_DIR
# Example: ./scripts/bootstrap_modality_repo.sh AMO ../qua-libs-amo

set -euo pipefail

MODALITY="${1:?Usage: $0 MODALITY TARGET_DIR}"
TARGET="${2:?Usage: $0 MODALITY TARGET_DIR}"
SOURCE="$(cd "$(dirname "$0")/.." && pwd)"

mkdir -p "$TARGET"/{docs/plans,docs/bootstrap,scripts,.cursor/rules,tests,"Quantum-Control-Applications/$MODALITY",.github/workflows}

cp "$SOURCE/docs/plans/qua-1.4.0-migration.md" "$TARGET/docs/plans/"
cp "$SOURCE/docs/plans/qua-1.4.0-migration-runbook.md" "$TARGET/docs/plans/"
cp "$SOURCE/docs/bootstrap/MANIFEST.md" "$TARGET/docs/bootstrap/"

cp "$SOURCE/scripts/migration_paths.py" "$TARGET/scripts/"
cp "$SOURCE/scripts/migrate_amp_to_amplitude_scale.py" "$TARGET/scripts/"
cp "$SOURCE/scripts/migrate_config_split.py" "$TARGET/scripts/"
cp "$SOURCE/scripts/migrate_qca_qua_131.py" "$TARGET/scripts/"
cp "$SOURCE/scripts/generate_qua_migrated_files_inventory.py" "$TARGET/scripts/"
cp "$SOURCE/scripts/bootstrap_modality_repo.sh" "$TARGET/scripts/"

cp "$SOURCE/Quantum-Control-Applications/Superconducting/qua_config_split.py" \
   "$TARGET/Quantum-Control-Applications/$MODALITY/"

cp "$SOURCE/tests/test_qca_migration_gates.py" "$TARGET/tests/"
cp "$SOURCE/.cursor/rules/qua-documentation.mdc" "$TARGET/.cursor/rules/"
cp "$SOURCE/.cursor/rules/changelog.mdc" "$TARGET/.cursor/rules/"

if [[ -f "$SOURCE/.github/workflows/ci.yml" ]]; then
  cp "$SOURCE/.github/workflows/ci.yml" "$TARGET/.github/workflows/"
fi

if [[ -f "$SOURCE/CONTRIBUTING.md" ]]; then
  cp "$SOURCE/CONTRIBUTING.md" "$TARGET/"
fi

if [[ -f "$SOURCE/CHANGELOG.md" ]]; then
  head -n 8 "$SOURCE/CHANGELOG.md" > "$TARGET/CHANGELOG.md"
  printf '\n## [Unreleased]\n\n### Added\n\n- Initial bootstrap from qua-libs-superconducting migration kit\n' >> "$TARGET/CHANGELOG.md"
fi

cat <<EOF

Bootstrap copied to: $TARGET

Next steps:
  1. Copy Quantum-Control-Applications/$MODALITY/ from qua-libs (upstream examples)
  2. Edit $TARGET/.cursor/rules/qua-documentation.mdc — set modality to $MODALITY
  3. Add pyproject.toml (pin qm-qua==1.4.0) and README.md
  4. cd $TARGET && uv sync
  5. Follow docs/plans/qua-1.4.0-migration-runbook.md

EOF
