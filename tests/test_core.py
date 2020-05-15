# Own
from .context import keyhint


def test_core_exit_code():
    """Does the program quit correctely?"""
    exit_code = 1
    try:
        keyhint.main(testrun=True)
    except SystemExit as exc:
        exit_code = exc.code
    assert exit_code == 0


def test_version_infos_exists():
    should_exist = [
        keyhint.__author__,
        keyhint.__email__,
        keyhint.__repo__,
        keyhint.__version__,
    ]
    all_exist = all(should_exist)
    assert all_exist is True
