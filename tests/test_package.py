import kiekkokeskus


def test_package_imports() -> None:
    assert isinstance(kiekkokeskus.__version__, str)
    assert kiekkokeskus.__version__ == "0.1.0"
