# django-housekeeping

Pluggable housekeeping framework for Django sites.

django\_housekeeping provides a management command that finds and run tasks
defined by your Django apps.

Tasks can declare dependencies on each other, run in multiple stages and
provide infrastructure that other tasks can use.

## Example

### Code

    # myapp/housekeeping.py:
    import django_housekeeping as hk

    # Order of execution of the housekeeping stages defined in this module
    STAGES = ["backup", "main"]

    class BackupDB(hk.Task):
        """
        Backup of the whole database
        """
        def run_backup(self, stage):
            # ...backup the database...

    class DailyAggregates(hk.Task):
        """
        Compute daily aggregates
        """
        def run_main(self, stage):
            # ...compute...

    class MonthlyAggregates(hk.Task):
        """
        Compute monthly aggregates
        """
        DEPENDS = [DailyAggregates]

        def run_main(self, stage):
            # ...compute monthly averages from daily averages...

### Execution

django\_housekeeping adds a `housekeeping` management command that runs all
tasks. You can schedule `./manage.py housekeeping` to run once a day to
automate the site maintenance.

To run the housekeeping tasks, just run:

    $ ./manage.py housekeeping

To see the order in which the tasks would be run, use:

    $ ./manage.py housekeeping --list

You can use `--logfile` to write a verbose log file, or run only some tasks
using `--include` and `--exclude`. See `./manage.py housekeeping --help` for
details.


## Configuration

There is currently only one configuration key for `settings.py`:
`HOUSEKEEPING_ROOT`. Set it to a string with a directory pathname, and it is
the same as if `--outdir=OUTDIR` is set.

Example:

	HOUSEKEEPING_ROOT = "/srv/mysite/housekeeping/"
