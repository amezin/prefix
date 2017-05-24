import argparse
import logging

from . import __version__

logger = logging.getLogger(__name__)


def parse_args(args=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', action='version', version='%(prog)s ' + __version__)

    logging_args = parser.add_mutually_exclusive_group()
    logging_args.add_argument('-v', '--verbose', action='count', default=0)
    logging_args.add_argument('-q', '--quiet', action='count', default=0)

    parsed_args = parser.parse_args(args=args)

    log_levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR, logging.CRITICAL]
    log_verbosity = log_levels.index(logging.INFO) + parsed_args.quiet - parsed_args.verbose
    logging.basicConfig(level=log_levels[min(len(log_levels) - 1, max(0, log_verbosity))])
