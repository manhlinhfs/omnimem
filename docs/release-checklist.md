# Release Checklist

Use this checklist before tagging a new OmniMem release.

## Pre-release
- Update `VERSION`
- Update `CHANGELOG.md`
- Confirm the release scope is tracked in a GitHub issue

## Quality gates
- Run `python3 -m compileall omnimem.py omni_add.py omni_search.py omni_import.py omni_del.py omni_bootstrap.py omni_doctor.py omni_metadata.py omni_update.py omni_version.py`
- Run `bash -n setup.sh`
- Run `bash -n omnimem`
- Run `python3 -m unittest discover -s tests -v`
- Run `./omnimem doctor`
- Run `./omnimem update --check`

## Release
- Merge the release branch to `main`
- Create and push the annotated git tag
- Close the release issue
- Save a short release snapshot to OmniMem with `omni_add.py`
