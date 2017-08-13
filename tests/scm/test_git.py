import os
import pathlib

import pytest

from prefix.scm.git import GitTool, update, DEFAULT_REMOTE


class GitRepo(GitTool):
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
def src_repo(tmpdir):
    repo_dir = tmpdir / 'src_repo'
    repo_dir.mkdir()
    repo = GitRepo(repo_dir)
    repo('init', '-q')
    return repo


@pytest.fixture
def dst_repo(tmpdir):
    return GitRepo(tmpdir / 'dst_repo')


def test_clone_then_pull(src_repo, dst_repo):
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE'})
    update(dst_repo.path, src_repo.url)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE'

    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE MODIFIED'})
    update(dst_repo.path, src_repo.url)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE MODIFIED'


def test_branch(src_repo, dst_repo):
    master_head = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE from master'})

    src_repo('checkout', '-b', 'test-branch')
    test_branch_head = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE from test-branch'})

    update(dst_repo.path, src_repo.url, commit='test-branch')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE from test-branch'
    assert dst_repo.output('rev-parse', 'refs/remotes/%s/test-branch' % DEFAULT_REMOTE) == test_branch_head
    with pytest.raises(Exception):
        dst_repo.output('rev-parse', 'refs/remotes/%s/master' % DEFAULT_REMOTE)

    update(dst_repo.path, src_repo.url, commit='master')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE from master'
    assert dst_repo.output('rev-parse', 'refs/remotes/%s/master' % DEFAULT_REMOTE) == master_head

    update(dst_repo.path, src_repo.url, commit='test-branch')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE from test-branch'

    test_branch_head = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE from test-branch 2'})
    update(dst_repo.path, src_repo.url, commit='test-branch')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE from test-branch 2'
    assert dst_repo.output('rev-parse', 'refs/remotes/%s/test-branch' % DEFAULT_REMOTE) == test_branch_head


def test_tag(src_repo, dst_repo):
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE from tag'})
    src_repo('tag', 'test-tag')
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE from master'})

    update(dst_repo.path, src_repo.url, commit='test-tag')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE from tag'
    with pytest.raises(Exception):
        dst_repo.output('rev-parse', 'refs/remotes/%s/master' % DEFAULT_REMOTE)

    update(dst_repo.path, src_repo.url, commit='master')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE from master'

    update(dst_repo.path, src_repo.url, commit='test-tag')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE from tag'


def test_sha(src_repo, dst_repo):
    commit1 = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 1'})
    commit2 = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 2'})

    update(dst_repo.path, src_repo.url, commit=commit1)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 1'

    update(dst_repo.path, src_repo.url, commit=commit2)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 2'

    update(dst_repo.path, src_repo.url, commit=commit1)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 1'


def test_remote_fix(src_repo, dst_repo):
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 1'})
    update(dst_repo.path, src_repo.url)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 1'

    dst_repo('remote', 'remove', DEFAULT_REMOTE)

    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 2'})
    update(dst_repo.path, src_repo.url)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 2'

    dst_repo('remote', 'set-url', DEFAULT_REMOTE, (src_repo.path.parent / 'non-existant-dir').as_uri())

    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 3'})

    with pytest.raises(Exception):
        update(dst_repo.path, src_repo.url)

    update(dst_repo.path, src_repo.url, clean=True)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 3'


def test_autostash(src_repo, dst_repo):
    commit1 = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3'})
    commit2 = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 2\nLine 2\nLine 3'})

    update(dst_repo.path, src_repo.url, commit=commit1)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 1\nLine 2\nLine 3'

    (dst_repo.path / 'test.txt').write_text('TEST FILE commit 1\nLine 2\nLine 3\nDIRTY')

    update(dst_repo.path, src_repo.url, commit=commit2)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 2\nLine 2\nLine 3\nDIRTY'


def test_same_commit(src_repo, dst_repo):
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3'})
    commit2 = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 2\nLine 2\nLine 3'})

    update(dst_repo.path, src_repo.url)
    (dst_repo.path / 'test.txt').write_text('TEST FILE commit 1\nLine 2\nLine 3\nDIRTY')

    old_stat = os.stat(src_repo.path / 'test.txt')

    update(dst_repo.path, src_repo.url, commit=commit2)

    assert os.stat(src_repo.path / 'test.txt') == old_stat


def test_rollback_to_unfetched_sha(src_repo, dst_repo):
    commit1 = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 1'})
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 2'})

    update(dst_repo.path, src_repo.url, depth=1)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 2'

    update(dst_repo.path, src_repo.url, commit=commit1)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 1'


def test_clean(src_repo, dst_repo):
    commit1 = src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3'})
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 2\nLine 2\nLine 3'})

    update(dst_repo.path, src_repo.url)

    (dst_repo.path / 'test.txt').write_text('TEST FILE commit 1\nLine 2\nLine 3\nDIRTY')
    (dst_repo.path / 'test2.txt').write_text('TEST 2')

    update(dst_repo.path, src_repo.url, commit=commit1, clean=True)

    assert dst_repo.output('status', '--porcelain') == ''


def test_commit_symbolic_name_clash(src_repo, dst_repo):
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 1'})

    update(dst_repo.path, src_repo.url)
    dst_repo('checkout', '-b', 'local-branch')
    dst_repo('tag', 'local-tag')

    with pytest.raises(Exception):
        update(dst_repo.path, src_repo.url, commit='local-branch')

    with pytest.raises(Exception):
        update(dst_repo.path, src_repo.url, commit='local-tag')


def test_rebase(src_repo, dst_repo):
    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3'})
    update(dst_repo.path, src_repo.url)
    dst_repo('checkout', 'master')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 1\nLine 2\nLine 3'

    update(dst_repo.path, src_repo.url)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 1\nLine 2\nLine 3'

    dst_repo.add_commit('Append "DIRTY"', {'test.txt': 'TEST FILE commit 1\nLine 2\nLine 3\nDIRTY'})
    update(dst_repo.path, src_repo.url)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 1\nLine 2\nLine 3\nDIRTY'

    src_repo.add_commit('TEST', {'test.txt': 'TEST FILE commit 2\nLine 2\nLine 3'})
    update(dst_repo.path, src_repo.url, depth=2)
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 2\nLine 2\nLine 3\nDIRTY'

    src_repo('checkout', '-b', 'test-branch')
    update(dst_repo.path, src_repo.url, commit='test-branch')
    assert (dst_repo.path / 'test.txt').read_text() == 'TEST FILE commit 2\nLine 2\nLine 3'
