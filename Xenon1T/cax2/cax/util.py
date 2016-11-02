import zlib
import uuid


def chunks(l, n):
    """
    Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i + n]


def generate_uuid():
    return str(uuid()).replace('-', '').lower()


def adler32(file):
    """
    An Adler-32 checksum is obtained by
    calculating two 16-bit checksums A and B
    and concatenating their bits into a 32-bit integer.
    A is the sum of all bytes in the stream plus one,
    and B is the sum of the individual values of A from each step.

    Args:
        file: Path to fil

    Returns:
        checksum: Hexified string, padded to 8 values.
    """

    # adler starting value is _not_ 0
    adler = 1L

    try:
        openFile = open(file, 'rb')
        for line in openFile:
            adler = zlib.adler32(line, adler)
    except:
        raise Exception('FATAL - could not get checksum of file %s' % file)

    # backflip on 32bit
    if adler < 0:
        adler = adler + 2 ** 32
    checksum = str('%08x' % adler)
    return checksum
