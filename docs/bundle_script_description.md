# Scripts to help with the running of integtests

The following scripts are intended to help developers find and run _integtests_ (regression and integration tests) in all repositories:

* `list_repos_with_integtests.sh`
* `list_available_integtests.sh`
* `dunedaq_integtest_bundle.sh`

All of these scripts support the "`--help`" command-line option to provide information on how they should be run. Here is what is currently shown for each of the three scripts:

### list_repos_with_integtests.sh --help 

```
Usage: list_repos_with_integtests.sh [optional "local" keyword]
  Lists the software repositories that have integration tests (integtests) in them.
  Searches the base releases, local install dir, and local sourcecode dir,
  unless "local" is passed as an argument. In that case, only the local
  install and sourcecode directories are searched.
```

### list_available_integtests.sh --help

```
Usage: list_available_integtests.sh [optional list of repo names|local|all]
  e.g. list_available_integtests.sh daqsystemtest
  If no repo name is specified, integtests for all repos are listed.
  If a special repo name of "local" is specified, only integtests for repos
      in the local software area are listed.
  If a special repo name of "all" is specified, integtests for all repos are listed.
```

### dunedaq_integtest_bundle.sh --help

```
Usage:
dunedaq_integtest_bundle.sh [option(s)]

Options:
    -h, --help : prints out usage information
    -r <the list of repositories for which integtests will be run>
       - this can be the name of a single repo
       - it can be a pipe-delimited string with a list of repos, e.g. 'dfmodules|trigger'
       - it can have the special value of "all" - integtests in all repos will be run
       - it can have the special value of "local" - integtests in locally-cloned repos will be run
    -k, --include <pipe-delimited string to select the tests that will be run ('egrep -i' match to test name)>
    -x, --exclude <pipe-delimited string to specify tests to be excluded ('egrep -i' match to test name)>
    -n <number of times to run each individual test, default=1>
    -N <number of times to run the full set of selected tests, default=1>
    --stop-on-failure : causes the script to stop when one of the integtests reports a failure
    --concise-output : suppresses run control and DAQApp messages in order to focus on test results
    --tmpdir : specifies a root directory to use for test output, e.g. a directory instead of '/tmp'
    --list-only : list the tests that match the requested patterns without running them
```
