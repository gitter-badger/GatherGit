#!/usr/bin/env python
# -*- coding: utf-8 -*-
# vim: ts=4 sw=4 et
"""gathergit

A description.

TODO:
 - do metadata parsing
"""

# Third party libs
import argparse

from cache import Cache
from misc import (Helper, ConfigParser)
from repo import Repo
from repoindex import Repoindex


def main():
    version = '0.0.1'
    program_name = 'gathergit'
    parser = argparse.ArgumentParser(prog=program_name, description='A description')

    # general args
    parser.add_argument('-V', action='version', version='%(prog)s {version}'.format(version=version))
    parser.add_argument('--confdir',
                        action='store',
                        dest='confdir',
                        help='directory to search for configuration files (default: config/)',
                        default='config/')
    parser.add_argument('--all',
                        action='store_true',
                        dest='sync_all',
                        help='Initialize, update and synchronize ALL repositories',
                        default=False)

    parser_results = parser.parse_args()
    confdir = parser_results.confdir
    sync_all = parser_results.sync_all

    # config parsing
    cfg_parser = ConfigParser(confdir)
    config = cfg_parser.dump()

    # logging
    logconfig = config.get('settings', {}).get('logging', {})
    logger = Helper().create_logger(program_name, logconfig)

    # let's start working now
    logger.debug('Starting new instance of %s', program_name)
    logger.debug('Raw configuration: %s', config)

    # collecting deployment configuration
    deployments = {}
    repolists = {}
    repoindex = Repoindex()
    for deployment_name, deployment_settings in config.get('deployments', {}).items():
        repos = deployment_settings.get('repos')

        if repos is None:
            continue

        deployments[deployment_name] = {'target': deployment_settings.get('target'), 'defaults': deployment_settings.get('defaults', {})}
        if deployment_name not in repolists.keys():
            repolists[deployment_name] = {}
        repolists[deployment_name].update(repos)

    # updating caches
    for deployment_name, repolist in Helper.sorted_dict(repolists).items():
        for repoid, repo_settings in Helper.sorted_dict(repolist).items():
            repo_name = repo_settings.get('name', repoid)
            repo_defaults = repo_settings.get('defaults', {})
            branches = repo_settings.get('branches')
            if branches is None:
                logger.info('Skipping repo %s of deployment definition %s, is doesn\'t have any branches defined', repo_name,
                            deployment_name)
                continue

            # adding repo to repoindex
            repo = Repo()
            repo['name'] = repo_name
            repo['defaults'] = repo_defaults
            repo['target'] = deployments[deployment_name].get('target')
            repo.add_branches(branches, deployments[deployment_name])
            repoindex.add_repo(deployment_name, repoid, repo)

            cache_name = repoindex[deployment_name][repoid].get('defaults').get('cache')
            cache_settings = config.get('settings').get('caches').get(cache_name)
            cache = Cache(name=cache_name, settings=cache_settings)
            cache.init()
            updated_refs = cache.update(repoindex[deployment_name][repoid])

            if updated_refs:
                repoindex[deployment_name][repoid]['updates'] = {'updated_refs': updated_refs, 'cache': cache}
            elif sync_all:
                repoindex[deployment_name][repoid]['updates'] = {'cache': cache}

    repoindex.sync_repos(sync_all)

    # Everything is done, closing now
    logger.debug('Shutting down..')


if __name__ == '__main__':
    exit(main())
