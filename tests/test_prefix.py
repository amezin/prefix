import prefix
import pytest
import sys


@pytest.fixture
def download_cache_dir(cache):
    return cache.makedir(__name__)


@pytest.fixture
def workspace(tmpdir, download_cache_dir):
    return prefix.Workspace(tmpdir, cache_dir=download_cache_dir)


def test_glib(workspace):
    prefix.build_cmake('zlib', url='https://zlib.net/zlib-1.2.11.tar.gz', workspace=workspace)
    prefix.build_autotools('libffi', url='ftp://sourceware.org/pub/libffi/libffi-3.2.1.tar.gz', workspace=workspace)
    prefix.build_autotools('gettext', url='https://ftp.gnu.org/pub/gnu/gettext/gettext-0.19.8.tar.xz', workspace=workspace)
    prefix.build_autotools('pcre', url='https://ftp.pcre.org/pub/pcre/pcre-8.41.tar.bz2', workspace=workspace,
                           deps=['zlib'], extra_configure_args=['--enable-unicode-properties'])

    deps = ['zlib', 'libffi', 'gettext', 'pcre']
    if sys.platform == 'linux':
        prefix.build_autotools('util-linux', url='https://www.kernel.org/pub/linux/utils/util-linux/v2.31/util-linux-2.31.1.tar.xz', workspace=workspace)
        deps += ['util-linux']

    prefix.build_autotools('glib', url='https://download.gnome.org/sources/glib/2.55/glib-2.55.2.tar.xz', workspace=workspace, deps=deps)
