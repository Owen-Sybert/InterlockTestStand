from pathlib import Path

def getPiHomeDir():
    return Path.home()

def getDefaultsDir():
    home = getPiHomeDir()
    defaults_dir = home / "TestStand" / "Defaults"
    defaults_dir.mkdir(parents=True, exist_ok=True)
    return defaults_dir

def getSavedTestsDir():
    home = getPiHomeDir()
    saved_tests_dir = home / "TestStand" / "SavedTests"
    saved_tests_dir.mkdir(parents=True, exist_ok=True)
    return saved_tests_dir

def getResultsDir():
    home = getPiHomeDir()
    results_dir = home / "TestStand" / "Results"
    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir
