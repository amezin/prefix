import multiprocessing
import os
import pathlib
import shlex
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

    def download(self, url):
        split_url = urllib.parse.urlsplit(url, scheme='file', allow_fragments=False)
        if split_url.scheme == 'file':
            if split_url.netloc:
                raise ValueError(f"{url}: file url should have no netloc (got {split_url.netloc})")

            return pathlib.Path(split_url.path)

        cached_file = self.cache_dir / urllib.parse.quote(url)
        if not cached_file.exists():
            cached_file.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, cached_file)

        return cached_file

    def download_and_extract(self, url, extract_dir):
        extract_dir = pathlib.Path(extract_dir)
        extract_dir.mkdir(parents=True, exist_ok=True)
        shutil.unpack_archive(str(self.download(url)), extract_dir)


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

    workspace.download_and_extract(url, src_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    install_dir.mkdir(parents=True, exist_ok=True)

    configure = find_file_bfs(src_dir, ['CMakeLists.txt'])
    src_dir = configure.parent

    subprocess.run(['cmake', '-DCMAKE_INSTALL_PREFIX={}'.format(install_dir), src_dir], cwd=build_dir, check=True)
    subprocess.run(['make', '-j', str(multiprocessing.cpu_count()), 'install'], cwd=build_dir, check=True)


def build_autotools(name, url, workspace, deps=[], extra_configure_args=[]):
    src_dir = workspace.src_dir_for(name)
    build_dir = workspace.build_dir_for(name)
    install_dir = workspace.install_dir_for(name)

    workspace.download_and_extract(url, src_dir)

    build_dir.mkdir(parents=True, exist_ok=True)
    install_dir.mkdir(parents=True, exist_ok=True)

    configure = find_file_bfs(src_dir, ['configure'])

    pkg_config_paths = []
    bin_paths = []
    lib_paths = []
    include_paths = []

    for dep in deps:
        dep_install_prefix = workspace.install_dir_for(dep)

        for pkg_config_path in [dep_install_prefix / 'lib' / 'pkgconfig', dep_install_prefix / 'share' / 'pkgconfig']:
            if pkg_config_path.exists() and pkg_config_path not in pkg_config_paths:
                pkg_config_paths.append(pkg_config_path)

        bin_path = dep_install_prefix / 'bin'
        if bin_path.exists() and bin_path not in bin_paths:
            bin_paths.append(bin_path)

        lib_path = dep_install_prefix / 'lib'
        if lib_path.exists() and lib_path not in lib_paths:
            lib_paths.append(lib_path)

        inc_path = dep_install_prefix / 'include'
        if inc_path.exists() and inc_path not in include_paths:
            include_paths.append(inc_path)

    env = os.environb.copy()
    pathsep = os.fsencode(os.pathsep)

    def add_paths(var_name, path_list):
        if path_list:
            existing = env.get(var_name, b'')
            if existing:
                existing = pathsep + existing

            env[var_name] = pathsep.join(os.fsencode(p) for p in path_list) + existing

    def add_flags(var_name, flag_list):
        if flag_list:
            existing = env.get(var_name, b'')
            if existing:
                existing += b' '

            env[var_name] = existing + b' '.join(os.fsencode(shlex.quote(flag)) for flag in flag_list)

    add_paths(b'PKG_CONFIG_PATH', pkg_config_paths)
    add_paths(b'PATH', bin_paths)
    add_paths(b'LD_LIBRARY_PATH', lib_paths)
    add_paths(b'DYLD_LIBRARY_PATH', lib_paths)
    add_flags(b'CPPFLAGS', ('-I{}'.format(p) for p in include_paths))
    add_flags(b'LDFLAGS', ('-L{}'.format(p) for p in lib_paths))
    # LT_SYS_LIBRARY_PATH?

    try:
        subprocess.run([configure, '--prefix', install_dir] + list(extra_configure_args), cwd=build_dir, check=True, env=env)
        subprocess.run(['make', '-j', str(multiprocessing.cpu_count()), 'install'], cwd=build_dir, check=True, env=env)

    except subprocess.CalledProcessError:
        print("Environment:", env)
        raise
