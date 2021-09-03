import click
from doozerlib.cli import cli
from doozerlib import util


@cli.command("release:calc-upgrade-tests", short_help="Returns a list of upgrade tests to run for a release")
@click.option("--version", metavar='NEW_VER', required=True,
              help="The release to calculate upgrade tests for (e.g. 4.5.4 or 4.6.0..hotfix)")
@click.option("-a", "--arch",
              metavar='ARCH',
              default='x86_64')
def release_calc_upgrade_tests(version, arch, graph_url, graph_content_stable, graph_content_candidate):
    major, minor = util.extract_version_fields(version, at_least=2)[:2]
    arch = util.go_arch_for_brew_arch(arch)

    # Get the names of channels we need to analyze
    candidate_channel = util.get_cincinnati_channels(major, minor)[0]
    prev_candidate_channel = util.get_cincinnati_channels(major, minor - 1)[0]

    def sort_semver(versions):
        return sorted(versions, key=functools.cmp_to_key(semver.compare), reverse=True)

    def get_channel_versions(channel):
        """
        Queries Cincinnati and returns a tuple containing:
        1. All of the versions in the specified channel in decending order (e.g. 4.6.26, ... ,4.6.1)
        2. A map of the edges associated with each version (e.g. map['4.6.1'] -> [ '4.6.2', '4.6.3', ... ]
        :param channel: The name of the channel to inspect
        :return: (versions, edge_map)
        """
        content = None

        if channel == 'stable' and graph_content_stable:
            # permit command line override
            with open(graph_content_stable, 'r') as f:
                content = f.read()

        if channel != 'stable' and graph_content_candidate:
            # permit command line override
            with open(graph_content_candidate, 'r') as f:
                content = f.read()

        if not content:
            url = f'{graph_url}?arch={arch}&channel={channel}'
            req = urllib.request.Request(url)
            req.add_header('Accept', 'application/json')
            content = exectools.urlopen_assert(req).read()

        graph = json.loads(content)
        versions = [node['version'] for node in graph['nodes']]
        descending_versions = sort_semver(versions)

        edges: Dict[str, List] = dict()
        for v in versions:
            # Ensure there is at least an empty list for all versions.
            edges[v] = []

        for edge_def in graph['edges']:
            # edge_def example [22, 20] where is number is an offset into versions
            from_ver = versions[edge_def[0]]
            to_ver = versions[edge_def[1]]
            edges[from_ver].append(to_ver)

        return descending_versions, edges
