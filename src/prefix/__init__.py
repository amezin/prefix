import multiprocessing
import pathlib
import shutil
import subprocess
import urllib.parse
import urllib.request


class Workspace:
    def __init__(self, root_dir, cache_dir=None):
        self.root_dir = pathlib.Path(root_dir).absolute()

        if cache_dir is None:
            cache_dir = self.root_dir / 'cache'

        self.cache_dir = pathlib.Path(cache_dir).absolute()

    def src_dir_for(self, project):
        return self.root_dir / project / 'src'

    def build_dir_for(self, project):
        return self.root_dir / project / 'build'

    def install_dir_for(self, project):
        return self.root_dir / project / 'install'


def download(url, cache_dir):
    cache_dir = pathlib.Path(cache_dir)
    split_url = urllib.parse.urlsplit(url, scheme='file', allow_fragments=False)
    if split_url.scheme == 'file':
        if split_url.netloc:
            raise ValueError(f"{url}: file url should have no netloc")

        return pathlib.Path(split_url.path)

    cached_file = cache_dir / urllib.parse.quote(url)
    if not cached_file.exists():
        cached_file.parent.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(url, cached_file)

    return cached_file


def download_and_extract(url, cache_dir, extract_dir):
    extract_dir = pathlib.Path(extract_dir)
    extract_dir.mkdir(parents=True, exist_ok=True)
    shutil.unpack_archive(str(download(url, cache_dir)), extract_dir)


def find_file_bfs(start_dir, filenames):
    dirs = [start_dir]
    found_files = []

    while dirs and not found_files:
        next_dirs = []
        found_files = []

        for test_dir in dirs:
            for filename in filenames:
                test_name = test_dir / filename
                if test_name.exists():
                    found_files.append(test_name)
                    break

            next_dirs.extend(d for d in test_dir.iterdir() if d.is_dir())

        dirs = next_dirs

    if len(found_files) > 1:
        raise LookupError("Multiple directories found: {}".format(found_files))
    elif not found_files:
        raise LookupError("File {} not found in {}".format(filenames, start_dir))
    else:
        return found_files[0]


def build_cmake(name, url, workspace):
    src_dir = workspace.src_dir_for(name)
    build_dir = workspace.build_dir_for(name)
    install_dir = workspace.install_dir_for(name)

    download_and_extract(url, workspace.cache_dir, src_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    install_dir.mkdir(parents=True, exist_ok=True)

    configure = find_file_bfs(src_dir, ['CMakeLists.txt'])
    src_dir = configure.parent

    subprocess.run(['cmake', '-DCMAKE_INSTALL_PREFIX={}'.format(install_dir), src_dir], cwd=build_dir, check=True)
    subprocess.run(['make', '-j', str(multiprocessing.cpu_count()), 'install'], cwd=build_dir, check=True)


def build_autotools(name, url, workspace):
    src_dir = workspace.src_dir_for(name)
    build_dir = workspace.build_dir_for(name)
    install_dir = workspace.install_dir_for(name)

    download_and_extract(url, workspace.cache_dir, src_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    install_dir.mkdir(parents=True, exist_ok=True)

    configure = find_file_bfs(src_dir, ['configure'])
    src_dir = configure.parent

    subprocess.run([configure, '--prefix', install_dir], cwd=build_dir, check=True)
    subprocess.run(['make', '-j', str(multiprocessing.cpu_count()), 'install'], cwd=build_dir, check=True)
