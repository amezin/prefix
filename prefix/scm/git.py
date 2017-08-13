import locale
import logging
import shlex
import subprocess
import sys


LOG = logging.getLogger(__name__)
DEFAULT_REMOTE = 'origin'


class GitTool:
    def __init__(self, cwd):
        self.base_args = ('git',)
        self.cwd = cwd
        self.encoding = locale.getpreferredencoding()

    def __call__(self, *args, **kwargs):
        kwargs.setdefault('check', True)
        kwargs.setdefault('cwd', self.cwd)
        kwargs.setdefault('encoding', self.encoding)
        args = self.base_args + args
        LOG.debug("Running %s", ' '.join(shlex.quote(str(arg)) for arg in args))
        return subprocess.run(args, **kwargs)

    def output(self, *args, **kwargs):
        kwargs.setdefault('stdout', subprocess.PIPE)
        return self(*args, **kwargs).stdout.strip()


def update(source_dir, url, commit='master', depth=1, remote=DEFAULT_REMOTE, clean=False):
    git = GitTool(source_dir)

    if not source_dir.exists():
        LOG.info("Creating directory '%s'", source_dir)
        source_dir.mkdir()

    git_dir = source_dir / '.git'
    if not git_dir.exists():
        LOG.info("Creating git repository in '%s'", source_dir)
        git('init', '-q')

    if remote in git.output('remote'):
        current_url = git.output('remote', 'get-url', remote)
        if current_url != url:
            if clean:
                LOG.warning("Changing URL of remote '%s' to '%s'", remote, url)
                git('remote', 'set-url', remote, url)
            else:
                raise Exception(f"Wrong remote '{remote}' URL '{current_url}' (should be '{url}')")
    else:
        LOG.info("Adding remote '%s' with URL '%s'", remote, url)
        git('remote', 'add', remote, url)

    try:
        LOG.info("Fetching '%s' from remote '%s' ('%s') to '%s'", commit, remote, url, source_dir)
        git('fetch', '--depth', str(depth), remote, '--', commit)
        commit_id = git.output('rev-parse', '--verify', 'FETCH_HEAD')

    except subprocess.CalledProcessError:
        if git.output('rev-parse', '--symbolic-full-name', commit):
            raise

        LOG.warning("Fetching '%s' failed, trying to fetch entire repository", commit)

        if (git_dir / 'shallow').exists():
            git('fetch', '--unshallow', remote)
        else:
            git('fetch', remote)

        commit_id = git.output('rev-parse', '--verify', commit)

    stashed = False

    if git.output('status', '--porcelain'):
        if clean:
            LOG.info("Cleaning '%s'", source_dir)
            git('reset', '--hard')
            git('clean', '-dff')

        else:
            LOG.info("Stashing changes in '%s'", source_dir)
            git('stash', 'save', '--all', 'Automatically stashed by "%s"' % sys.argv[0])
            stashed = True

    try:
        upstream = git.output('rev-parse', '--verify', '-q', '--symbolic-full-name', '@{u}')
        upstream_id = git.output('rev-parse', '--verify', '-q', '@{u}')
    except subprocess.CalledProcessError:
        upstream = None
        upstream_id = None

    if not clean and upstream == f'refs/remotes/{remote}/{commit}' and upstream_id == commit_id:
        LOG.info("Rebasing '%s' onto '%s' (%s)", source_dir, commit, commit_id)
        git('rebase', commit_id)

    else:
        LOG.info("Switching '%s' to '%s' (%s)", source_dir, commit, commit_id)
        git('checkout', '-q', commit_id)

    if stashed:
        LOG.info("Restoring changes in '%s'", source_dir)
        git('stash', 'pop')
