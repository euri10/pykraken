import re

from .exceptions import BadParamterError


def commasep(entryList, sep=','):
    return sep.join(entryList)

def parseOTime(timestring):

    a = re.match('^\+\d+', timestring )
    b = re.match('^\d+', timestring)
    if a or b:
        return
    else:
        raise BadParamterError('+<n> = schedule start time <n> seconds from now <n> = unix timestamp of start time')

