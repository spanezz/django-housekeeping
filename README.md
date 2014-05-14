# django-housekeeping

Pluggable housekeeping framework for Django sites.

django\_housekeeping provides a management command that finds and run tasks
defined by your Django apps.

Tasks can declare dependencies on each other, run in multiple stages and
provide infrastructure that other tasks can use.

## Example

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

