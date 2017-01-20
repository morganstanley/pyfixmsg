def pytest_addoption(parser):
    parser.addoption("--spec", action='store')
    parser.addoption("--profile", action='store_true')
