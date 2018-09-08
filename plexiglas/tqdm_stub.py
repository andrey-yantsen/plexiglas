import sys
from time import time

from . import log

if sys.stderr.isatty():
    from tqdm import tqdm
else:
    from humanfriendly import format_size, format_timespan
    from math import floor

    class tqdm:
        def __init__(self, total, desc, initial, **kwargs):
            self.total = total
            self.desc = desc
            self.pos = initial
            self.last_report_str = ''
            self._last_report_ts = 0
            self._min_report_interval = int(kwargs.pop('min_report_interval', 20))
            self._begin = None

        def update(self, l):
            if self._begin is None:
                self._begin = time()
            self.pos += l
            progress = floor(self.pos) / self.total * 100
            if progress < 99:
                progress = round(progress)
            else:
                progress = floor(progress)
            report = '%s downloaded %d%%' % (self.desc, progress)
            if self.last_report_str != report and time() - self._last_report_ts >= self._min_report_interval:
                self.last_report_str = report
                self._last_report_ts = time()

                appendix = ' (%s out of %s)' % (format_size(self.pos, binary=True),
                                                format_size(self.total, binary=True))

                log.info(report + appendix)

        def close(self):
            report = '%s download complete after %s' % (self.desc, format_timespan(time() - self._begin))
            log.info(report)
