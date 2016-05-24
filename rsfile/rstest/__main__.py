
from rsfile.rstest.test_rsfile_streams import test_main as streams_test_main
from rsfile.rstest.test_rsfile_locking import test_main as locking_test_main


if __name__ == '__main__':
    # these tests will all stop as soon as one of their suites fails
    streams_test_main()
    locking_test_main()

