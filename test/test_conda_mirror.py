import pytest
import itertools
import copy
import sys
from conda_mirror import conda_mirror
from collections import namedtuple
import os
import bz2

@pytest.fixture(scope='module')
def repodata():
    rd = namedtuple('repodata', ['anaconda', 'condaforge'])
    anaconda = conda_mirror.get_repodata('anaconda', 'linux-64')
    cf = conda_mirror.get_repodata('conda-forge', 'linux-64')
    return rd(anaconda, cf)


def test_match(repodata):
    repodata_info, repodata_packages = repodata.anaconda
    matched = conda_mirror.match(repodata_packages, {'name': 'jupyter'})
    assert set([v['name'] for v in matched.values()]) == set(['jupyter'])

@pytest.mark.parametrize(
    'channel,platform',
    itertools.product(['anaconda', 'conda-forge'], ['linux-64']))
def test_cli(tmpdir, channel, platform):
    info, packages = conda_mirror.get_repodata(channel, platform)
    smallest_package = sorted(packages, key=lambda x: packages[x]['size'])[0]
    f2 = tmpdir.mkdir('%s' % channel)
    f1 = tmpdir.mkdir('conf').join('conf.yaml')

    f1.write('''
blacklist:
    - name: "*"
whitelist:
    - name: {}
      version: {}'''.format(
            packages[smallest_package]['name'],
            packages[smallest_package]['version']))
    cli_args = ("conda-mirror"
                " --config {}"
                " --upstream-channel anaconda"
                " --target-directory {}"
                " --platform {}"
                " --pdb"
                ).format(f1.strpath,
                         f2.strpath,
                         platform)
    old_argv = copy.deepcopy(sys.argv)
    sys.argv = cli_args.split(' ')
    conda_mirror.cli()
    sys.argv = old_argv


def test_handling_bad_package(tmpdir):
    local_repo_root = tmpdir.mkdir('repo').strpath
    bad_pkg_root = os.path.join(local_repo_root, 'linux-64')
    os.makedirs(bad_pkg_root)
    bad_pkg_name = 'bad-1-0.tar.bz2'
    bad_pkg_path = os.path.join(bad_pkg_root, bad_pkg_name)

    if os.path.exists(bad_pkg_path):
        os.remove(bad_pkg_path)

    with bz2.BZ2File(bad_pkg_path, 'wb') as f:
        f.write("This is a fake package".encode())
    assert bad_pkg_name in os.listdir(bad_pkg_root)
    conda_mirror.run_conda_index(bad_pkg_root)
    assert bad_pkg_name not in os.listdir(bad_pkg_root)