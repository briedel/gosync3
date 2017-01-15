import subprocess
import threading
from logging import getLogger

LOG = getLogger('rsync')


# Taken from 
# http://www.zultron.com/2012/06/python-subprocess-example-running-a-background-subprocess-with-non-blocking-output-processing/

class rsync(subprocess.Popen):
    """
    Run rsync as a subprocess sending output to a logger.
    This class subclasses subprocess.Popen
    """

    def log_thread(self, pipe, logger):
        """
        Start a thread logging output from pipe
        """

        # thread function to log subprocess output
        def log_output(out, logger):
            for line in iter(out.readline, b''):
                logger(line.rstrip('\n'))

        # start thread
        t = threading.Thread(target=log_output,
                             args=(pipe, logger))
        # thread dies with the program
        t.daemon = True
        t.start()

    def __init__(self, src, dest,
                 delete=False,
                 dry_run=False):
        # construct the command line
        if not delete and not dry_run:
            cmd = ['/usr/bin/rsync', '-rlptvHa',
                   '--ignore-times',
                   src, dest]
        elif delete and not dry_run:
            cmd = ['/usr/bin/rsync', '-rlptvHa',
                   '--ignore-times',
                   '--delete',
                   src, dest]
        elif not delete and dry_run:
            cmd = ['/usr/bin/rsync', '-rlptvHa',
                   '--dry-run',
                   '--ignore-times',
                   src, dest]
        elif delete and dry_run:
            cmd = ['/usr/bin/rsync', '-rlptvHa',
                   '--dry-run',
                   '--ignore-times',
                   '--delete',
                   src, dest]


        # spawn the rsync process
        super(rsync, self).__init__(
            cmd, shell=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            bufsize=1, close_fds='posix')

        LOG.debug("Started rsync subprocess, pid %s" % self.pid)
        LOG.debug("Command:  '%s'" % "','".join(cmd))

        # start stdout and stderr logging threads
        self.log_thread(self.stdout,LOG.info)
        self.log_thread(self.stderr,LOG.warn)