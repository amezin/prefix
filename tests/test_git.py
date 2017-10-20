import os
import pathlib

import pytest

from prefix.git import GitTool, GitRepo


class GitFixture(GitTool):
    def __init__(self, path):
        super().__init__(path)
        self.path = pathlib.Path(path)
        self.url = self.path.as_uri()

    def add_commit(self, message, files):
        all_files = []

        for filename, content in files.items():
            filename = self.path / filename
            filename.write_text(content)
            all_files.append(filename)

        self('add', '--', *all_files)
        self('commit', '-q', '--message', message)
        return self.output('rev-parse', 'HEAD')


@pytest.fixture
def src_git(tmpdir):
    repo_dir = tmpdir / 'src_git'
    repo_dir.mkdir()
    git = GitFixture(repo_dir)
    git('init', '-q')
    return git


@pytest.fixture
def dst_git(tmpdir):
    return GitFixture(tmpdir / 'dst_git')


def test_clone_then_pull(src_git, dst_git):
    repo = GitRepo(source_dir=dst_git.path, url=src_git.url)

    src_git.add_commit('TEST', {'test.txt': 'TEST FILE'})
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE'

    src_git.add_commit('TEST', {'test.txt': 'TEST FILE MODIFIED'})
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE MODIFIED'


def test_branch(src_git, dst_git):
    master_head = src_git.add_commit('TEST', {'test.txt': 'TEST FILE from master'})

    src_git('checkout', '-b', 'test-branch')
    test_branch_head = src_git.add_commit('TEST', {'test.txt': 'TEST FILE from test-branch'})

    repo = GitRepo(source_dir=dst_git.path, url=src_git.url, commit='test-branch')
    repo.update()

    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE from test-branch'
    assert dst_git.output('rev-parse', 'refs/remotes/%s/test-branch' % GitRepo.remote.default) == test_branch_head
    with pytest.raises(Exception):
        dst_git.output('rev-parse', 'refs/remotes/%s/master' % GitRepo.remote.default)

    repo.commit = 'master'
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE from master'
    assert dst_git.output('rev-parse', 'refs/remotes/%s/master' % GitRepo.remote.default) == master_head

    repo.commit = 'test-branch'
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE from test-branch'

    test_branch_head = src_git.add_commit('TEST', {'test.txt': 'TEST FILE from test-branch 2'})
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE from test-branch 2'
    assert dst_git.output('rev-parse', 'refs/remotes/%s/test-branch' % GitRepo.remote.default) == test_branch_head


def test_tag(src_git, dst_git):
    src_git.add_commit('TEST', {'test.txt': 'TEST FILE from tag'})
    src_git('tag', 'test-tag')
    src_git.add_commit('TEST', {'test.txt': 'TEST FILE from master'})

    repo = GitRepo(source_dir=dst_git.path, url=src_git.url, commit='test-tag')
    repo.update()

    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE from tag'
    with pytest.raises(Exception):
        dst_git.output('rev-parse', 'refs/remotes/%s/master' % DEFAULT_REMOTE)

    repo.commit = 'master'
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE from master'

    repo.commit = 'test-tag'
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE from tag'


def test_sha(src_git, dst_git):
    commit1 = src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 1'})
    commit2 = src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 2'})

    repo = GitRepo(source_dir=dst_git.path, url=src_git.url, commit=commit1)
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 1'

    repo.commit = commit2
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 2'

    repo.commit = commit1
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 1'


def test_remote_fix(src_git, dst_git):
    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 1'})
    repo = GitRepo(source_dir=dst_git.path, url=src_git.url)
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 1'

    dst_git('remote', 'remove', GitRepo.remote.default)

    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 2'})
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 2'

    dst_git('remote', 'set-url', GitRepo.remote.default, (src_git.path.parent / 'non-existant-dir').as_uri())

    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 3'})

    with pytest.raises(Exception):
        repo.update()

    repo.update(clean=True)
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 3'


def test_autostash(src_git, dst_git):
    commit1 = src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3'})
    commit2 = src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 2\nLine 2\nLine 3'})

    repo = GitRepo(source_dir=dst_git.path, url=src_git.url, commit=commit1)
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 1\nLine 2\nLine 3'

    (dst_git.path / 'test.txt').write_text('TEST FILE commit 1\nLine 2\nLine 3\nDIRTY')

    repo.commit = commit2
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 2\nLine 2\nLine 3\nDIRTY'


def test_same_commit(src_git, dst_git):
    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3'})
    commit2 = src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 2\nLine 2\nLine 3'})

    repo = GitRepo(source_dir=dst_git.path, url=src_git.url)
    repo.update()
    (dst_git.path / 'test.txt').write_text('TEST FILE commit 1\nLine 2\nLine 3\nDIRTY')

    old_stat = os.stat(src_git.path / 'test.txt')

    repo.commit = commit2
    repo.update()

    assert os.stat(src_git.path / 'test.txt') == old_stat


def test_rollback_to_unfetched_sha(src_git, dst_git):
    commit1 = src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 1'})
    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 2'})

    repo = GitRepo(source_dir=dst_git.path, url=src_git.url, depth=1)
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 2'

    repo.commit = commit1
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 1'


def test_clean(src_git, dst_git):
    commit1 = src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3'})
    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 2\nLine 2\nLine 3'})

    repo = GitRepo(source_dir=dst_git.path, url=src_git.url)
    repo.update()

    (dst_git.path / 'test.txt').write_text('TEST FILE commit 1\nLine 2\nLine 3\nDIRTY')
    (dst_git.path / 'test2.txt').write_text('TEST 2')

    repo.commit = commit1
    repo.update(clean=True)

    assert dst_git.output('status', '--porcelain') == ''


def test_commit_symbolic_name_clash(src_git, dst_git):
    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 1'})

    repo = GitRepo(source_dir=dst_git.path, url=src_git.url)
    repo.update()

    dst_git('checkout', '-b', 'local-branch')
    dst_git('tag', 'local-tag')

    with pytest.raises(Exception):
        repo.commit = 'local-branch'
        repo.update()

    with pytest.raises(Exception):
        repo.commit = 'local-tag'
        repo.update()


def test_rebase(src_git, dst_git):
    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3'})
    repo = GitRepo(source_dir=dst_git.path, url=src_git.url)
    repo.update()
    dst_git('checkout', 'master')
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 1\nLine 2\nLine 3'

    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 1\nLine 2\nLine 3'

    dst_git.add_commit('Append "DIRTY"', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3\nDIRTY'})
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 1\nLine 2\nLine 3\nDIRTY'

    src_git.add_commit('TEST', {'test.txt': 'TEST FILE commit 2\nLine 2\nLine 3'})
    repo.depth = 2
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 2\nLine 2\nLine 3\nDIRTY'

    src_git('checkout', '-b', 'test-branch')
    repo.commit = 'test-branch'
    repo.update()
    assert (dst_git.path / 'test.txt').read_text() == 'TEST FILE commit 2\nLine 2\nLine 3'
