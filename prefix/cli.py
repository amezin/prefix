import argparse

from . import __version__


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    parser.parse_args(args=args)
