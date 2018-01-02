import pytest

import prefix


@pytest.fixture
def download_cache_dir(cache):
    return cache.makedir(__name__)


@pytest.fixture
def workspace(tmpdir, download_cache_dir):
    return prefix.Workspace(tmpdir, cache_dir=download_cache_dir)


def test_zlib_cmake(workspace):
    prefix.build_cmake('zlib', url='https://zlib.net/zlib-1.2.11.tar.gz', workspace=workspace)


def test_libffi_autotools(workspace):
    prefix.build_autotools('libffi', url='ftp://sourceware.org/pub/libffi/libffi-3.2.1.tar.gz', workspace=workspace)
