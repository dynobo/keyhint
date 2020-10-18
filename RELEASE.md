# How To Release new version

(Notes to myself)

## Prepare

1. Commit latest changes to `dev`, and see if tests run through
2. Increase version number (major.minor.patch):

```sh
bumpversion major
bumpversion minor
bumpversion patch
```

## Merge

1. Create pull request from master to dev
2. See, if all tests ran through
3. Tag master with version

## Submit to pypi

1. Build: `python setup.py sdist bdist_wheel`
2. Upload to testpypi: `twine upload --repository testpypi dist/*`
3. Test package: `twine upload --repository testpypi dist/*`
4. Upload to pypi: `twine upload --repository pypi dist/*`
