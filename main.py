#!/usr/bin/env python3


from sys import argv
import re

import pycurl
import curl


PATCHES = \
    [
        {
            "name": "aufs",
            "meta-url": "http://sources.gentoo.org/cgi-bin/viewvc.cgi/gentoo-x86/sys-kernel/aufs-sources/",
            "meta-pattern": "aufs-sources-${kseries}.\d+.ebuild",
            "url": "http://sources.gentoo.org/cgi-bin/viewvc.cgi/gentoo-x86/sys-kernel/aufs-sources/${eval-meta-pattern}",
            "pattern": '(?<=AUFS_VERSION=).*'
        },
        {
            "name": "ck",  # ck != bfs, ck is a superset of bfs
            "url": "http://ck.kolivas.org/patches/3.0/${kseries}",
            "pattern": "${kseries}-ck[0-9]"
        },
        {
            "name": "genpatches",
            "url": "http://dev.gentoo.org/~mpagano/genpatches/tarballs/",
            "pattern": "genpatches-${kseries}-\d+"
        },
        {
            "name": "reiser4",
            "url": "http://sourceforge.net/projects/reiser4/files/reiser4-for-linux-3.x/",
            "pattern": "reiser4-for-${kseries}(?:.\d+)?.patch.gz"
        },
        {
            "name": "tuxonice",
            "url": "http://tuxonice.nigelcunningham.com.au/downloads/all/",
            "pattern": "tuxonice-for-linux(?:-head)?-${kseries}\.\d+-\d+-\d+-\d+"
        },
        {
            "name": "uksm",
            "meta-meta-url": "http://kerneldedup.org/projects/uksm/download/",
            "meta-meta-pattern": "0\.1\.\d+\.(?:\d+)?",
            "meta-url": "http://kerneldedup.org/projects/uksm/download/",
            "meta-pattern": "(?<=http://kerneldedup.org/projects/uksm/download/uksm/${eval-meta-meta-pattern}/#wpfb-cat-)\d+",
            "url": "http://kerneldedup.org/wp-content/plugins/wp-filebase/wpfb-ajax.php?action=tree&type=browser&base=${eval-meta-pattern}",
            "pattern": "uksm-0\.1\.\d+\.(?:\d+)?-for-v${kseries}.ge.\d+.patch",
        },
    ]


def http_get(url):
    _curl = curl.Curl()
    content = _curl.get(url).decode("UTF-8")
    response_code = _curl.get_info(pycurl.RESPONSE_CODE)
    if response_code == 200:
        return content
    elif response_code == 404:
        return None
    else:
        raise RuntimeError("HTTP Error: %d" % response_code)


class VersionNumber():

    def __init__(self, version_string):
        from distutils.version import LooseVersion
        self._verstr = version_string

        for idx, val in enumerate(version_string):
            # the problem is that we can not compare two patches
            # differently named but actually just the same thing:
            #
            # patch-3.1.2 and patch-experimental-4.0.1
            #
            # So, I assume different branches of a patch never use the same
            # version number. So just ignore until the first number,
            # but we also need to keep the original version string for output.

            if val.isdigit():
                self._verobj = LooseVersion(version_string[idx:])

    def __gt__(self, other):
        return self._verobj > other._verobj

    def __eq__(self, other):
        return self._verobj == other._verobj

    def __lt__(self, other):
        return self._verobj < other._verobj

    def __str__(self):
        return self._verstr


def latest_version(versions_list):
    versions_list = list(set(versions_list))

    versions = []

    for version in versions_list:
        versions.append(VersionNumber(version))
    return str(max(versions))


class ReplaceTable():

    def __init__(self):
        self._table = {}

    def add(self, k, v):
        self._table[k] = v

    def replace(self, string):
        for k, v in self._table.items():
            string = string.replace("${%s}" % k, v)
        return string


if __name__ == "__main__":
    if len(argv) < 2:
        print("Usage: %s [LINUX KERNEL SERIES]" % argv[0])
        print("Example: %s 3.10" % argv[0])
        exit()

    for patch in PATCHES:
        print("checking %s..." % patch["name"], end="")

        # init replace table
        table = ReplaceTable()
        table.add("kseries", argv[1])

        # how many levels?
        level = 0
        for key in patch.keys():
            _level = key.count("meta")
            if _level > level:
                level = _level

        # perform each level
        while level >= 0:
            # replace
            for k, v in patch.items():
                patch[k] = table.replace(v)

            prefix = "%s-" % "meta" * level
            content = http_get(patch[prefix + "url"])
            if not content:
                print("unsupported (404)")
                break
            matched = re.findall(patch[prefix + "pattern"], content)
            if not matched:
                print("unsupported (no matched item)")
                break
            version = latest_version(matched)
            table.add("eval-%spattern" % prefix, version)
            if level == 0:
                print(version)

            level -= 1
