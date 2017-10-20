import locale
import logging
import shlex
import subprocess
import sys

from prefix.scm.dir import SourceDir, Option


LOG = logging.getLogger(__name__)


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


class GitRepo(SourceDir):
    url = Option(str)
    commit = Option(str, default='master')
    depth = Option(int, default=1)
    remote = Option(str, default='origin')

    def update(self, clean=False):
        git = GitTool(self.source_dir)

        if not self.source_dir.exists():
            LOG.info("Creating directory '%s'", self.source_dir)
            self.source_dir.mkdir()

        git_dir = self.source_dir / '.git'
        if not git_dir.exists():
            LOG.info("Creating git repository in '%s'", self.source_dir)
            git('init', '-q')

        if self.remote in git.output('remote'):
            current_url = git.output('remote', 'get-url', self.remote)
            if current_url != self.url:
                if clean:
                    LOG.warning("Changing URL of remote '%s' to '%s'", self.remote, self.url)
                    git('remote', 'set-url', self.remote, self.url)
                else:
                    raise Exception(f"Wrong remote '{self.remote}' URL '{current_url}' (should be '{self.url}')")
        else:
            LOG.info("Adding remote '%s' with URL '%s'", self.remote, self.url)
            git('remote', 'add', self.remote, self.url)

        try:
            LOG.info("Fetching '%s' from remote '%s' ('%s') to '%s'", self.commit, self.remote, self.url, self.source_dir)
            git('fetch', '--depth', str(self.depth), self.remote, '--', self.commit)
            commit_id = git.output('rev-parse', '--verify', 'FETCH_HEAD')

        except subprocess.CalledProcessError:
            if git.output('rev-parse', '--symbolic-full-name', self.commit):
                raise

            LOG.warning("Fetching '%s' failed, trying to fetch entire repository", self.commit)

            if (git_dir / 'shallow').exists():
                git('fetch', '--unshallow', self.remote)
            else:
                git('fetch', self.remote)

            commit_id = git.output('rev-parse', '--verify', self.commit)

        stashed = False

        if git.output('status', '--porcelain'):
            if clean:
                LOG.info("Cleaning '%s'", self.source_dir)
                git('reset', '--hard')
                git('clean', '-dff')

            else:
                LOG.info("Stashing changes in '%s'", self.source_dir)
                git('stash', 'save', '--all', 'Automatically stashed by "%s"' % sys.argv[0])
                stashed = True

        try:
            upstream = git.output('rev-parse', '--verify', '-q', '--symbolic-full-name', '@{u}', stderr=subprocess.DEVNULL)
            upstream_id = git.output('rev-parse', '--verify', '-q', '@{u}', stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            upstream = None
            upstream_id = None

        if not clean and upstream == f'refs/remotes/{self.remote}/{self.commit}' and upstream_id == commit_id:
            LOG.info("Rebasing '%s' onto '%s' (%s)", self.source_dir, self.commit, commit_id)
            git('rebase', commit_id)

        else:
            LOG.info("Switching '%s' to '%s' (%s)", self.source_dir, self.commit, commit_id)
            git('checkout', '-q', commit_id)

        if stashed:
            LOG.info("Restoring changes in '%s'", self.source_dir)
            git('stash', 'pop')
