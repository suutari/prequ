import os
import subprocess
import sys
from textwrap import dedent

import pytest
from click.testing import CliRunner
from six.moves.urllib.request import pathname2url

from prequ.scripts.compile_in import cli


@pytest.yield_fixture
def pip_conf(tmpdir):
    test_conf = dedent("""\
        [global]
        index-url = http://example.com
        trusted-host = example.com
    """)

    pip_conf_file = 'pip.conf' if os.name != 'nt' else 'pip.ini'
    path = (tmpdir / pip_conf_file).strpath

    with open(path, 'w') as f:
        f.write(test_conf)

    old_value = os.environ.get('PIP_CONFIG_FILE')
    try:
        os.environ['PIP_CONFIG_FILE'] = path
        yield path
    finally:
        if old_value is not None:
            os.environ['PIP_CONFIG_FILE'] = old_value
        else:
            del os.environ['PIP_CONFIG_FILE']
        os.remove(path)


def test_default_pip_conf_read(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        # preconditions
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v'])

        # check that we have our index-url as specified in pip.conf
        assert 'Using indexes:\n  http://example.com' in out.output
        assert '--index-url http://example.com' in out.output


def test_command_line_overrides_pip_conf(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        # preconditions
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v', '-i', 'http://override.com'])

        # check that we have our index-url as specified in pip.conf
        assert 'Using indexes:\n  http://override.com' in out.output


def test_command_line_setuptools_read(pip_conf):

    runner = CliRunner()
    with runner.isolated_filesystem():
        package = open('setup.py', 'w')
        package.write(dedent("""\
            from setuptools import setup
            setup(install_requires=[])
        """))
        package.close()
        out = runner.invoke(cli)

        # check that compile generated a configuration
        assert 'This file is autogenerated by Prequ' in out.output


def test_find_links_option(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        find_link_options = [
            '-f', './libs1',
            '-f', '/global-libs',
            '-f', './libs2',
        ]
        out = runner.invoke(cli, ['-v'] + find_link_options)

        # Check that find-links has been passed to pip
        assert ('Configuration:\n'
                '  -f ./libs1\n'
                '  -f /global-libs\n'
                '  -f ./libs2\n') in out.output

        assert ('--find-links libs1\n'
                '--find-links libs2\n') in out.output


def test_extra_index_option(pip_conf):

    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v',
                                  '--extra-index-url', 'http://extraindex1.com',
                                  '--extra-index-url', 'http://extraindex2.com'])
        assert ('Using indexes:\n'
                '  http://example.com\n'
                '  http://extraindex1.com\n'
                '  http://extraindex2.com' in out.output)
        assert ('--index-url http://example.com\n'
                '--extra-index-url http://extraindex1.com\n'
                '--extra-index-url http://extraindex2.com' in out.output)


def test_trusted_host(pip_conf):
    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v',
                                  '--trusted-host', 'example.com',
                                  '--trusted-host', 'example2.com'])
        assert ('--trusted-host example.com\n'
                '--trusted-host example2.com\n' in out.output)


def test_trusted_host_no_emit(pip_conf):
    assert os.path.exists(pip_conf)

    runner = CliRunner()
    with runner.isolated_filesystem():
        open('requirements.in', 'w').close()
        out = runner.invoke(cli, ['-v',
                                  '--trusted-host', 'example.com',
                                  '--no-emit-trusted-host'])
        assert '--trusted-host example.com' not in out.output


def test_realistic_complex_sub_dependencies(tmpdir):

    # make a temporary wheel of a fake package
    subprocess.check_output(['pip', 'wheel',
                             '--no-deps',
                             '-w', str(tmpdir),
                             os.path.join('.', 'tests', 'fake_pypi', 'fake_package', '.')])

    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('fake_with_deps')  # require fake package

        out = runner.invoke(cli, ['-v',
                                  '-n', '--rebuild',
                                  '-f', str(tmpdir)])

        assert out.exit_code == 0


def _invoke(command):
    """Invoke sub-process."""
    try:
        output = subprocess.check_output(
            command,
            stderr=subprocess.STDOUT,
        )
        status = 0
    except subprocess.CalledProcessError as error:
        output = error.output
        status = error.returncode

    return status, output


def test_run_as_module_compile_in(tmpdir):
    """Prequ can be run as ``python -m prequ compile-in ...``."""

    status, output = _invoke([
        sys.executable, '-m', 'prequ', 'compile-in', '--help',
    ])

    # Should have run prequ compile successfully.
    output = output.decode('utf-8')
    assert output.startswith('Usage:')
    assert 'INTERNAL: Compile a single in-file.' in output
    assert 'command is considered implementation detail' in output
    assert status == 0


def test_run_as_module_sync():
    """Prequ can be run as ``python -m prequ sync ...``."""

    status, output = _invoke([
        sys.executable, '-m', 'prequ', 'sync', '--help',
    ])

    # Should have run pip-compile successfully.
    output = output.decode('utf-8')
    assert output.startswith('Usage:')
    assert 'Synchronize virtual environment with' in output
    assert status == 0


def test_editable_package(tmpdir):
    """Prequ can compile an editable """
    fake_package_dir = os.path.join(os.path.split(__file__)[0], 'fake_pypi', 'small_fake_package')
    fake_package_dir = 'file:' + pathname2url(fake_package_dir)
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('-e ' + fake_package_dir)  # require editable fake package

        out = runner.invoke(cli, ['-n'])

        assert out.exit_code == 0
        assert fake_package_dir in out.output
        assert 'six==1.10.0' in out.output


def test_editable_package_vcs(tmpdir):
    vcs_package = (
        'git+git://github.com/pytest-dev/pytest-django'
        '@21492afc88a19d4ca01cd0ac392a5325b14f95c7'
        '#egg=pytest-django'
    )
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('-e ' + vcs_package)
        out = runner.invoke(cli, ['-n',
                                  '--rebuild'])
        assert out.exit_code == 0
        assert vcs_package in out.output
        assert 'pytest' in out.output  # dependency of pytest-django


def test_input_file_without_extension(tmpdir):
    """
    Prequ can compile a file without an extension,
    and add .txt as the defaut output file extension.
    """
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements', 'w') as req_in:
            req_in.write('six==1.10.0')

        out = runner.invoke(cli, ['requirements'])

        assert out.exit_code == 0
        assert os.path.exists('requirements.txt')
        assert 'six==1.10.0' in open('requirements.txt').read()


def test_upgrade_packages_option(tmpdir):
    """
    Prequ respects --upgrade-package/-P inline list.
    """
    fake_package_dir = os.path.join(os.path.split(__file__)[0], 'fake_pypi', 'minimal_wheels')
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open('requirements.in', 'w') as req_in:
            req_in.write('small-fake-a\nsmall-fake-b')
        with open('requirements.txt', 'w') as req_in:
            req_in.write('small-fake-a==0.1\nsmall-fake-b==0.1')

        out = runner.invoke(cli, [
            '-P', 'small_fake_b',
            '-f', fake_package_dir,
        ])

        assert out.exit_code == 0
        assert 'small-fake-a==0.1' in out.output
        assert 'small-fake-b==0.2' in out.output
