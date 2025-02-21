import sys, time


def spinner():
    while True:
        yield from "|/-\\"


spinner = spinner()

while True:
    sys.stdout.write(next(spinner))
    sys.stdout.flush()
    time.sleep(0.1)
    sys.stdout.write("\r")
