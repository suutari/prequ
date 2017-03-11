import click

from . import build_wheels
from . import check
from . import compile_in
from . import compile
from . import sync
from . import update

click.disable_unicode_literals_warning = True


@click.group()
@click.version_option()
def main():
    pass


main.add_command(build_wheels.main, 'build-wheels')
main.add_command(check.main, 'check')
main.add_command(compile_in.cli, 'compile-in')
main.add_command(compile.main, 'compile')
main.add_command(sync.cli, 'sync')
main.add_command(update.main, 'update')


if __name__ == '__main__':
    main()
